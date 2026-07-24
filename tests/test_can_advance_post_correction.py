"""T011: can_advance / advance_stage exigem 100% aprovados + ≥1 meta após correções."""

from __future__ import annotations

from decimal import Decimal

import pytest

from apps.competencies.models import CargoCompetencia, Competencia, Escala
from apps.cycles.exceptions import StageTransitionError
from apps.cycles.services.stage import ETAPAS, advance_stage, can_advance
from apps.goals.models import Meta
from apps.reviews.models import Avaliacao

CANONICAL_ETAPAS = (
    'input_metas',
    'aprovacao_metas',
    'resultados',
    'aprovacao_resultados',
    'avaliacao',
    'feedback',
)


@pytest.mark.django_db
def test_etapas_canonica_inalterada():
    assert ETAPAS == CANONICAL_ETAPAS
    assert tuple(c.value for c in Avaliacao.Etapa) == CANONICAL_ETAPAS


@pytest.mark.django_db
def test_aprovacao_metas_bloqueia_sem_meta(avaliacao):
    avaliacao.etapa = Avaliacao.Etapa.APROVACAO_METAS
    avaliacao.save(update_fields=['etapa', 'updated_at'])

    ok, motivo = can_advance(avaliacao)
    assert ok is False
    assert 'meta' in motivo.lower()


@pytest.mark.django_db
def test_aprovacao_metas_bloqueia_com_reprovada_ou_pendente_pos_correcao(
    avaliacao,
    metas,
    lider,
):
    meta_a, meta_b = metas
    avaliacao.etapa = Avaliacao.Etapa.APROVACAO_METAS
    avaliacao.save(update_fields=['etapa', 'updated_at'])

    meta_a.status = Meta.Status.APROVADA
    meta_a.save(update_fields=['status', 'updated_at'])
    meta_b.status = Meta.Status.REPROVADA
    meta_b.save(update_fields=['status', 'updated_at'])

    ok, _ = can_advance(avaliacao)
    assert ok is False

    with pytest.raises(StageTransitionError):
        advance_stage(avaliacao, lider)

    # Correção elegível: reopen → pendente; avanço ainda bloqueado.
    meta_b.reopen()
    meta_b.save(update_fields=['status', 'updated_at'])
    assert meta_b.status == Meta.Status.PENDENTE

    ok, motivo = can_advance(avaliacao)
    assert ok is False
    assert 'aprovad' in motivo.lower()

    with pytest.raises(StageTransitionError):
        advance_stage(avaliacao, lider)


@pytest.mark.django_db
def test_aprovacao_metas_avanca_somente_com_100_porcento(
    avaliacao,
    metas,
    lider,
):
    meta_a, meta_b = metas
    avaliacao.etapa = Avaliacao.Etapa.APROVACAO_METAS
    avaliacao.save(update_fields=['etapa', 'updated_at'])

    Meta.objects.filter(pk__in=[meta_a.pk, meta_b.pk]).update(
        status=Meta.Status.APROVADA,
    )

    ok, motivo = can_advance(avaliacao)
    assert ok is True
    assert motivo == ''

    advanced = advance_stage(avaliacao, lider)
    assert advanced.etapa == Avaliacao.Etapa.RESULTADOS


@pytest.mark.django_db
def test_aprovacao_resultados_bloqueia_com_reprovado_ou_pendente_pos_correcao(
    avaliacao,
    metas,
    lider,
):
    meta_a, meta_b = metas
    avaliacao.etapa = Avaliacao.Etapa.APROVACAO_RESULTADOS
    avaliacao.save(update_fields=['etapa', 'updated_at'])

    Meta.objects.filter(pk__in=[meta_a.pk, meta_b.pk]).update(
        status=Meta.Status.APROVADA,
        progresso=Decimal('50.00'),
        status_resultado=Meta.StatusResultado.APROVADO,
    )
    meta_b.refresh_from_db()
    meta_b.status_resultado = Meta.StatusResultado.REPROVADO
    meta_b.save(update_fields=['status_resultado', 'updated_at'])

    ok, _ = can_advance(avaliacao)
    assert ok is False

    with pytest.raises(StageTransitionError):
        advance_stage(avaliacao, lider)

    meta_b.reopen_resultado()
    meta_b.save(update_fields=['status_resultado', 'updated_at'])
    assert meta_b.status_resultado == Meta.StatusResultado.PENDENTE

    ok, motivo = can_advance(avaliacao)
    assert ok is False
    assert 'aprovad' in motivo.lower()

    with pytest.raises(StageTransitionError):
        advance_stage(avaliacao, lider)


@pytest.mark.django_db
def test_aprovacao_resultados_avanca_somente_com_100_porcento(
    avaliacao,
    metas,
    lider,
    cargo_colab,
):
    meta_a, meta_b = metas
    avaliacao.etapa = Avaliacao.Etapa.APROVACAO_RESULTADOS
    avaliacao.save(update_fields=['etapa', 'updated_at'])

    Meta.objects.filter(pk__in=[meta_a.pk, meta_b.pk]).update(
        status=Meta.Status.APROVADA,
        progresso=Decimal('80.00'),
        status_resultado=Meta.StatusResultado.APROVADO,
    )

    escala = Escala.objects.create(
        nome='Escala T011',
        valor_minimo=1,
        valor_maximo=5,
    )
    competencia = Competencia.objects.create(
        nome='Competência T011',
        tipo=Competencia.Tipo.TECNICA,
        escala=escala,
    )
    CargoCompetencia.objects.create(
        cargo=cargo_colab,
        competencia=competencia,
        nivel_esperado=Decimal('3.00'),
        peso=Decimal('1.00'),
    )

    ok, motivo = can_advance(avaliacao)
    assert ok is True
    assert motivo == ''

    advanced = advance_stage(avaliacao, lider)
    assert advanced.etapa == Avaliacao.Etapa.AVALIACAO
