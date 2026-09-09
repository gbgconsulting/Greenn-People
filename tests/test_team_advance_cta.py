"""CTA de liberar etapa no Painel do time (sem ir ao detalhe da avaliação)."""

from __future__ import annotations

import pytest
from django.test import Client
from django.urls import reverse

from apps.goals.models import Meta
from apps.reviews.models import Avaliacao


def _login_lider(lider) -> Client:
    client = Client()
    client.force_login(lider)
    return client


@pytest.mark.django_db
def test_team_mostra_liberar_etapa_quando_metas_aprovadas(
    lider,
    colaborador,
    avaliacao,
    meta,
):
    avaliacao.etapa = Avaliacao.Etapa.APROVACAO_METAS
    avaliacao.save(update_fields=['etapa', 'updated_at'])
    meta.status = Meta.Status.APROVADA
    meta.save(update_fields=['status', 'updated_at'])

    client = _login_lider(lider)
    resp = client.get(reverse('dashboard:team'))

    assert resp.status_code == 200
    html = resp.content.decode()
    assert 'Liberar etapa de resultados' in html

    membros = resp.context['membros_resumo']
    row = next(m for m in membros if m['usuario'].pk == colaborador.pk)
    assert row['pode_avancar'] is True
    assert row['rotulo_avanco'] == 'Liberar etapa de resultados'

    destaque = resp.context['destaque_atencao']
    assert destaque
    assert destaque[0]['pode_avancar'] is True


@pytest.mark.django_db
def test_team_oculta_liberar_etapa_quando_meta_ainda_pendente(
    lider,
    colaborador,
    avaliacao,
    meta,
):
    avaliacao.etapa = Avaliacao.Etapa.APROVACAO_METAS
    avaliacao.save(update_fields=['etapa', 'updated_at'])
    assert meta.status == Meta.Status.PENDENTE

    client = _login_lider(lider)
    resp = client.get(reverse('dashboard:team'))

    assert resp.status_code == 200
    html = resp.content.decode()
    assert 'Liberar etapa de resultados' not in html

    row = next(
        m
        for m in resp.context['membros_resumo']
        if m['usuario'].pk == colaborador.pk
    )
    assert row['pode_avancar'] is False


@pytest.mark.django_db
def test_team_liberar_etapa_post_volta_ao_painel(
    lider,
    colaborador,
    avaliacao,
    meta,
):
    avaliacao.etapa = Avaliacao.Etapa.APROVACAO_METAS
    avaliacao.save(update_fields=['etapa', 'updated_at'])
    meta.status = Meta.Status.APROVADA
    meta.save(update_fields=['status', 'updated_at'])

    client = _login_lider(lider)
    team_url = reverse('dashboard:team')
    resp = client.post(
        reverse('reviews:advance', kwargs={'pk': avaliacao.pk}),
        {'next': team_url},
    )

    assert resp.status_code == 302
    assert resp['Location'] == team_url
    avaliacao.refresh_from_db()
    assert avaliacao.etapa == Avaliacao.Etapa.RESULTADOS
