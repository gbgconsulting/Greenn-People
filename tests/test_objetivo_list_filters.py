"""Testes de filtros e apresentação da listagem de objetivos estratégicos."""

from __future__ import annotations

import pytest
from django.urls import reverse

from apps.cycles.services.objetivo_list import (
    apply_objetivo_list_filters,
    get_base_objetivo_list_queryset,
)
from apps.goals.models import ObjetivoEstrategico


@pytest.fixture
def objetivos_catalogo(ciclo_aberto):
    lideranca = ObjetivoEstrategico.objects.create(
        descricao='Liderança',
        ciclo=ciclo_aberto,
    )
    inovacao = ObjetivoEstrategico.objects.create(
        descricao='Inovação e Tecnologia',
        ciclo=ciclo_aberto,
    )
    return lideranca, inovacao


def test_apply_objetivo_list_filters_busca(db, ciclo_aberto, objetivos_catalogo):
    lideranca, inovacao = objetivos_catalogo
    base = get_base_objetivo_list_queryset(ciclo_aberto)

    filtrado = apply_objetivo_list_filters(base, busca='Inovação')
    assert inovacao in filtrado
    assert lideranca not in filtrado

    vazio = apply_objetivo_list_filters(base, busca='inexistente')
    assert vazio.count() == 0


def test_objetivo_list_requer_admin(client, ciclo_aberto, colaborador):
    url = reverse('cycles:objetivo_list', kwargs={'ciclo_pk': ciclo_aberto.pk})
    client.force_login(colaborador)
    response = client.get(url)
    assert response.status_code == 403


def test_objetivo_list_admin_ok(client, admin, ciclo_aberto, objetivos_catalogo):
    url = reverse('cycles:objetivo_list', kwargs={'ciclo_pk': ciclo_aberto.pk})
    client.force_login(admin)
    response = client.get(url)
    assert response.status_code == 200
    content = response.content.decode()
    assert 'Objetivos estratégicos' in content
    assert 'Liderança' in content
    assert 'Inovação e Tecnologia' in content
    assert 'objetivo-registry-table' in content


def test_objetivo_list_busca_htmx(client, admin, ciclo_aberto, objetivos_catalogo):
    url = reverse('cycles:objetivo_list', kwargs={'ciclo_pk': ciclo_aberto.pk})
    client.force_login(admin)
    response = client.get(
        url,
        {'busca': 'Liderança'},
        HTTP_HX_REQUEST='true',
    )
    assert response.status_code == 200
    content = response.content.decode()
    assert 'Liderança' in content
    assert 'Inovação e Tecnologia' not in content
