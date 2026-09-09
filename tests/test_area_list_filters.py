"""Testes de filtros e apresentação da listagem administrativa de áreas."""

from __future__ import annotations

import pytest
from django.urls import reverse

from apps.accounts.models import CustomUser
from apps.organization.models import Area
from apps.organization.services.area_list import (
    apply_area_list_filters,
    build_hierarchical_area_rows,
    get_allowed_parent_area_ids,
    get_base_area_list_queryset,
    resolve_parent_filter,
)


@pytest.fixture
def areas_hierarquia(db):
    diretoria = Area.objects.create(nome='Diretoria Executiva')
    tecnologia = Area.objects.create(nome='Tecnologia & Inovação', parent=diretoria)
    frontend = Area.objects.create(nome='Desenvolvimento Front-end', parent=tecnologia)
    rh = Area.objects.create(nome='Recursos Humanos', is_active=False)
    return diretoria, tecnologia, frontend, rh


@pytest.fixture
def colaboradores_ti(db, areas_hierarquia):
    _diretoria, tecnologia, _frontend, _rh = areas_hierarquia
    gestor = CustomUser.objects.create_user(
        email='carlos@example.com',
        password='pass',
        nome='Carlos Pereira',
        area=tecnologia,
    )
    CustomUser.objects.create_user(
        email='ana@example.com',
        password='pass',
        nome='Ana Rodrigues',
        area=tecnologia,
        line_manager=gestor,
    )
    return gestor


def test_build_hierarchical_area_rows(db, areas_hierarquia):
    diretoria, tecnologia, frontend, rh = areas_hierarquia
    base = get_base_area_list_queryset()
    rows = build_hierarchical_area_rows(base)
    nomes = [row.area.nome for row in rows]
    assert nomes.index(diretoria.nome) < nomes.index(tecnologia.nome)
    assert nomes.index(tecnologia.nome) < nomes.index(frontend.nome)
    assert rows[0].depth == 0
    assert any(row.area.nome == frontend.nome and row.depth == 2 for row in rows)
    assert rh.nome in nomes


def test_apply_area_list_filters(db, areas_hierarquia):
    _diretoria, _tecnologia, _frontend, rh = areas_hierarquia
    base = get_base_area_list_queryset()

    ativos = apply_area_list_filters(base, status='ativo')
    assert rh not in ativos

    inativos = apply_area_list_filters(base, status='inativo')
    assert rh in inativos

    busca = apply_area_list_filters(base, busca='Front-end')
    assert busca.count() == 1


def test_parent_filter_invalido_ignorado(db, areas_hierarquia):
    base = get_base_area_list_queryset()
    allowed = get_allowed_parent_area_ids(base)
    parent_id = resolve_parent_filter(999, allowed)
    assert parent_id is None


def test_colaboradores_count_na_lista(client, admin, areas_hierarquia, colaboradores_ti):
    client.force_login(admin)
    resp = client.get(reverse('organization:area_list'))
    assert resp.status_code == 200
    html = resp.content.decode()
    assert 'area-registry-table' in html
    assert 'filter-segment-bar' in html
    assert 'Buscar área...' in html
    assert 'Gestor responsável' not in html
    assert 'Colaboradores' in html
    assert 'Mostrando' in html
    assert html.count('>2<') >= 1


def test_editar_link_preserva_estado_da_lista(client, admin, areas_hierarquia):
    _diretoria, _tecnologia, frontend, _rh = areas_hierarquia
    client.force_login(admin)
    list_path = reverse('organization:area_list')
    return_path = f'{list_path}?status=ativo&busca=Front'
    resp = client.get(return_path)
    assert resp.status_code == 200
    html = resp.content.decode()
    edit_fragment = reverse('organization:area_update', kwargs={'pk': frontend.pk})
    assert edit_fragment in html
    assert 'next=' in html
    assert 'Front' in html


def test_salvar_area_retorna_para_lista_filtrada(client, admin, areas_hierarquia):
    _diretoria, _tecnologia, frontend, _rh = areas_hierarquia
    client.force_login(admin)
    edit_url = reverse('organization:area_update', kwargs={'pk': frontend.pk})
    return_path = f'{reverse("organization:area_list")}?status=ativo&busca=Front'
    resp = client.post(
        f'{edit_url}?next={return_path}',
        data={
            'next': return_path,
            'nome': frontend.nome,
            'parent': frontend.parent_id,
            'is_active': 'on',
        },
    )
    assert resp.status_code == 302
    assert 'busca=Front' in resp['Location']
    assert 'status=ativo' in resp['Location']


def test_next_externo_ignorado_no_redirect(client, admin, areas_hierarquia):
    _diretoria, _tecnologia, frontend, _rh = areas_hierarquia
    client.force_login(admin)
    edit_url = reverse('organization:area_update', kwargs={'pk': frontend.pk})
    malicious_next = 'https://evil.example/phish'
    resp = client.post(
        f'{edit_url}?next={malicious_next}',
        data={
            'next': malicious_next,
            'nome': frontend.nome,
            'parent': frontend.parent_id,
            'is_active': 'on',
        },
    )
    assert resp.status_code == 302
    assert resp['Location'] == reverse('organization:area_list')


def test_admin_filtra_por_status(client, admin, areas_hierarquia):
    _diretoria, _tecnologia, _frontend, rh = areas_hierarquia
    client.force_login(admin)
    url = reverse('organization:area_list')
    resp = client.get(url, {'status': 'inativo'})
    html = resp.content.decode()
    assert rh.nome in html
    assert 'Diretoria Executiva' not in html


def test_nao_admin_recebe_403(client, lider):
    client.force_login(lider)
    resp = client.get(reverse('organization:area_list'))
    assert resp.status_code == 403
