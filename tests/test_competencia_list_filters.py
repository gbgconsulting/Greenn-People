"""Testes de filtros e apresentação da listagem administrativa de competências."""

from __future__ import annotations

from urllib.parse import unquote

import pytest
from django.urls import reverse

from apps.competencies.models import Competencia, Escala
from apps.competencies.services.competencia_list import (
    apply_competencia_list_filters,
    get_allowed_tipo_values,
    get_base_competencia_list_queryset,
    parse_tipo_filter,
    resolve_tipo_filter,
)


@pytest.fixture
def escala(db):
    return Escala.objects.create(
        nome='Escala Teste',
        valor_minimo=1,
        valor_maximo=5,
    )


@pytest.fixture
def competencias_catalogo(db, escala):
    comunicacao = Competencia.objects.create(
        nome='Comunicação Assertiva',
        descricao='Capacidade de expressar ideias de forma clara.',
        tipo=Competencia.Tipo.COMPORTAMENTAL,
        escala=escala,
    )
    analise = Competencia.objects.create(
        nome='Análise de Dados',
        descricao='Habilidade de interpretar métricas complexas.',
        tipo=Competencia.Tipo.TECNICA,
        escala=escala,
    )
    legacy = Competencia.objects.create(
        nome='Gestão de Tempo Legacy',
        descricao='Metodologia antiga de produtividade.',
        tipo=Competencia.Tipo.COMPORTAMENTAL,
        escala=escala,
        is_active=False,
    )
    return comunicacao, analise, legacy


def test_parse_tipo_filter_invalido():
    assert parse_tipo_filter('invalido') == ''
    assert parse_tipo_filter('') == ''


def test_apply_competencia_list_filters(db, competencias_catalogo):
    comunicacao, analise, legacy = competencias_catalogo
    base = get_base_competencia_list_queryset()

    ativos = apply_competencia_list_filters(base, status='ativo')
    assert comunicacao in ativos
    assert legacy not in ativos

    inativos = apply_competencia_list_filters(base, status='inativo')
    assert legacy in inativos
    assert analise not in inativos

    busca = apply_competencia_list_filters(base, busca='métricas')
    assert analise in busca
    assert comunicacao not in busca

    por_tipo = apply_competencia_list_filters(base, tipo='tecnica')
    assert analise in por_tipo
    assert comunicacao not in por_tipo


def test_tipo_invalido_ignorado(db, competencias_catalogo):
    base = get_base_competencia_list_queryset()
    allowed = get_allowed_tipo_values(base)
    tipo = resolve_tipo_filter('inexistente', allowed)
    assert tipo == ''
    assert apply_competencia_list_filters(base, tipo=tipo).count() == base.count()


def test_admin_lista_competencias_com_tabela_padronizada(
    client,
    admin,
    competencias_catalogo,
):
    client.force_login(admin)
    url = reverse('competencies:competencia_list')
    resp = client.get(url)
    assert resp.status_code == 200
    html = resp.content.decode()
    assert 'competencia-registry-table' in html
    assert 'filter-segment-bar' in html
    assert 'Buscar competência...' in html
    assert 'Comunicação Assertiva' in html
    assert 'Mostrando' in html


def test_editar_link_preserva_estado_da_lista(client, admin, competencias_catalogo):
    comunicacao, _analise, _legacy = competencias_catalogo
    client.force_login(admin)
    list_path = reverse('competencies:competencia_list')
    return_path = f'{list_path}?status=ativo&busca=Comunicação'
    resp = client.get(return_path)
    assert resp.status_code == 200
    html = resp.content.decode()
    edit_fragment = reverse(
        'competencies:competencia_update',
        kwargs={'pk': comunicacao.pk},
    )
    assert edit_fragment in html
    assert 'next=' in html
    assert 'Comunicação' in html


def test_salvar_competencia_retorna_para_lista_filtrada(
    client,
    admin,
    competencias_catalogo,
    escala,
):
    comunicacao, _analise, _legacy = competencias_catalogo
    client.force_login(admin)
    edit_url = reverse(
        'competencies:competencia_update',
        kwargs={'pk': comunicacao.pk},
    )
    return_path = (
        f'{reverse("competencies:competencia_list")}?status=ativo&busca=Comunicação'
    )
    resp = client.post(
        f'{edit_url}?next={return_path}',
        data={
            'next': return_path,
            'nome': comunicacao.nome,
            'descricao': comunicacao.descricao,
            'tipo': comunicacao.tipo,
            'escala': escala.pk,
            'is_active': 'on',
        },
    )
    assert resp.status_code == 302
    location = unquote(resp['Location'])
    assert 'busca=Comunicação' in location
    assert 'status=ativo' in location


def test_next_externo_ignorado_no_redirect(client, admin, competencias_catalogo, escala):
    comunicacao, _analise, _legacy = competencias_catalogo
    client.force_login(admin)
    edit_url = reverse(
        'competencies:competencia_update',
        kwargs={'pk': comunicacao.pk},
    )
    malicious_next = 'https://evil.example/phish'
    resp = client.post(
        f'{edit_url}?next={malicious_next}',
        data={
            'next': malicious_next,
            'nome': comunicacao.nome,
            'descricao': comunicacao.descricao,
            'tipo': comunicacao.tipo,
            'escala': escala.pk,
            'is_active': 'on',
        },
    )
    assert resp.status_code == 302
    assert resp['Location'] == reverse('competencies:competencia_list')


def test_admin_filtra_por_status(client, admin, competencias_catalogo):
    _comunicacao, _analise, legacy = competencias_catalogo
    client.force_login(admin)
    url = reverse('competencies:competencia_list')
    resp = client.get(url, {'status': 'inativo'})
    html = resp.content.decode()
    assert legacy.nome in html
    assert 'Comunicação Assertiva' not in html


def test_admin_filtra_por_tipo(client, admin, competencias_catalogo):
    _comunicacao, analise, _legacy = competencias_catalogo
    client.force_login(admin)
    url = reverse('competencies:competencia_list')
    resp = client.get(url, {'tipo': 'tecnica'})
    html = resp.content.decode()
    assert analise.nome in html
    assert 'Comunicação Assertiva' not in html


def test_nao_admin_recebe_403(client, lider, competencias_catalogo):
    client.force_login(lider)
    url = reverse('competencies:competencia_list')
    resp = client.get(url)
    assert resp.status_code == 403
