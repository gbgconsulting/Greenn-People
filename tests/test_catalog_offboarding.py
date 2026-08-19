"""T035: soft-delete de catálogos, unicidade entre ativos e offboarding."""

from __future__ import annotations

import pytest
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.accounts.models import CustomUser
from apps.accounts.services.offboarding import reassign_direct_reports
from apps.audit.models import AuditLog
from apps.competencies.models import Competencia, Escala
from apps.organization.models import Area, Cargo
from tests.conftest import DEFAULT_PASSWORD


def _soft_delete(instance) -> None:
    instance.is_active = False
    instance.save(update_fields=['is_active', 'updated_at'])


def _assert_duplicate_active_nome_rejected(model, *, nome: str, **extra):
    """Unicidade condicional: segundo ativo com o mesmo nome deve falhar."""
    model.objects.create(nome=nome, **extra)
    with pytest.raises((IntegrityError, ValidationError)):
        with transaction.atomic():
            duplicate = model(nome=nome, **extra)
            try:
                duplicate.full_clean()
            except ValidationError:
                raise
            duplicate.save()


# --- Soft-delete + FK histórica ---


@pytest.mark.django_db
def test_soft_delete_area_em_uso_preserva_fk(colaborador, area):
    """Área em uso: soft-delete → inativa; FK histórica do usuário intacta."""
    assert colaborador.area_id == area.pk

    _soft_delete(area)

    area.refresh_from_db()
    colaborador.refresh_from_db()
    assert area.is_active is False
    assert colaborador.area_id == area.pk
    assert Area.objects.filter(pk=area.pk).exists()


@pytest.mark.django_db
def test_soft_delete_cargo_em_uso_preserva_fk(colaborador, cargo_colab):
    """Cargo em uso: soft-delete → inativo; FK histórica intacta."""
    assert colaborador.cargo_id == cargo_colab.pk

    _soft_delete(cargo_colab)

    cargo_colab.refresh_from_db()
    colaborador.refresh_from_db()
    assert cargo_colab.is_active is False
    assert colaborador.cargo_id == cargo_colab.pk


@pytest.mark.django_db
def test_soft_delete_escala_em_uso_preserva_fk(db):
    """Escala referenciada por Competência: soft-delete sem hard-delete."""
    escala = Escala.objects.create(
        nome='Escala Soft',
        valor_minimo=1,
        valor_maximo=5,
    )
    competencia = Competencia.objects.create(
        nome='Competência Soft',
        tipo=Competencia.Tipo.TECNICA,
        escala=escala,
    )

    _soft_delete(escala)

    escala.refresh_from_db()
    competencia.refresh_from_db()
    assert escala.is_active is False
    assert competencia.escala_id == escala.pk


# --- Unicidade entre ativos ---


@pytest.mark.django_db
def test_segunda_area_ativa_mesmo_nome_rejeitada(db):
    """Criar segunda Área ativa com o mesmo nome → rejeição."""
    _assert_duplicate_active_nome_rejected(Area, nome='Área Duplicada')


@pytest.mark.django_db
def test_segunda_cargo_ativo_mesmo_nome_rejeitado(db):
    _assert_duplicate_active_nome_rejected(
        Cargo,
        nome='Cargo Duplicado',
        nivel=1,
    )


@pytest.mark.django_db
def test_segunda_escala_ativa_mesmo_nome_rejeitada(db):
    _assert_duplicate_active_nome_rejected(
        Escala,
        nome='Escala Duplicada',
        valor_minimo=1,
        valor_maximo=5,
    )


@pytest.mark.django_db
def test_segunda_competencia_ativa_mesmo_nome_rejeitada(db):
    escala = Escala.objects.create(
        nome='Escala Unicidade',
        valor_minimo=1,
        valor_maximo=5,
    )
    _assert_duplicate_active_nome_rejected(
        Competencia,
        nome='Competência Duplicada',
        tipo=Competencia.Tipo.COMPORTAMENTAL,
        escala=escala,
    )


@pytest.mark.django_db
def test_nome_de_area_inativa_pode_ser_reutilizado(db):
    """Nome de registro inativo pode ser reutilizado por um novo ativo."""
    antiga = Area.objects.create(nome='Nome Reutilizável')
    _soft_delete(antiga)

    nova = Area.objects.create(nome='Nome Reutilizável')
    assert nova.is_active is True
    assert nova.pk != antiga.pk
    assert Area.objects.filter(nome='Nome Reutilizável', is_active=True).count() == 1


@pytest.mark.django_db
def test_nome_de_escala_inativa_pode_ser_reutilizado(db):
    antiga = Escala.objects.create(
        nome='Escala Reutilizável',
        valor_minimo=1,
        valor_maximo=5,
    )
    _soft_delete(antiga)

    nova = Escala.objects.create(
        nome='Escala Reutilizável',
        valor_minimo=0,
        valor_maximo=10,
    )
    assert nova.is_active is True
    assert nova.pk != antiga.pk


# --- Offboarding: bloqueio + reatribuição em lote ---


@pytest.mark.django_db
def test_desativar_gestor_com_liderados_falha(lider, colaborador):
    """Gestor com liderados ativos: desativação → ValidationError."""
    assert colaborador.line_manager_id == lider.pk
    assert lider.has_active_direct_reports()

    lider.is_active = False
    with pytest.raises(ValidationError) as exc_info:
        lider.save()

    lider.refresh_from_db()
    assert lider.is_active is True
    assert 'is_active' in exc_info.value.message_dict


@pytest.mark.django_db
def test_reatribuicao_em_lote_depois_desativacao_ok(
    lider,
    colaborador,
    admin,
    area,
    cargo_lider,
):
    """Após reassign completo (0 liderados ativos), desativação sucede."""
    novo_gestor = CustomUser.objects.create_user(
        email='novo.gestor@test.greenn.com.br',
        password=DEFAULT_PASSWORD,
        nome='Novo Gestor',
        cargo=cargo_lider,
        area=area,
        line_manager=admin,
        email_confirmado_em=timezone.now(),
    )
    segundo = CustomUser.objects.create_user(
        email='colab2@test.greenn.com.br',
        password=DEFAULT_PASSWORD,
        nome='Colaborador Dois',
        cargo=colaborador.cargo,
        area=area,
        line_manager=lider,
        email_confirmado_em=timezone.now(),
    )

    before_audit = AuditLog.objects.filter(
        campo='line_manager_id',
        acao=AuditLog.Acao.UPDATE,
    ).count()

    count = reassign_direct_reports(
        from_manager=lider,
        to_manager=novo_gestor,
        actor=admin,
    )

    assert count == 2
    colaborador.refresh_from_db()
    segundo.refresh_from_db()
    assert colaborador.line_manager_id == novo_gestor.pk
    assert segundo.line_manager_id == novo_gestor.pk
    assert not lider.has_active_direct_reports()

    after_audit = AuditLog.objects.filter(
        campo='line_manager_id',
        acao=AuditLog.Acao.UPDATE,
    ).count()
    assert after_audit >= before_audit + 2
    recent = (
        AuditLog.objects.filter(
            campo='line_manager_id',
            acao=AuditLog.Acao.UPDATE,
            usuario_id=admin.pk,
        )
        .order_by('-created_at')[:2]
    )
    assert recent.count() == 2

    lider.is_active = False
    lider.save()
    lider.refresh_from_db()
    assert lider.is_active is False


@pytest.mark.django_db
def test_to_manager_inativo_rejeita_liderados_inalterados(
    lider,
    colaborador,
    admin,
    area,
    cargo_lider,
):
    """to_manager inativo → ValidationError; liderados permanecem no gestor."""
    inativo = CustomUser.objects.create_user(
        email='gestor.inativo@test.greenn.com.br',
        password=DEFAULT_PASSWORD,
        nome='Gestor Inativo',
        cargo=cargo_lider,
        area=area,
        line_manager=admin,
        email_confirmado_em=timezone.now(),
    )
    inativo.is_active = False
    inativo.save(update_fields=['is_active'])

    with pytest.raises(ValidationError):
        reassign_direct_reports(
            from_manager=lider,
            to_manager=inativo,
            actor=admin,
        )

    colaborador.refresh_from_db()
    assert colaborador.line_manager_id == lider.pk
    assert lider.has_active_direct_reports()


@pytest.mark.django_db
def test_reatribuicao_mesmo_gestor_rejeitada(lider, colaborador, admin):
    """to_manager == from_manager → ValidationError."""
    with pytest.raises(ValidationError):
        reassign_direct_reports(
            from_manager=lider,
            to_manager=lider,
            actor=admin,
        )

    colaborador.refresh_from_db()
    assert colaborador.line_manager_id == lider.pk


@pytest.mark.django_db
def test_reatribuicao_nao_admin_permission_denied(
    lider,
    colaborador,
    area,
    cargo_lider,
    admin,
):
    """Ator sem is_admin → PermissionDenied; liderados intactos."""
    outro = CustomUser.objects.create_user(
        email='lider.destino@test.greenn.com.br',
        password=DEFAULT_PASSWORD,
        nome='Líder Destino',
        cargo=cargo_lider,
        area=area,
        line_manager=admin,
        email_confirmado_em=timezone.now(),
    )

    with pytest.raises(PermissionDenied):
        reassign_direct_reports(
            from_manager=lider,
            to_manager=outro,
            actor=lider,
        )

    colaborador.refresh_from_db()
    assert colaborador.line_manager_id == lider.pk
