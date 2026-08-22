"""AuthZ do GET ``cycles:ciclo_detail`` + T012 [US1] + T029 [US3].

Cobertura do contrato ``cycle-managerial-detail.md``:
- Admin → 200
- Não-admin autenticado → 403 (RequiresAdminMixin vigente)
- Anônimo → redirect login

T012: cabeçalho ``concluida`` sem nota → empty ``sem_nota`` em
desempenho/gap/aderência; pipeline de etapa MAY permanecer; copy não trata
como desempenho 100% saudável; AuthZ ``AdminCyclesMixin`` intacta.

T029: ``?visao=historico`` na URL existente ``cycles/<pk>/`` → barra 100%
empilhada de status/conclusão cap ``HISTORY_DEFAULT_N``; empty local de
desempenho; resto da página intacto; AuthZ intacta. Sem rota ``/historico/``.

Só view GET. Não altera asserts de negócio open/close / ``cycle.py``.
MUST NOT ``data/legado-solides/raw/``.
"""

from __future__ import annotations

from datetime import date
from urllib.parse import quote

import pytest
from django.test import Client
from django.urls import reverse

from apps.cycles.models import Ciclo
from apps.cycles.views import AdminCyclesMixin, CicloDetailView
from apps.dashboard.chart_payloads import (
    CHART_TYPE_AREA,
    CHART_TYPE_BAR,
    CHART_TYPE_BAR_HORIZONTAL,
    EMPTY_KIND_COPY,
    EMPTY_KIND_SEM_DADO,
    EMPTY_KIND_SEM_NOTA,
    HISTORY_DEFAULT_N,
)
from apps.reviews.models import Avaliacao


def _detail_url(ciclo) -> str:
    return reverse('cycles:ciclo_detail', kwargs={'pk': ciclo.pk})


@pytest.mark.django_db
def test_ciclo_detail_get_admin_200(admin, ciclo_aberto):
    """Admin autenticado obtém o painel gerencial (200)."""
    assert admin.is_admin

    client = Client()
    client.force_login(admin)
    resp = client.get(_detail_url(ciclo_aberto))

    assert resp.status_code == 200


@pytest.mark.django_db
def test_ciclo_detail_get_lider_403(lider, ciclo_aberto):
    """Líder autenticado (não-admin) é negado com 403."""
    assert not lider.is_admin
    assert lider.is_authenticated

    client = Client()
    client.force_login(lider)
    resp = client.get(_detail_url(ciclo_aberto))

    assert resp.status_code == 403


@pytest.mark.django_db
def test_ciclo_detail_get_colaborador_403(colaborador, ciclo_aberto):
    """Colaborador autenticado (não-admin) é negado com 403."""
    assert not colaborador.is_admin

    client = Client()
    client.force_login(colaborador)
    resp = client.get(_detail_url(ciclo_aberto))

    assert resp.status_code == 403


@pytest.mark.django_db
def test_ciclo_detail_get_anonimo_redirect_login(ciclo_aberto):
    """Anônimo é redirecionado para login (LoginRequiredMixin)."""
    client = Client()
    url = _detail_url(ciclo_aberto)
    resp = client.get(url)

    assert resp.status_code == 302
    login_url = reverse('accounts:login')
    assert resp.url.startswith(login_url)
    assert f'next={quote(url)}' in resp.url


# --- T028 / quickstart §3 (SC-002 parcial) ---------------------------------


@pytest.mark.django_db
def test_ciclo_detail_quickstart_s3_painel_secoes(admin, ciclo_aberto):
    """§3.1–3.2: lista → ``/cycles/<pk>/`` com KPI + progresso/cobertura/aderência/checklist."""
    client = Client()
    client.force_login(admin)

    detail_path = _detail_url(ciclo_aberto)
    assert detail_path == f'/cycles/{ciclo_aberto.pk}/'

    list_resp = client.get(reverse('cycles:ciclo_list'))
    assert list_resp.status_code == 200
    list_html = list_resp.content.decode()
    assert detail_path in list_html
    assert 'Visão gerencial' in list_html
    # Abrir/Encerrar permanece na lista (comportamento pré-feature).
    assert (
        reverse('cycles:ciclo_open', kwargs={'pk': ciclo_aberto.pk}) in list_html
        or reverse('cycles:ciclo_close', kwargs={'pk': ciclo_aberto.pk}) in list_html
    )

    resp = client.get(detail_path)
    assert resp.status_code == 200
    html = resp.content.decode()

    for needle in (
        'managerial-panel',
        'Progresso das avaliações',
        'Cobertura por área',
        'Cobertura por cargo',
        'Distribuição de aderência',
        'Checklist operacional',
        'chart.js@4.5.1',
        'dashboard_charts.js',
    ):
        assert needle in html, needle

    for key in (
        'chart_ciclo_progresso',
        'chart_cobertura_area',
        'chart_cobertura_cargo',
        'chart_aderencia_distribuicao',
        'rh_pre_open_checklist',
        'avaliacoes_resumo',
        'cobertura_resumo',
        'aderencia_resumo',
    ):
        assert key in resp.context, key

    checklist = resp.context['rh_pre_open_checklist']
    assert checklist.advisory_only is True
    assert 'data-advisory-only="true"' in html


@pytest.mark.django_db
def test_ciclo_detail_quickstart_s3_empty_local_sem_inventar(admin, db):
    """§3.4: ciclo sem avaliações/snapshots → empty local (has_data falso), sem inventar série."""
    from datetime import date, timedelta

    from apps.cycles.models import Ciclo

    ciclo = Ciclo.objects.create(
        nome='Ciclo vazio T028',
        data_inicio=date.today(),
        data_fim=date.today() + timedelta(days=30),
        status=Ciclo.Status.ENCERRADO,
    )
    client = Client()
    client.force_login(admin)
    resp = client.get(_detail_url(ciclo))
    assert resp.status_code == 200

    assert resp.context['chart_ciclo_progresso']['has_data'] is False
    assert resp.context['chart_aderencia_distribuicao']['has_data'] is False
    assert resp.context['chart_cobertura_area']['has_data'] is False
    assert resp.context['chart_cobertura_cargo']['has_data'] is False
    html = resp.content.decode()
    # Empty via _chart_block / empty_state — kinds D (012); sem série inventada.
    assert resp.context['chart_ciclo_progresso']['empty_message'] == (
        EMPTY_KIND_COPY[EMPTY_KIND_SEM_DADO]
    )
    assert 'chart-ciclo-progresso' in html or EMPTY_KIND_COPY[EMPTY_KIND_SEM_DADO] in html
    assert 'data-chart-payload="chart-cobertura-area"' not in html
    assert 'data-chart-payload="chart-cobertura-cargo"' not in html
    assert 'data-chart-payload="chart-aderencia-distribuicao"' not in html
    # Slots always present via _chart_block (titles + empty kinds), sem canvas.
    assert 'Cobertura por área' in html
    assert 'Cobertura por cargo' in html
    assert 'Distribuição de aderência' in html


# --- T012 [US1] / quickstart §1.5 (empty ``sem_nota``) ----------------------

_DESEMPENHO_CHART_KEYS = (
    'chart_aderencia_distribuicao',
    'chart_gaps_competencia',
    'chart_desempenho',
)


def _ciclo_legado_concluida_sem_nota(usuario, *, n_cabecalhos: int = 2) -> Ciclo:
    """Ciclo encerrado sintético: etapa terminal + ``concluida``, zero nota."""
    ciclo = Ciclo.objects.create(
        nome='Legado T012 concluida sem nota',
        data_inicio=date(2019, 1, 15),
        data_fim=date(2019, 12, 15),
        status=Ciclo.Status.ENCERRADO,
    )
    Avaliacao.objects.create(
        ciclo=ciclo,
        usuario=usuario,
        etapa=Avaliacao.Etapa.FEEDBACK,
        concluida=True,
        nota_final_lider=None,
        nota_final_autoavaliacao=None,
    )
    extras = list(
        usuario.__class__.objects.exclude(pk=usuario.pk).filter(
            is_admin=False,
            is_active=True,
        )[: n_cabecalhos - 1]
    )
    for extra in extras:
        Avaliacao.objects.create(
            ciclo=ciclo,
            usuario=extra,
            etapa=Avaliacao.Etapa.FEEDBACK,
            concluida=True,
            nota_final_lider=None,
            nota_final_autoavaliacao=None,
        )
    return ciclo


def _assert_empty_sem_nota(chart: dict) -> None:
    copy = EMPTY_KIND_COPY[EMPTY_KIND_SEM_NOTA]
    assert chart.get('has_data') is not True
    assert chart.get('empty_message') == copy
    assert list(chart.get('labels') or []) == []
    assert list(chart.get('values') or []) == []
    if 'series' in chart:
        assert list(chart.get('series') or []) == []


def test_ciclo_detail_authz_admin_cycles_mixin_intacta():
    """T012: AuthZ permanece ``AdminCyclesMixin`` (LoginRequired + admin)."""
    assert issubclass(CicloDetailView, AdminCyclesMixin)


@pytest.mark.django_db
def test_ciclo_detail_concluida_sem_nota_empty_desempenho_gap_aderencia(
    admin,
    colaborador,
):
    """§1.5: ``feedback`` + ``concluida`` sem nota → empty ``sem_nota``.

    Pipeline de etapa MAY permanecer. Doughnut/gap/desempenho não inventam
    saúde de nota. Copy canônica T006; sem gráfico fantasma.
    """
    ciclo = _ciclo_legado_concluida_sem_nota(colaborador)
    total = Avaliacao.objects.filter(ciclo=ciclo).count()
    assert total >= 1
    assert not Avaliacao.objects.filter(ciclo=ciclo).exclude(
        nota_final_lider=None,
        nota_final_autoavaliacao=None,
    ).exists()
    assert Avaliacao.objects.filter(
        ciclo=ciclo,
        concluida=True,
        etapa=Avaliacao.Etapa.FEEDBACK,
    ).count() == total

    client = Client()
    client.force_login(admin)
    resp = client.get(_detail_url(ciclo))

    assert resp.status_code == 200
    copy = EMPTY_KIND_COPY[EMPTY_KIND_SEM_NOTA]
    html = resp.content.decode()
    assert copy in html

    aderencia = resp.context['chart_aderencia_distribuicao']
    _assert_empty_sem_nota(aderencia)
    assert 'data-chart-payload="chart-aderencia-distribuicao"' not in html

    for key in _DESEMPENHO_CHART_KEYS:
        chart = resp.context.get(key)
        if chart is None:
            continue
        _assert_empty_sem_nota(chart)

    progresso = resp.context['chart_ciclo_progresso']
    # MAY: cabeçalhos com etapa alimentam o pipeline mesmo sem nota.
    if progresso.get('has_data') is True:
        assert progresso['type'] == CHART_TYPE_BAR_HORIZONTAL
        assert int(progresso.get('total') or 0) == total

    resumo = resp.context['avaliacoes_resumo']
    assert resumo['total'] == total
    assert resumo['concluidas'] == total
    assert resumo['percentual_concluidas'] is not None

    lowered = html.lower()
    assert 'saudável' not in lowered
    assert '100% saudável' not in lowered
    # FR-009: 100% concluídas ≠ desempenho completo (a copy deixa isso explícito).
    assert 'não significa desempenho completo' in lowered


@pytest.mark.django_db
def test_ciclo_detail_concluida_sem_nota_kpi_nao_e_saude_de_nota(
    admin,
    colaborador,
):
    """KPI de conclusão = processo/etapa, não saúde de desempenho."""
    ciclo = _ciclo_legado_concluida_sem_nota(colaborador)
    client = Client()
    client.force_login(admin)
    resp = client.get(_detail_url(ciclo))

    assert resp.status_code == 200
    html = resp.content.decode()
    copy = EMPTY_KIND_COPY[EMPTY_KIND_SEM_NOTA]
    assert copy in html
    assert 'Saúde do ciclo' not in html
    assert 'desempenho 100%' not in html.lower()
    # Percentual de conclusão, se visível, não substitui o empty de nota.
    assert 'data-chart-payload="chart-aderencia-distribuicao"' not in html


@pytest.mark.django_db
def test_ciclo_detail_concluida_sem_nota_lider_403(
    lider,
    colaborador,
):
    """AuthZ intacta: líder não-admin continua 403 no detalhe legado."""
    assert not lider.is_admin
    ciclo = _ciclo_legado_concluida_sem_nota(colaborador)
    client = Client()
    client.force_login(lider)
    resp = client.get(_detail_url(ciclo))
    assert resp.status_code == 403


# --- T029 [US3] / ``?visao=historico`` em ``cycles/<pk>/`` -------------------

_ARCHIVE_PREFIX = 'HIST-DETALHE-'
_N_ARQUIVO = 12
_N_ARQUIVO_CAP = 21
_COPY_SEM_NOTA = EMPTY_KIND_COPY[EMPTY_KIND_SEM_NOTA]


def _seed_arquivo_detalhe(
    *,
    n: int = _N_ARQUIVO,
    usuario=None,
) -> list[Ciclo]:
    """Ciclos encerrados sintéticos — nunca dump ``legado-solides/raw``."""
    ciclos: list[Ciclo] = []
    for i in range(n):
        year = 2000 + i
        ciclo = Ciclo.objects.create(
            nome=f'{_ARCHIVE_PREFIX}{year}',
            data_inicio=date(year, 1, 15),
            data_fim=date(year, 12, 15),
            status=Ciclo.Status.ENCERRADO,
        )
        ciclos.append(ciclo)
        if usuario is not None:
            Avaliacao.objects.create(
                ciclo=ciclo,
                usuario=usuario,
                etapa=Avaliacao.Etapa.FEEDBACK,
                concluida=True,
            )
    return ciclos


def _assert_history_stacked(chart: dict | None, *, max_labels: int = HISTORY_DEFAULT_N) -> None:
    assert chart is not None
    assert chart.get('has_data') is True
    assert chart.get('type') == CHART_TYPE_BAR
    assert chart.get('stacked') is True
    labels = list(chart.get('labels') or [])
    assert 1 <= len(labels) <= max_labels
    assert len(labels) <= HISTORY_DEFAULT_N


@pytest.mark.django_db
def test_ciclo_detail_sem_visao_permanece_operacional_nao_tendencia(
    admin,
    ciclo_aberto,
    colaborador,
):
    """Sem ``visao=``: pipeline do ``pk``; sem série ``area`` de tendência."""
    _seed_arquivo_detalhe(usuario=colaborador)
    client = Client()
    client.force_login(admin)
    resp = client.get(_detail_url(ciclo_aberto))

    assert resp.status_code == 200
    assert resp.context.get('visao') != 'historico'
    assert resp.context.get('chart_stage_history') is None
    progresso = resp.context['chart_ciclo_progresso']
    assert progresso['type'] == CHART_TYPE_BAR_HORIZONTAL
    assert progresso['type'] != CHART_TYPE_AREA
    html = resp.content.decode()
    assert 'data-chart-payload="chart-stage-history"' not in html
    assert _detail_url(ciclo_aberto) == f'/cycles/{ciclo_aberto.pk}/'
    assert '/historico/' not in html
    # T033: toggle GET na mesma URL; sem path /historico/.
    assert 'data-component="visao-toggle"' in html
    assert 'visao=historico' in html


@pytest.mark.django_db
def test_ciclo_detail_visao_historico_stacked_cap_n(
    admin,
    colaborador,
):
    """``?visao=historico`` em ``cycles/<pk>/``: barra empilhada ≤ ``HISTORY_DEFAULT_N``."""
    arquivo = _seed_arquivo_detalhe(n=_N_ARQUIVO_CAP, usuario=colaborador)
    assert len(arquivo) == _N_ARQUIVO_CAP
    assert _N_ARQUIVO_CAP > HISTORY_DEFAULT_N
    # Âncora = um ciclo do arquivo (pk já é escolha explícita).
    ancora = arquivo[-1]

    client = Client()
    client.force_login(admin)
    resp = client.get(_detail_url(ancora), {'visao': 'historico'})

    assert resp.status_code == 200
    assert _detail_url(ancora) == f'/cycles/{ancora.pk}/'
    assert resp.context.get('visao') == 'historico'
    history = resp.context['chart_stage_history']
    _assert_history_stacked(history)
    labels = list(history['labels'])
    assert len(labels) == HISTORY_DEFAULT_N
    assert len(labels) < len(arquivo)
    esperados = [c.nome for c in arquivo[-HISTORY_DEFAULT_N:]]
    assert labels == esperados

    html = resp.content.decode()
    assert 'data-chart-payload="chart-stage-history"' in html
    assert '/historico/' not in html


@pytest.mark.django_db
def test_ciclo_detail_visao_historico_empty_desempenho_local(
    admin,
    colaborador,
):
    """No modo histórico: empty ``sem_nota`` em desempenho/gap/aderência."""
    arquivo = _seed_arquivo_detalhe(n=_N_ARQUIVO, usuario=colaborador)
    ancora = arquivo[-1]

    client = Client()
    client.force_login(admin)
    resp = client.get(_detail_url(ancora), {'visao': 'historico'})

    assert resp.status_code == 200
    history = resp.context['chart_stage_history']
    _assert_history_stacked(history)

    for key in _DESEMPENHO_CHART_KEYS:
        chart = resp.context.get(key)
        if chart is None:
            continue
        _assert_empty_sem_nota(chart)

    html = resp.content.decode()
    assert _COPY_SEM_NOTA in html
    assert 'data-chart-payload="chart-aderencia-distribuicao"' not in html
    assert 'data-chart-payload="chart-stage-history"' in html


@pytest.mark.django_db
def test_ciclo_detail_visao_historico_resto_da_pagina_intacto(
    admin,
    colaborador,
):
    """Histórico no visual principal; cobertura/checklist/pipeline do ``pk`` seguem."""
    arquivo = _seed_arquivo_detalhe(n=_N_ARQUIVO, usuario=colaborador)
    ancora = arquivo[-1]

    client = Client()
    client.force_login(admin)
    resp = client.get(_detail_url(ancora), {'visao': 'historico'})

    assert resp.status_code == 200
    html = resp.content.decode()

    for needle in (
        'managerial-panel',
        'Cobertura por área',
        'Cobertura por cargo',
        'Checklist operacional',
        'chart.js@4.5.1',
        'dashboard_charts.js',
    ):
        assert needle in html, needle

    for key in (
        'chart_stage_history',
        'chart_ciclo_progresso',
        'chart_cobertura_area',
        'chart_cobertura_cargo',
        'rh_pre_open_checklist',
        'avaliacoes_resumo',
        'cobertura_resumo',
    ):
        assert key in resp.context, key

    # Pipeline do ``pk`` permanece no modo operacional (T032).
    progresso = resp.context['chart_ciclo_progresso']
    assert progresso['type'] == CHART_TYPE_BAR_HORIZONTAL
    assert progresso.get('has_data') is True

    checklist = resp.context['rh_pre_open_checklist']
    assert checklist.advisory_only is True
    assert 'data-advisory-only="true"' in html


@pytest.mark.django_db
def test_ciclo_detail_visao_historico_authz_lider_403(
    lider,
    colaborador,
):
    """AuthZ intacta: líder não-admin continua 403 mesmo com ``visao=historico``."""
    assert not lider.is_admin
    arquivo = _seed_arquivo_detalhe(n=3, usuario=colaborador)
    client = Client()
    client.force_login(lider)
    resp = client.get(_detail_url(arquivo[-1]), {'visao': 'historico'})
    assert resp.status_code == 403


@pytest.mark.django_db
def test_ciclo_detail_visao_historico_ciclos_cap_n(
    admin,
    colaborador,
):
    """``?ciclos=`` na mesma URL: só ids pedidos; cap ``HISTORY_DEFAULT_N``."""
    arquivo = _seed_arquivo_detalhe(n=_N_ARQUIVO_CAP, usuario=colaborador)
    pedidos = arquivo[:10]
    assert len(pedidos) > HISTORY_DEFAULT_N
    ciclos_param = ','.join(str(c.pk) for c in pedidos)
    ancora = arquivo[-1]

    client = Client()
    client.force_login(admin)
    resp = client.get(
        _detail_url(ancora),
        {'visao': 'historico', 'ciclos': ciclos_param},
    )

    assert resp.status_code == 200
    history = resp.context['chart_stage_history']
    _assert_history_stacked(history)
    labels = list(history['labels'])
    assert len(labels) == HISTORY_DEFAULT_N
    assert labels == [c.nome for c in pedidos[:HISTORY_DEFAULT_N]]
    omitidos = {c.nome for c in pedidos[HISTORY_DEFAULT_N:]}
    assert omitidos.isdisjoint(set(labels))
