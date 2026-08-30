"""Testes de filtros e segurança da listagem operacional de avaliações."""

from __future__ import annotations

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import CustomUser
from apps.organization.models import Area, Cargo
from apps.reviews.models import Avaliacao
from apps.reviews.services.team_avaliacao_list import (
    apply_team_list_filters,
    get_allowed_area_ids,
    get_area_filter_options,
    parse_area_filter,
    parse_etapa_filter,
    parse_status_filter,
    resolve_area_filter,
)
from tests.conftest import DEFAULT_PASSWORD, FIXTURE_DATA_ENTRADA


@pytest.fixture
def duas_areas(db):
    area_ti = Area.objects.create(nome='Tecnologia')
    area_rh = Area.objects.create(nome='Recursos Humanos')
    cargo = Cargo.objects.create(nome='Analista', nivel=1)
    return area_ti, area_rh, cargo


@pytest.fixture
def hierarquia_duas_areas(db, admin, duas_areas, ciclo_aberto):
    """Dois líderes irmãos, cada um com colaborador em área distinta."""
    area_ti, area_rh, cargo = duas_areas
    lider_ti = CustomUser.objects.create_user(
        email='lider.ti@test.greenn.com.br',
        password=DEFAULT_PASSWORD,
        nome='Líder TI',
        area=area_ti,
        line_manager=admin,
        data_entrada=FIXTURE_DATA_ENTRADA,
        email_confirmado_em=timezone.now(),
    )
    lider_rh = CustomUser.objects.create_user(
        email='lider.rh@test.greenn.com.br',
        password=DEFAULT_PASSWORD,
        nome='Líder RH',
        area=area_rh,
        line_manager=admin,
        data_entrada=FIXTURE_DATA_ENTRADA,
        email_confirmado_em=timezone.now(),
    )
    colab_ti = CustomUser.objects.create_user(
        email='colab.ti@test.greenn.com.br',
        password=DEFAULT_PASSWORD,
        nome='Colab TI',
        cargo=cargo,
        area=area_ti,
        line_manager=lider_ti,
        data_entrada=FIXTURE_DATA_ENTRADA,
        email_confirmado_em=timezone.now(),
    )
    colab_rh = CustomUser.objects.create_user(
        email='colab.rh@test.greenn.com.br',
        password=DEFAULT_PASSWORD,
        nome='Colab RH',
        cargo=cargo,
        area=area_rh,
        line_manager=lider_rh,
        data_entrada=FIXTURE_DATA_ENTRADA,
        email_confirmado_em=timezone.now(),
    )
    aval_ti, _ = Avaliacao.objects.get_or_create(
        ciclo=ciclo_aberto,
        usuario=colab_ti,
        defaults={'etapa': Avaliacao.Etapa.INPUT_METAS},
    )
    aval_rh, _ = Avaliacao.objects.get_or_create(
        ciclo=ciclo_aberto,
        usuario=colab_rh,
        defaults={'etapa': Avaliacao.Etapa.INPUT_METAS},
    )
    return {
        'area_ti': area_ti,
        'area_rh': area_rh,
        'lider_ti': lider_ti,
        'lider_rh': lider_rh,
        'colab_ti': colab_ti,
        'colab_rh': colab_rh,
        'aval_ti': aval_ti,
        'aval_rh': aval_rh,
    }


@pytest.mark.django_db
def test_parse_filters_invalidos():
    assert parse_status_filter('invalido') == ''
    assert parse_etapa_filter('invalido') == ''
    assert parse_area_filter('abc') is None


@pytest.mark.django_db
def test_resolve_area_filter_rejeita_fora_do_escopo():
    allowed = frozenset({1, 2})
    assert resolve_area_filter(1, allowed) == 1
    assert resolve_area_filter(99, allowed) is None


@pytest.mark.django_db
def test_apply_status_filter_pendente(ciclo_aberto, colaborador, avaliacao):
    avaliacao.etapa = Avaliacao.Etapa.APROVACAO_METAS
    avaliacao.concluida = False
    avaliacao.save(update_fields=['etapa', 'concluida', 'updated_at'])

    base = Avaliacao.objects.filter(ciclo=ciclo_aberto)
    filtrado = apply_team_list_filters(base, status='pendente')
    assert list(filtrado.values_list('pk', flat=True)) == [avaliacao.pk]


@pytest.mark.django_db
def test_admin_filtra_por_area(client, admin, hierarquia_duas_areas):
    ctx = hierarquia_duas_areas
    client.force_login(admin)
    url = reverse('reviews:list')

    response = client.get(url, {'area': ctx['area_ti'].pk})
    html = response.content.decode()
    assert response.status_code == 200
    assert ctx['colab_ti'].nome in html
    assert ctx['colab_rh'].nome not in html


@pytest.mark.django_db
def test_lider_so_ve_opcoes_de_area_do_escopo(client, hierarquia_duas_areas):
    ctx = hierarquia_duas_areas
    client.force_login(ctx['lider_ti'])
    response = client.get(reverse('reviews:list'))
    html = response.content.decode()

    assert response.status_code == 200
    assert ctx['colab_ti'].nome in html
    assert ctx['colab_rh'].nome not in html
    assert 'Tecnologia' in html
    assert 'Recursos Humanos' not in html


@pytest.mark.django_db
def test_lider_nao_vaza_com_area_fora_do_escopo(client, hierarquia_duas_areas):
    """``?area=`` de outra estrutura é ignorado — escopo permanece intacto."""
    ctx = hierarquia_duas_areas
    client.force_login(ctx['lider_ti'])
    response = client.get(
        reverse('reviews:list'),
        {'area': ctx['area_rh'].pk},
    )
    html = response.content.decode()

    assert response.status_code == 200
    assert ctx['colab_ti'].nome in html
    assert ctx['colab_rh'].nome not in html


@pytest.mark.django_db
def test_lider_rh_nao_ve_colab_ti(client, hierarquia_duas_areas):
    ctx = hierarquia_duas_areas
    client.force_login(ctx['lider_rh'])
    response = client.get(reverse('reviews:list'))
    html = response.content.decode()

    assert ctx['colab_rh'].nome in html
    assert ctx['colab_ti'].nome not in html


@pytest.mark.django_db
def test_filtro_etapa(client, admin, hierarquia_duas_areas):
    ctx = hierarquia_duas_areas
    ctx['aval_ti'].etapa = Avaliacao.Etapa.AVALIACAO
    ctx['aval_ti'].save(update_fields=['etapa', 'updated_at'])
    ctx['aval_rh'].etapa = Avaliacao.Etapa.INPUT_METAS
    ctx['aval_rh'].save(update_fields=['etapa', 'updated_at'])

    client.force_login(admin)
    response = client.get(reverse('reviews:list'), {'etapa': 'avaliacao'})
    html = response.content.decode()

    assert ctx['colab_ti'].nome in html
    assert ctx['colab_rh'].nome not in html


@pytest.mark.django_db
def test_filtro_status_em_andamento(client, admin, hierarquia_duas_areas):
    ctx = hierarquia_duas_areas
    ctx['aval_ti'].etapa = Avaliacao.Etapa.AVALIACAO
    ctx['aval_ti'].concluida = False
    ctx['aval_ti'].save(update_fields=['etapa', 'concluida', 'updated_at'])
    ctx['aval_rh'].concluida = True
    ctx['aval_rh'].save(update_fields=['concluida', 'updated_at'])

    client.force_login(admin)
    response = client.get(reverse('reviews:list'), {'status': 'em_andamento'})
    html = response.content.decode()

    assert ctx['colab_ti'].nome in html
    assert ctx['colab_rh'].nome not in html


@pytest.mark.django_db
def test_area_options_derivadas_do_escopo(hierarquia_duas_areas, ciclo_aberto):
    ctx = hierarquia_duas_areas
    base_admin = Avaliacao.objects.filter(ciclo=ciclo_aberto)
    opcoes_admin = get_area_filter_options(base_admin)
    nomes_admin = {item['nome'] for item in opcoes_admin}
    assert 'Tecnologia' in nomes_admin
    assert 'Recursos Humanos' in nomes_admin

    base_lider_ti = base_admin.filter(usuario__line_manager=ctx['lider_ti'])
    opcoes_lider = get_area_filter_options(base_lider_ti)
    assert len(opcoes_lider) == 1
    assert opcoes_lider[0]['nome'] == 'Tecnologia'
    assert get_allowed_area_ids(base_lider_ti) == frozenset({ctx['area_ti'].pk})


@pytest.mark.django_db
def test_gestor_filtra_area_na_subarvore(db, client, admin, duas_areas, ciclo_aberto):
    """Gestor com liderados em áreas distintas filtra só o que está no escopo."""
    area_ti, area_rh, cargo = duas_areas
    gestor = CustomUser.objects.create_user(
        email='gestor@test.greenn.com.br',
        password=DEFAULT_PASSWORD,
        nome='Gestor Multi',
        area=area_ti,
        line_manager=admin,
        data_entrada=FIXTURE_DATA_ENTRADA,
        email_confirmado_em=timezone.now(),
    )
    lider_ti = CustomUser.objects.create_user(
        email='gestor.lider.ti@test.greenn.com.br',
        password=DEFAULT_PASSWORD,
        nome='Líder sob Gestor TI',
        area=area_ti,
        line_manager=gestor,
        data_entrada=FIXTURE_DATA_ENTRADA,
        email_confirmado_em=timezone.now(),
    )
    lider_rh = CustomUser.objects.create_user(
        email='gestor.lider.rh@test.greenn.com.br',
        password=DEFAULT_PASSWORD,
        nome='Líder sob Gestor RH',
        area=area_rh,
        line_manager=gestor,
        data_entrada=FIXTURE_DATA_ENTRADA,
        email_confirmado_em=timezone.now(),
    )
    colab_ti = CustomUser.objects.create_user(
        email='gestor.colab.ti@test.greenn.com.br',
        password=DEFAULT_PASSWORD,
        nome='Folha TI Gestor',
        cargo=cargo,
        area=area_ti,
        line_manager=lider_ti,
        data_entrada=FIXTURE_DATA_ENTRADA,
        email_confirmado_em=timezone.now(),
    )
    colab_rh = CustomUser.objects.create_user(
        email='gestor.colab.rh@test.greenn.com.br',
        password=DEFAULT_PASSWORD,
        nome='Folha RH Gestor',
        cargo=cargo,
        area=area_rh,
        line_manager=lider_rh,
        data_entrada=FIXTURE_DATA_ENTRADA,
        email_confirmado_em=timezone.now(),
    )
    for usuario in (colab_ti, colab_rh):
        Avaliacao.objects.get_or_create(
            ciclo=ciclo_aberto,
            usuario=usuario,
            defaults={'etapa': Avaliacao.Etapa.INPUT_METAS},
        )

    client.force_login(gestor)
    url = reverse('reviews:list')

    response_all = client.get(url)
    html_all = response_all.content.decode()
    assert colab_ti.nome in html_all
    assert colab_rh.nome in html_all

    response_ti = client.get(url, {'area': area_ti.pk})
    html_ti = response_ti.content.decode()
    assert colab_ti.nome in html_ti
    assert colab_rh.nome not in html_ti

    response_fora = client.get(url, {'area': 99999})
    html_fora = response_fora.content.decode()
    assert colab_ti.nome in html_fora
    assert colab_rh.nome in html_fora
