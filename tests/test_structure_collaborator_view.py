"""Visão por colaborador na Estrutura — lista, drawer, AuthZ e timeline."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal

import pytest
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import CustomUser
from apps.accounts.services.scope import get_visible_users
from apps.audit.models import AuditLog
from apps.audit.services import write_audit_log
from apps.cycles.models import Ciclo
from apps.dashboard.services.collaborator_profile import (
    build_collaborator_drawer,
    build_structure_collaborator_rows,
)
from apps.organization.models import Area, Cargo
from apps.reviews.models import Avaliacao
from tests.conftest import DEFAULT_PASSWORD


def _structure_url(**params) -> str:
    url = reverse('dashboard:structure')
    if not params:
        return url
    from urllib.parse import urlencode

    return f'{url}?{urlencode(params)}'


def _drawer_url(user_pk: int, **params) -> str:
    url = reverse('dashboard:structure_collaborator_drawer', kwargs={'user_pk': user_pk})
    if not params:
        return url
    from urllib.parse import urlencode

    return f'{url}?{urlencode(params)}'


def _login(client: Client, user: CustomUser) -> None:
    assert client.login(username=user.email, password=DEFAULT_PASSWORD)


def _seed_closed_ciclo(*, nome: str, offset_days: int) -> Ciclo:
    today = date.today()
    return Ciclo.objects.create(
        nome=nome,
        data_inicio=today - timedelta(days=offset_days + 60),
        data_fim=today - timedelta(days=offset_days),
        status=Ciclo.Status.ENCERRADO,
    )


@pytest.fixture
def gerente(db, area, cargo_lider, lider, colaborador) -> CustomUser:
    """Garante is_manager (neto sob o líder)."""
    gerente = CustomUser.objects.create_user(
        email='gerente.estrutura@test.greenn.com.br',
        password=DEFAULT_PASSWORD,
        nome='Gerente Estrutura',
        cargo=cargo_lider,
        area=area,
        is_admin=False,
        data_entrada=date(2019, 1, 1),
        email_confirmado_em=timezone.now(),
    )
    lider.line_manager = gerente
    lider.save(update_fields=['line_manager'])
    assert gerente.is_manager
    return gerente


@pytest.mark.django_db
def test_structure_default_continua_visao_ciclo(admin, ciclo_aberto, client):
    _login(client, admin)
    resp = client.get(_structure_url())
    assert resp.status_code == 200
    assert resp.context['structure_visao'] == 'ciclo'
    assert b'Cobertura Total' in resp.content
    assert b'Vis\xc3\xa3o por colaborador' in resp.content


@pytest.mark.django_db
def test_structure_visao_colaborador_lista_no_escopo(
    admin,
    colaborador,
    ciclo_aberto,
    client,
):
    _login(client, admin)
    resp = client.get(_structure_url(visao='colaborador'))
    assert resp.status_code == 200
    assert resp.context['structure_visao'] == 'colaborador'
    emails = {row['usuario'].email for row in resp.context['colaboradores_resumo']}
    assert colaborador.email in emails
    assert admin.email not in emails
    assert b'Ver perfil' in resp.content


@pytest.mark.django_db
def test_structure_colaborador_respeita_escopo_gerente(
    gerente,
    colaborador,
    ciclo_aberto,
    client,
    area,
    cargo_colab,
):
    outsider = CustomUser.objects.create_user(
        email='outsider.estrutura@test.greenn.com.br',
        password=DEFAULT_PASSWORD,
        nome='Outsider',
        cargo=cargo_colab,
        area=area,
        data_entrada=date(2020, 1, 1),
        email_confirmado_em=timezone.now(),
    )
    _login(client, gerente)
    resp = client.get(_structure_url(visao='colaborador'))
    assert resp.status_code == 200
    emails = {row['usuario'].email for row in resp.context['colaboradores_resumo']}
    assert colaborador.email in emails
    assert outsider.email not in emails
    assert gerente.email not in emails


@pytest.mark.django_db
def test_structure_colaborador_htmx_pagina_so_partial(
    admin,
    colaborador,
    ciclo_aberto,
    client,
):
    """Paginação HTMX deve devolver só #list-container — nunca a página inteira."""
    _login(client, admin)
    url = _structure_url(visao='colaborador', page=2)
    # HTMX 2 envia o id sem ``#``.
    resp = client.get(
        url,
        HTTP_HX_REQUEST='true',
        HTTP_HX_TARGET='list-container',
    )
    assert resp.status_code == 200
    html = resp.content.decode()
    assert 'id="list-container"' in html
    assert 'Panorama da Estrutura' not in html
    assert 'Filtros de Estrutura' not in html
    assert 'Visão do ciclo' not in html
    assert 'id="structure-collaborator-drawer"' not in html
    assert 'Ver perfil' in html


@pytest.mark.django_db
def test_structure_colaborador_htmx_target_com_hash_ainda_partial(
    admin,
    colaborador,
    ciclo_aberto,
    client,
):
    _login(client, admin)
    resp = client.get(
        _structure_url(visao='colaborador', page=1),
        HTTP_HX_REQUEST='true',
        HTTP_HX_TARGET='#list-container',
    )
    assert resp.status_code == 200
    html = resp.content.decode()
    assert 'id="list-container"' in html
    assert 'Panorama da Estrutura' not in html


@pytest.mark.django_db
def test_structure_drawer_htmx_ok_no_escopo(
    admin,
    colaborador,
    ciclo_aberto,
    client,
):
    _login(client, admin)
    resp = client.get(
        _drawer_url(colaborador.pk, ciclo=ciclo_aberto.pk),
        HTTP_HX_REQUEST='true',
    )
    assert resp.status_code == 200
    assert colaborador.nome.encode() in resp.content
    assert b'Perfil do colaborador' in resp.content
    assert b'Enviar lembrete' not in resp.content


@pytest.mark.django_db
def test_structure_drawer_outsider_404(
    gerente,
    ciclo_aberto,
    client,
    area,
    cargo_colab,
):
    outsider = CustomUser.objects.create_user(
        email='outsider.drawer@test.greenn.com.br',
        password=DEFAULT_PASSWORD,
        nome='Outsider Drawer',
        cargo=cargo_colab,
        area=area,
        data_entrada=date(2020, 1, 1),
        email_confirmado_em=timezone.now(),
    )
    _login(client, gerente)
    resp = client.get(
        _drawer_url(outsider.pk, ciclo=ciclo_aberto.pk),
        HTTP_HX_REQUEST='true',
    )
    assert resp.status_code == 404


@pytest.mark.django_db
def test_structure_drawer_sem_htmx_redireciona(admin, colaborador, client):
    _login(client, admin)
    resp = client.get(_drawer_url(colaborador.pk))
    assert resp.status_code == 302
    assert 'visao=colaborador' in resp['Location']


@pytest.mark.django_db
def test_structure_lider_puro_403(lider, ciclo_aberto, client):
    assert lider.is_leader
    assert not lider.is_manager
    _login(client, lider)
    assert client.get(_structure_url(visao='colaborador')).status_code == 403
    assert client.get(
        _drawer_url(lider.pk),
        HTTP_HX_REQUEST='true',
    ).status_code == 403


@pytest.mark.django_db
def test_timeline_delta_e_avaliador_confiavel(
    admin,
    colaborador,
    lider,
    ciclo_aberto,
):
    ciclo_antigo = _seed_closed_ciclo(nome='Ciclo Antigo', offset_days=200)
    ciclo_meio = _seed_closed_ciclo(nome='Ciclo Meio', offset_days=100)

    Avaliacao.objects.create(
        ciclo=ciclo_antigo,
        usuario=colaborador,
        etapa=Avaliacao.Etapa.FEEDBACK,
        concluida=True,
        nota_final_lider=Decimal('0.8000'),
    )
    Avaliacao.objects.create(
        ciclo=ciclo_meio,
        usuario=colaborador,
        etapa=Avaliacao.Etapa.FEEDBACK,
        concluida=True,
        nota_final_lider=Decimal('0.8600'),
    )

    # Gestor mudou depois do ciclo antigo e antes do ciclo meio.
    change_at = timezone.make_aware(
        datetime.combine(
            ciclo_antigo.data_fim + timedelta(days=10),
            datetime.min.time(),
        ),
    )
    log = write_audit_log(
        acao=AuditLog.Acao.UPDATE,
        entity_type='accounts.CustomUser',
        entity_id=colaborador.pk,
        campo='line_manager_id',
        valor_anterior=str(lider.pk),
        valor_novo=str(admin.pk),
        usuario=admin,
    )
    AuditLog.objects.filter(pk=log.pk).update(created_at=change_at)

    visible = get_visible_users(admin).filter(is_active=True)
    payload = build_collaborator_drawer(visible, colaborador.pk, ciclo_aberto)
    assert payload is not None
    timeline = payload['timeline_preview'] + payload['timeline_older']
    by_nome = {item['ciclo'].nome: item for item in timeline}

    meio = by_nome['Ciclo Meio']
    assert meio['nota_display'] == '86%'
    assert meio['delta']['pp'] == 6
    assert meio['delta']['label'] == '+6pp'
    assert meio['avaliador_reliable'] is True
    assert meio['avaliador_nome'] == admin.nome

    antigo = by_nome['Ciclo Antigo']
    assert antigo['avaliador_reliable'] is True
    assert antigo['avaliador_nome'] == lider.nome


@pytest.mark.django_db
def test_timeline_sem_audit_omite_avaliador_historico(
    admin,
    colaborador,
    ciclo_aberto,
):
    ciclo_antigo = _seed_closed_ciclo(nome='Sem Audit', offset_days=120)
    Avaliacao.objects.create(
        ciclo=ciclo_antigo,
        usuario=colaborador,
        etapa=Avaliacao.Etapa.FEEDBACK,
        concluida=True,
        nota_final_lider=Decimal('0.7000'),
    )
    visible = get_visible_users(admin).filter(is_active=True)
    payload = build_collaborator_drawer(visible, colaborador.pk, ciclo_aberto)
    item = (payload['timeline_preview'] + payload['timeline_older'])[0]
    assert item['avaliador_reliable'] is False
    assert item['avaliador_nome'] is None


@pytest.mark.django_db
def test_timeline_nao_expoe_pii_gestor_fora_do_escopo(
    gerente,
    colaborador,
    lider,
    ciclo_aberto,
    area,
    cargo_colab,
    client,
):
    """Audit com line_manager outsider não deve vazar nome/e-mail no drawer."""
    outsider = CustomUser.objects.create_user(
        email='outsider.exgestor@test.greenn.com.br',
        password=DEFAULT_PASSWORD,
        nome='Outsider ExGestor Secreto',
        cargo=cargo_colab,
        area=area,
        data_entrada=date(2018, 1, 1),
        email_confirmado_em=timezone.now(),
    )
    ciclo_antigo = _seed_closed_ciclo(nome='Ciclo ExGestor', offset_days=150)
    Avaliacao.objects.create(
        ciclo=ciclo_antigo,
        usuario=colaborador,
        etapa=Avaliacao.Etapa.FEEDBACK,
        concluida=True,
        nota_final_lider=Decimal('0.7500'),
    )
    # Histórico: colaborador reportava ao outsider (fora da subárvore do gerente).
    change_at = timezone.make_aware(
        datetime.combine(
            ciclo_antigo.data_fim + timedelta(days=5),
            datetime.min.time(),
        ),
    )
    log = write_audit_log(
        acao=AuditLog.Acao.UPDATE,
        entity_type='accounts.CustomUser',
        entity_id=colaborador.pk,
        campo='line_manager_id',
        valor_anterior=str(outsider.pk),
        valor_novo=str(lider.pk),
        usuario=gerente,
    )
    AuditLog.objects.filter(pk=log.pk).update(created_at=change_at)

    visible = get_visible_users(gerente).filter(is_active=True)
    assert outsider.pk not in set(visible.values_list('pk', flat=True))

    payload = build_collaborator_drawer(visible, colaborador.pk, ciclo_aberto)
    assert payload is not None
    timeline = payload['timeline_preview'] + payload['timeline_older']
    antigo = next(item for item in timeline if item['ciclo'].nome == 'Ciclo ExGestor')
    assert antigo['avaliador_reliable'] is True
    assert antigo['avaliador_nome'] == 'Gestor anterior'
    assert outsider.nome not in (antigo['avaliador_nome'] or '')
    assert outsider.email not in (antigo['avaliador_nome'] or '')

    # Qualquer rótulo estrutural também não pode vazar PII do outsider.
    for item in timeline:
        for change in item.get('structural_changes') or []:
            assert outsider.nome not in change['text']
            assert outsider.email not in change['text']

    _login(client, gerente)
    resp = client.get(
        _drawer_url(colaborador.pk, ciclo=ciclo_aberto.pk),
        HTTP_HX_REQUEST='true',
    )
    assert resp.status_code == 200
    html = resp.content.decode()
    assert outsider.nome not in html
    assert outsider.email not in html
    assert 'Gestor anterior' in html


@pytest.mark.django_db
def test_rows_filtro_sem_avaliacao(admin, colaborador, ciclo_aberto):
    visible = get_visible_users(admin).filter(is_active=True)
    # Remove avaliação do colaborador no ciclo aberto.
    Avaliacao.objects.filter(ciclo=ciclo_aberto, usuario=colaborador).delete()
    rows = build_structure_collaborator_rows(
        visible,
        ciclo_aberto,
        status='sem_avaliacao',
        exclude_user_id=admin.pk,
    )
    emails = {r['usuario'].email for r in rows}
    assert colaborador.email in emails
    assert all(r['coverage'] == 'sem_avaliacao' for r in rows)


@pytest.mark.django_db
def test_drawer_link_avaliacao_completa(admin, colaborador, ciclo_aberto, client):
    av = Avaliacao.objects.get(ciclo=ciclo_aberto, usuario=colaborador)
    _login(client, admin)
    resp = client.get(
        _drawer_url(colaborador.pk, ciclo=ciclo_aberto.pk),
        HTTP_HX_REQUEST='true',
    )
    assert resp.status_code == 200
    assert reverse('reviews:detail', kwargs={'pk': av.pk}).encode() in resp.content
