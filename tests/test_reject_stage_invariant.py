"""Invariantes de rejeição (T005): reject_* não altera Avaliacao.etapa."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from apps.goals.models import Meta
from apps.goals.services.approval import reject_meta, reject_resultado
from apps.reviews.models import Avaliacao


@pytest.mark.django_db
def test_reject_meta_nao_altera_etapa(avaliacao, meta, lider):
    avaliacao.etapa = Avaliacao.Etapa.APROVACAO_METAS
    avaliacao.save(update_fields=['etapa', 'updated_at'])
    etapa_antes = avaliacao.etapa

    with patch('apps.cycles.services.stage.advance_stage') as advance_mock:
        resultado = reject_meta(meta, lider)

    avaliacao.refresh_from_db()
    meta.refresh_from_db()

    assert resultado.status == Meta.Status.REPROVADA
    assert meta.status == Meta.Status.REPROVADA
    assert avaliacao.etapa == etapa_antes
    advance_mock.assert_not_called()


@pytest.mark.django_db
def test_reject_resultado_nao_altera_etapa(avaliacao, meta, lider):
    avaliacao.etapa = Avaliacao.Etapa.APROVACAO_RESULTADOS
    avaliacao.save(update_fields=['etapa', 'updated_at'])
    meta.status = Meta.Status.APROVADA
    meta.status_resultado = Meta.StatusResultado.PENDENTE
    meta.save(update_fields=['status', 'status_resultado', 'updated_at'])
    etapa_antes = avaliacao.etapa

    with patch('apps.cycles.services.stage.advance_stage') as advance_mock:
        resultado = reject_resultado(meta, lider)

    avaliacao.refresh_from_db()
    meta.refresh_from_db()

    assert resultado.status_resultado == Meta.StatusResultado.REPROVADO
    assert meta.status_resultado == Meta.StatusResultado.REPROVADO
    assert avaliacao.etapa == etapa_antes
    advance_mock.assert_not_called()
