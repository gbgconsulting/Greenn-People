"""T031: can_advance / advance_stage com pré-condições inválidas."""

from __future__ import annotations

from decimal import Decimal

import pytest
from django.utils import timezone

from apps.competencies.models import CargoCompetencia, Competencia, Escala
from apps.cycles.exceptions import CycleClosedError, StageTransitionError
from apps.cycles.services.cycle import close_cycle
from apps.cycles.services.stage import advance_stage, can_advance
from apps.goals.models import Meta
from apps.reviews.models import Avaliacao, AvaliacaoCompetencia, Feedback


def _set_etapa(avaliacao: Avaliacao, etapa: str) -> Avaliacao:
    avaliacao.etapa = etapa
    avaliacao.save(update_fields=['etapa', 'updated_at'])
    return avaliacao


def _vincular_competencia(cargo) -> CargoCompetencia:
    escala = Escala.objects.create(
        nome='Escala Stage Machine',
        valor_minimo=1,
        valor_maximo=5,
    )
    competencia = Competencia.objects.create(
        nome='Competência Stage Machine',
        tipo=Competencia.Tipo.TECNICA,
        escala=escala,
    )
    return CargoCompetencia.objects.create(
        cargo=cargo,
        competencia=competencia,
        nivel_esperado=Decimal('3.00'),
        peso=Decimal('1.00'),
    )


def _assert_blocked(avaliacao: Avaliacao, actor, *, motivo_fragment: str | None = None):
    ok, motivo = can_advance(avaliacao)
    assert ok is False
    if motivo_fragment is not None:
        assert motivo_fragment.lower() in motivo.lower()
    with pytest.raises(StageTransitionError):
        advance_stage(avaliacao, actor)
    avaliacao.refresh_from_db()
    return motivo


# --- ciclo encerrado ---


@pytest.mark.django_db
def test_advance_stage_ciclo_encerrado_levanta_cycle_closed(
    avaliacao,
    meta,
    ciclo_aberto,
    lider,
):
    _set_etapa(avaliacao, Avaliacao.Etapa.INPUT_METAS)
    close_cycle(ciclo_aberto)
    avaliacao.refresh_from_db()

    ok, motivo = can_advance(avaliacao)
    assert ok is False
    assert 'encerrado' in motivo.lower()

    with pytest.raises(CycleClosedError):
        advance_stage(avaliacao, lider)


# --- input_metas ---


@pytest.mark.django_db
def test_input_metas_bloqueia_sem_meta(avaliacao, lider):
    _set_etapa(avaliacao, Avaliacao.Etapa.INPUT_METAS)
    _assert_blocked(avaliacao, lider, motivo_fragment='meta')
    assert avaliacao.etapa == Avaliacao.Etapa.INPUT_METAS


@pytest.mark.django_db
def test_input_metas_avanca_com_meta(avaliacao, meta, lider):
    _set_etapa(avaliacao, Avaliacao.Etapa.INPUT_METAS)
    ok, motivo = can_advance(avaliacao)
    assert ok is True
    assert motivo == ''

    advanced = advance_stage(avaliacao, lider)
    assert advanced.etapa == Avaliacao.Etapa.APROVACAO_METAS


# --- aprovacao_metas ---


@pytest.mark.django_db
def test_aprovacao_metas_bloqueia_sem_meta(avaliacao, lider):
    _set_etapa(avaliacao, Avaliacao.Etapa.APROVACAO_METAS)
    _assert_blocked(avaliacao, lider, motivo_fragment='meta')
    assert avaliacao.etapa == Avaliacao.Etapa.APROVACAO_METAS


@pytest.mark.django_db
def test_aprovacao_metas_bloqueia_sem_100_porcento(avaliacao, metas, lider):
    meta_a, meta_b = metas
    _set_etapa(avaliacao, Avaliacao.Etapa.APROVACAO_METAS)
    meta_a.status = Meta.Status.APROVADA
    meta_a.save(update_fields=['status', 'updated_at'])
    # meta_b permanece pendente

    _assert_blocked(avaliacao, lider, motivo_fragment='aprovad')
    assert avaliacao.etapa == Avaliacao.Etapa.APROVACAO_METAS


# --- resultados ---


@pytest.mark.django_db
def test_resultados_bloqueia_sem_progresso(avaliacao, meta, lider):
    _set_etapa(avaliacao, Avaliacao.Etapa.RESULTADOS)
    meta.status = Meta.Status.APROVADA
    meta.progresso = None
    meta.save(update_fields=['status', 'progresso', 'updated_at'])

    _assert_blocked(avaliacao, lider, motivo_fragment='progresso')
    assert avaliacao.etapa == Avaliacao.Etapa.RESULTADOS


@pytest.mark.django_db
def test_resultados_bloqueia_sem_metas_aprovadas(avaliacao, meta, lider):
    _set_etapa(avaliacao, Avaliacao.Etapa.RESULTADOS)
    # meta permanece pendente (não aprovada)
    _assert_blocked(avaliacao, lider, motivo_fragment='aprovad')
    assert avaliacao.etapa == Avaliacao.Etapa.RESULTADOS


# --- aprovacao_resultados ---


@pytest.mark.django_db
def test_aprovacao_resultados_bloqueia_sem_100_porcento(
    avaliacao,
    metas,
    lider,
    cargo_colab,
):
    meta_a, meta_b = metas
    _set_etapa(avaliacao, Avaliacao.Etapa.APROVACAO_RESULTADOS)
    _vincular_competencia(cargo_colab)

    Meta.objects.filter(pk=meta_a.pk).update(
        status=Meta.Status.APROVADA,
        progresso=Decimal('50.00'),
        status_resultado=Meta.StatusResultado.APROVADO,
    )
    Meta.objects.filter(pk=meta_b.pk).update(
        status=Meta.Status.APROVADA,
        progresso=Decimal('50.00'),
        status_resultado=Meta.StatusResultado.PENDENTE,
    )

    _assert_blocked(avaliacao, lider, motivo_fragment='aprovad')
    assert avaliacao.etapa == Avaliacao.Etapa.APROVACAO_RESULTADOS


@pytest.mark.django_db
def test_aprovacao_resultados_bloqueia_sem_cargo_competencias(
    avaliacao,
    meta,
    lider,
):
    _set_etapa(avaliacao, Avaliacao.Etapa.APROVACAO_RESULTADOS)
    meta.status = Meta.Status.APROVADA
    meta.progresso = Decimal('80.00')
    meta.status_resultado = Meta.StatusResultado.APROVADO
    meta.save(
        update_fields=['status', 'progresso', 'status_resultado', 'updated_at'],
    )
    # cargo do colaborador sem CargoCompetencia

    _assert_blocked(avaliacao, lider, motivo_fragment='compet')
    assert avaliacao.etapa == Avaliacao.Etapa.APROVACAO_RESULTADOS


# --- avaliacao ---


@pytest.mark.django_db
def test_avaliacao_bloqueia_sem_linhas_competencia(avaliacao, lider):
    _set_etapa(avaliacao, Avaliacao.Etapa.AVALIACAO)
    _assert_blocked(avaliacao, lider, motivo_fragment='compet')
    assert avaliacao.etapa == Avaliacao.Etapa.AVALIACAO


@pytest.mark.django_db
def test_avaliacao_bloqueia_sem_nota_lider(avaliacao, lider, cargo_colab):
    _set_etapa(avaliacao, Avaliacao.Etapa.AVALIACAO)
    cc = _vincular_competencia(cargo_colab)
    AvaliacaoCompetencia.objects.create(
        avaliacao=avaliacao,
        competencia=cc.competencia,
        peso_utilizado=cc.peso,
        nivel_esperado_utilizado=cc.nivel_esperado,
        nota_lider=None,
    )

    _assert_blocked(avaliacao, lider, motivo_fragment='nota')
    assert avaliacao.etapa == Avaliacao.Etapa.AVALIACAO


@pytest.mark.django_db
def test_avaliacao_bloqueia_sem_nota_final_lider(avaliacao, lider, cargo_colab):
    _set_etapa(avaliacao, Avaliacao.Etapa.AVALIACAO)
    cc = _vincular_competencia(cargo_colab)
    AvaliacaoCompetencia.objects.create(
        avaliacao=avaliacao,
        competencia=cc.competencia,
        peso_utilizado=cc.peso,
        nivel_esperado_utilizado=cc.nivel_esperado,
        nota_lider=Decimal('4.00'),
    )
    assert avaliacao.nota_final_lider is None

    _assert_blocked(avaliacao, lider, motivo_fragment='nota final')
    assert avaliacao.etapa == Avaliacao.Etapa.AVALIACAO


# --- feedback ---


@pytest.mark.django_db
def test_feedback_bloqueia_sem_feedback_lider(avaliacao, lider):
    _set_etapa(avaliacao, Avaliacao.Etapa.FEEDBACK)
    _assert_blocked(avaliacao, lider, motivo_fragment='feedback')
    assert avaliacao.etapa == Avaliacao.Etapa.FEEDBACK
    assert avaliacao.concluida is False


@pytest.mark.django_db
def test_feedback_bloqueia_sem_ciente_em(avaliacao, lider):
    _set_etapa(avaliacao, Avaliacao.Etapa.FEEDBACK)
    Feedback.objects.create(
        avaliacao=avaliacao,
        autor=lider,
        tipo=Feedback.Tipo.LIDER,
        conteudo='Feedback de teste sem ciência.',
        ciente_em=None,
    )

    _assert_blocked(avaliacao, lider, motivo_fragment='ciência')
    assert avaliacao.etapa == Avaliacao.Etapa.FEEDBACK
    assert avaliacao.concluida is False


@pytest.mark.django_db
def test_feedback_conclui_com_ciente_em(avaliacao, lider):
    _set_etapa(avaliacao, Avaliacao.Etapa.FEEDBACK)
    Feedback.objects.create(
        avaliacao=avaliacao,
        autor=lider,
        tipo=Feedback.Tipo.LIDER,
        conteudo='Feedback completo.',
        ciente_em=timezone.now(),
    )

    ok, motivo = can_advance(avaliacao)
    assert ok is True
    assert motivo == ''

    result = advance_stage(avaliacao, lider)
    assert result.etapa == Avaliacao.Etapa.FEEDBACK
    assert result.concluida is True
