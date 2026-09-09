"""Testes de filtros e apresentação da listagem de pendentes de vínculo."""

from __future__ import annotations

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import CustomUser
from apps.organization.models import Area, Cargo
from apps.organization.services.user_list import (
    apply_pending_user_list_filters,
    get_base_pending_user_list_queryset,
    parse_pendencia_filter,
)
from tests.conftest import DEFAULT_PASSWORD, FIXTURE_DATA_ENTRADA


@pytest.fixture
def pendentes_mistos(db, admin):
    area = Area.objects.create(nome='Operações')
    cargo = Cargo.objects.create(nome='Analista', nivel=1)
    gestor = CustomUser.objects.create_user(
        email='gestor.pending@test.greenn.com.br',
        password=DEFAULT_PASSWORD,
        nome='Gestor Pending',
        area=area,
        cargo=cargo,
        line_manager=admin,
        data_entrada=FIXTURE_DATA_ENTRADA,
        email_confirmado_em=timezone.now(),
    )
    sem_ambos = CustomUser.objects.create_user(
        email='sem.ambos@test.greenn.com.br',
        password=DEFAULT_PASSWORD,
        nome='Sem Ambos',
        line_manager=gestor,
        data_entrada=FIXTURE_DATA_ENTRADA,
        email_confirmado_em=timezone.now(),
    )
    sem_area = CustomUser.objects.create_user(
        email='sem.area@test.greenn.com.br',
        password=DEFAULT_PASSWORD,
        nome='Sem Area',
        cargo=cargo,
        line_manager=gestor,
        data_entrada=FIXTURE_DATA_ENTRADA,
        email_confirmado_em=timezone.now(),
    )
    sem_cargo = CustomUser.objects.create_user(
        email='sem.cargo@test.greenn.com.br',
        password=DEFAULT_PASSWORD,
        nome='Sem Cargo',
        area=area,
        line_manager=gestor,
        data_entrada=FIXTURE_DATA_ENTRADA,
        email_confirmado_em=timezone.now(),
    )
    completo = CustomUser.objects.create_user(
        email='completo@test.greenn.com.br',
        password=DEFAULT_PASSWORD,
        nome='Completo',
        area=area,
        cargo=cargo,
        line_manager=gestor,
        data_entrada=FIXTURE_DATA_ENTRADA,
        email_confirmado_em=timezone.now(),
    )
    return sem_ambos, sem_area, sem_cargo, completo, gestor, area


def test_parse_pendencia_invalida():
    assert parse_pendencia_filter('invalido') == ''


def test_apply_pendencia_filters(db, pendentes_mistos):
    sem_ambos, sem_area, sem_cargo, completo, _gestor, _area = pendentes_mistos
    base = get_base_pending_user_list_queryset()

    assert completo not in base
    assert sem_ambos in base
    assert sem_area in base
    assert sem_cargo in base

    ambos = apply_pending_user_list_filters(base, pendencia='ambos')
    assert sem_ambos in ambos
    assert sem_area not in ambos
    assert sem_cargo not in ambos

    so_area = apply_pending_user_list_filters(base, pendencia='area')
    assert sem_area in so_area
    assert sem_ambos not in so_area

    so_cargo = apply_pending_user_list_filters(base, pendencia='cargo')
    assert sem_cargo in so_cargo
    assert sem_ambos not in so_cargo


def test_admin_pending_lista_padronizada(client, admin, pendentes_mistos):
    client.force_login(admin)
    url = reverse('organization:user_pending')
    resp = client.get(url)
    assert resp.status_code == 200
    html = resp.content.decode()
    assert 'user-registry-table' in html
    assert 'filter-segment-bar' in html
    assert 'Filtrar por pendência' in html
    assert 'Filtros' in html
    assert 'Mostrando' in html
    assert 'Sem Ambos' in html
    assert 'Completo' not in html


def test_admin_pending_filtra_por_gestor(client, admin, pendentes_mistos):
    sem_ambos, sem_area, sem_cargo, _completo, gestor, _area = pendentes_mistos
    client.force_login(admin)
    url = reverse('organization:user_pending')
    resp = client.get(url, {'gestor': gestor.pk})
    html = resp.content.decode()
    assert sem_ambos.nome in html
    assert sem_area.nome in html
    assert sem_cargo.nome in html


def test_vincular_preserva_estado_da_lista(client, admin, pendentes_mistos):
    sem_ambos, _sem_area, _sem_cargo, _completo, _gestor, _area = pendentes_mistos
    client.force_login(admin)
    list_path = reverse('organization:user_pending')
    return_path = f'{list_path}?pendencia=ambos'
    resp = client.get(return_path)
    assert resp.status_code == 200
    html = resp.content.decode()
    edit_fragment = reverse('organization:user_update', kwargs={'pk': sem_ambos.pk})
    assert edit_fragment in html
    assert 'next=' in html
    assert 'pendencia' in html


def test_salvar_pending_retorna_para_lista_filtrada(client, admin, pendentes_mistos):
    _sem_ambos, sem_area, _sem_cargo, _completo, _gestor, area = pendentes_mistos
    client.force_login(admin)
    edit_url = reverse('organization:user_update', kwargs={'pk': sem_area.pk})
    return_path = f'{reverse("organization:user_pending")}?pendencia=area'
    resp = client.post(
        f'{edit_url}?next={return_path}',
        data={
            'next': return_path,
            'nome': sem_area.nome,
            'area': '',
            'cargo': sem_area.cargo_id,
            'line_manager': sem_area.line_manager_id,
            'data_entrada': sem_area.data_entrada.isoformat(),
            'is_admin': '',
            'is_active': 'on',
        },
    )
    assert resp.status_code == 302
    assert 'pendencia=area' in resp['Location']


def test_nao_admin_pending_recebe_403(client, lider):
    client.force_login(lider)
    url = reverse('organization:user_pending')
    resp = client.get(url)
    assert resp.status_code == 403
