"""T027 [US3] — AuthZ do GET ``cycles:ciclo_detail``.

Cobertura do contrato ``cycle-managerial-detail.md``:
- Admin → 200
- Não-admin autenticado → 403 (RequiresAdminMixin vigente)
- Anônimo → redirect login

Só view GET. Não altera asserts de negócio open/close / ``cycle.py``.
"""

from __future__ import annotations

from urllib.parse import quote

import pytest
from django.test import Client
from django.urls import reverse


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
