"""Aderência por compliance — fórmula, população e estado neutro."""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.accounts.models import CustomUser
from apps.audit.models import AuditLog
from apps.dashboard.models import AderenciaSnapshot
from apps.dashboard.services.adherence import compute_adherence
from apps.dashboard.services.eligible_leaders import (
    leader_ids_with_team_in_ciclo,
)
from apps.dashboard.tasks import _leader_ids_for_ciclo, calculate_adherence_snapshot
from apps.reviews.models import Avaliacao

from .conftest import DEFAULT_PASSWORD, FIXTURE_DATA_ENTRADA


def _set_etapa(avaliacao: Avaliacao, etapa: str) -> Avaliacao:
    avaliacao.etapa = etapa
    avaliacao.save(update_fields=['etapa', 'updated_at'])
    return avaliacao


@pytest.mark.django_db
def test_compute_adherence_neutro_sem_obrigacoes(lider, colaborador, ciclo_aberto):
    """Início de ciclo sem ações nem pendências vencidas → neutro (NULL)."""
    del colaborador
    percentual, componentes = compute_adherence(lider.pk, ciclo_aberto.pk)
    assert percentual is None
    assert componentes['estado'] == 'neutro'
    assert componentes['aprovacoes']['total'] == 0
    assert componentes['aprovacoes']['percentual'] is None


@pytest.mark.django_db
def test_compute_adherence_nao_infla_100_sem_acoes(lider, colaborador, ciclo_aberto):
    """Regressão: 0/0 não deve inflar para 100%."""
    del colaborador
    percentual, _ = compute_adherence(lider.pk, ciclo_aberto.pk)
    assert percentual is None


@pytest.mark.django_db
def test_compute_adherence_baixa_apos_prazo_com_pendencia(
    lider,
    colaborador,
    ciclo_aberto,
    meta,
):
    """Após data_fim, pendência acionável entra no denominador."""
    _set_etapa(
        Avaliacao.objects.get(ciclo=ciclo_aberto, usuario=colaborador),
        Avaliacao.Etapa.APROVACAO_METAS,
    )
    ref = ciclo_aberto.data_fim + timedelta(days=1)
    percentual, componentes = compute_adherence(
        lider.pk,
        ciclo_aberto.pk,
        today=ref,
    )
    assert percentual == Decimal('0.00')
    assert componentes['aprovacoes']['total'] >= 1
    assert componentes['aprovacoes']['no_prazo'] == 0


@pytest.mark.django_db
def test_compute_adherence_neutro_antes_prazo_com_pendencia(
    lider,
    colaborador,
    ciclo_aberto,
    meta,
):
    """Antes de data_fim, pendência acionável não penaliza (neutro)."""
    _set_etapa(
        Avaliacao.objects.get(ciclo=ciclo_aberto, usuario=colaborador),
        Avaliacao.Etapa.APROVACAO_METAS,
    )
    ref = ciclo_aberto.data_fim
    percentual, componentes = compute_adherence(
        lider.pk,
        ciclo_aberto.pk,
        today=ref,
    )
    assert percentual is None
    assert componentes['estado'] == 'neutro'


@pytest.mark.django_db
def test_compute_adherence_conta_acao_no_prazo(
    lider,
    colaborador,
    ciclo_aberto,
    meta,
):
    """Aprovação registrada no prazo eleva o índice."""
    avaliacao = Avaliacao.objects.get(ciclo=ciclo_aberto, usuario=colaborador)
    _set_etapa(avaliacao, Avaliacao.Etapa.APROVACAO_METAS)
    AuditLog.objects.create(
        usuario=lider,
        acao=AuditLog.Acao.UPDATE,
        entity_type='reviews.Avaliacao',
        entity_id=avaliacao.pk,
        campo='etapa',
        valor_anterior=Avaliacao.Etapa.APROVACAO_METAS,
        valor_novo=Avaliacao.Etapa.RESULTADOS,
    )
    percentual, componentes = compute_adherence(lider.pk, ciclo_aberto.pk)
    assert percentual == Decimal('100.00')
    assert componentes['aprovacoes']['no_prazo'] == 1


@pytest.mark.django_db
def test_leader_ids_for_ciclo_exige_liderado_matriculado(
    lider,
    colaborador,
    ciclo_aberto,
    admin,
    area,
    cargo_lider,
):
    """Gestor sem liderado no ciclo não entra na população."""
    del colaborador
    sem_time_no_ciclo = CustomUser.objects.create_user(
        email='gestor.fora.ciclo@test.greenn.com.br',
        password=DEFAULT_PASSWORD,
        nome='Gestor Fora Ciclo',
        cargo=cargo_lider,
        area=area,
        line_manager=admin,
        data_entrada=FIXTURE_DATA_ENTRADA,
        email_confirmado_em=timezone.now(),
    )
    CustomUser.objects.create_user(
        email='colab.fora.ciclo@test.greenn.com.br',
        password=DEFAULT_PASSWORD,
        nome='Colab Fora Ciclo',
        cargo=cargo_lider,
        area=area,
        line_manager=sem_time_no_ciclo,
        data_entrada=FIXTURE_DATA_ENTRADA,
        email_confirmado_em=timezone.now(),
    )
    # Colaborador sem Avaliacao (não matriculado): criar ciclo separado sem open.
    assert lider.pk in leader_ids_with_team_in_ciclo(ciclo_aberto)
    assert sem_time_no_ciclo.pk not in leader_ids_with_team_in_ciclo(ciclo_aberto)
    assert _leader_ids_for_ciclo(ciclo_aberto) == leader_ids_with_team_in_ciclo(
        ciclo_aberto,
    )


@pytest.mark.django_db
def test_calculate_adherence_snapshot_remove_fora_ciclo(
    lider,
    ciclo_aberto,
    admin,
    area,
    cargo_lider,
):
    """Task remove snapshot de gestor sem time no ciclo."""
    gestor_fora = CustomUser.objects.create_user(
        email='snap.fora@test.greenn.com.br',
        password=DEFAULT_PASSWORD,
        nome='Snap Fora',
        cargo=cargo_lider,
        area=area,
        line_manager=admin,
        data_entrada=FIXTURE_DATA_ENTRADA,
        email_confirmado_em=timezone.now(),
    )
    AderenciaSnapshot.objects.create(
        lider=gestor_fora,
        ciclo=ciclo_aberto,
        percentual=Decimal('80.00'),
        componentes={},
        calculado_em=timezone.now(),
    )
    result = calculate_adherence_snapshot(gestor_fora.pk, ciclo_aberto.pk)
    assert 'sem time no ciclo' in result
    assert not AderenciaSnapshot.objects.filter(
        lider=gestor_fora,
        ciclo=ciclo_aberto,
    ).exists()


@pytest.mark.django_db
def test_aderencia_status_neutro_para_percentual_nulo():
    from apps.dashboard.views import aderencia_status

    assert aderencia_status(None) == 'neutro'
