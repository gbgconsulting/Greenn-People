"""Testes de filtros e apresentação da listagem administrativa de cargos."""

from __future__ import annotations

import pytest
from django.urls import reverse

from apps.competencies.models import CargoCompetencia, Competencia, Escala
from apps.organization.models import Cargo
from apps.organization.services.cargo_list import (
    apply_cargo_list_filters,
    get_allowed_nivel_values,
    get_base_cargo_list_queryset,
    parse_nivel_filter,
    resolve_nivel_filter,
)
from apps.organization.services.display import format_cargo_nivel_label


@pytest.fixture
def cargos_catalogo(db):
    dev_senior = Cargo.objects.create(nome='Desenvolvedor Frontend', nivel=4)
    dev_pleno = Cargo.objects.create(nome='Desenvolvedor Backend', nivel=3)
    designer = Cargo.objects.create(
        nome='Designer UI/UX',
        nivel=2,
        is_active=False,
    )
    gerente = Cargo.objects.create(nome='Gerente de Projetos', nivel=4)
    return dev_senior, dev_pleno, designer, gerente


@pytest.fixture
def escala(db):
    return Escala.objects.create(
        nome='Escala Teste',
        valor_minimo=1,
        valor_maximo=5,
    )


def _vincular(cargo, escala, nome: str) -> None:
    competencia = Competencia.objects.create(
        nome=nome,
        tipo=Competencia.Tipo.TECNICA,
        escala=escala,
    )
    CargoCompetencia.objects.create(
        cargo=cargo,
        competencia=competencia,
        nivel_esperado='3.00',
        peso='1.00',
    )


def test_parse_nivel_filter_invalido():
    assert parse_nivel_filter('abc') is None
    assert parse_nivel_filter('-1') is None


def test_format_cargo_nivel_label():
    assert format_cargo_nivel_label(4) == 'Sênior'
    assert format_cargo_nivel_label(99) == '99'
    assert format_cargo_nivel_label(None) == '—'


def test_apply_cargo_list_filters(db, cargos_catalogo):
    dev_senior, dev_pleno, designer, gerente = cargos_catalogo
    base = get_base_cargo_list_queryset()

    ativos = apply_cargo_list_filters(base, status='ativo')
    assert dev_senior in ativos
    assert designer not in ativos

    inativos = apply_cargo_list_filters(base, status='inativo')
    assert designer in inativos
    assert dev_pleno not in inativos

    busca = apply_cargo_list_filters(base, busca='Frontend')
    assert dev_senior in busca
    assert dev_pleno not in busca

    por_nivel = apply_cargo_list_filters(base, nivel=4)
    assert dev_senior in por_nivel
    assert gerente in por_nivel
    assert dev_pleno not in por_nivel


def test_nivel_invalido_ignorado(db, cargos_catalogo):
    base = get_base_cargo_list_queryset()
    allowed = get_allowed_nivel_values(base)
    nivel = resolve_nivel_filter(999, allowed)
    assert nivel is None
    assert apply_cargo_list_filters(base, nivel=nivel).count() == base.count()


def test_admin_lista_cargos_com_tabela_padronizada(client, admin, cargos_catalogo):
    client.force_login(admin)
    url = reverse('organization:cargo_list')
    resp = client.get(url)
    assert resp.status_code == 200
    html = resp.content.decode()
    assert 'cargo-registry-table' in html
    assert 'filter-segment-bar' in html
    assert 'Buscar cargos...' in html
    assert 'Competências vinculadas' in html
    assert 'Mostrando' in html


def test_editar_link_preserva_estado_da_lista(client, admin, cargos_catalogo):
    dev_senior, _dev_pleno, _designer, _gerente = cargos_catalogo
    client.force_login(admin)
    list_path = reverse('organization:cargo_list')
    return_path = f'{list_path}?status=ativo&busca=Frontend'
    resp = client.get(return_path)
    assert resp.status_code == 200
    html = resp.content.decode()
    edit_fragment = reverse('organization:cargo_update', kwargs={'pk': dev_senior.pk})
    assert edit_fragment in html
    assert 'next=' in html
    assert 'Frontend' in html


def test_salvar_cargo_retorna_para_lista_filtrada(client, admin, cargos_catalogo):
    dev_senior, _dev_pleno, _designer, _gerente = cargos_catalogo
    client.force_login(admin)
    edit_url = reverse('organization:cargo_update', kwargs={'pk': dev_senior.pk})
    return_path = f'{reverse("organization:cargo_list")}?status=ativo&busca=Frontend'
    resp = client.post(
        f'{edit_url}?next={return_path}',
        data={
            'next': return_path,
            'nome': dev_senior.nome,
            'nivel': dev_senior.nivel,
            'is_active': 'on',
        },
    )
    assert resp.status_code == 302
    assert 'busca=Frontend' in resp['Location']
    assert 'status=ativo' in resp['Location']


def test_next_externo_ignorado_no_redirect(client, admin, cargos_catalogo):
    dev_senior, _dev_pleno, _designer, _gerente = cargos_catalogo
    client.force_login(admin)
    edit_url = reverse('organization:cargo_update', kwargs={'pk': dev_senior.pk})
    malicious_next = 'https://evil.example/phish'
    resp = client.post(
        f'{edit_url}?next={malicious_next}',
        data={
            'next': malicious_next,
            'nome': dev_senior.nome,
            'nivel': dev_senior.nivel,
            'is_active': 'on',
        },
    )
    assert resp.status_code == 302
    assert resp['Location'] == reverse('organization:cargo_list')


def test_admin_filtra_por_status(client, admin, cargos_catalogo):
    _dev_senior, _dev_pleno, designer, _gerente = cargos_catalogo
    client.force_login(admin)
    url = reverse('organization:cargo_list')
    resp = client.get(url, {'status': 'inativo'})
    html = resp.content.decode()
    assert designer.nome in html
    assert 'Desenvolvedor Frontend' not in html


def test_competencias_vinculadas_na_lista(client, admin, cargos_catalogo, escala):
    dev_senior, _dev_pleno, _designer, _gerente = cargos_catalogo
    _vincular(dev_senior, escala, 'Comunicação')
    _vincular(dev_senior, escala, 'Liderança')
    client.force_login(admin)
    resp = client.get(reverse('organization:cargo_list'))
    html = resp.content.decode()
    assert html.count('>2<') >= 1


def test_nao_admin_recebe_403(client, lider):
    client.force_login(lider)
    url = reverse('organization:cargo_list')
    resp = client.get(url)
    assert resp.status_code == 403
