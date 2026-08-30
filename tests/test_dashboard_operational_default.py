"""T011 / T018 [US1] + T022 [US2] — default operacional (admin / time / estrutura / aderência / pessoal).

Contrato: ``density-history-empty.md`` §1 / FR-001 / FR-002 / FR-004 / FR-017.
GET ``/dashboard/admin/``: ciclo aberto ou empty ``operacional``; ``?ciclo=``
só com intenção explícita; ``percentual_encerrados`` não é KPI de saúde.
GET ``/cycles/``: aberto em Operacional; arquivo paginado (``paginate_by=5`` na lista de cards);
partial sem ``_chart_block``.
GET ``/dashboard/team|structure|adherence/``: mesmo default aberto + empty
``operacional`` / ``escopo``; ``?ciclo=`` explícito; pipeline/KPIs só do escopo.

Não altera asserts de stage/scope; denylist intacta.
Fixtures sintéticas (12–21 ciclos encerrados); MUST NOT ``data/legado-solides/raw/``.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import CustomUser
from apps.core.mixins import HtmxPaginatedListMixin
from apps.cycles.models import Ciclo
from apps.cycles.views import CicloListView
from apps.dashboard.chart_payloads import (
    CHART_TYPE_BAR,
    CHART_TYPE_BAR_HORIZONTAL,
    CHART_TYPE_DOUGHNUT,
    EMPTY_KIND_COPY,
    EMPTY_KIND_ESCOPO,
    EMPTY_KIND_OPERACIONAL,
    EMPTY_KIND_SEM_DADO,
    EMPTY_KIND_SEM_NOTA,
    SEM_AVALIACAO_KEY,
)
from apps.dashboard.models import AderenciaSnapshot
from apps.reviews.models import Avaliacao
from tests.conftest import DEFAULT_PASSWORD, FIXTURE_DATA_ENTRADA

ARCHIVE_PREFIX = 'ARQ-LEGADO-'
N_ARQUIVO = 12
_ADMIN_CHART_KEYS = (
    'chart_ciclo_progresso',
    'chart_aderencia_distribuicao',
)


def _admin_url() -> str:
    return reverse('dashboard:admin')


def _login_admin(admin) -> Client:
    client = Client()
    client.force_login(admin)
    return client


def _seed_arquivo(
    *,
    n: int = N_ARQUIVO,
    usuario=None,
    etapa: str | None = None,
) -> list[Ciclo]:
    """12–20 ciclos encerrados sintéticos — nunca dump ``legado-solides/raw``."""
    etapa_val = etapa or Avaliacao.Etapa.FEEDBACK
    ciclos: list[Ciclo] = []
    for i in range(n):
        year = 2010 + i
        ciclo = Ciclo.objects.create(
            nome=f'{ARCHIVE_PREFIX}{year}',
            data_inicio=date(year, 1, 15),
            data_fim=date(year, 12, 15),
            status=Ciclo.Status.ENCERRADO,
        )
        ciclos.append(ciclo)
        if usuario is not None:
            Avaliacao.objects.create(
                ciclo=ciclo,
                usuario=usuario,
                etapa=etapa_val,
                concluida=True,
            )
    return ciclos


def _usuarios_extra(n: int, *, area, cargo_colab, lider) -> list[CustomUser]:
    users: list[CustomUser] = []
    for i in range(n):
        users.append(
            CustomUser.objects.create_user(
                email=f'arq{i}@test.greenn.com.br',
                password=DEFAULT_PASSWORD,
                nome=f'Arquivo User {i}',
                cargo=cargo_colab,
                area=area,
                line_manager=lider,
                email_confirmado_em=timezone.now(),
            ),
        )
    return users


def _pipeline_total(chart: dict | None) -> int:
    if not chart:
        return 0
    if chart.get('has_data') is not True:
        return 0
    return int(chart.get('total') or 0)


def _pipeline_count(chart: dict | None, etapa_key: str) -> int:
    if not chart or chart.get('has_data') is not True:
        return 0
    keys = list(chart.get('keys') or [])
    values = list(chart.get('values') or [])
    if keys:
        return int(dict(zip(keys, values)).get(etapa_key, 0) or 0)
    labels = list(chart.get('labels') or [])
    label = dict(Avaliacao.Etapa.choices).get(etapa_key, etapa_key)
    if label in labels:
        return int(values[labels.index(label)] or 0)
    return 0


def _assert_empty_operacional(resp) -> None:
    """Home gerencial sem aberto: empty ``operacional``, sem série do arquivo."""
    copy = EMPTY_KIND_COPY[EMPTY_KIND_OPERACIONAL]
    html = resp.content.decode()
    assert copy in html

    indicador = resp.context.get('ciclo_indicador')
    assert indicador is None

    aberto = resp.context.get('ciclo_aberto')
    assert aberto is None

    for key in _ADMIN_CHART_KEYS:
        chart = resp.context.get(key)
        if chart is None:
            continue
        assert chart.get('has_data') is not True
        assert list(chart.get('labels') or []) == []
        assert list(chart.get('values') or []) == []
        assert chart.get('empty_message') == copy

    assert 'data-chart-payload="chart-ciclo-progresso"' not in html
    assert 'data-chart-payload="chart-aderencia-distribuicao"' not in html
    # T009/T014: empty operacional via ``_chart_block`` nos slots pipeline +
    # aderência (não ``<p>`` ad hoc; sem canvas ``data-chart-payload``).
    assert 'id="pipeline-heading"' in html
    assert 'id="aderencia-heading"' in html
    assert 'id="visualizacoes-heading"' not in html
    assert html.count('role="status"') >= 2
    progresso = resp.context.get('chart_ciclo_progresso') or {}
    assert progresso.get('empty_message') == copy
    aderencia = resp.context.get('chart_aderencia_distribuicao') or {}
    assert aderencia.get('empty_message') == copy
    assert copy in html
    for nome in Ciclo.objects.filter(status=Ciclo.Status.ENCERRADO).values_list(
        'nome',
        flat=True,
    ):
        for key in _ADMIN_CHART_KEYS:
            chart = resp.context.get(key) or {}
            assert nome not in list(chart.get('labels') or [])


def _assert_percentual_encerrados_nao_e_kpi(resp) -> None:
    """FR-004: % do arquivo Sólides não conta como saúde da operação."""
    html = resp.content.decode()
    assert 'Ciclos encerrados' not in html
    assert 'Indicadores de governança' not in html
    resumo = resp.context.get('ciclos_resumo') or {}
    assert 'percentual_encerrados' not in resumo
    assert 'Em avaliação' in html
    assert 'Pendências' in html
    assert 'Sem avaliação' in html


# --- Sem ciclo aberto (quickstart §1.1 / 1.2) ---------------------------------


@pytest.mark.django_db
def test_admin_sem_ciclo_aberto_empty_operacional(admin, colaborador):
    """Dezenas de encerrados + zero aberto → empty operacional, sem fallback."""
    assert not Ciclo.objects.filter(status=Ciclo.Status.ABERTO).exists()
    arquivo = _seed_arquivo(usuario=colaborador)
    assert len(arquivo) == N_ARQUIVO
    assert all(c.status == Ciclo.Status.ENCERRADO for c in arquivo)

    client = _login_admin(admin)
    resp = client.get(_admin_url())

    assert resp.status_code == 200
    _assert_empty_operacional(resp)
    _assert_percentual_encerrados_nao_e_kpi(resp)

    resumo = resp.context.get('avaliacoes_resumo') or {}
    assert resumo.get('total', 0) == 0
    kpis = resp.context.get('ciclo_kpis') or {}
    assert kpis.get('has_ciclo') is False
    assert kpis.get('total') is None
    html = resp.content.decode()
    assert 'name="ciclo"' not in html
    resp_hist = client.get(_admin_url(), {'visao': 'historico'})
    html_hist = resp_hist.content.decode()
    assert f'{N_ARQUIVO} ciclos encerrados' in html_hist
    assert 'name="ciclo"' in html_hist


@pytest.mark.django_db
def test_admin_sem_ciclo_aberto_nao_seleciona_encerrado_implicito(
    admin,
    colaborador,
):
    """``ciclo_indicador`` / último encerrado MUST NOT virar default da home."""
    arquivo = _seed_arquivo(usuario=colaborador)
    mais_recente = arquivo[-1]

    client = _login_admin(admin)
    resp = client.get(_admin_url())

    assert resp.status_code == 200
    html = resp.content.decode()
    # Visão operacional: sem seletor; arquivo fica no histórico.
    assert 'name="ciclo"' not in html
    assert resp.context.get('ciclo_indicador') is None
    assert resp.context.get('ciclo_selecionado') is None
    progresso = resp.context.get('chart_ciclo_progresso') or {}
    assert progresso.get('has_data') is not True
    assert _pipeline_total(progresso) == 0
    html_hist = client.get(_admin_url(), {'visao': 'historico'}).content.decode()
    assert 'name="ciclo"' in html_hist
    assert f'value="{mais_recente.pk}"' in html_hist


# --- Com ciclo aberto (quickstart §1.7) --------------------------------------


@pytest.mark.django_db
def test_admin_com_ciclo_aberto_kpis_e_pipeline_so_desse_ciclo(
    admin,
    ciclo_aberto,
    colaborador,
    lider,
    area,
    cargo_colab,
):
    """Pipeline e KPIs refletem só o aberto; arquivo não polui eixos nem totais."""
    arquivo = _seed_arquivo(usuario=colaborador)
    extras = _usuarios_extra(4, area=area, cargo_colab=cargo_colab, lider=lider)
    alvo_arquivo = arquivo[-1]
    for user in extras:
        Avaliacao.objects.create(
            ciclo=alvo_arquivo,
            usuario=user,
            etapa=Avaliacao.Etapa.FEEDBACK,
            concluida=True,
        )

    aberto_total = Avaliacao.objects.filter(ciclo=ciclo_aberto).count()
    arquivo_feedback = Avaliacao.objects.filter(
        ciclo=alvo_arquivo,
        etapa=Avaliacao.Etapa.FEEDBACK,
    ).count()
    assert aberto_total > 0
    assert arquivo_feedback > aberto_total

    client = _login_admin(admin)
    resp = client.get(_admin_url())

    assert resp.status_code == 200
    assert resp.context['ciclo_aberto'].pk == ciclo_aberto.pk
    indicador = resp.context.get('ciclo_indicador')
    if indicador is not None:
        assert indicador.pk == ciclo_aberto.pk
        assert indicador.status == Ciclo.Status.ABERTO
    assert resp.context['ciclo_selecionado'].pk == ciclo_aberto.pk

    resumo = resp.context['avaliacoes_resumo']
    assert resumo['total'] == aberto_total

    kpis = resp.context['ciclo_kpis']
    assert kpis['has_ciclo'] is True
    assert kpis['total'] == aberto_total
    assert kpis['pendencias'] == Avaliacao.objects.filter(
        ciclo=ciclo_aberto,
        concluida=False,
    ).count()
    assert kpis['sem_avaliacao'] == len(extras)

    progresso = resp.context['chart_ciclo_progresso']
    assert progresso['has_data'] is True
    assert progresso['type'] == CHART_TYPE_BAR_HORIZONTAL
    assert _pipeline_total(progresso) == aberto_total
    assert _pipeline_count(progresso, Avaliacao.Etapa.FEEDBACK) == (
        Avaliacao.objects.filter(
            ciclo=ciclo_aberto,
            etapa=Avaliacao.Etapa.FEEDBACK,
        ).count()
    )

    html = resp.content.decode()
    assert ciclo_aberto.nome in html
    assert 'name="ciclo"' not in html
    _assert_percentual_encerrados_nao_e_kpi(resp)


@pytest.mark.django_db
def test_admin_percentual_encerrados_nao_e_kpi_de_saude(
    admin,
    ciclo_aberto,
    colaborador,
):
    """FR-004: dezenas de encerrados não viram % de governança na home."""
    _seed_arquivo(usuario=colaborador)
    encerrados = Ciclo.objects.filter(status=Ciclo.Status.ENCERRADO).count()
    total = Ciclo.objects.count()
    assert encerrados >= N_ARQUIVO
    assert total > encerrados

    client = _login_admin(admin)
    resp = client.get(_admin_url())

    assert resp.status_code == 200
    _assert_percentual_encerrados_nao_e_kpi(resp)
    html = resp.content.decode()
    assert 'name="ciclo"' not in html
    resp_hist = client.get(_admin_url(), {'visao': 'historico'})
    assert f'{encerrados} ciclos encerrados' in resp_hist.content.decode()
    kpis = resp.context['ciclo_kpis']
    assert kpis['has_ciclo'] is True
    assert kpis['total'] == Avaliacao.objects.filter(ciclo=ciclo_aberto).count()


# --- ``?ciclo=`` explícito (quickstart §1.4) ----------------------------------


@pytest.mark.django_db
def test_admin_operacional_ignora_ciclo_query_arquivo(
    admin,
    colaborador,
    lider,
    area,
    cargo_colab,
):
    """Visão operacional usa só o aberto; ``?ciclo=`` de arquivo é ignorado."""
    assert not Ciclo.objects.filter(status=Ciclo.Status.ABERTO).exists()
    arquivo = _seed_arquivo(usuario=colaborador)
    alvo = arquivo[0]
    extras = _usuarios_extra(4, area=area, cargo_colab=cargo_colab, lider=lider)
    for user in extras:
        Avaliacao.objects.create(
            ciclo=alvo,
            usuario=user,
            etapa=Avaliacao.Etapa.FEEDBACK,
            concluida=True,
        )
    alvo_total = Avaliacao.objects.filter(ciclo=alvo).count()
    assert alvo_total > 0

    client = _login_admin(admin)
    url = _admin_url()

    resp_operacional = client.get(url, {'ciclo': alvo.pk})
    assert resp_operacional.status_code == 200
    assert resp_operacional.context.get('ciclo_aberto') is None
    assert resp_operacional.context.get('ciclo_selecionado') is None
    _assert_empty_operacional(resp_operacional)
    html_operacional = resp_operacional.content.decode()
    assert 'name="ciclo"' not in html_operacional

    resp_historico = client.get(url, {'visao': 'historico', 'ciclo': alvo.pk})
    assert resp_historico.status_code == 200
    assert resp_historico.context.get('visao') == 'historico'
    html_historico = resp_historico.content.decode()
    assert 'name="ciclo"' in html_historico
    assert 'optgroup label="Encerrados"' in html_historico
    assert alvo.nome in html_historico


# --- T016 [US1] hierarquia KPI → pipeline → drill ---------------------------


_EMPTY_ADERENCIA_COPIES = (
    EMPTY_KIND_COPY[EMPTY_KIND_SEM_DADO],
    EMPTY_KIND_COPY[EMPTY_KIND_SEM_NOTA],
)


def _assert_hierarquia_kpi_pipeline_drill(html: str) -> None:
    """FR-005: KPI → ``bar_horizontal`` de etapas → doughnut (se houver) → drill."""
    kpi = html.find('Em avaliação')
    pipeline = html.find('id="pipeline-heading"')
    drill = html.find('id="baixa-aderencia-heading"')
    assert kpi != -1
    assert pipeline != -1
    assert drill != -1
    assert kpi < pipeline < drill
    aderencia = html.find('id="aderencia-heading"')
    if aderencia != -1:
        assert pipeline < aderencia < drill


def _seed_snapshot(*, lider, ciclo, percentual: str = '42.00') -> AderenciaSnapshot:
    """Snapshot sintético — não chama ``compute_adherence`` (denylist)."""
    return AderenciaSnapshot.objects.create(
        lider=lider,
        ciclo=ciclo,
        percentual=Decimal(percentual),
        componentes={},
        calculado_em=timezone.now(),
    )


@pytest.mark.django_db
def test_admin_hierarquia_kpi_pipeline_antes_do_drill(
    admin,
    ciclo_aberto,
    colaborador,
):
    """T016: visual principal = pipeline; doughnut não vem antes nem no lugar."""
    _seed_arquivo(usuario=colaborador)
    client = _login_admin(admin)
    resp = client.get(_admin_url())

    assert resp.status_code == 200
    html = resp.content.decode()
    _assert_hierarquia_kpi_pipeline_drill(html)
    assert 'id="visualizacoes-heading"' not in html
    assert 'data-chart-payload="chart-ciclo-progresso"' in html
    progresso = resp.context['chart_ciclo_progresso']
    assert progresso['type'] == CHART_TYPE_BAR_HORIZONTAL
    assert progresso['has_data'] is True


@pytest.mark.django_db
def test_admin_doughnut_sem_snapshot_usa_empty_canonico(
    admin,
    ciclo_aberto,
    colaborador,
):
    """T016: doughnut só com snapshot real; senão empty ``sem_dado``/``sem_nota``."""
    _seed_arquivo(usuario=colaborador)
    assert not AderenciaSnapshot.objects.filter(ciclo=ciclo_aberto).exists()

    client = _login_admin(admin)
    resp = client.get(_admin_url())

    assert resp.status_code == 200
    html = resp.content.decode()
    aderencia = resp.context['chart_aderencia_distribuicao']
    assert aderencia.get('has_data') is not True
    assert aderencia.get('empty_message') in _EMPTY_ADERENCIA_COPIES
    assert list(aderencia.get('labels') or []) == []
    assert 'data-chart-payload="chart-aderencia-distribuicao"' not in html
    assert any(copy in html for copy in _EMPTY_ADERENCIA_COPIES)

    progresso = resp.context['chart_ciclo_progresso']
    assert progresso['has_data'] is True
    assert 'data-chart-payload="chart-ciclo-progresso"' in html
    _assert_hierarquia_kpi_pipeline_drill(html)


@pytest.mark.django_db
def test_admin_doughnut_so_com_snapshot_real(
    admin,
    ciclo_aberto,
    colaborador,
    lider,
):
    """T016: snapshot persistido → doughnut ``has_data``; pipeline continua principal."""
    _seed_arquivo(usuario=colaborador)
    _seed_snapshot(lider=lider, ciclo=ciclo_aberto)

    client = _login_admin(admin)
    resp = client.get(_admin_url())

    assert resp.status_code == 200
    html = resp.content.decode()
    aderencia = resp.context['chart_aderencia_distribuicao']
    assert aderencia['has_data'] is True
    assert aderencia['type'] == CHART_TYPE_DOUGHNUT
    assert 'data-chart-payload="chart-aderencia-distribuicao"' in html
    assert 'data-chart-payload="chart-ciclo-progresso"' in html
    _assert_hierarquia_kpi_pipeline_drill(html)
    assert html.find('data-chart-payload="chart-ciclo-progresso"') < html.find(
        'data-chart-payload="chart-aderencia-distribuicao"',
    )


# --- T018 [US1] lista de ciclos: aberto vs arquivo -------------------------

_CICLO_LIST_PARTIAL = (
    Path(__file__).resolve().parents[1]
    / 'templates'
    / 'cycles'
    / 'ciclo_list_partial.html'
)


def _ciclo_list_url() -> str:
    return reverse('cycles:ciclo_list')


def test_ciclo_list_paginate_by_cards():
    """Lista de ciclos em cards: página menor; mixin permanece 20 para outras listas."""
    assert HtmxPaginatedListMixin.paginate_by == 20
    assert CicloListView.paginate_by == 5
    assert CicloListView.__dict__['paginate_by'] == 5


def test_ciclo_list_partial_nao_inclui_chart_block():
    """T018 / FR-017: partial HTMX da lista MUST NOT incluir ``_chart_block``."""
    source = _CICLO_LIST_PARTIAL.read_text(encoding='utf-8')
    assert '_chart_block' not in source
    assert 'dashboard_charts' not in source
    assert 'chart.js' not in source.lower()
    assert 'id="list-container"' in source


@pytest.mark.django_db
def test_ciclo_list_agrupa_aberto_vs_arquivo(admin, ciclo_aberto, colaborador):
    """T018: ciclo aberto em Operacional; encerrados só no Arquivo."""
    arquivo = _seed_arquivo(n=3, usuario=colaborador)
    client = _login_admin(admin)
    resp = client.get(_ciclo_list_url())

    assert resp.status_code == 200
    html = resp.content.decode()
    operacional = resp.context['ciclo_operacional']
    assert operacional is not None
    assert operacional.pk == ciclo_aberto.pk
    assert all(c.status == Ciclo.Status.ENCERRADO for c in resp.context['ciclos'])
    assert operacional.pk not in {c.pk for c in resp.context['ciclos']}

    op_pos = html.find('data-ciclo-group="operacional"')
    ar_pos = html.find('data-ciclo-group="arquivo"')
    assert 0 <= op_pos < ar_pos
    row_aberto = f'id="ciclo-row-{ciclo_aberto.pk}"'
    assert op_pos < html.find(row_aberto) < ar_pos
    assert html.find(f'id="ciclo-row-{arquivo[0].pk}"') > ar_pos
    assert 'Em andamento' in html
    assert 'Encerrados' in html
    assert '_chart_block' not in html
    assert 'data-chart-payload' not in html
    assert 'data-ciclo-create-cta' in html


@pytest.mark.django_db
def test_ciclo_list_sem_aberto_empty_operacional_arquivo_paginado(admin, colaborador):
    """T018 / quickstart 1.3: sem aberto → empty operacional; arquivo permanece."""
    arquivo = _seed_arquivo(n=4, usuario=colaborador)
    assert not Ciclo.objects.filter(status=Ciclo.Status.ABERTO).exists()

    client = _login_admin(admin)
    resp = client.get(_ciclo_list_url())

    assert resp.status_code == 200
    html = resp.content.decode()
    assert resp.context['ciclo_operacional'] is None
    assert resp.context['arquivo_total'] == 4
    assert {c.pk for c in resp.context['ciclos']} == {c.pk for c in arquivo}
    assert 'data-empty="operacional"' in html
    assert 'Nenhum ciclo aberto' in html
    assert f'id="ciclo-row-{arquivo[0].pk}"' in html


@pytest.mark.django_db
def test_ciclo_list_arquivo_paginate_by_cards_aberto_fixo(
    admin,
    ciclo_aberto,
    colaborador,
):
    """Arquivo pagina em 5 (cards); aberto continua visível fora do corte."""
    n_arquivo = CicloListView.paginate_by + 1
    arquivo = _seed_arquivo(n=n_arquivo, usuario=colaborador)
    client = _login_admin(admin)
    url = _ciclo_list_url()

    page1 = client.get(url)
    assert page1.status_code == 200
    paginator = page1.context['paginator']
    assert paginator.per_page == 5
    assert paginator.count == n_arquivo
    assert page1.context['arquivo_total'] == n_arquivo
    assert len(page1.context['object_list']) == 5
    assert page1.context['ciclo_operacional'].pk == ciclo_aberto.pk
    html1 = page1.content.decode()
    assert f'id="ciclo-row-{ciclo_aberto.pk}"' in html1
    assert 'data-ciclo-create-cta' in html1
    assert page1.context['page_obj'].has_next()

    page2 = client.get(url, {'page': 2})
    assert page2.status_code == 200
    assert len(page2.context['object_list']) == 1
    assert page2.context['ciclo_operacional'].pk == ciclo_aberto.pk
    html2 = page2.content.decode()
    assert f'id="ciclo-row-{ciclo_aberto.pk}"' in html2
    assert 'data-ciclo-create-cta' not in html2
    arquivo_pks = {c.pk for c in arquivo}
    assert {c.pk for c in page1.context['object_list']} <= arquivo_pks
    assert {c.pk for c in page2.context['object_list']} <= arquivo_pks
    assert ciclo_aberto.pk not in {c.pk for c in page1.context['object_list']}
    assert ciclo_aberto.pk not in {c.pk for c in page2.context['object_list']}


@pytest.mark.django_db
def test_ciclo_list_htmx_partial_sem_chart(admin, ciclo_aberto, colaborador):
    """T018 / FR-017: swap HTMX devolve o partial, sem canvas/chart."""
    _seed_arquivo(n=2, usuario=colaborador)
    client = _login_admin(admin)
    resp = client.get(_ciclo_list_url(), HTTP_HX_REQUEST='true')

    assert resp.status_code == 200
    html = resp.content.decode()
    assert 'id="list-container"' in html
    assert 'data-ciclo-group="operacional"' in html
    assert 'data-ciclo-group="arquivo"' in html
    assert 'Ciclos de avaliação' not in html
    assert '_chart_block' not in html
    assert 'dashboard_charts' not in html
    assert 'chart.js' not in html.lower()
    assert 'data-chart-payload' not in html


# --- T022 [US2] time / estrutura / aderência — default operacional ---------

_TEAM_CHART_KEYS = ('chart_escopo_status',)
_STRUCTURE_CHART_KEYS = ('chart_cobertura_area', 'chart_cobertura_cargo')
_COPY_OPERACIONAL = EMPTY_KIND_COPY[EMPTY_KIND_OPERACIONAL]
_COPY_ESCOPO = EMPTY_KIND_COPY[EMPTY_KIND_ESCOPO]


def _team_url() -> str:
    return reverse('dashboard:team')


def _structure_url() -> str:
    return reverse('dashboard:structure')


def _adherence_url() -> str:
    return reverse('dashboard:adherence')


def _login_lider(lider) -> Client:
    client = Client()
    client.force_login(lider)
    return client


def _assert_chart_empty_kind(chart: dict | None, *, kind_copy: str) -> None:
    assert chart is not None
    assert chart.get('has_data') is not True
    assert list(chart.get('labels') or []) == []
    assert list(chart.get('values') or []) == []
    assert list(chart.get('series') or []) == []
    assert chart.get('empty_message') == kind_copy


def _assert_no_arquivo_in_chart_labels(resp, chart_keys: tuple[str, ...]) -> None:
    for nome in Ciclo.objects.filter(status=Ciclo.Status.ENCERRADO).values_list(
        'nome',
        flat=True,
    ):
        for key in chart_keys:
            chart = resp.context.get(key) or {}
            assert nome not in list(chart.get('labels') or [])


@pytest.mark.django_db
def test_team_sem_ciclo_aberto_empty_operacional(lider, colaborador):
    """T022 / quickstart 2.2: time sem aberto → empty operacional, sem série."""
    assert not Ciclo.objects.filter(status=Ciclo.Status.ABERTO).exists()
    arquivo = _seed_arquivo(usuario=colaborador)
    assert len(arquivo) == N_ARQUIVO

    client = _login_lider(lider)
    resp = client.get(_team_url())

    assert resp.status_code == 200
    assert resp.context.get('ciclo_aberto') is None
    resumo = resp.context['team_resumo']
    assert resumo['has_ciclo'] is False
    assert resumo['aguardando_acao'] is None
    assert resumo['sem_avaliacao'] is None

    chart = resp.context['chart_escopo_status']
    _assert_chart_empty_kind(chart, kind_copy=_COPY_OPERACIONAL)
    assert chart['type'] == CHART_TYPE_BAR
    html = resp.content.decode()
    assert _COPY_OPERACIONAL in html
    assert 'data-chart-payload="chart-escopo-status"' not in html
    _assert_no_arquivo_in_chart_labels(resp, _TEAM_CHART_KEYS)
    assert resp.context.get('destaque_atencao') == []


@pytest.mark.django_db
def test_structure_sem_ciclo_aberto_empty_operacional(admin, colaborador):
    """T022 / quickstart 2.3: estrutura sem aberto → empty operacional."""
    assert not Ciclo.objects.filter(status=Ciclo.Status.ABERTO).exists()
    _seed_arquivo(usuario=colaborador)

    client = _login_admin(admin)
    resp = client.get(_structure_url())

    assert resp.status_code == 200
    assert resp.context.get('ciclo_aberto') is None
    assert resp.context.get('ciclo_filtro') is None
    resumo = resp.context['cobertura_resumo']
    assert resumo['has_ciclo'] is False
    assert resumo['percentual'] is None

    for key in _STRUCTURE_CHART_KEYS:
        _assert_chart_empty_kind(resp.context[key], kind_copy=_COPY_OPERACIONAL)
    html = resp.content.decode()
    assert _COPY_OPERACIONAL in html
    assert 'data-chart-payload="chart-cobertura-area"' not in html
    assert 'data-chart-payload="chart-cobertura-cargo"' not in html
    _assert_no_arquivo_in_chart_labels(resp, _STRUCTURE_CHART_KEYS)


@pytest.mark.django_db
def test_adherence_sem_ciclo_aberto_empty_operacional(admin, lider, colaborador):
    """T022 / quickstart 2.4: aderência sem aberto → empty; sem encerrado implícito."""
    assert not Ciclo.objects.filter(status=Ciclo.Status.ABERTO).exists()
    arquivo = _seed_arquivo(usuario=colaborador)
    alvo = arquivo[-1]
    _seed_snapshot(lider=lider, ciclo=alvo, percentual='18.00')

    client = _login_admin(admin)
    resp = client.get(_adherence_url())

    assert resp.status_code == 200
    assert resp.context.get('ciclo_aberto') is None
    assert resp.context.get('ciclo_filtro') is None
    resumo = resp.context['aderencia_resumo']
    assert resumo['has_ciclo'] is False
    assert resumo['media'] is None
    assert resumo['baixa'] is None
    assert resumo['alta'] is None
    assert resumo['media_n'] is None
    assert 'chart_aderencia_distribuicao' not in resp.context

    html = resp.content.decode()
    assert _COPY_OPERACIONAL in html
    assert 'data-chart-payload="chart-aderencia-distribuicao"' not in html
    assert 'chart.js' not in html.lower()
    assert 'Alta ·' not in html


@pytest.mark.django_db
def test_team_com_ciclo_aberto_pipeline_kpis_so_do_escopo(
    lider,
    colaborador,
    ciclo_aberto,
    area,
    cargo_colab,
    admin,
):
    """T022 / quickstart 2.1: pipeline/KPIs só do escopo do líder no aberto."""
    arquivo = _seed_arquivo(usuario=colaborador)
    # Fora do escopo do líder: outro time com avaliações no aberto e no arquivo.
    outro_lider = CustomUser.objects.create_user(
        email='outro.lider@test.greenn.com.br',
        password=DEFAULT_PASSWORD,
        nome='Outro Líder',
        cargo=lider.cargo,
        area=area,
        line_manager=admin,
        email_confirmado_em=timezone.now(),
    )
    fora = CustomUser.objects.create_user(
        email='fora.escopo@test.greenn.com.br',
        password=DEFAULT_PASSWORD,
        nome='Fora Escopo',
        cargo=cargo_colab,
        area=area,
        line_manager=outro_lider,
        email_confirmado_em=timezone.now(),
    )
    Avaliacao.objects.create(
        ciclo=ciclo_aberto,
        usuario=fora,
        etapa=Avaliacao.Etapa.FEEDBACK,
        concluida=True,
    )
    Avaliacao.objects.create(
        ciclo=arquivo[-1],
        usuario=fora,
        etapa=Avaliacao.Etapa.FEEDBACK,
        concluida=True,
    )

    av_colab = Avaliacao.objects.get(ciclo=ciclo_aberto, usuario=colaborador)
    # Garantir etapa de atenção no escopo (KPI aguardando_acao).
    av_colab.etapa = Avaliacao.Etapa.AVALIACAO
    av_colab.concluida = False
    av_colab.save(update_fields=['etapa', 'concluida'])

    # Extra no escopo sem Avaliacao no aberto → fatia sem_avaliacao.
    extra = CustomUser.objects.create_user(
        email='extra.escopo@test.greenn.com.br',
        password=DEFAULT_PASSWORD,
        nome='Extra Escopo',
        cargo=cargo_colab,
        area=area,
        line_manager=lider,
        email_confirmado_em=timezone.now(),
    )

    client = _login_lider(lider)
    resp = client.get(_team_url())

    assert resp.status_code == 200
    assert resp.context['ciclo_aberto'].pk == ciclo_aberto.pk
    resumo = resp.context['team_resumo']
    assert resumo['has_ciclo'] is True
    assert resumo['total_escopo'] == 2  # colaborador + extra
    assert resumo['aguardando_acao'] == 1
    assert resumo['sem_avaliacao'] == 1

    chart = resp.context['chart_escopo_status']
    assert chart['has_data'] is True
    assert chart['type'] == CHART_TYPE_BAR
    assert _pipeline_total(chart) == 2
    assert _pipeline_count(chart, Avaliacao.Etapa.AVALIACAO) == 1
    keys = list(chart.get('keys') or [])
    values = list(chart.get('values') or [])
    assert keys and SEM_AVALIACAO_KEY in keys
    assert int(dict(zip(keys, values)).get(SEM_AVALIACAO_KEY, 0) or 0) == 1
    # Fora do escopo não entra no total do pipeline.
    assert _pipeline_total(chart) < Avaliacao.objects.filter(
        ciclo=ciclo_aberto,
    ).count()

    html = resp.content.decode()
    assert ciclo_aberto.nome in html
    assert 'data-chart-payload="chart-escopo-status"' in html
    assert fora.email not in html
    assert colaborador.email in html or colaborador.nome in html


@pytest.mark.django_db
def test_structure_com_ciclo_aberto_cobertura_so_do_ciclo(
    admin,
    ciclo_aberto,
    colaborador,
):
    """T022: estrutura com aberto → cobertura só desse ciclo (não arquivo)."""
    arquivo = _seed_arquivo(usuario=colaborador)
    alvo = arquivo[-1]
    # Avaliações de arquivo não devem virar cobertura do aberto.
    assert Avaliacao.objects.filter(ciclo=alvo).exists()

    client = _login_admin(admin)
    resp = client.get(_structure_url())

    assert resp.status_code == 200
    assert resp.context['ciclo_aberto'].pk == ciclo_aberto.pk
    assert resp.context['ciclo_filtro'].pk == ciclo_aberto.pk
    resumo = resp.context['cobertura_resumo']
    assert resumo['has_ciclo'] is True
    com_aberto = Avaliacao.objects.filter(
        ciclo=ciclo_aberto,
        usuario__is_active=True,
    ).values('usuario_id').distinct().count()
    assert resumo['com_avaliacao'] == com_aberto
    assert resumo['com_avaliacao'] != Avaliacao.objects.filter(
        ciclo=alvo,
    ).values('usuario_id').distinct().count()

    for key in _STRUCTURE_CHART_KEYS:
        chart = resp.context[key]
        assert chart['has_data'] is True
        assert chart['type'] == CHART_TYPE_BAR_HORIZONTAL


@pytest.mark.django_db
def test_adherence_com_ciclo_aberto_so_snapshots_do_ciclo(
    admin,
    ciclo_aberto,
    lider,
    colaborador,
):
    """T022: aderência com aberto → KPIs/pills só do ciclo aberto."""
    arquivo = _seed_arquivo(usuario=colaborador)
    _seed_snapshot(lider=lider, ciclo=ciclo_aberto, percentual='72.00')
    _seed_snapshot(lider=lider, ciclo=arquivo[-1], percentual='11.00')

    client = _login_admin(admin)
    resp = client.get(_adherence_url())

    assert resp.status_code == 200
    assert resp.context['ciclo_filtro'].pk == ciclo_aberto.pk
    resumo = resp.context['aderencia_resumo']
    assert resumo['has_ciclo'] is True
    assert resumo['total_lideres'] == 1
    assert resumo['media'] == Decimal('72.00')
    assert resumo['alta'] == 0
    assert resumo['media_n'] == 1
    assert resumo['baixa'] == 0
    assert 'chart_aderencia_distribuicao' not in resp.context

    html = resp.content.decode()
    assert 'Alta · 0' in html
    assert 'Média · 1' in html
    assert 'Baixa · 0' in html
    assert 'data-chart-payload="chart-aderencia-distribuicao"' not in html
    assert 'chart.js' not in html.lower()


@pytest.mark.django_db
def test_team_ciclo_query_explicito_carrega_arquivo_sem_virar_default(
    lider,
    colaborador,
):
    """T022: ``?ciclo=`` no time carrega arquivo; home sem query não grava."""
    assert not Ciclo.objects.filter(status=Ciclo.Status.ABERTO).exists()
    arquivo = _seed_arquivo(usuario=colaborador)
    alvo = arquivo[0]
    # Etapa distinta no alvo para validar pipeline do arquivo escolhido.
    Avaliacao.objects.filter(ciclo=alvo, usuario=colaborador).update(
        etapa=Avaliacao.Etapa.APROVACAO_METAS,
        concluida=False,
    )

    client = _login_lider(lider)
    url = _team_url()

    resp_arquivo = client.get(url, {'ciclo': alvo.pk})
    assert resp_arquivo.status_code == 200
    assert resp_arquivo.context.get('ciclo_aberto') is None
    # Ciclo resolvido = arquivo explícito (não None / não fallback).
    selecionado = (
        resp_arquivo.context.get('ciclo_selecionado')
        or resp_arquivo.context.get('ciclo_filtro')
        or resp_arquivo.context.get('ciclo_indicador')
    )
    assert selecionado is not None
    assert selecionado.pk == alvo.pk
    resumo = resp_arquivo.context['team_resumo']
    assert resumo['has_ciclo'] is True
    chart = resp_arquivo.context['chart_escopo_status']
    assert chart['has_data'] is True
    assert _pipeline_count(chart, Avaliacao.Etapa.APROVACAO_METAS) == 1
    html = resp_arquivo.content.decode()
    assert alvo.nome in html

    resp_home = client.get(url)
    assert resp_home.status_code == 200
    assert resp_home.context.get('ciclo_aberto') is None
    assert resp_home.context['team_resumo']['has_ciclo'] is False
    _assert_chart_empty_kind(
        resp_home.context['chart_escopo_status'],
        kind_copy=_COPY_OPERACIONAL,
    )


@pytest.mark.django_db
def test_structure_ciclo_query_explicito_sem_virar_default(
    admin,
    colaborador,
):
    """T022: estrutura ``?ciclo=`` carrega arquivo; home sem query volta empty."""
    assert not Ciclo.objects.filter(status=Ciclo.Status.ABERTO).exists()
    arquivo = _seed_arquivo(usuario=colaborador)
    alvo = arquivo[0]

    client = _login_admin(admin)
    url = _structure_url()

    resp_arquivo = client.get(url, {'ciclo': alvo.pk})
    assert resp_arquivo.status_code == 200
    assert resp_arquivo.context['ciclo_filtro'].pk == alvo.pk
    assert resp_arquivo.context['cobertura_resumo']['has_ciclo'] is True
    assert resp_arquivo.context['chart_cobertura_area']['has_data'] is True

    resp_home = client.get(url)
    assert resp_home.status_code == 200
    assert resp_home.context.get('ciclo_filtro') is None
    assert resp_home.context['cobertura_resumo']['has_ciclo'] is False
    _assert_chart_empty_kind(
        resp_home.context['chart_cobertura_area'],
        kind_copy=_COPY_OPERACIONAL,
    )


@pytest.mark.django_db
def test_structure_header_badge_reflete_ciclo_do_filtro(
    admin,
    colaborador,
    ciclo_aberto,
):
    """Badge do topo segue ``ciclo_filtro``, não só existência de ciclo aberto."""
    arquivo = _seed_arquivo(usuario=colaborador)
    alvo = arquivo[0]
    client = _login_admin(admin)
    url = _structure_url()

    resp_aberto = client.get(url)
    assert resp_aberto.status_code == 200
    html_aberto = resp_aberto.content.decode()
    assert f'Ativo · {ciclo_aberto.nome}' in html_aberto
    assert 'Sem ciclo aberto' not in html_aberto

    resp_arquivo = client.get(url, {'ciclo': alvo.pk})
    assert resp_arquivo.status_code == 200
    assert resp_arquivo.context['ciclo_filtro'].pk == alvo.pk
    assert resp_arquivo.context['ciclo_aberto'].pk == ciclo_aberto.pk
    html_arquivo = resp_arquivo.content.decode()
    assert alvo.nome in html_arquivo
    assert f'Ativo · {ciclo_aberto.nome}' not in html_arquivo
    assert 'Sem ciclo aberto' not in html_arquivo


@pytest.mark.django_db
def test_structure_header_badge_sem_ciclo_filtro(
    admin,
    colaborador,
):
    """Sem ciclo aberto e sem ``?ciclo=`` → badge ``Sem ciclo aberto``."""
    assert not Ciclo.objects.filter(status=Ciclo.Status.ABERTO).exists()
    _seed_arquivo(usuario=colaborador)

    client = _login_admin(admin)
    resp = client.get(_structure_url())
    assert resp.status_code == 200
    assert resp.context.get('ciclo_filtro') is None
    assert 'Sem ciclo aberto' in resp.content.decode()


@pytest.mark.django_db
def test_structure_lider_sem_snapshot_mostra_sem_avaliacao_registrada(
    admin,
    lider,
    colaborador,
    ciclo_aberto,
):
    """Líder sem snapshot → badge neutro ``Sem avaliação registrada`` (não ``—``)."""
    assert not AderenciaSnapshot.objects.filter(
        ciclo=ciclo_aberto,
        lider=lider,
    ).exists()

    client = _login_admin(admin)
    resp = client.get(_structure_url())
    assert resp.status_code == 200

    lideres = resp.context['lideres_resumo']
    lider_row = next(item for item in lideres if item['lider'].pk == lider.pk)
    assert lider_row['snapshot'] is None
    assert lider_row['status'] is None

    html = resp.content.decode()
    assert 'Sem avaliação registrada' in html
    # Traço isolado na célula de aderência não deve permanecer como empty.
    assert 'text-slate-400">—</span>' not in html


@pytest.mark.django_db
def test_structure_lider_snapshot_neutro_mostra_badge_neutro(
    admin,
    lider,
    colaborador,
    ciclo_aberto,
):
    """Snapshot com percentual NULL → badge Neutro (igual à tela de aderência)."""
    AderenciaSnapshot.objects.create(
        lider=lider,
        ciclo=ciclo_aberto,
        percentual=None,
        componentes={'estado': 'neutro'},
        calculado_em=timezone.now(),
    )

    client = _login_admin(admin)
    resp = client.get(_structure_url())
    assert resp.status_code == 200

    lider_row = next(
        item for item in resp.context['lideres_resumo'] if item['lider'].pk == lider.pk
    )
    assert lider_row['status'] == 'neutro'

    html = resp.content.decode()
    assert 'Neutro' in html
    assert 'Baixo (' not in html


@pytest.mark.django_db
def test_structure_lideres_paginate_by_20(
    admin,
    lider,
    area,
    cargo_lider,
    cargo_colab,
    ciclo_aberto,
):
    """Líderes no escopo paginam em 20; HTMX troca só o #list-container."""
    per_page = HtmxPaginatedListMixin.paginate_by
    for i in range(per_page):
        gestor = CustomUser.objects.create_user(
            email=f'struct.pag.{i}@test.greenn.com.br',
            password=DEFAULT_PASSWORD,
            nome=f'Gestor Pag {i}',
            cargo=cargo_lider,
            area=area,
            line_manager=admin,
            email_confirmado_em=timezone.now(),
        )
        CustomUser.objects.create_user(
            email=f'struct.pag.colab.{i}@test.greenn.com.br',
            password=DEFAULT_PASSWORD,
            nome=f'Colab Pag {i}',
            cargo=cargo_colab,
            area=area,
            line_manager=gestor,
            data_entrada=FIXTURE_DATA_ENTRADA,
            email_confirmado_em=timezone.now(),
        )

    client = _login_admin(admin)
    resp = client.get(_structure_url())
    assert resp.status_code == 200
    page_obj = resp.context['page_obj']
    assert page_obj.paginator.per_page == per_page
    assert page_obj.paginator.count > per_page
    assert len(resp.context['lideres_resumo']) == per_page
    assert page_obj.has_next()

    html = resp.content.decode()
    assert 'Mostrando' in html
    assert 'líder' in html

    resp2 = client.get(_structure_url(), {'page': 2})
    assert resp2.status_code == 200
    assert len(resp2.context['lideres_resumo']) == page_obj.paginator.count - per_page

    resp_htmx = client.get(
        _structure_url(),
        {'page': 2},
        HTTP_HX_REQUEST='true',
        HTTP_HX_TARGET='#list-container',
    )
    assert resp_htmx.status_code == 200
    partial = resp_htmx.content.decode()
    assert 'id="list-container"' in partial
    assert 'Líderes Diretos' not in partial


@pytest.mark.django_db
def test_adherence_lista_paginate_by_20(
    admin,
    area,
    cargo_lider,
    cargo_colab,
    ciclo_aberto,
):
    """Gestores na aderência paginam em 20 com resumo «Mostrando X a Y»."""
    from apps.reviews.services.enrollment import ensure_avaliacao_for_user

    per_page = HtmxPaginatedListMixin.paginate_by
    for i in range(per_page + 1):
        gestor = CustomUser.objects.create_user(
            email=f'ader.pag.{i}@test.greenn.com.br',
            password=DEFAULT_PASSWORD,
            nome=f'Ader Pag {i}',
            cargo=cargo_lider,
            area=area,
            line_manager=admin,
            email_confirmado_em=timezone.now(),
        )
        colab = CustomUser.objects.create_user(
            email=f'ader.pag.colab.{i}@test.greenn.com.br',
            password=DEFAULT_PASSWORD,
            nome=f'Colab Ader {i}',
            cargo=cargo_colab,
            area=area,
            line_manager=gestor,
            data_entrada=FIXTURE_DATA_ENTRADA,
            email_confirmado_em=timezone.now(),
        )
        ensure_avaliacao_for_user(colab, ciclo=ciclo_aberto)
        _seed_snapshot(
            lider=gestor,
            ciclo=ciclo_aberto,
            percentual=f'{10 + i}.00',
        )

    client = _login_admin(admin)
    resp = client.get(_adherence_url())
    assert resp.status_code == 200
    page_obj = resp.context['page_obj']
    assert page_obj.paginator.per_page == per_page
    assert page_obj.paginator.count == per_page + 1
    assert len(resp.context['snapshots_resumo']) == per_page
    assert page_obj.has_next()
    assert 'Mostrando' in resp.content.decode()
    assert 'gestor' in resp.content.decode()

    resp2 = client.get(_adherence_url(), {'page': 2})
    assert len(resp2.context['snapshots_resumo']) == 1


@pytest.mark.django_db
def test_structure_remove_visao_por_area_mantem_charts_e_alertas(
    admin,
    colaborador,
    ciclo_aberto,
):
    """Sem bloco Visão por Área; charts horizontais + Alertas Em breve permanecem."""
    client = _login_admin(admin)
    resp = client.get(_structure_url())
    assert resp.status_code == 200
    assert 'cobertura_por_area' not in resp.context

    html = resp.content.decode()
    assert 'Visão por Área' not in html
    assert 'id="cobertura-charts"' in html
    assert 'Alertas de Gestão' in html
    assert 'Em breve' in html


@pytest.mark.django_db
def test_structure_oculta_lacunas_por_cargo_quando_um_cargo(
    admin,
    colaborador,
    cargo_colab,
    ciclo_aberto,
):
    """Com ≤1 cargo distinto no escopo filtrado, some Diferenças por cargo."""
    client = _login_admin(admin)
    resp = client.get(_structure_url(), {'cargo': cargo_colab.pk})
    assert resp.status_code == 200
    assert resp.context['mostrar_lacunas_por_cargo'] is False
    assert 'Diferenças por cargo' not in resp.content.decode()
    assert 'Diferenças por área' in resp.content.decode()


@pytest.mark.django_db
def test_structure_mostra_lacunas_por_cargo_quando_varios(
    admin,
    colaborador,
    ciclo_aberto,
):
    """Hierarquia padrão (líder + colab) → ≥2 cargos → tabela de cargo visível."""
    client = _login_admin(admin)
    resp = client.get(_structure_url())
    assert resp.status_code == 200
    assert resp.context['mostrar_lacunas_por_cargo'] is True
    assert 'Diferenças por cargo' in resp.content.decode()


@pytest.mark.django_db
def test_structure_sem_busca_ciclo_encerrado_e_lacunas_colapsaveis(
    admin,
    colaborador,
    ciclo_aberto,
):
    """Estrutura: sem campo Buscar ciclo; diferenças atrás de Ver tabela."""
    # Garante que o seletor *poderia* mostrar q (>20 arquivo), mas a tela oculta.
    from datetime import timedelta

    from apps.cycles.models import Ciclo

    today = date.today()
    for i in range(22):
        Ciclo.objects.create(
            nome=f'Arquivo Extra {i}',
            data_inicio=today - timedelta(days=400 + i),
            data_fim=today - timedelta(days=370 + i),
            status=Ciclo.Status.ENCERRADO,
        )

    client = _login_admin(admin)
    resp = client.get(_structure_url())
    assert resp.status_code == 200
    html = resp.content.decode()
    assert 'Buscar ciclo encerrado' not in html
    assert 'name="q"' not in html
    assert 'Ver tabela' in html
    assert 'Ver todas' not in html
    assert html.count('<details') >= 1
    assert 'gp-structure-scroll-top' in html
    assert 'sm:max-w-[16rem]' in html
    # Hint sob o select de ciclo some no compact; título da página pode citar arquivo.
    assert 'id="ciclo-arquivo-hint"' not in html



@pytest.mark.django_db
def test_adherence_ciclo_query_explicito_sem_virar_default(
    admin,
    lider,
    colaborador,
):
    """T022: aderência ``?ciclo=`` carrega arquivo; home sem query → empty."""
    assert not Ciclo.objects.filter(status=Ciclo.Status.ABERTO).exists()
    arquivo = _seed_arquivo(usuario=colaborador)
    alvo = arquivo[0]
    _seed_snapshot(lider=lider, ciclo=alvo, percentual='55.00')

    client = _login_admin(admin)
    url = _adherence_url()

    resp_arquivo = client.get(url, {'ciclo': alvo.pk})
    assert resp_arquivo.status_code == 200
    assert resp_arquivo.context['ciclo_filtro'].pk == alvo.pk
    assert resp_arquivo.context['aderencia_resumo']['has_ciclo'] is True
    assert resp_arquivo.context['aderencia_resumo']['media'] == Decimal('55.00')
    assert resp_arquivo.context['aderencia_resumo']['media_n'] == 1
    assert 'chart_aderencia_distribuicao' not in resp_arquivo.context
    assert 'Média · 1' in resp_arquivo.content.decode()

    resp_home = client.get(url)
    assert resp_home.status_code == 200
    assert resp_home.context.get('ciclo_filtro') is None
    assert resp_home.context['aderencia_resumo']['has_ciclo'] is False
    assert 'chart_aderencia_distribuicao' not in resp_home.context
    assert _COPY_OPERACIONAL in resp_home.content.decode()


@pytest.mark.django_db
def test_adherence_header_badge_reflete_ciclo_do_filtro(
    admin,
    colaborador,
    ciclo_aberto,
):
    """Badge do topo segue ``ciclo_filtro`` (mesmo include da estrutura)."""
    arquivo = _seed_arquivo(usuario=colaborador)
    alvo = arquivo[0]
    client = _login_admin(admin)
    url = _adherence_url()

    resp_aberto = client.get(url)
    assert resp_aberto.status_code == 200
    html_aberto = resp_aberto.content.decode()
    assert f'Ativo · {ciclo_aberto.nome}' in html_aberto
    assert 'Sem ciclo aberto' not in html_aberto

    resp_arquivo = client.get(url, {'ciclo': alvo.pk})
    assert resp_arquivo.status_code == 200
    assert resp_arquivo.context['ciclo_filtro'].pk == alvo.pk
    html_arquivo = resp_arquivo.content.decode()
    assert alvo.nome in html_arquivo
    assert f'Ativo · {ciclo_aberto.nome}' not in html_arquivo
    assert 'Sem ciclo aberto' not in html_arquivo


@pytest.mark.django_db
def test_adherence_lista_ordena_percentual_asc_e_filtra_nivel(
    admin,
    ciclo_aberto,
    lider,
    area,
    cargo_lider,
    cargo_colab,
):
    """Lista: % ASC (pior primeiro); ``?nivel=`` filtra no servidor (paginação HTMX)."""
    lider_alto = CustomUser.objects.create_user(
        email='ader.alto@test.greenn.com.br',
        password=DEFAULT_PASSWORD,
        nome='Ader Alto',
        cargo=cargo_lider,
        area=area,
        line_manager=admin,
        email_confirmado_em=timezone.now(),
    )
    lider_medio = CustomUser.objects.create_user(
        email='ader.medio@test.greenn.com.br',
        password=DEFAULT_PASSWORD,
        nome='Ader Medio',
        cargo=cargo_lider,
        area=area,
        line_manager=admin,
        email_confirmado_em=timezone.now(),
    )
    for gestor in (lider_alto, lider_medio):
        colab = CustomUser.objects.create_user(
            email=f'colab.{gestor.email}',
            password=DEFAULT_PASSWORD,
            nome=f'Colab {gestor.nome}',
            cargo=cargo_colab,
            area=area,
            line_manager=gestor,
            data_entrada=FIXTURE_DATA_ENTRADA,
            email_confirmado_em=timezone.now(),
        )
        from apps.reviews.services.enrollment import ensure_avaliacao_for_user

        ensure_avaliacao_for_user(colab, ciclo=ciclo_aberto)
    _seed_snapshot(lider=lider, ciclo=ciclo_aberto, percentual='15.00')
    _seed_snapshot(lider=lider_medio, ciclo=ciclo_aberto, percentual='60.00')
    _seed_snapshot(lider=lider_alto, ciclo=ciclo_aberto, percentual='90.00')

    client = _login_admin(admin)
    resp = client.get(_adherence_url())
    assert resp.status_code == 200
    ordered = [item['snapshot'].lider.email for item in resp.context['snapshots_resumo']]
    assert ordered == [
        lider.email,
        lider_medio.email,
        lider_alto.email,
    ]
    resumo = resp.context['aderencia_resumo']
    assert resumo['baixa'] == 1
    assert resumo['media_n'] == 1
    assert resumo['alta'] == 1

    resp_baixa = client.get(_adherence_url(), {'nivel': 'baixa'})
    assert resp_baixa.status_code == 200
    assert resp_baixa.context['filtro_nivel'] == 'baixa'
    filtrados = [
        item['snapshot'].lider.email for item in resp_baixa.context['snapshots_resumo']
    ]
    assert filtrados == [lider.email]
    # Contagens das pills permanecem do escopo completo (não do filtro).
    assert resp_baixa.context['aderencia_resumo']['alta'] == 1
    assert resp_baixa.context['aderencia_resumo']['media_n'] == 1
    assert resp_baixa.context['aderencia_resumo']['baixa'] == 1
    html_baixa = resp_baixa.content.decode()
    assert 'aria-pressed="true"' in html_baixa
    assert lider.email in html_baixa
    assert lider_alto.email not in html_baixa

    # Toggle: mesmo nível limpa o filtro.
    resp_toggle = client.get(_adherence_url())
    assert resp_toggle.context.get('filtro_nivel') is None
    assert len(resp_toggle.context['snapshots_resumo']) == 3


@pytest.mark.django_db
def test_adherence_componente_total_zero_exibe_traco(
    admin,
    ciclo_aberto,
    lider,
):
    """Componentes 0/0 não mostram (100.00%) — evita inflar adesão sem itens."""
    AderenciaSnapshot.objects.create(
        lider=lider,
        ciclo=ciclo_aberto,
        percentual=Decimal('100.00'),
        componentes={
            'aprovacoes': {'total': 0, 'no_prazo': 0, 'percentual': '100.00'},
            'feedbacks': {'total': 0, 'no_prazo': 0, 'percentual': '100.00'},
            'acoes_pdi': {'total': 2, 'no_prazo': 1, 'percentual': '50.00'},
        },
        calculado_em=timezone.now(),
    )
    client = _login_admin(admin)
    html = client.get(_adherence_url()).content.decode()
    assert '0/0' not in html
    assert '0/0 (100.00%)' not in html
    assert '1/2 (50.00%)' in html


@pytest.mark.django_db
def test_adherence_filtro_area_reduz_lista_e_kpis(
    admin,
    ciclo_aberto,
    lider,
    area,
    cargo_lider,
    cargo_colab,
):
    """``?area=`` reduz lista + KPIs/pills (AuthZ intacta); compõe com ``?nivel=``."""
    from apps.organization.models import Area

    outra = Area.objects.create(nome='Área Outra Aderência')
    lider_outra = CustomUser.objects.create_user(
        email='ader.outra.area@test.greenn.com.br',
        password=DEFAULT_PASSWORD,
        nome='Ader Outra Área',
        cargo=cargo_lider,
        area=outra,
        line_manager=admin,
        email_confirmado_em=timezone.now(),
    )
    colab_outra = CustomUser.objects.create_user(
        email='colab.outra.area@test.greenn.com.br',
        password=DEFAULT_PASSWORD,
        nome='Colab Outra Área',
        cargo=cargo_colab,
        area=outra,
        line_manager=lider_outra,
        data_entrada=FIXTURE_DATA_ENTRADA,
        email_confirmado_em=timezone.now(),
    )
    from apps.reviews.services.enrollment import ensure_avaliacao_for_user

    ensure_avaliacao_for_user(colab_outra, ciclo=ciclo_aberto)
    _seed_snapshot(lider=lider, ciclo=ciclo_aberto, percentual='20.00')
    _seed_snapshot(lider=lider_outra, ciclo=ciclo_aberto, percentual='90.00')

    client = _login_admin(admin)
    url = _adherence_url()

    resp_all = client.get(url)
    assert resp_all.status_code == 200
    assert resp_all.context['aderencia_resumo']['total_lideres'] == 2
    assert resp_all.context['aderencia_resumo']['baixa'] == 1
    assert resp_all.context['aderencia_resumo']['alta'] == 1
    assert 'name="area"' in resp_all.content.decode()
    assert 'id="area"' in resp_all.content.decode()

    resp_area = client.get(url, {'area': area.pk})
    assert resp_area.status_code == 200
    assert resp_area.context['filtro_area_id'] == area.pk
    emails = [
        item['snapshot'].lider.email for item in resp_area.context['snapshots_resumo']
    ]
    assert emails == [lider.email]
    resumo = resp_area.context['aderencia_resumo']
    assert resumo['total_lideres'] == 1
    assert resumo['baixa'] == 1
    assert resumo['alta'] == 0
    assert resumo['media'] == Decimal('20.00')
    html_area = resp_area.content.decode()
    assert 'Baixa · 1' in html_area
    assert 'Alta · 0' in html_area
    assert lider_outra.email not in html_area

    # Nível aplica sobre o resultado já reduzido por área.
    resp_combo = client.get(url, {'area': area.pk, 'nivel': 'alta'})
    assert resp_combo.status_code == 200
    assert resp_combo.context['filtro_nivel'] == 'alta'
    assert resp_combo.context['snapshots_resumo'] == []
    # Pills/KPIs seguem a área (sem nível).
    assert resp_combo.context['aderencia_resumo']['baixa'] == 1
    assert resp_combo.context['aderencia_resumo']['alta'] == 0


@pytest.mark.django_db
def test_team_lider_sem_subordinados_visiveis_empty_escopo(
    lider,
    ciclo_aberto,
    area,
    cargo_colab,
):
    """T022 / R2: líder sem subordinados ativos → empty ``escopo`` (não inventa)."""
    # is_leader permanece True (há report), mas nenhum ativo no QS do time.
    CustomUser.objects.filter(line_manager=lider, is_active=True).update(
        is_active=False,
    )
    # Report inativo extra — reforça is_leader sem entrar no escopo filtrado.
    CustomUser.objects.create_user(
        email='inativo@test.greenn.com.br',
        password=DEFAULT_PASSWORD,
        nome='Inativo',
        cargo=cargo_colab,
        area=area,
        line_manager=lider,
        is_active=False,
        email_confirmado_em=timezone.now(),
    )
    assert lider.is_leader
    assert not CustomUser.objects.filter(
        line_manager=lider,
        is_active=True,
    ).exists()

    client = _login_lider(lider)
    resp = client.get(_team_url())

    assert resp.status_code == 200
    assert resp.context['ciclo_aberto'].pk == ciclo_aberto.pk
    resumo = resp.context['team_resumo']
    assert resumo['total_escopo'] == 0
    chart = resp.context['chart_escopo_status']
    _assert_chart_empty_kind(chart, kind_copy=_COPY_ESCOPO)
    html = resp.content.decode()
    assert _COPY_ESCOPO in html
    assert 'data-chart-payload="chart-escopo-status"' not in html
    assert resp.context.get('destaque_atencao') == []


# --- T022 [US2] meu painel — empty kinds D (presentation-only views) ---------

_COPY_SEM_DADO = EMPTY_KIND_COPY[EMPTY_KIND_SEM_DADO]
_COPY_SEM_NOTA = EMPTY_KIND_COPY[EMPTY_KIND_SEM_NOTA]


def _personal_gap_chart(fr005: dict) -> dict:
    from apps.dashboard.views import PersonalDashboardView

    return PersonalDashboardView()._chart_gaps_competencia(fr005)


def test_personal_vinculo_pendente_empty_sem_dado_t022():
    """T022 / A7: vínculo pendente → ``sem_dado`` canônico (não copy ad hoc)."""
    chart = _personal_gap_chart({'vinculo_pendente': True, 'competencias_resumo': []})
    _assert_chart_empty_kind(chart, kind_copy=_COPY_SEM_DADO)


def test_personal_sem_competencias_empty_sem_dado_t022():
    """T022 / A7: cargo sem competências → ``sem_dado`` canônico."""
    chart = _personal_gap_chart({'vinculo_pendente': False, 'competencias_resumo': []})
    _assert_chart_empty_kind(chart, kind_copy=_COPY_SEM_DADO)


def test_personal_sem_notas_comparaveis_empty_sem_nota_t022():
    """T022 / A7: competências sem nota → ``sem_nota`` canônico."""
    from types import SimpleNamespace

    chart = _personal_gap_chart({
        'vinculo_pendente': False,
        'competencias_resumo': [
            {
                'competencia': SimpleNamespace(nome='Comp A'),
                'nivel_esperado': 3,
                'nota_atual': None,
            },
        ],
    })
    _assert_chart_empty_kind(chart, kind_copy=_COPY_SEM_NOTA)


@pytest.mark.django_db
def test_team_busca_filtra_lista_sem_afetar_pipeline(
    lider,
    colaborador,
    ciclo_aberto,
    area,
    cargo_colab,
):
    """``?busca=`` filtra a tabela; gráfico/KPI permanecem no escopo completo."""
    CustomUser.objects.create_user(
        email='outro.membro@test.greenn.com.br',
        password=DEFAULT_PASSWORD,
        nome='Bruno Outro',
        cargo=cargo_colab,
        area=area,
        line_manager=lider,
        email_confirmado_em=timezone.now(),
    )
    client = _login_lider(lider)
    resp = client.get(_team_url(), {'busca': colaborador.nome.split()[0]})

    assert resp.status_code == 200
    assert resp.context['filtro_busca']
    assert resp.context['filtro_ativo'] is True
    nomes = [m['usuario'].pk for m in resp.context['membros_resumo']]
    assert colaborador.pk in nomes
    assert len(nomes) == 1
    # Pipeline não encolhe com a busca.
    assert resp.context['team_resumo']['total_escopo'] == 2
    assert _pipeline_total(resp.context['chart_escopo_status']) == 2
    html = resp.content.decode()
    assert 'Buscar colaborador...' in html
    assert 'de 2 colaborador' in html


@pytest.mark.django_db
def test_team_etapa_filtra_lista_e_ignora_invalida(
    lider,
    colaborador,
    ciclo_aberto,
    area,
    cargo_colab,
):
    """``?etapa=`` filtra por bucket do pipeline; valor inválido é ignorado."""
    extra = CustomUser.objects.create_user(
        email='sem.av@test.greenn.com.br',
        password=DEFAULT_PASSWORD,
        nome='Sem Aval',
        cargo=cargo_colab,
        area=area,
        line_manager=lider,
        email_confirmado_em=timezone.now(),
    )
    av = Avaliacao.objects.get(ciclo=ciclo_aberto, usuario=colaborador)
    av.etapa = Avaliacao.Etapa.AVALIACAO
    av.save(update_fields=['etapa'])

    client = _login_lider(lider)
    resp = client.get(_team_url(), {'etapa': Avaliacao.Etapa.AVALIACAO})
    assert resp.status_code == 200
    assert resp.context['filtro_etapa'] == Avaliacao.Etapa.AVALIACAO
    pks = {m['usuario'].pk for m in resp.context['membros_resumo']}
    assert pks == {colaborador.pk}
    assert resp.context['team_resumo']['total_escopo'] == 2

    resp_sem = client.get(_team_url(), {'etapa': SEM_AVALIACAO_KEY})
    pks_sem = {m['usuario'].pk for m in resp_sem.context['membros_resumo']}
    assert pks_sem == {extra.pk}

    resp_bad = client.get(_team_url(), {'etapa': 'etapa_inventada'})
    assert resp_bad.context['filtro_etapa'] == ''
    assert len(resp_bad.context['membros_resumo']) == 2


@pytest.mark.django_db
def test_team_etapa_nao_aplica_no_historico(lider, colaborador, ciclo_aberto):
    """No histórico, ``?etapa=`` não filtra; busca por nome permanece."""
    client = _login_lider(lider)
    resp = client.get(
        _team_url(),
        {
            'visao': 'historico',
            'etapa': Avaliacao.Etapa.AVALIACAO,
            'busca': 'zzzz-nao-existe',
        },
    )
    assert resp.status_code == 200
    assert resp.context['visao'] == 'historico'
    assert resp.context['filtro_etapa'] == ''
    assert resp.context['filtro_busca'] == 'zzzz-nao-existe'
    assert resp.context['membros_resumo'] == []
    html = resp.content.decode()
    assert 'Nenhum colaborador encontrado' in html
    assert 'Filtrar por estágio do ciclo' not in html


@pytest.mark.django_db
def test_team_htmx_partial_traz_contador_e_chips(
    lider,
    colaborador,
    ciclo_aberto,
):
    client = _login_lider(lider)
    resp = client.get(
        _team_url(),
        {'etapa': Avaliacao.Etapa.INPUT_METAS},
        HTTP_HX_REQUEST='true',
    )
    assert resp.status_code == 200
    html = resp.content.decode()
    assert 'id="list-container"' in html
    assert 'team-busca-input' in html
    assert 'aria-pressed="true"' in html
    assert 'hx-trigger="keyup changed delay:300ms, search"' in html
