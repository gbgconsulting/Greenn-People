"""Filtro por colaborador na gestão de metas e CTA Revisar do painel do time."""

from __future__ import annotations

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import CustomUser
from apps.reviews.models import Avaliacao
from tests.conftest import DEFAULT_PASSWORD, FIXTURE_DATA_ENTRADA


@pytest.fixture
def outsider(db, area, cargo_colab) -> CustomUser:
    return CustomUser.objects.create_user(
        email='outsider-meta-filter@test.greenn.com.br',
        password=DEFAULT_PASSWORD,
        nome='Outsider Teste',
        area=area,
        cargo=cargo_colab,
        data_entrada=FIXTURE_DATA_ENTRADA,
        email_confirmado_em=timezone.now(),
    )


@pytest.mark.django_db
def test_meta_list_filtra_por_usuario_no_escopo(
    client,
    lider,
    colaborador,
    meta,
):
    client.login(email=lider.email, password=DEFAULT_PASSWORD)
    url = reverse('goals:meta_list')
    resp = client.get(url, {'usuario': colaborador.pk})

    assert resp.status_code == 200
    assert resp.context['colaborador_filtro'].pk == colaborador.pk
    assert resp.context['revisando_colaborador'] is True
    assert list(resp.context['metas']) == [meta]
    html = resp.content.decode()
    assert 'Filtrando por colaborador' in html
    assert 'Voltar ao Painel do Time' in html
    assert reverse('dashboard:team') in html


@pytest.mark.django_db
def test_meta_list_usuario_fora_do_escopo_retorna_vazio(
    client,
    lider,
    meta,
    outsider,
):
    """Líder não vê metas de outsider mesmo com ?usuario=."""
    client.login(email=lider.email, password=DEFAULT_PASSWORD)
    resp = client.get(reverse('goals:meta_list'), {'usuario': outsider.pk})

    assert resp.status_code == 200
    assert resp.context['colaborador_filtro'] is None
    assert resp.context['filtro_usuario_negado'] is True
    assert list(resp.context['metas']) == []


@pytest.mark.django_db
def test_painel_revisar_aponta_para_gestao_metas_filtrada(
    client,
    lider,
    colaborador,
    avaliacao,
):
    avaliacao.etapa = Avaliacao.Etapa.APROVACAO_METAS
    avaliacao.save(update_fields=['etapa'])

    client.login(email=lider.email, password=DEFAULT_PASSWORD)
    resp = client.get(reverse('dashboard:team'))
    assert resp.status_code == 200
    html = resp.content.decode()
    expected = f"{reverse('goals:meta_list')}?usuario={colaborador.pk}"
    assert expected in html
    assert 'Revisar' in html
