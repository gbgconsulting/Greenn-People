"""AuthZ do GET ``cycles:ciclo_detail`` + T012 [US1] empty ``sem_nota``.

Cobertura do contrato ``cycle-managerial-detail.md``:
- Admin → 200
- Não-admin autenticado → 403 (RequiresAdminMixin vigente)
- Anônimo → redirect login

T012: cabeçalho ``concluida`` sem nota → empty ``sem_nota`` em
desempenho/gap/aderência; pipeline de etapa MAY permanecer; copy não trata
como desempenho 100% saudável; AuthZ ``AdminCyclesMixin`` intacta.

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
    CHART_TYPE_BAR_HORIZONTAL,
    EMPTY_KIND_COPY,
    EMPTY_KIND_SEM_NOTA,
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
        'Cobertura por dimensão',
        'Aderência da liderança',
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
    html = resp.content.decode()
    # Empty via _chart_block / empty_state — sem série inventada no canvas.
    assert 'chart-ciclo-progresso' in html or 'Não há avaliações' in html


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
