"""T032: pós-reprovação — etapa inalterada, reopen, irmãos intactos, regra 100%."""

from __future__ import annotations

from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError

from apps.cycles.exceptions import StageTransitionError
from apps.cycles.services.stage import advance_stage, can_advance
from apps.goals.models import Meta
from apps.goals.services.approval import (
    approve_meta,
    approve_resultado,
    reject_meta,
    reject_resultado,
)
from apps.reviews.models import Avaliacao


def _set_etapa(avaliacao: Avaliacao, etapa: str) -> Avaliacao:
    avaliacao.etapa = etapa
    avaliacao.save(update_fields=['etapa', 'updated_at'])
    return avaliacao


# --- reject_meta: etapa inalterada + irmãos intactos ---


@pytest.mark.django_db
def test_reject_meta_nao_altera_etapa(avaliacao, meta, lider):
    _set_etapa(avaliacao, Avaliacao.Etapa.APROVACAO_METAS)
    etapa_antes = avaliacao.etapa

    reject_meta(meta, lider)

    avaliacao.refresh_from_db()
    meta.refresh_from_db()
    assert avaliacao.etapa == etapa_antes == Avaliacao.Etapa.APROVACAO_METAS
    assert meta.status == Meta.Status.REPROVADA


@pytest.mark.django_db
def test_reject_meta_irmaos_aprovados_intactos(avaliacao, metas, lider):
    """Reprovar 1 de N: N−1 aprovadas permanecem; etapa não muda."""
    meta_a, meta_b = metas
    _set_etapa(avaliacao, Avaliacao.Etapa.APROVACAO_METAS)

    approve_meta(meta_a, lider)
    reject_meta(meta_b, lider)

    meta_a.refresh_from_db()
    meta_b.refresh_from_db()
    avaliacao.refresh_from_db()

    assert meta_a.status == Meta.Status.APROVADA
    assert meta_b.status == Meta.Status.REPROVADA
    assert avaliacao.etapa == Avaliacao.Etapa.APROVACAO_METAS


# --- reopen: caminho acionável ---


@pytest.mark.django_db
def test_reopen_meta_reprovada_volta_pendente(avaliacao, meta, lider):
    _set_etapa(avaliacao, Avaliacao.Etapa.APROVACAO_METAS)
    reject_meta(meta, lider)
    meta.refresh_from_db()

    meta.reopen()
    meta.save(update_fields=['status', 'updated_at'])
    meta.refresh_from_db()
    avaliacao.refresh_from_db()

    assert meta.status == Meta.Status.PENDENTE
    assert avaliacao.etapa == Avaliacao.Etapa.APROVACAO_METAS


@pytest.mark.django_db
def test_reopen_meta_nao_reprovada_levanta_validation_error(meta):
    assert meta.status == Meta.Status.PENDENTE
    with pytest.raises(ValidationError):
        meta.reopen()


@pytest.mark.django_db
def test_reopen_nao_altera_status_de_irmaos(avaliacao, metas, lider):
    meta_a, meta_b = metas
    _set_etapa(avaliacao, Avaliacao.Etapa.APROVACAO_METAS)
    approve_meta(meta_a, lider)
    reject_meta(meta_b, lider)

    meta_b.refresh_from_db()
    meta_b.reopen()
    meta_b.save(update_fields=['status', 'updated_at'])

    meta_a.refresh_from_db()
    meta_b.refresh_from_db()
    assert meta_a.status == Meta.Status.APROVADA
    assert meta_b.status == Meta.Status.PENDENTE


# --- regra 100%: bloqueio até todas aprovadas; depois avança ---


@pytest.mark.django_db
def test_apos_rejeicao_parcial_can_advance_bloqueado(avaliacao, metas, lider):
    meta_a, meta_b = metas
    _set_etapa(avaliacao, Avaliacao.Etapa.APROVACAO_METAS)
    approve_meta(meta_a, lider)
    reject_meta(meta_b, lider)

    ok, motivo = can_advance(avaliacao)
    assert ok is False
    assert 'aprovad' in motivo.lower()
    with pytest.raises(StageTransitionError):
        advance_stage(avaliacao, lider)
    avaliacao.refresh_from_db()
    assert avaliacao.etapa == Avaliacao.Etapa.APROVACAO_METAS


@pytest.mark.django_db
def test_apos_correcao_e_100_porcento_advance_stage_sucede(
    avaliacao,
    metas,
    lider,
):
    """Corrige → reopen → reaprova → 100% → advance_stage → resultados."""
    meta_a, meta_b = metas
    _set_etapa(avaliacao, Avaliacao.Etapa.APROVACAO_METAS)
    approve_meta(meta_a, lider)
    reject_meta(meta_b, lider)

    meta_b.refresh_from_db()
    meta_b.reopen()
    meta_b.save(update_fields=['status', 'updated_at'])
    approve_meta(meta_b, lider)

    ok, motivo = can_advance(avaliacao)
    assert ok is True
    assert motivo == ''

    advanced = advance_stage(avaliacao, lider)
    assert advanced.etapa == Avaliacao.Etapa.RESULTADOS


# --- reject_resultado / reopen_resultado ---


@pytest.mark.django_db
def test_reject_resultado_nao_altera_etapa(avaliacao, meta, lider):
    _set_etapa(avaliacao, Avaliacao.Etapa.APROVACAO_RESULTADOS)
    Meta.objects.filter(pk=meta.pk).update(
        status=Meta.Status.APROVADA,
        progresso=Decimal('50.00'),
        status_resultado=Meta.StatusResultado.PENDENTE,
    )
    meta.refresh_from_db()
    etapa_antes = avaliacao.etapa

    reject_resultado(meta, lider)

    avaliacao.refresh_from_db()
    meta.refresh_from_db()
    assert avaliacao.etapa == etapa_antes == Avaliacao.Etapa.APROVACAO_RESULTADOS
    assert meta.status_resultado == Meta.StatusResultado.REPROVADO


@pytest.mark.django_db
def test_reject_resultado_irmaos_aprovados_intactos(avaliacao, metas, lider):
    meta_a, meta_b = metas
    _set_etapa(avaliacao, Avaliacao.Etapa.APROVACAO_RESULTADOS)
    Meta.objects.filter(pk__in=[meta_a.pk, meta_b.pk]).update(
        status=Meta.Status.APROVADA,
        progresso=Decimal('60.00'),
        status_resultado=Meta.StatusResultado.PENDENTE,
    )
    meta_a.refresh_from_db()
    meta_b.refresh_from_db()

    approve_resultado(meta_a, lider)
    reject_resultado(meta_b, lider)

    meta_a.refresh_from_db()
    meta_b.refresh_from_db()
    avaliacao.refresh_from_db()

    assert meta_a.status_resultado == Meta.StatusResultado.APROVADO
    assert meta_b.status_resultado == Meta.StatusResultado.REPROVADO
    assert avaliacao.etapa == Avaliacao.Etapa.APROVACAO_RESULTADOS


@pytest.mark.django_db
def test_reopen_resultado_volta_pendente(avaliacao, meta, lider):
    _set_etapa(avaliacao, Avaliacao.Etapa.APROVACAO_RESULTADOS)
    Meta.objects.filter(pk=meta.pk).update(
        status=Meta.Status.APROVADA,
        progresso=Decimal('40.00'),
        status_resultado=Meta.StatusResultado.PENDENTE,
    )
    meta.refresh_from_db()
    reject_resultado(meta, lider)
    meta.refresh_from_db()

    meta.reopen_resultado()
    meta.save(update_fields=['status_resultado', 'updated_at'])
    meta.refresh_from_db()
    avaliacao.refresh_from_db()

    assert meta.status_resultado == Meta.StatusResultado.PENDENTE
    assert avaliacao.etapa == Avaliacao.Etapa.APROVACAO_RESULTADOS


@pytest.mark.django_db
def test_reopen_resultado_nao_reprovado_levanta_validation_error(meta):
    assert meta.status_resultado == Meta.StatusResultado.PENDENTE
    with pytest.raises(ValidationError):
        meta.reopen_resultado()
