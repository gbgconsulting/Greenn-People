"""T027 [US4]: AuthZ + superfície de governança do automático.

Quickstart V5; SC-006 / SC-007; contratos:
- ``governance-surface-contract.md``
- ``backend-scope-authz.md``

Cobre:
- Admin GET → 200 com blocos (entrantes / sem admissão / alertas / falhas / KPIs)
- Líder e colaborador GET → 403; sem leak da fila organizacional
- Anônimo → redirect login
- GET não processa lote do mês (só leitura)
"""

from __future__ import annotations

from datetime import date, datetime
from urllib.parse import quote
from zoneinfo import ZoneInfo

import pytest
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import CustomUser
from apps.cycles.models import AutoCycleEvent, AutoCycleRun, Ciclo
from apps.cycles.views import AdminCyclesMixin, AutoGovernanceView
from tests.conftest import DEFAULT_PASSWORD

TZ = ZoneInfo('America/Sao_Paulo')
PERIOD_YEAR = 2026
PERIOD_MONTH = 7
REF_DATE = date(2026, 7, 1)

# Nomes/emails únicos para assert de leak (não devem aparecer em 403).
LEAK_ENTRANTE_NOME = 'Entrante Gov Leak Unique'
LEAK_ENTRANTE_EMAIL = 'entrante.gov.leak@test.greenn.com.br'
LEAK_PENDENCIA_NOME = 'Pendencia Gov Leak Unique'
LEAK_PENDENCIA_EMAIL = 'pendencia.gov.leak@test.greenn.com.br'
LEAK_ALERTA_NOME = 'Alerta Gov Leak Unique'
LEAK_ALERTA_EMAIL = 'alerta.gov.leak@test.greenn.com.br'


def _governance_url(**query) -> str:
    url = reverse('cycles:auto_governance')
    if query:
        from urllib.parse import urlencode

        return f'{url}?{urlencode(query)}'
    return url


def _make_peer(
    *,
    email: str,
    nome: str,
    lider,
    area,
    cargo_colab,
) -> CustomUser:
    return CustomUser.objects.create_user(
        email=email,
        password=DEFAULT_PASSWORD,
        nome=nome,
        cargo=cargo_colab,
        area=area,
        line_manager=lider,
        data_entrada=date(2026, 1, 10),
        email_confirmado_em=timezone.now(),
    )


@pytest.fixture
def governance_seed(db, lider, area, cargo_colab) -> dict:
    """Run + events nominativos do período jul/2026 (fila org sensível)."""
    ciclo = Ciclo.objects.create(
        nome='Ciclo Auto Gov AuthZ',
        data_inicio=REF_DATE,
        data_fim=REF_DATE.replace(day=21),
        admitidos_ate=REF_DATE,
        status=Ciclo.Status.ABERTO,
        origem=Ciclo.Origem.AUTOMATICO,
        marco_competencia=REF_DATE,
    )
    run = AutoCycleRun.objects.create(
        executado_em=datetime(2026, 7, 1, 0, 35, tzinfo=TZ),
        data_referencia=REF_DATE,
        era_primeiro_dia_util=True,
        marco_competencia=REF_DATE,
        ciclo=ciclo,
        status=AutoCycleRun.Status.PARCIAL,
        matriculados=1,
        alertas_ciclo_aberto=1,
        excluidos_sem_admissao=1,
        mensagem='Seed T027 governança AuthZ',
    )

    entrante = _make_peer(
        email=LEAK_ENTRANTE_EMAIL,
        nome=LEAK_ENTRANTE_NOME,
        lider=lider,
        area=area,
        cargo_colab=cargo_colab,
    )
    pendente = _make_peer(
        email=LEAK_PENDENCIA_EMAIL,
        nome=LEAK_PENDENCIA_NOME,
        lider=lider,
        area=area,
        cargo_colab=cargo_colab,
    )
    alertado = _make_peer(
        email=LEAK_ALERTA_EMAIL,
        nome=LEAK_ALERTA_NOME,
        lider=lider,
        area=area,
        cargo_colab=cargo_colab,
    )

    AutoCycleEvent.objects.create(
        run=run,
        tipo=AutoCycleEvent.Tipo.MATRICULA,
        usuario=entrante,
        ciclo=ciclo,
        payload={'motivo': 'matriculado no lote'},
    )
    AutoCycleEvent.objects.create(
        run=run,
        tipo=AutoCycleEvent.Tipo.PENDENCIA_SEM_ADMISSAO,
        usuario=pendente,
        ciclo=None,
        payload={'motivo': 'sem data_entrada'},
    )
    AutoCycleEvent.objects.create(
        run=run,
        tipo=AutoCycleEvent.Tipo.ALERTA_CICLO_ABERTO,
        usuario=alertado,
        ciclo=ciclo,
        payload={'motivo': 'ciclo ainda aberto'},
    )
    AutoCycleEvent.objects.create(
        run=run,
        tipo=AutoCycleEvent.Tipo.FALHA,
        usuario=None,
        ciclo=ciclo,
        payload={'motivo': 'falha operacional seed T027'},
    )

    return {
        'ciclo': ciclo,
        'run': run,
        'entrante': entrante,
        'pendente': pendente,
        'alertado': alertado,
    }


def _assert_no_org_queue_leak(content: str) -> None:
    """Resposta 403 / redirect não pode vazar fila nominativa da governança."""
    for marker in (
        LEAK_ENTRANTE_NOME,
        LEAK_ENTRANTE_EMAIL,
        LEAK_PENDENCIA_NOME,
        LEAK_PENDENCIA_EMAIL,
        LEAK_ALERTA_NOME,
        LEAK_ALERTA_EMAIL,
        'Entrou no lote',
        'Sem data de entrada',
        'Ciclo ainda aberto',
        'Falha na rotina',
        'auto-governance-kpis',
        'data-gov-section',
    ):
        assert marker not in content, f'Leak de governança: {marker!r}'


# --- AuthZ -----------------------------------------------------------------------


@pytest.mark.django_db
def test_auto_governance_view_usa_admin_cycles_mixin():
    """AuthZ da superfície = AdminCyclesMixin (LoginRequired + RequiresAdmin)."""
    assert issubclass(AutoGovernanceView, AdminCyclesMixin)


@pytest.mark.django_db
def test_auto_governance_get_admin_200_com_blocos(admin, governance_seed):
    """Admin vê 200 com KPIs + blocos nominativos do período (SC-007)."""
    assert admin.is_admin

    client = Client()
    client.force_login(admin)
    resp = client.get(
        _governance_url(year=PERIOD_YEAR, month=PERIOD_MONTH),
    )

    assert resp.status_code == 200
    content = resp.content.decode()

    assert 'Governança do automático' in content
    assert 'data-component="auto-governance"' in content
    assert 'data-component="auto-governance-kpis"' in content
    assert 'data-gov-section="entrantes"' in content
    assert 'data-gov-section="sem-admissao"' in content
    assert 'data-gov-section="alertas"' in content
    assert 'data-gov-section="falhas"' in content

    assert LEAK_ENTRANTE_NOME in content
    assert LEAK_ENTRANTE_EMAIL in content
    assert LEAK_PENDENCIA_NOME in content
    assert LEAK_ALERTA_NOME in content
    assert 'falha operacional seed T027' in content

    ctx = resp.context
    assert ctx['kpis']['entrantes'] == 1
    assert ctx['kpis']['sem_admissao'] == 1
    assert ctx['kpis']['alertas'] == 1
    assert ctx['kpis']['falhas'] >= 1
    assert ctx['kpis']['runs_total'] == 1
    assert ctx['ultimo_run'].pk == governance_seed['run'].pk


@pytest.mark.django_db
def test_auto_governance_get_lider_403_sem_leak(lider, governance_seed):
    """Líder autenticado → 403; não vê fila organizacional (SC-006)."""
    assert not lider.is_admin
    assert lider.is_authenticated

    client = Client()
    client.force_login(lider)
    resp = client.get(
        _governance_url(year=PERIOD_YEAR, month=PERIOD_MONTH),
    )

    assert resp.status_code == 403
    _assert_no_org_queue_leak(resp.content.decode())


@pytest.mark.django_db
def test_auto_governance_get_colaborador_403_sem_leak(colaborador, governance_seed):
    """Colaborador autenticado → 403; sem leak da fila org (SC-006)."""
    assert not colaborador.is_admin

    client = Client()
    client.force_login(colaborador)
    resp = client.get(
        _governance_url(year=PERIOD_YEAR, month=PERIOD_MONTH),
    )

    assert resp.status_code == 403
    _assert_no_org_queue_leak(resp.content.decode())


@pytest.mark.django_db
def test_auto_governance_get_anonimo_redirect_login(governance_seed):
    """Anônimo é redirecionado para login (LoginRequiredMixin)."""
    client = Client()
    url = _governance_url(year=PERIOD_YEAR, month=PERIOD_MONTH)
    resp = client.get(url)

    assert resp.status_code == 302
    login_url = reverse('accounts:login')
    assert resp.url.startswith(login_url)
    assert f'next={quote(url)}' in resp.url
    # Redirect não embute corpo com fila org.
    _assert_no_org_queue_leak(resp.content.decode())


@pytest.mark.django_db
def test_auto_governance_query_periodo_nao_bypass_authz(lider, governance_seed):
    """Manipular year/month/query não libera governança a não-admin."""
    client = Client()
    client.force_login(lider)

    for query in (
        {},
        {'year': PERIOD_YEAR, 'month': PERIOD_MONTH},
        {'year': 2020, 'month': 1},
        {'year': '9999', 'month': '12'},
    ):
        resp = client.get(_governance_url(**query))
        assert resp.status_code == 403
        _assert_no_org_queue_leak(resp.content.decode())


@pytest.mark.django_db
def test_auto_governance_get_nao_processa_lote(admin, governance_seed):
    """HTTP da governança só lê — GET não cria AutoCycleRun (FR-021)."""
    runs_antes = AutoCycleRun.objects.count()
    events_antes = AutoCycleEvent.objects.count()

    client = Client()
    client.force_login(admin)
    resp = client.get(
        _governance_url(year=PERIOD_YEAR, month=PERIOD_MONTH),
    )

    assert resp.status_code == 200
    assert AutoCycleRun.objects.count() == runs_antes
    assert AutoCycleEvent.objects.count() == events_antes
