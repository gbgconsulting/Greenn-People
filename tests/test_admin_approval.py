"""T034: aprovação admin + AuditLog.actor; líder fora do escopo negado."""

from __future__ import annotations

import pytest
from django.core.exceptions import PermissionDenied
from django.utils import timezone

from apps.accounts.models import CustomUser
from apps.audit.models import AuditLog
from apps.goals.models import Meta
from apps.goals.services.approval import approve_meta, reject_meta
from apps.reviews.models import Avaliacao
from tests.conftest import DEFAULT_PASSWORD


def _set_etapa(avaliacao: Avaliacao, etapa: str) -> Avaliacao:
    avaliacao.etapa = etapa
    avaliacao.save(update_fields=['etapa', 'updated_at'])
    return avaliacao


@pytest.fixture
def lider_outro(db, admin, area, cargo_lider) -> CustomUser:
    """Líder ativo que NÃO é o line_manager do colaborador das fixtures."""
    return CustomUser.objects.create_user(
        email='lider.outro@test.greenn.com.br',
        password=DEFAULT_PASSWORD,
        nome='Líder Fora do Escopo',
        cargo=cargo_lider,
        area=area,
        line_manager=admin,
        email_confirmado_em=timezone.now(),
    )


def _status_audit_logs(meta: Meta):
    return AuditLog.objects.filter(
        entity_type='goals.Meta',
        entity_id=meta.pk,
        campo='status',
        acao=AuditLog.Acao.UPDATE,
    ).order_by('-created_at')


# --- Admin override (FR-014) + ator real (FR-015) ---


@pytest.mark.django_db
def test_admin_approve_com_gestor_presente_status_e_audit_actor(
    avaliacao,
    meta,
    admin,
    lider,
):
    """Admin aprova com gestor presente → aprovada + AuditLog.actor = admin."""
    assert meta.usuario.line_manager_id == lider.pk
    assert not admin.is_anonymous
    _set_etapa(avaliacao, Avaliacao.Etapa.APROVACAO_METAS)

    before = _status_audit_logs(meta).count()
    result = approve_meta(meta, admin)

    assert result.status == Meta.Status.APROVADA
    meta.refresh_from_db()
    assert meta.status == Meta.Status.APROVADA

    logs = _status_audit_logs(meta)
    assert logs.count() == before + 1
    log = logs.first()
    assert log is not None
    assert log.usuario_id == admin.pk
    assert log.valor_anterior == Meta.Status.PENDENTE
    assert log.valor_novo == Meta.Status.APROVADA


@pytest.mark.django_db
def test_admin_reject_com_gestor_presente_audit_actor(
    avaliacao,
    meta,
    admin,
    lider,
):
    """Admin reprova com gestor presente → reprovada + AuditLog.actor = admin."""
    assert meta.usuario.line_manager_id == lider.pk
    _set_etapa(avaliacao, Avaliacao.Etapa.APROVACAO_METAS)

    before = _status_audit_logs(meta).count()
    result = reject_meta(meta, admin)

    assert result.status == Meta.Status.REPROVADA
    logs = _status_audit_logs(meta)
    assert logs.count() == before + 1
    assert logs.first().usuario_id == admin.pk


# --- Líder fora do escopo (FR-016) ---


@pytest.mark.django_db
def test_lider_fora_do_escopo_permission_denied(
    avaliacao,
    meta,
    lider_outro,
    lider,
):
    """Líder que não é line_manager → PermissionDenied; status intacto."""
    assert meta.usuario.line_manager_id == lider.pk
    assert lider_outro.pk != lider.pk
    _set_etapa(avaliacao, Avaliacao.Etapa.APROVACAO_METAS)

    before_logs = _status_audit_logs(meta).count()
    with pytest.raises(PermissionDenied):
        approve_meta(meta, lider_outro)

    meta.refresh_from_db()
    assert meta.status == Meta.Status.PENDENTE
    assert _status_audit_logs(meta).count() == before_logs


# --- Fluxo feliz do gestor direto ---


@pytest.mark.django_db
def test_lider_direto_pode_aprovar(avaliacao, meta, lider):
    """Line manager continua podendo aprovar (fluxo feliz)."""
    _set_etapa(avaliacao, Avaliacao.Etapa.APROVACAO_METAS)

    result = approve_meta(meta, lider)

    assert result.status == Meta.Status.APROVADA
    log = _status_audit_logs(meta).first()
    assert log is not None
    assert log.usuario_id == lider.pk


@pytest.mark.django_db
def test_aprovar_ja_aprovada_sem_audit_sucesso_falso(avaliacao, meta, admin):
    """Item já aprovado → PermissionDenied sem novo AuditLog de sucesso."""
    _set_etapa(avaliacao, Avaliacao.Etapa.APROVACAO_METAS)
    approve_meta(meta, admin)
    meta.refresh_from_db()
    before = _status_audit_logs(meta).count()

    with pytest.raises(PermissionDenied):
        approve_meta(meta, admin)

    assert _status_audit_logs(meta).count() == before
