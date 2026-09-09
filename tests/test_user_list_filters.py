"""Testes de filtros e apresentação da listagem administrativa de usuários."""

from __future__ import annotations

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import CustomUser
from apps.organization.models import Area, Cargo
from apps.organization.services.user_list import (
    apply_user_list_filters,
    get_allowed_area_ids,
    get_allowed_manager_ids,
    get_base_user_list_queryset,
    parse_int_filter,
    parse_search_filter,
    parse_status_filter,
    resolve_id_filter,
)
from tests.conftest import DEFAULT_PASSWORD, FIXTURE_DATA_ENTRADA


@pytest.fixture
def duas_areas(db):
    area_ti = Area.objects.create(nome='Tecnologia')
    area_rh = Area.objects.create(nome='Recursos Humanos')
    cargo_gerente = Cargo.objects.create(nome='Gerente', nivel=2)
    cargo_analista = Cargo.objects.create(nome='Analista', nivel=1)
    return area_ti, area_rh, cargo_gerente, cargo_analista


@pytest.fixture
def usuarios_duas_areas(db, admin, duas_areas):
    area_ti, area_rh, cargo_gerente, cargo_analista = duas_areas
    gestor_ti = CustomUser.objects.create_user(
        email='gestor.ti@test.greenn.com.br',
        password=DEFAULT_PASSWORD,
        nome='Gestor TI',
        cargo=cargo_gerente,
        area=area_ti,
        line_manager=admin,
        data_entrada=FIXTURE_DATA_ENTRADA,
        email_confirmado_em=timezone.now(),
    )
    colab_ti = CustomUser.objects.create_user(
        email='colab.ti@test.greenn.com.br',
        password=DEFAULT_PASSWORD,
        nome='Colab TI',
        cargo=cargo_analista,
        area=area_ti,
        line_manager=gestor_ti,
        data_entrada=FIXTURE_DATA_ENTRADA,
        email_confirmado_em=timezone.now(),
    )
    colab_rh = CustomUser.objects.create_user(
        email='colab.rh@test.greenn.com.br',
        password=DEFAULT_PASSWORD,
        nome='Colab RH',
        cargo=cargo_analista,
        area=area_rh,
        line_manager=admin,
        data_entrada=FIXTURE_DATA_ENTRADA,
        email_confirmado_em=timezone.now(),
    )
    inativo = CustomUser.objects.create_user(
        email='inativo@test.greenn.com.br',
        password=DEFAULT_PASSWORD,
        nome='Inativo Teste',
        cargo=cargo_analista,
        area=area_ti,
        line_manager=gestor_ti,
        is_active=False,
        data_entrada=FIXTURE_DATA_ENTRADA,
        email_confirmado_em=timezone.now(),
    )
    return gestor_ti, colab_ti, colab_rh, inativo, area_ti, area_rh


def test_parse_filtros_invalidos():
    assert parse_status_filter('invalido') == ''
    assert parse_int_filter('abc') is None
    assert parse_int_filter('-1') is None
    assert parse_search_filter('  busca  ') == 'busca'


def test_resolve_id_filter_rejeita_fora_do_catalogo(db, admin):
    base = get_base_user_list_queryset()
    allowed = get_allowed_area_ids(base)
    assert resolve_id_filter(999_999, allowed) is None


def test_apply_user_list_filters(db, usuarios_duas_areas):
    gestor_ti, colab_ti, colab_rh, inativo, area_ti, _area_rh = usuarios_duas_areas
    base = get_base_user_list_queryset()

    por_area = apply_user_list_filters(base, area_id=area_ti.pk)
    assert colab_ti in por_area
    assert colab_rh not in por_area

    por_gestor = apply_user_list_filters(base, gestor_id=gestor_ti.pk)
    assert colab_ti in por_gestor
    assert colab_rh not in por_gestor

    ativos = apply_user_list_filters(base, status='ativo')
    assert inativo not in ativos
    assert colab_ti in ativos

    inativos = apply_user_list_filters(base, status='inativo')
    assert inativo in inativos
    assert colab_ti not in inativos

    busca = apply_user_list_filters(base, busca='Colab RH')
    assert colab_rh in busca
    assert colab_ti not in busca


def test_filtro_area_id_invalido_ignorado(db, usuarios_duas_areas):
    base = get_base_user_list_queryset()
    allowed = get_allowed_area_ids(base)
    area_id = resolve_id_filter(999_999, allowed)
    assert area_id is None
    assert apply_user_list_filters(base, area_id=area_id).count() == base.count()


def test_gestor_ids_derivados_do_catalogo(db, usuarios_duas_areas):
    gestor_ti, colab_ti, _colab_rh, _inativo, _area_ti, _area_rh = usuarios_duas_areas
    base = get_base_user_list_queryset()
    allowed = get_allowed_manager_ids(base)
    assert gestor_ti.pk in allowed
    assert colab_ti.pk not in allowed


def test_admin_lista_usuarios_com_tabela_padronizada(client, admin, usuarios_duas_areas):
    client.force_login(admin)
    url = reverse('organization:user_list')
    resp = client.get(url)
    assert resp.status_code == 200
    html = resp.content.decode()
    assert 'user-registry-table' in html
    assert 'filter-segment-bar' in html
    assert 'Buscar colaborador...' in html
    assert 'Mostrando' in html
    assert 'Filtros' in html


def test_editar_link_preserva_estado_da_lista(client, admin, usuarios_duas_areas):
    _gestor, colab_ti, _colab_rh, _inativo, area_ti, _area_rh = usuarios_duas_areas
    client.force_login(admin)
    list_path = reverse('organization:user_list')
    return_path = f'{list_path}?status=ativo&area={area_ti.pk}'
    resp = client.get(return_path)
    assert resp.status_code == 200
    html = resp.content.decode()
    edit_fragment = reverse('organization:user_update', kwargs={'pk': colab_ti.pk})
    assert edit_fragment in html
    assert 'next=' in html
    assert 'status' in html and 'ativo' in html


def test_salvar_usuario_retorna_para_lista_filtrada(client, admin, usuarios_duas_areas):
    _gestor, colab_ti, _colab_rh, _inativo, area_ti, _area_rh = usuarios_duas_areas
    client.force_login(admin)
    edit_url = reverse('organization:user_update', kwargs={'pk': colab_ti.pk})
    return_path = f'{reverse("organization:user_list")}?status=ativo&area={area_ti.pk}'
    resp = client.post(
        f'{edit_url}?next={return_path}',
        data={
            'next': return_path,
            'nome': colab_ti.nome,
            'area': colab_ti.area_id,
            'cargo': colab_ti.cargo_id,
            'line_manager': colab_ti.line_manager_id,
            'data_entrada': colab_ti.data_entrada.isoformat(),
            'is_admin': '',
            'is_active': 'on',
        },
    )
    assert resp.status_code == 302
    assert f'area={area_ti.pk}' in resp['Location']
    assert 'status=ativo' in resp['Location']


def test_next_externo_ignorado_no_redirect(client, admin, usuarios_duas_areas):
    _gestor, colab_ti, _colab_rh, _inativo, _area_ti, _area_rh = usuarios_duas_areas
    client.force_login(admin)
    edit_url = reverse('organization:user_update', kwargs={'pk': colab_ti.pk})
    malicious_next = 'https://evil.example/phish'
    resp = client.post(
        f'{edit_url}?next={malicious_next}',
        data={
            'next': malicious_next,
            'nome': colab_ti.nome,
            'area': colab_ti.area_id or '',
            'cargo': colab_ti.cargo_id or '',
            'line_manager': colab_ti.line_manager_id or '',
            'data_entrada': colab_ti.data_entrada.isoformat(),
            'is_admin': '',
            'is_active': 'on',
        },
    )
    assert resp.status_code == 302
    assert resp['Location'] == reverse('organization:user_list')


def test_admin_filtra_por_area(client, admin, usuarios_duas_areas):
    _gestor, _colab_ti, colab_rh, _inativo, area_ti, _area_rh = usuarios_duas_areas
    client.force_login(admin)
    url = reverse('organization:user_list')
    resp = client.get(url, {'area': area_ti.pk})
    html = resp.content.decode()
    assert 'Colab TI' in html
    assert 'Colab RH' not in html


def test_admin_filtra_por_gestor(client, admin, usuarios_duas_areas):
    gestor_ti, colab_ti, colab_rh, _inativo, _area_ti, _area_rh = usuarios_duas_areas
    client.force_login(admin)
    url = reverse('organization:user_list')
    resp = client.get(url, {'gestor': gestor_ti.pk})
    html = resp.content.decode()
    assert colab_ti.nome in html
    assert colab_rh.nome not in html


def test_admin_filtra_area_invalida_ignorada(client, admin, usuarios_duas_areas):
    client.force_login(admin)
    url = reverse('organization:user_list')
    resp = client.get(url, {'area': '999999'})
    assert resp.status_code == 200
    html = resp.content.decode()
    assert 'Colab TI' in html
    assert 'Colab RH' in html


def test_nao_admin_recebe_403(client, lider):
    client.force_login(lider)
    url = reverse('organization:user_list')
    resp = client.get(url)
    assert resp.status_code == 403
