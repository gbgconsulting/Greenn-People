"""T028 [US3] — modo ``?visao=historico`` (admin / time / pessoal / rotas).

Contrato: ``density-history-empty.md`` §2 / FR-003 / FR-016 / quickstart §3.
GET admin/time **sem** ``visao=`` → operacional (não tendência).
``?visao=historico`` → ``type: area``, ≤ ``HISTORY_DEFAULT_N`` ciclos, escopo.
``?visao=historico&ciclos=`` → só ids pedidos, cap 8, nunca ~57.
Lacuna → ``null`` ≠ 0; nota/gap/aderência → ``has_data=false`` + empty ``sem_nota``.
Pessoal MUST NOT honrar ``visao=historico``; nenhuma rota ``/historico/``.

Fixtures sintéticas (12–21 ciclos); MUST NOT ``data/legado-solides/raw/``.
Denylist intacta (allowlist testes).
"""

from __future__ import annotations

from datetime import date

import pytest
from django.test import Client
from django.urls import NoReverseMatch, reverse
from django.utils import timezone

from apps.accounts.models import CustomUser
from apps.cycles.models import Ciclo
from apps.dashboard.chart_payloads import (
    CHART_TYPE_AREA,
    CHART_TYPE_BAR_HORIZONTAL,
    EMPTY_KIND_COPY,
    EMPTY_KIND_ESCOPO,
    EMPTY_KIND_SEM_DADO,
    EMPTY_KIND_SEM_NOTA,
    HISTORY_DEFAULT_N,
)
from apps.dashboard.services.history import (
    build_stage_history,
    default_history_ciclos,
    parse_history_ciclos,
)
from apps.reviews.models import Avaliacao
from tests.conftest import DEFAULT_PASSWORD

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


def _series_values(chart: dict | None) -> list:
    """Achata ``series[].values`` (multi) ou ``values`` (single)."""
    if not chart:
        return []
    series = list(chart.get('series') or [])
    if series:
        out: list = []
        for serie in series:
            out.extend(list(serie.get('values') or []))
        return out
    return list(chart.get('values') or [])


def _assert_history_area(chart: dict | None, *, max_labels: int = HISTORY_DEFAULT_N) -> None:
    assert chart is not None
    assert chart.get('has_data') is True
    assert chart.get('type') == CHART_TYPE_AREA
    labels = list(chart.get('labels') or [])
    assert 1 <= len(labels) <= max_labels
    assert len(labels) <= HISTORY_DEFAULT_N


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
    assert chart['type'] == CHART_TYPE_BAR_HORIZONTAL
    assert chart['type'] != CHART_TYPE_AREA
    html = resp.content.decode()
    assert 'data-chart-payload="chart-stage-history"' not in html
    assert 'data-chart-payload="chart-escopo-status"' in html
    assert 'data-component="visao-toggle"' in html
    assert 'visao=historico' in html


# --- ``?visao=historico`` → area cap N (quickstart §3.2) ---------------------


@pytest.mark.django_db
def test_admin_visao_historico_area_cap_n_e_kpis_janela(
    admin,
    colaborador,
):
    """Admin ``?visao=historico``: ``area`` ≤ N; KPIs evoluiu/estável/sem dado."""
    arquivo = _seed_arquivo(n=N_ARQUIVO_CAP, usuario=colaborador)
    assert len(arquivo) == N_ARQUIVO_CAP
    assert N_ARQUIVO_CAP > HISTORY_DEFAULT_N

    client = _login(admin)
    resp = client.get(_admin_url(), {'visao': 'historico'})

    assert resp.status_code == 200
    assert resp.context.get('visao') == 'historico'
    history = resp.context['chart_stage_history']
    _assert_history_area(history)
    labels = list(history['labels'])
    # Default = últimos N por data_inicio/pk — nunca o arquivo completo.
    assert len(labels) == HISTORY_DEFAULT_N
    assert len(labels) < len(arquivo)
    esperados = [c.nome for c in arquivo[-HISTORY_DEFAULT_N:]]
    assert labels == esperados

    html = resp.content.decode()
    assert 'data-chart-payload="chart-stage-history"' in html
    assert 'evoluiu' in html.lower() or 'Evoluiu' in html
    assert 'estável' in html.lower() or 'Estável' in html
    assert 'sem dado' in html.lower() or 'Sem dado' in html
    assert 'data-component="visao-toggle"' in html
    # Toggle ativo em Histórico; Operacional remove a query.
    toggle = html.split('data-component="visao-toggle"')[1].split('</nav>')[0]
    assert 'aria-current="page"' in toggle
    assert 'Histórico' in toggle


@pytest.mark.django_db
def test_team_visao_historico_area_so_do_escopo(
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
    _assert_history_area(history)
    labels = list(history['labels'])
    assert len(labels) <= HISTORY_DEFAULT_N
    assert set(labels) <= {c.nome for c in arquivo}

    # Totais da série ≤ 1 por ciclo (só colaborador no escopo), não 2 (com fora).
    flat = [v for v in _series_values(history) if v is not None]
    assert flat
    assert max(flat) <= 1
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
    _assert_history_area(history)
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
def test_admin_visao_historico_lacuna_e_null_nao_zero(
    admin,
    colaborador,
):
    """Ponto sem cabeçalho útil no escopo → ``null`` na série, nunca 0 de desempenho."""
    # Ciclo do meio sem Avaliacao → lacuna explícita na janela.
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
    _assert_history_area(history, max_labels=5)
    labels = list(history['labels'])
    assert lacuna.nome in labels
    idx = labels.index(lacuna.nome)

    series = list(history.get('series') or [])
    assert series, 'tendência area multi-série (etapa/conclusão) esperada'
    for serie in series:
        values = list(serie.get('values') or [])
        assert len(values) == len(labels)
        assert values[idx] is None
        assert values[idx] != 0
    # Demais pontos com cabeçalho não são null forçados.
    preenchidos = [
        v
        for serie in series
        for i, v in enumerate(serie.get('values') or [])
        if i != idx
    ]
    assert any(v is not None for v in preenchidos)


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
    _assert_history_area(history)
    _assert_aderencia_sem_nota(resp.context.get('chart_aderencia_distribuicao'))
    html = resp.content.decode()
    assert _COPY_SEM_NOTA in html
    assert 'data-chart-payload="chart-aderencia-distribuicao"' not in html
    assert 'data-chart-payload="chart-stage-history"' in html


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
    assert payload['type'] == CHART_TYPE_AREA
    assert payload['empty_message'] == EMPTY_KIND_COPY[EMPTY_KIND_ESCOPO]
    assert payload['id'] == 'chart-stage-history'


@pytest.mark.django_db
def test_build_stage_history_empty_janela(colaborador):
    visible = CustomUser.objects.filter(pk=colaborador.pk)
    payload = build_stage_history(visible, [])
    assert payload['has_data'] is False
    assert payload['empty_message'] == EMPTY_KIND_COPY[EMPTY_KIND_SEM_DADO]


@pytest.mark.django_db
def test_build_stage_history_lacuna_null_e_area(colaborador):
    """Lacuna sem cabeçalho → ``null``; etapas + concluídas em ``series``."""
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
    assert payload['has_data'] is True
    assert payload['type'] == CHART_TYPE_AREA
    assert payload['labels'] == [c.nome for c in ciclos]
    assert payload['series']

    lacuna_idx = 2
    for serie in payload['series']:
        values = list(serie['values'])
        assert len(values) == 5
        assert values[lacuna_idx] is None
        assert values[lacuna_idx] != 0

    feedback = next(
        s for s in payload['series'] if s['key'] == Avaliacao.Etapa.FEEDBACK
    )
    assert feedback['values'][0] == 1
    assert feedback['values'][2] is None

    concluida = next(s for s in payload['series'] if s['key'] == 'concluida')
    assert concluida['values'][0] == 1
    assert concluida['values'][2] is None


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
    feedback = next(
        s for s in payload['series'] if s['key'] == Avaliacao.Etapa.FEEDBACK
    )
    assert feedback['values'] == [1]
