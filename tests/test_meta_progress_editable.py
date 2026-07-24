"""Elegibilidade de edição de progresso (T008) e reopen pós-reprovação (T009)."""

from __future__ import annotations

from decimal import Decimal

import pytest

from apps.goals.forms import MetaProgressForm, meta_progress_editable
from apps.goals.models import Meta
from apps.reviews.models import Avaliacao


@pytest.mark.django_db
def test_meta_progress_editable_na_etapa_resultados_meta_aprovada(avaliacao, meta):
    avaliacao.etapa = Avaliacao.Etapa.RESULTADOS
    avaliacao.save(update_fields=['etapa', 'updated_at'])
    meta.status = Meta.Status.APROVADA
    meta.save(update_fields=['status', 'updated_at'])

    assert meta_progress_editable(avaliacao, meta) is True


@pytest.mark.django_db
def test_meta_progress_editable_resultado_reprovado_em_aprovacao_resultados(
    avaliacao,
    meta,
):
    avaliacao.etapa = Avaliacao.Etapa.APROVACAO_RESULTADOS
    avaliacao.save(update_fields=['etapa', 'updated_at'])
    meta.status = Meta.Status.APROVADA
    meta.status_resultado = Meta.StatusResultado.REPROVADO
    meta.save(update_fields=['status', 'status_resultado', 'updated_at'])

    assert meta_progress_editable(avaliacao, meta) is True


@pytest.mark.django_db
def test_meta_progress_editable_resultado_pendente_em_aprovacao_resultados_bloqueado(
    avaliacao,
    meta,
):
    avaliacao.etapa = Avaliacao.Etapa.APROVACAO_RESULTADOS
    avaliacao.save(update_fields=['etapa', 'updated_at'])
    meta.status = Meta.Status.APROVADA
    meta.status_resultado = Meta.StatusResultado.PENDENTE
    meta.save(update_fields=['status', 'status_resultado', 'updated_at'])

    assert meta_progress_editable(avaliacao, meta) is False


@pytest.mark.django_db
def test_meta_progress_form_reopen_resultado_apos_correcao(avaliacao, meta):
    """Salvar progresso elegível pós-reprovação reabre status_resultado → pendente."""
    etapa_antes = Avaliacao.Etapa.APROVACAO_RESULTADOS
    avaliacao.etapa = etapa_antes
    avaliacao.save(update_fields=['etapa', 'updated_at'])
    meta.status = Meta.Status.APROVADA
    meta.status_resultado = Meta.StatusResultado.REPROVADO
    meta.progresso = Decimal('40.00')
    meta.save(update_fields=['status', 'status_resultado', 'progresso', 'updated_at'])

    form = MetaProgressForm(
        data={'progresso': '55.00'},
        instance=meta,
    )
    assert form.is_valid(), form.errors
    saved = form.save()

    saved.refresh_from_db()
    avaliacao.refresh_from_db()
    assert saved.status_resultado == Meta.StatusResultado.PENDENTE
    assert saved.progresso == Decimal('55.00')
    assert avaliacao.etapa == etapa_antes
