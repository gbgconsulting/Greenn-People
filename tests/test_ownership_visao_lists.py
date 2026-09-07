"""Fatia próprias vs equipe em Metas/PDI — escopo só no backend."""

from __future__ import annotations

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import CustomUser
from apps.accounts.services.scope import (
    VISAO_EQUIPE,
    VISAO_PROPRIAS,
    apply_ownership_visao,
    can_view_team_ownership_list,
    resolve_ownership_visao,
)
from apps.goals.models import Meta
from apps.pdi.models import PDI
from tests.conftest import DEFAULT_PASSWORD, FIXTURE_DATA_ENTRADA


@pytest.fixture
def outsider(db, area, cargo_colab) -> CustomUser:
    return CustomUser.objects.create_user(
        email='outsider-ownership@test.greenn.com.br',
        password=DEFAULT_PASSWORD,
        nome='Outsider Ownership',
        area=area,
        cargo=cargo_colab,
        data_entrada=FIXTURE_DATA_ENTRADA,
        email_confirmado_em=timezone.now(),
    )


@pytest.fixture
def meta_lider(lider, objetivo) -> Meta:
    return Meta.objects.create(
        usuario=lider,
        objetivo_estrategico=objetivo,
        descricao='Meta do próprio líder',
    )


@pytest.fixture
def meta_outsider(outsider, objetivo) -> Meta:
    return Meta.objects.create(
        usuario=outsider,
        objetivo_estrategico=objetivo,
        descricao='Meta fora do escopo',
    )


@pytest.fixture
def pdi_colaborador(colaborador) -> PDI:
    return PDI.objects.create(
        usuario=colaborador,
        titulo='PDI do colaborador',
        status=PDI.Status.ATIVO,
    )


@pytest.fixture
def pdi_lider(lider) -> PDI:
    return PDI.objects.create(
        usuario=lider,
        titulo='PDI do líder',
        status=PDI.Status.ATIVO,
    )


@pytest.fixture
def pdi_outsider(outsider) -> PDI:
    return PDI.objects.create(
        usuario=outsider,
        titulo='PDI fora do escopo',
        status=PDI.Status.ATIVO,
    )


# --- helpers unitários ---


@pytest.mark.django_db
def test_resolve_ownership_visao_colaborador_ignora_equipe(colaborador):
    assert can_view_team_ownership_list(colaborador) is False
    assert resolve_ownership_visao(colaborador, VISAO_EQUIPE) == VISAO_PROPRIAS
    assert resolve_ownership_visao(colaborador, None) == VISAO_PROPRIAS


@pytest.mark.django_db
def test_resolve_ownership_visao_lider_aceita_equipe(lider, colaborador):
    # ``colaborador`` torna ``lider.is_leader`` verdadeiro (hierarquia).
    assert colaborador.line_manager_id == lider.pk
    assert can_view_team_ownership_list(lider) is True
    assert resolve_ownership_visao(lider, VISAO_EQUIPE) == VISAO_EQUIPE
    assert resolve_ownership_visao(lider, None) == VISAO_PROPRIAS
    assert resolve_ownership_visao(lider, 'invalido') == VISAO_PROPRIAS


@pytest.mark.django_db
def test_apply_ownership_visao_nao_amplia_qs(lider, meta, meta_lider, meta_outsider):
    """apply_ownership_visao só fatia; não deve trazer outsider se QS já scoped."""
    from apps.accounts.services.scope import get_visible_users

    scoped = Meta.objects.filter(usuario__in=get_visible_users(lider))
    proprias = apply_ownership_visao(scoped, lider, VISAO_PROPRIAS)
    equipe = apply_ownership_visao(scoped, lider, VISAO_EQUIPE)

    assert list(proprias) == [meta_lider]
    assert list(equipe) == [meta]
    assert meta_outsider not in proprias
    assert meta_outsider not in equipe


# --- Metas ---


@pytest.mark.django_db
def test_meta_list_default_lider_so_proprias(
    client,
    lider,
    meta,
    meta_lider,
    meta_outsider,
):
    client.login(email=lider.email, password=DEFAULT_PASSWORD)
    resp = client.get(reverse('goals:meta_list'))

    assert resp.status_code == 200
    assert resp.context['visao'] == VISAO_PROPRIAS
    assert resp.context['mostrar_toggle_visao'] is True
    assert list(resp.context['metas']) == [meta_lider]
    html = resp.content.decode()
    assert 'data-component="ownership-visao-toggle"' in html
    assert 'Minhas' in html


@pytest.mark.django_db
def test_meta_list_visao_equipe_exclui_self_e_outsider(
    client,
    lider,
    meta,
    meta_lider,
    meta_outsider,
):
    client.login(email=lider.email, password=DEFAULT_PASSWORD)
    resp = client.get(reverse('goals:meta_list'), {'visao': VISAO_EQUIPE})

    assert resp.status_code == 200
    assert resp.context['visao'] == VISAO_EQUIPE
    assert list(resp.context['metas']) == [meta]
    assert meta_lider not in resp.context['metas']
    assert meta_outsider not in resp.context['metas']


@pytest.mark.django_db
def test_meta_list_colaborador_visao_equipe_nao_vaza(
    client,
    colaborador,
    meta,
    meta_outsider,
):
    """Colaborador pedindo equipe continua só no self (pedido ignorado)."""
    client.login(email=colaborador.email, password=DEFAULT_PASSWORD)
    resp = client.get(reverse('goals:meta_list'), {'visao': VISAO_EQUIPE})

    assert resp.status_code == 200
    assert resp.context['visao'] == VISAO_PROPRIAS
    assert resp.context['mostrar_toggle_visao'] is False
    assert list(resp.context['metas']) == [meta]
    assert 'data-component="ownership-visao-toggle"' not in resp.content.decode()


@pytest.mark.django_db
def test_meta_list_usuario_tem_precedencia_sobre_visao(
    client,
    lider,
    colaborador,
    meta,
    meta_lider,
):
    client.login(email=lider.email, password=DEFAULT_PASSWORD)
    resp = client.get(
        reverse('goals:meta_list'),
        {'usuario': colaborador.pk, 'visao': VISAO_PROPRIAS},
    )

    assert resp.status_code == 200
    assert resp.context['revisando_colaborador'] is True
    assert resp.context['mostrar_toggle_visao'] is False
    assert list(resp.context['metas']) == [meta]


# --- PDI ---


@pytest.mark.django_db
def test_pdi_list_default_lider_so_proprias(
    client,
    lider,
    pdi_lider,
    pdi_colaborador,
    pdi_outsider,
):
    client.login(email=lider.email, password=DEFAULT_PASSWORD)
    resp = client.get(reverse('pdi:list'))

    assert resp.status_code == 200
    assert resp.context['visao'] == VISAO_PROPRIAS
    assert resp.context['mostrar_toggle_visao'] is True
    assert resp.context['mostrar_empty_porta'] is False
    pdi_ids = {row['pdi'].pk for row in resp.context['pdi_rows']}
    assert pdi_ids == {pdi_lider.pk}


@pytest.mark.django_db
def test_pdi_list_visao_equipe_exclui_self_e_outsider(
    client,
    lider,
    pdi_lider,
    pdi_colaborador,
    pdi_outsider,
):
    client.login(email=lider.email, password=DEFAULT_PASSWORD)
    resp = client.get(reverse('pdi:list'), {'visao': VISAO_EQUIPE})

    assert resp.status_code == 200
    assert resp.context['visao'] == VISAO_EQUIPE
    pdi_ids = {row['pdi'].pk for row in resp.context['pdi_rows']}
    assert pdi_ids == {pdi_colaborador.pk}
    assert pdi_outsider.pk not in pdi_ids
    assert pdi_lider.pk not in pdi_ids


@pytest.mark.django_db
def test_pdi_list_colaborador_visao_equipe_nao_vaza(
    client,
    colaborador,
    pdi_colaborador,
    pdi_outsider,
):
    client.login(email=colaborador.email, password=DEFAULT_PASSWORD)
    resp = client.get(reverse('pdi:list'), {'visao': VISAO_EQUIPE})

    assert resp.status_code == 200
    assert resp.context['visao'] == VISAO_PROPRIAS
    assert resp.context['mostrar_toggle_visao'] is False
    pdi_ids = {row['pdi'].pk for row in resp.context['pdi_rows']}
    assert pdi_ids == {pdi_colaborador.pk}
    assert pdi_outsider.pk not in pdi_ids
