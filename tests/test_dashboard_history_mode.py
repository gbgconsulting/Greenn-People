"""T028 [US3] — modo ``?visao=historico`` (admin / time / pessoal / rotas).

Contrato: ``density-history-empty.md`` §2 / FR-003 / FR-016 / quickstart §3.
GET admin/time **sem** ``visao=`` → operacional (não tendência).
``?visao=historico`` → barra 100% empilhada (3 status), ≤ ``HISTORY_DEFAULT_N``.
``?visao=historico&ciclos=`` → só ids pedidos, cap 8, nunca ~57.
Ciclo sem cabeçalho → 100% ``sem_avaliacao`` (parados), não 0 de nota.
Nota/gap/aderência → ``has_data=false`` + empty ``sem_nota``.
Pessoal MUST NOT honrar ``visao=historico``; nenhuma rota ``/historico/``.

Fixtures sintéticas (12–21 ciclos); MUST NOT ``data/legado-solides/raw/``.
Denylist intacta (allowlist testes).
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from django.test import Client
from django.urls import NoReverseMatch, reverse
from django.utils import timezone

from apps.accounts.models import CustomUser
from apps.cycles.models import Ciclo
from apps.dashboard.chart_payloads import (
    CHART_TYPE_AREA,
    CHART_TYPE_BAR,
    CHART_TYPE_BAR_HORIZONTAL,
    EMPTY_KIND_COPY,
    EMPTY_KIND_ESCOPO,
    EMPTY_KIND_SEM_DADO,
    EMPTY_KIND_SEM_NOTA,
    HISTORY_DEFAULT_N,
)
from apps.dashboard.models import AderenciaSnapshot
from apps.dashboard.services.history import (
    STATUS_MAP,
    build_stage_history,
    default_history_ciclos,
    parse_history_ciclos,
    resolve_history_ciclos,
)
from apps.reviews.models import Avaliacao
from tests.conftest import DEFAULT_PASSWORD

_ROOT = Path(__file__).resolve().parents[1]
_CHART_BLOCK = _ROOT / 'templates' / 'dashboard' / '_chart_block.html'
_PERSONAL_TMPL = _ROOT / 'templates' / 'dashboard' / 'personal.html'
_HTMX_PARTIALS = (
    _ROOT / 'templates' / 'dashboard' / 'team_list_partial.html',
    _ROOT / 'templates' / 'dashboard' / 'adherence_list_partial.html',
    _ROOT / 'templates' / 'cycles' / 'ciclo_list_partial.html',
)
_CHART_SURFACES = (
    _ROOT / 'templates' / 'dashboard' / 'admin.html',
    _ROOT / 'templates' / 'dashboard' / 'team.html',
    _ROOT / 'templates' / 'dashboard' / 'structure.html',
    _ROOT / 'templates' / 'dashboard' / 'personal.html',
    _ROOT / 'templates' / 'cycles' / 'ciclo_detail.html',
)
_NO_CHART_SURFACES = (
    _ROOT / 'templates' / 'dashboard' / 'adherence.html',
)
_CANVAS_CSS = _ROOT / 'static' / 'src' / 'input.css'
_DASHBOARD_CHARTS_JS = _ROOT / 'static' / 'js' / 'dashboard_charts.js'
_BASE_HTML = _ROOT / 'templates' / 'base.html'
ARCHIVE_PREFIX = 'HIST-LEGADO-'
N_ARQUIVO = 12
N_ARQUIVO_CAP = 21
_COPY_SEM_NOTA = EMPTY_KIND_COPY[EMPTY_KIND_SEM_NOTA]


def _admin_url() -> str:
    return reverse('dashboard:admin')


def _team_url() -> str:
    return reverse('dashboard:team')


def _personal_url() -> str:
    return reverse('dashboard:personal')


def _login(user) -> Client:
    client = Client()
    client.force_login(user)
    return client


def _seed_arquivo(
    *,
    n: int = N_ARQUIVO,
    usuario=None,
    etapa: str | None = None,
    skip_indices: frozenset[int] | None = None,
) -> list[Ciclo]:
    """Ciclos encerrados sintéticos — nunca dump ``legado-solides/raw``."""
    etapa_val = etapa or Avaliacao.Etapa.FEEDBACK
    skip = skip_indices or frozenset()
    ciclos: list[Ciclo] = []
    for i in range(n):
        year = 2000 + i
        ciclo = Ciclo.objects.create(
            nome=f'{ARCHIVE_PREFIX}{year}',
            data_inicio=date(year, 1, 15),
            data_fim=date(year, 12, 15),
            status=Ciclo.Status.ENCERRADO,
        )
        ciclos.append(ciclo)
        if usuario is not None and i not in skip:
            Avaliacao.objects.create(
                ciclo=ciclo,
                usuario=usuario,
                etapa=etapa_val,
                concluida=True,
            )
    return ciclos


def _assert_history_stacked(chart: dict | None, *, max_labels: int = HISTORY_DEFAULT_N) -> None:
    assert chart is not None
    assert chart.get('has_data') is True
    assert chart.get('type') == CHART_TYPE_BAR
    assert chart.get('stacked') is True
    assert chart.get('html_legend') is True
    labels = list(chart.get('labels') or [])
    assert 1 <= len(labels) <= max_labels
    assert len(labels) <= HISTORY_DEFAULT_N
    series = list(chart.get('series') or [])
    keys = [serie.get('key') for serie in series]
    assert 'sem_avaliacao' in keys
    assert 'em_andamento' in keys
    assert 'concluida' in keys
    status = [serie for serie in series if serie.get('kind') != 'line']
    for index in range(len(labels)):
        total = sum(int(serie['values'][index] or 0) for serie in status)
        assert total == 100, (index, total)


def _assert_aderencia_sem_nota(chart: dict | None) -> None:
    assert chart is not None
    assert chart.get('has_data') is not True
    assert chart.get('empty_message') == _COPY_SEM_NOTA
    assert list(chart.get('labels') or []) == []
    assert list(chart.get('values') or []) == []
    assert list(chart.get('series') or []) == []


# --- Sem ``visao=`` → operacional (quickstart §3.1) ---------------------------


@pytest.mark.django_db
def test_admin_sem_visao_permanece_operacional_nao_tendencia(
    admin,
    ciclo_aberto,
    colaborador,
):
    """Admin sem ``visao=``: pipeline operacional; sem série ``area`` de tendência."""
    _seed_arquivo(usuario=colaborador)
    client = _login(admin)
    resp = client.get(_admin_url())

    assert resp.status_code == 200
    assert resp.context.get('visao') != 'historico'
    assert resp.context.get('chart_stage_history') is None
    progresso = resp.context['chart_ciclo_progresso']
    assert progresso['has_data'] is True
    assert progresso['type'] == CHART_TYPE_BAR_HORIZONTAL
    assert progresso['type'] != CHART_TYPE_AREA
    html = resp.content.decode()
    assert 'data-chart-payload="chart-stage-history"' not in html
    assert 'data-chart-payload="chart-ciclo-progresso"' in html
    # T033: toggle GET presente; Histórico aponta visao=historico (sem HTMX).
    assert 'data-component="visao-toggle"' in html
    assert 'visao=historico' in html
    assert 'hx-get' not in html.split('data-component="visao-toggle"')[1].split('</nav>')[0]


@pytest.mark.django_db
def test_team_sem_visao_permanece_operacional_nao_tendencia(
    lider,
    ciclo_aberto,
    colaborador,
):
    """Time sem ``visao=``: pipeline do escopo; sem tendência ``area``."""
    _seed_arquivo(usuario=colaborador)
    client = _login(lider)
    resp = client.get(_team_url())

    assert resp.status_code == 200
    assert resp.context.get('visao') != 'historico'
    assert resp.context.get('chart_stage_history') is None
    chart = resp.context['chart_escopo_status']
    assert chart['has_data'] is True
    assert chart['type'] == CHART_TYPE_BAR
    assert chart['type'] != CHART_TYPE_AREA
    html = resp.content.decode()
    assert 'data-chart-payload="chart-stage-history"' not in html
    assert 'data-chart-payload="chart-escopo-status"' in html
    assert 'data-component="visao-toggle"' in html
    assert 'visao=historico' in html


# --- ``?visao=historico`` → area cap N (quickstart §3.2) ---------------------


@pytest.mark.django_db
def test_admin_visao_historico_stacked_cap_n_e_kpis_janela(
    admin,
    colaborador,
):
    """Admin ``?visao=historico``: barra empilhada ≤ N; KPIs evoluiu/estável/sem dado."""
    arquivo = _seed_arquivo(n=N_ARQUIVO_CAP, usuario=colaborador)
    assert len(arquivo) == N_ARQUIVO_CAP
    assert N_ARQUIVO_CAP > HISTORY_DEFAULT_N

    client = _login(admin)
    resp = client.get(_admin_url(), {'visao': 'historico'})

    assert resp.status_code == 200
    assert resp.context.get('visao') == 'historico'
    history = resp.context['chart_stage_history']
    _assert_history_stacked(history)
    labels = list(history['labels'])
    # Default = últimos N por data_inicio/pk — nunca o arquivo completo.
    assert len(labels) == HISTORY_DEFAULT_N
    assert len(labels) < len(arquivo)
    esperados = [c.nome for c in arquivo[-HISTORY_DEFAULT_N:]]
    assert labels == esperados

    html = resp.content.decode()
    assert 'data-chart-payload="chart-stage-history"' in html
    assert 'avançaram' in html.lower()
    assert 'mesmo ponto' in html.lower()
    assert 'sem registro' in html.lower()
    assert 'data-component="visao-toggle"' in html
    assert 'name="ciclo"' in html
    # Toggle ativo em Histórico; Neste ciclo remove a query.
    toggle = html.split('data-component="visao-toggle"')[1].split('</nav>')[0]
    assert 'aria-current="page"' in toggle
    assert 'Histórico' in toggle


@pytest.mark.django_db
def test_team_visao_historico_stacked_so_do_escopo(
    lider,
    colaborador,
    area,
    cargo_colab,
    admin,
):
    """Time ``?visao=historico``: tendência só do escopo do líder (não org inteira)."""
    arquivo = _seed_arquivo(n=N_ARQUIVO, usuario=colaborador)
    outro_lider = CustomUser.objects.create_user(
        email='outro.hist.lider@test.greenn.com.br',
        password=DEFAULT_PASSWORD,
        nome='Outro Líder Hist',
        cargo=lider.cargo,
        area=area,
        line_manager=admin,
        email_confirmado_em=timezone.now(),
    )
    fora = CustomUser.objects.create_user(
        email='fora.hist@test.greenn.com.br',
        password=DEFAULT_PASSWORD,
        nome='Fora Hist',
        cargo=cargo_colab,
        area=area,
        line_manager=outro_lider,
        email_confirmado_em=timezone.now(),
    )
    # Fora do escopo: muitos cabeçalhos no mesmo arquivo — não devem poluir.
    for ciclo in arquivo:
        Avaliacao.objects.create(
            ciclo=ciclo,
            usuario=fora,
            etapa=Avaliacao.Etapa.FEEDBACK,
            concluida=True,
        )

    client = _login(lider)
    resp = client.get(_team_url(), {'visao': 'historico'})

    assert resp.status_code == 200
    assert resp.context.get('visao') == 'historico'
    history = resp.context['chart_stage_history']
    _assert_history_stacked(history)
    labels = list(history['labels'])
    assert len(labels) <= HISTORY_DEFAULT_N
    assert set(labels) <= {c.nome for c in arquivo}

    # Contagens só do colaborador no escopo — não 2 (com fora).
    for point in history['points']:
        totais = point['totais']
        assert totais['em_andamento'] + totais['concluida'] <= 1
        assert sum(point['detalhe_etapas'].values()) <= 1
    assert fora.email not in resp.content.decode()


# --- ``?ciclos=`` cap / nunca ~57 (quickstart §3.3) --------------------------


@pytest.mark.django_db
def test_admin_visao_historico_ciclos_honra_ids_e_cap(
    admin,
    colaborador,
):
    """``?ciclos=``: só ids pedidos; cap ``HISTORY_DEFAULT_N``; nunca ~57 eixos."""
    arquivo = _seed_arquivo(n=N_ARQUIVO_CAP, usuario=colaborador)
    # Pedido explícito: 10 ids (acima do teto) + ordem deliberada (não default).
    pedidos = arquivo[:10]
    assert len(pedidos) > HISTORY_DEFAULT_N
    ciclos_param = ','.join(str(c.pk) for c in pedidos)

    client = _login(admin)
    resp = client.get(
        _admin_url(),
        {'visao': 'historico', 'ciclos': ciclos_param},
    )

    assert resp.status_code == 200
    history = resp.context['chart_stage_history']
    _assert_history_stacked(history)
    labels = list(history['labels'])
    assert len(labels) == HISTORY_DEFAULT_N
    # Cap nos primeiros N do pedido — não plota o arquivo inteiro nem os 10.
    assert labels == [c.nome for c in pedidos[:HISTORY_DEFAULT_N]]
    omitidos = {c.nome for c in pedidos[HISTORY_DEFAULT_N:]}
    assert omitidos.isdisjoint(set(labels))
    resto_arquivo = {c.nome for c in arquivo[10:]}
    assert resto_arquivo.isdisjoint(set(labels))
    assert len(labels) != N_ARQUIVO_CAP


# --- Lacuna → null ≠ 0 (quickstart §3.4) -------------------------------------


@pytest.mark.django_db
def test_admin_visao_historico_sem_cabecalho_e_100_sem_avaliacao(
    admin,
    colaborador,
):
    """Ciclo sem cabeçalho no escopo → 100% sem avaliação (parados), não 0 de nota."""
    arquivo = _seed_arquivo(
        n=5,
        usuario=colaborador,
        skip_indices=frozenset({2}),
    )
    lacuna = arquivo[2]
    assert not Avaliacao.objects.filter(ciclo=lacuna, usuario=colaborador).exists()

    client = _login(admin)
    ciclos_param = ','.join(str(c.pk) for c in arquivo)
    resp = client.get(
        _admin_url(),
        {'visao': 'historico', 'ciclos': ciclos_param},
    )

    assert resp.status_code == 200
    history = resp.context['chart_stage_history']
    _assert_history_stacked(history, max_labels=5)
    labels = list(history['labels'])
    assert lacuna.nome in labels
    idx = labels.index(lacuna.nome)
    point = history['points'][idx]
    assert point['sem_avaliacao_pct'] == 100
    assert point['em_andamento_pct'] == 0
    assert point['concluida_pct'] == 0
    assert point['totais']['concluida'] == 0
    assert sum(point['detalhe_etapas'].values()) == 0
    preenchidos = [p for i, p in enumerate(history['points']) if i != idx]
    assert preenchidos
    assert all(p['totais']['concluida'] == 1 for p in preenchidos)
    assert all(p['concluida_pct'] > 0 for p in preenchidos)


# --- Aderência/gap empty ``sem_nota`` no modo histórico (quickstart §3.4) ----


@pytest.mark.django_db
def test_admin_visao_historico_aderencia_empty_sem_nota(
    admin,
    colaborador,
):
    """No modo histórico, série de aderência/nota → empty ``sem_nota`` (não principal)."""
    _seed_arquivo(n=N_ARQUIVO, usuario=colaborador)

    client = _login(admin)
    resp = client.get(_admin_url(), {'visao': 'historico'})

    assert resp.status_code == 200
    history = resp.context['chart_stage_history']
    _assert_history_stacked(history)
    _assert_aderencia_sem_nota(resp.context.get('chart_aderencia_distribuicao'))
    html = resp.content.decode()
    assert _COPY_SEM_NOTA in html
    assert 'data-chart-payload="chart-aderencia-distribuicao"' not in html
    assert 'data-chart-payload="chart-stage-history"' in html


# --- ``?ciclo=`` singular honrado na visão histórica (seletor agrupado) ------


@pytest.mark.django_db
def test_admin_visao_historico_ciclo_singular_filtra_janela_e_kpis(
    admin,
    colaborador,
):
    """``?visao=historico&ciclo=``: seletor singular → janela de 1 ciclo; KPIs mudam."""
    arquivo = _seed_arquivo(n=5, usuario=colaborador)
    alvo = arquivo[2]
    # Garante avaliação no ciclo alvo para o chart ter dado.
    assert Avaliacao.objects.filter(ciclo=alvo, usuario=colaborador).exists()

    client = _login(admin)

    resp_default = client.get(_admin_url(), {'visao': 'historico'})
    assert resp_default.status_code == 200
    history_default = resp_default.context['chart_stage_history']
    assert len(history_default['labels']) == 5

    resp_filtrado = client.get(
        _admin_url(),
        {'visao': 'historico', 'ciclo': alvo.pk},
    )
    assert resp_filtrado.status_code == 200
    assert resp_filtrado.context['ciclo_selecionado'].pk == alvo.pk
    history_filtrado = resp_filtrado.context['chart_stage_history']
    assert history_filtrado['labels'] == [alvo.nome]
    assert len(history_filtrado['labels']) != len(history_default['labels'])


@pytest.mark.django_db
def test_admin_visao_historico_ciclo_singular_com_aderencia_plota_doughnut(
    admin,
    lider,
    colaborador,
):
    """``?visao=historico&ciclo=`` com snapshot → doughnut de aderência plotável."""
    arquivo = _seed_arquivo(n=3, usuario=colaborador)
    alvo = arquivo[1]
    AderenciaSnapshot.objects.create(
        lider=lider,
        ciclo=alvo,
        percentual=Decimal('72.00'),
        componentes={},
        calculado_em=timezone.now(),
    )

    client = _login(admin)
    resp = client.get(
        _admin_url(),
        {'visao': 'historico', 'ciclo': alvo.pk},
    )

    assert resp.status_code == 200
    chart = resp.context['chart_aderencia_distribuicao']
    assert chart.get('has_data') is True
    html = resp.content.decode()
    assert 'data-chart-payload="chart-aderencia-distribuicao"' in html
    assert _COPY_SEM_NOTA not in html


@pytest.mark.django_db
def test_resolve_history_ciclos_honra_ciclo_singular(db):
    """``resolve_history_ciclos`` usa ``?ciclo=`` quando ``?ciclos=`` ausente."""
    from django.test import RequestFactory

    ciclos = _seed_arquivo(n=5)
    alvo = ciclos[3]
    request = RequestFactory().get('/', {'visao': 'historico', 'ciclo': str(alvo.pk)})
    janela = resolve_history_ciclos(request)
    assert len(janela) == 1
    assert janela[0].pk == alvo.pk


# --- Pessoal MUST NOT (quickstart §3.5) --------------------------------------


@pytest.mark.django_db
def test_personal_must_not_honor_visao_historico(colaborador, ciclo_aberto):
    """Pessoal ignora ``visao=historico`` — sem tendência / sem toggle."""
    assert ciclo_aberto.status == Ciclo.Status.ABERTO
    client = _login(colaborador)
    resp = client.get(
        _personal_url(),
        {'visao': 'historico', 'ciclos': '1,2,3'},
    )

    assert resp.status_code == 200
    assert resp.context.get('visao') != 'historico'
    assert resp.context.get('chart_stage_history') is None
    chart = resp.context['chart_gaps_competencia']
    assert chart['type'] != CHART_TYPE_AREA
    html = resp.content.decode()
    assert 'visao=historico' not in html
    assert 'data-chart-payload="chart-stage-history"' not in html
    assert '/historico/' not in html


# --- Sem rota ``/historico/`` (quickstart §3.6 / denylist) -------------------


def test_nenhuma_rota_historico_nos_urlconfs():
    """MUST NOT path ``/historico/`` em dashboard/cycles nem reverse dedicado."""
    from apps.cycles import urls as cycles_urls
    from apps.dashboard import urls as dashboard_urls

    for module in (dashboard_urls, cycles_urls):
        patterns = ''.join(str(p.pattern) for p in module.urlpatterns)
        assert 'historico' not in patterns.lower()

    with pytest.raises(NoReverseMatch):
        reverse('dashboard:historico')
    with pytest.raises(NoReverseMatch):
        reverse('cycles:historico')


@pytest.mark.django_db
def test_get_historico_path_retorna_404(admin):
    """GET ``/historico/`` não é superfície — 404 (sem página dedicada)."""
    client = _login(admin)
    for path in ('/historico/', '/dashboard/historico/', '/cycles/historico/'):
        resp = client.get(path)
        assert resp.status_code == 404, path


# --- T030: builder ``build_stage_history`` (unitário; views na T031) ----------


@pytest.mark.django_db
def test_build_stage_history_empty_escopo():
    payload = build_stage_history(CustomUser.objects.none(), [])
    assert payload['has_data'] is False
    assert payload['type'] == CHART_TYPE_BAR
    assert payload['empty_message'] == EMPTY_KIND_COPY[EMPTY_KIND_ESCOPO]
    assert payload['id'] == 'chart-stage-history'


@pytest.mark.django_db
def test_build_stage_history_empty_janela(colaborador):
    visible = CustomUser.objects.filter(pk=colaborador.pk)
    payload = build_stage_history(visible, [])
    assert payload['has_data'] is False
    assert payload['empty_message'] == EMPTY_KIND_COPY[EMPTY_KIND_SEM_DADO]


@pytest.mark.django_db
def test_build_stage_history_sem_cabecalho_e_100_sem_avaliacao(colaborador):
    """Ciclo sem cabeçalho → 100% sem avaliação; demais 100% concluídas."""
    visible = CustomUser.objects.filter(pk=colaborador.pk)
    ciclos: list[Ciclo] = []
    for i in range(5):
        year = 2010 + i
        ciclo = Ciclo.objects.create(
            nome=f'T030-{year}',
            data_inicio=date(year, 1, 15),
            data_fim=date(year, 12, 15),
            status=Ciclo.Status.ENCERRADO,
        )
        ciclos.append(ciclo)
        if i == 2:
            continue
        Avaliacao.objects.create(
            ciclo=ciclo,
            usuario=colaborador,
            etapa=Avaliacao.Etapa.FEEDBACK,
            concluida=True,
        )

    payload = build_stage_history(visible, ciclos)
    _assert_history_stacked(payload, max_labels=5)
    assert payload['labels'] == [c.nome for c in ciclos]
    point = payload['points'][2]
    assert point['sem_avaliacao_pct'] == 100
    assert point['em_andamento_pct'] == 0
    assert point['concluida_pct'] == 0
    assert payload['points'][0]['concluida_pct'] == 100
    assert payload['points'][0]['detalhe_etapas'][Avaliacao.Etapa.FEEDBACK] == 1
    line = next(s for s in payload['series'] if s['key'] == 'taxa_conclusao')
    assert line['kind'] == 'line'
    assert line['values'][0] == 100
    assert line['values'][2] == 0


@pytest.mark.django_db
def test_build_stage_history_sem_cabecalhos(colaborador):
    visible = CustomUser.objects.filter(pk=colaborador.pk)
    ciclo = Ciclo.objects.create(
        nome='T030-bare',
        data_inicio=date(1999, 1, 1),
        data_fim=date(1999, 12, 1),
        status=Ciclo.Status.ENCERRADO,
    )
    payload = build_stage_history(visible, [ciclo])
    assert payload['has_data'] is False
    assert payload['empty_message'] == EMPTY_KIND_COPY[EMPTY_KIND_SEM_DADO]


@pytest.mark.django_db
def test_default_e_parse_history_ciclos_cap_n():
    arquivo: list[Ciclo] = []
    for i in range(12):
        year = 2020 + i
        arquivo.append(
            Ciclo.objects.create(
                nome=f'T030D-{year}',
                data_inicio=date(year, 1, 1),
                data_fim=date(year, 12, 1),
                status=Ciclo.Status.ENCERRADO,
            ),
        )

    default = default_history_ciclos()
    assert len(default) == HISTORY_DEFAULT_N
    assert [c.nome for c in default] == [
        c.nome for c in arquivo[-HISTORY_DEFAULT_N:]
    ]

    pedidos = arquivo[:10]
    parsed = parse_history_ciclos(','.join(str(c.pk) for c in pedidos))
    assert parsed is not None
    assert len(parsed) == HISTORY_DEFAULT_N
    assert [c.pk for c in parsed] == [c.pk for c in pedidos[:HISTORY_DEFAULT_N]]
    assert parse_history_ciclos(None) is None
    assert parse_history_ciclos('') is None


@pytest.mark.django_db
def test_build_stage_history_respeita_escopo_visible(
    colaborador,
    area,
    cargo_colab,
    admin,
):
    """Contagens só do QS ``visible`` — não do org inteiro."""
    fora = CustomUser.objects.create_user(
        email='fora.t030@test.greenn.com.br',
        password=DEFAULT_PASSWORD,
        nome='Fora T030',
        cargo=cargo_colab,
        area=area,
        line_manager=admin,
        email_confirmado_em=timezone.now(),
    )
    ciclo = Ciclo.objects.create(
        nome='T030-escopo',
        data_inicio=date(2015, 1, 1),
        data_fim=date(2015, 12, 1),
        status=Ciclo.Status.ENCERRADO,
    )
    for user in (colaborador, fora):
        Avaliacao.objects.create(
            ciclo=ciclo,
            usuario=user,
            etapa=Avaliacao.Etapa.FEEDBACK,
            concluida=True,
        )

    visible = CustomUser.objects.filter(pk=colaborador.pk)
    payload = build_stage_history(visible, [ciclo])
    assert payload['has_data'] is True
    point = payload['points'][0]
    assert point['totais']['concluida'] == 1
    assert point['detalhe_etapas'][Avaliacao.Etapa.FEEDBACK] == 1
    assert point['concluida_pct'] == 100
    assert point['totais']['em_andamento'] == 0


@pytest.mark.django_db
def test_build_stage_history_agrupa_tres_status(
    colaborador,
    area,
    cargo_colab,
    admin,
):
    """Metas/feedback em aberto = em_andamento; flag concluida; sem cabeçalho = sem_avaliacao."""
    for etapa in Avaliacao.Etapa:
        assert STATUS_MAP[etapa.value] == 'em_andamento'
    andamento = CustomUser.objects.create_user(
        email='andamento.t030@test.greenn.com.br',
        password=DEFAULT_PASSWORD,
        nome='Andamento T030',
        cargo=cargo_colab,
        area=area,
        line_manager=admin,
        email_confirmado_em=timezone.now(),
    )
    parado = CustomUser.objects.create_user(
        email='parado.t030@test.greenn.com.br',
        password=DEFAULT_PASSWORD,
        nome='Parado T030',
        cargo=cargo_colab,
        area=area,
        line_manager=admin,
        email_confirmado_em=timezone.now(),
    )
    ciclo = Ciclo.objects.create(
        nome='T030-triade',
        data_inicio=date(2016, 3, 1),
        data_fim=date(2016, 4, 30),
        status=Ciclo.Status.ENCERRADO,
    )
    Avaliacao.objects.create(
        ciclo=ciclo,
        usuario=colaborador,
        etapa=Avaliacao.Etapa.FEEDBACK,
        concluida=True,
    )
    Avaliacao.objects.create(
        ciclo=ciclo,
        usuario=andamento,
        etapa=Avaliacao.Etapa.INPUT_METAS,
        concluida=False,
    )
    visible = CustomUser.objects.filter(
        pk__in=[colaborador.pk, andamento.pk, parado.pk],
    )
    payload = build_stage_history(visible, [ciclo])
    _assert_history_stacked(payload, max_labels=1)
    point = payload['points'][0]
    assert point['totais'] == {
        'sem_avaliacao': 1,
        'em_andamento': 1,
        'concluida': 1,
    }
    assert point['sem_avaliacao_pct'] + point['em_andamento_pct'] + point['concluida_pct'] == 100
    assert point['detalhe_etapas'][Avaliacao.Etapa.INPUT_METAS] == 1
    assert point['detalhe_etapas'][Avaliacao.Etapa.FEEDBACK] == 1
    assert point['data'] == '2016-03-01'
    legend_labels = [item['label'] for item in payload['legend_items']]
    assert legend_labels == ['Sem avaliação', 'Em andamento', 'Concluídas']
    assert 'T030-triade' in payload['legend_caption']


# --- T034: Freeze D / density-history-empty (SC-004–006) ---


def test_t034_chart_block_sem_figcaption_bar_horizontal_area():
    """T034 / chart-catalog: bar, bar_horizontal, area e radar sem figcaption duplicado."""
    source = _CHART_BLOCK.read_text(encoding='utf-8')
    assert 'figcaption' in source
    assert 'chart.type != "bar"' in source
    assert 'chart.type != "bar_horizontal"' in source
    assert 'chart.type != "area"' in source
    assert 'chart.type != "radar"' in source
    assert 'html_legend' in source
    assert 'dashboard-chart-canvas' in source
    assert 'min-w-0' in source


def test_t034_partials_htmx_sem_chart_block():
    """T034 / FR-017: partials de lista sem canvas."""
    for path in _HTMX_PARTIALS:
        text = path.read_text(encoding='utf-8')
        assert '_chart_block' not in text, path.name
        assert 'data-chart-payload' not in text, path.name


def test_t034_pessoal_sem_toggle_historico():
    """T034 / FR-016: pessoal sem tendência nesta fatia."""
    text = _PERSONAL_TMPL.read_text(encoding='utf-8')
    assert '_visao_toggle' not in text
    assert 'visao=historico' not in text
    assert '_chart_block' in text


def test_t034_superficies_com_chart_usam_min_w0_e_canvas_css():
    """T034 / SC-006: cadeia min-w-0 + altura fixa do canvas (~375px)."""
    css = _CANVAS_CSS.read_text(encoding='utf-8')
    assert '.dashboard-chart-canvas' in css
    assert 'min-w-0' in css
    assert '15.5rem' in css

    for path in _CHART_SURFACES:
        text = path.read_text(encoding='utf-8')
        assert '_chart_block' in text, path.name
        assert 'min-w-0' in text, path.name
        assert 'chart.js@4.5.1' in text.lower(), path.name


# --- T037: Chart.js 4.5.1 / DOMContentLoaded / FR-017 ---


def test_t012_dashboard_charts_bar_fallback_mono_not_triad():
    """T012 / V-L1: bar sem colors → mono teal; Status Triad só no doughnut."""
    source = _DASHBOARD_CHARTS_JS.read_text(encoding='utf-8')
    assert 'COLOR_FINISH_TEAL' in source
    assert 'isDoughnut ? STATUS_TRIAD : [COLOR_FINISH_TEAL]' in source
    assert 'isDoughnut ? STATUS_TRIAD[0] : COLOR_FINISH_TEAL' in source
    # Não regressar ao fallback Triad cego em buildSingleSeriesConfig.
    assert (
        "payload.colors && payload.colors.length ? payload.colors : STATUS_TRIAD"
        not in source
    )


def test_t037_dashboard_charts_init_sem_htmx_after_swap():
    """T037 / FR-017: init só em DOMContentLoaded; sem htmx:afterSwap; sem plugin npm."""
    source = _DASHBOARD_CHARTS_JS.read_text(encoding='utf-8')
    assert "addEventListener('DOMContentLoaded', initAll)" in source
    assert 'htmx:afterSwap' not in source
    assert 'require(' not in source
    assert 'import ' not in source
    # Comentários documentam rejeição de plugin npm; plugins reais são inline.
    assert 'sem chartjs-plugin' in source.lower() or 'sem plugin npm' in source.lower()
    assert 'afterDraw' in source
    assert 'afterDatasetsDraw' in source
    assert 'buildStackedPercentConfig' in source
    assert "payload.stacked === true" in source
    assert 'function fitCanvasFrame' in source


def test_t037_base_sem_chartjs_global_e_partials_sem_chart_block():
    """T037: Chart.js só via extra_js das superfícies; partials HTMX sem canvas."""
    base = _BASE_HTML.read_text(encoding='utf-8')
    assert 'chart.js' not in base.lower()
    assert 'dashboard_charts' not in base

    for path in _HTMX_PARTIALS:
        text = path.read_text(encoding='utf-8')
        assert '_chart_block' not in text, path.name
        assert 'data-chart-payload' not in text, path.name
        assert 'chart.js' not in text.lower(), path.name

    for path in _CHART_SURFACES:
        text = path.read_text(encoding='utf-8')
        assert 'chart.js@4.5.1' in text.lower(), path.name
        assert 'dashboard_charts.js' in text, path.name

    for path in _NO_CHART_SURFACES:
        text = path.read_text(encoding='utf-8')
        assert 'chart.js' not in text.lower(), path.name
        assert 'dashboard_charts' not in text, path.name
        assert '_chart_block' not in text, path.name
        assert 'data-chart-payload' not in text, path.name
