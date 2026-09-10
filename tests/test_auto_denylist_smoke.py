"""T031 [US5]: smoke denylist — non-goals 018 permanecem fora.

Alinhado a ``specs/018-auto-cycle-admission/contracts/non-goals-denylist.md``:
stage / fórmulas / PDI / escopo hierárquico intactos; Opção B, backfill de
marcos, feriado municipal, papel RH novo, lib de feriados, DRF/SPA e
disparo HTTP do lote do mês fora do corte.
"""

from __future__ import annotations

import ast
import inspect
from datetime import date
from decimal import Decimal
from pathlib import Path

from django.apps import apps
from django.conf import settings

from apps.accounts.models import CustomUser
from apps.accounts.services import scope as scope_mod
from apps.core import calendar_br
from apps.cycles.services import stage as stage_mod
from apps.cycles.services.marco import next_future_marco, user_is_auto_candidate
from apps.cycles.views import AutoGovernanceView
from apps.goals.services import approval as approval_mod
from apps.talent.services.classification import (
    calculate_quadrante,
    derive_desempenho,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
REQUIREMENTS = (REPO_ROOT / 'requirements.txt').read_text(encoding='utf-8')


# ---------------------------------------------------------------------------
# Paths de domínio — superfície pública intacta (diff de regra vazio)
# ---------------------------------------------------------------------------


def test_denylist_stage_surface_intacta():
    """Machine de etapas continua exportando can_advance / advance_stage."""
    assert callable(stage_mod.can_advance)
    assert callable(stage_mod.advance_stage)


def test_denylist_approval_surface_intacta():
    """Fórmulas/fluxo de aprovação de metas não foram removidos."""
    assert callable(approval_mod.approve_meta)
    assert callable(approval_mod.reject_meta)


def test_denylist_scope_hierarquico_intacta():
    """Escopo hierárquico permanece backend-authoritative."""
    assert callable(scope_mod.get_visible_users)
    assert callable(scope_mod.get_scope_level)
    assert callable(scope_mod.user_in_scope)


def test_denylist_talent_formulas_limiares_intactos():
    """9-box: limiares 0.33 / 0.66 e rótulos intactos (FR-019)."""
    assert derive_desempenho(Decimal('0.32')) == 1
    assert derive_desempenho(Decimal('0.33')) == 2
    assert derive_desempenho(Decimal('0.66')) == 2
    assert derive_desempenho(Decimal('0.67')) == 3
    assert calculate_quadrante(2, 3) == 'medio_alto'


def test_denylist_pdi_app_presente_sem_papel_novo():
    """App PDI existe; sem app Django nova só para o automático."""
    assert apps.is_installed('apps.pdi')
    assert apps.is_installed('apps.cycles')
    forbidden = {'apps.auto_cycles', 'apps.rh', 'rest_framework'}
    installed = set(settings.INSTALLED_APPS)
    assert not (forbidden & installed)


# ---------------------------------------------------------------------------
# Non-goals explícitos
# ---------------------------------------------------------------------------


def test_denylist_sem_papel_rh_is_rh():
    """RH = is_admin; campo/papel is_rh não existe (FR-019)."""
    field_names = {f.name for f in CustomUser._meta.get_fields()}
    assert 'is_admin' in field_names
    assert 'is_rh' not in field_names
    assert not hasattr(CustomUser, 'is_rh')


def test_denylist_sem_lib_feriados_nem_drf():
    """Sem holidays/workalendar/DRF nas deps (Princípio I / stack)."""
    lowered = REQUIREMENTS.lower()
    for banned in ('holidays', 'workalendar', 'djangorestframework', 'rest_framework'):
        assert banned not in lowered, f'dep proibida na denylist: {banned}'


def test_denylist_feriado_municipal_fora_do_calendario():
    """Calendário BR nacional: aniversários municipais conhecidos fora."""
    # São Paulo (25/01), Rio (20/01), BH (12/12) — municipais, não federais.
    municipais = (
        date(2026, 1, 25),
        date(2026, 1, 20),
        date(2026, 12, 12),
    )
    for d in municipais:
        assert d not in calendar_br.national_holidays(d.year)
        # Em dia de semana sem federal → ainda é dia útil nacional.
        if d.weekday() < 5:
            assert calendar_br.is_business_day(d) is True

    src = inspect.getsource(calendar_br)
    assert 'municipal' in src.lower() or 'estaduais' in src.lower()
    assert 'national_holidays' in src


def test_denylist_opcao_a_ritmo_admissao_nao_opcao_b():
    """Opção A: elegibilidade por marco +6m — não lote único sem ritmo.

    Opção B seria matricular todos os ativos do mês sem série de admissão.
    """
    # Admitido jan/2025; ref jul/2026 → próximo marco = jul/2026 (k=3)
    assert next_future_marco(date(2025, 1, 10), date(2026, 7, 1)) == (2026, 7)
    # Admitido fev/2025; ref jul/2026 → próximo = ago/2026 (não entra em jul)
    assert next_future_marco(date(2025, 2, 10), date(2026, 7, 1)) == (2026, 8)

    class _U:
        is_active = True
        data_entrada = date(2025, 2, 10)

    assert user_is_auto_candidate(_U(), year=2026, month=7, ref_date=date(2026, 7, 1)) is False
    assert user_is_auto_candidate(_U(), year=2026, month=8, ref_date=date(2026, 8, 3)) is True


def test_denylist_bootstrap_nao_recupera_marco_passado():
    """Zero backfill: next_future_marco nunca devolve mês < ref (FR-005)."""
    ref = date(2026, 9, 15)
    # Admissão jan/2022 — série …/jul/2026/jan/2027; ref set → jan/2027
    year, month = next_future_marco(date(2022, 1, 5), ref)
    assert (year, month) >= (ref.year, ref.month)
    assert (year, month) == (2027, 1)


def test_denylist_governanca_http_somente_leitura():
    """Governança não processa o lote do mês via HTTP (FR-021)."""
    assert AutoGovernanceView.http_method_names == ['get', 'head', 'options']
    src = inspect.getsource(AutoGovernanceView)
    for banned in (
        'run_auto_cycle_admission_daily',
        'open_auto_cohort',
        'process_auto',
        'ensure_avaliacao_for_user',
    ):
        assert banned not in src

    # Source do módulo de views: AutoGovernanceView não importa a task
    views_path = REPO_ROOT / 'apps' / 'cycles' / 'views.py'
    tree = ast.parse(views_path.read_text(encoding='utf-8'))
    imported_names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            for alias in node.names:
                imported_names.add(alias.name)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                imported_names.add(alias.name.split('.')[-1])
    assert 'run_auto_cycle_admission_daily' not in imported_names


def test_denylist_paths_contrato_existem():
    """Paths listados no contrato ainda existem (não foram deletados/movidos)."""
    paths = [
        'apps/cycles/services/stage.py',
        'apps/goals/services/approval.py',
        'apps/reviews/services/evaluation.py',
        'apps/dashboard/services/adherence.py',
        'apps/accounts/services/scope.py',
        'apps/talent',
        'apps/pdi',
    ]
    for rel in paths:
        assert (REPO_ROOT / rel).exists(), f'path denylist ausente: {rel}'


def test_denylist_inativo_e_sem_data_fora_do_automatico():
    """Matrícula de inativo / sem data_entrada permanece fora (FR-003/004)."""

    class _SemData:
        is_active = True
        data_entrada = None

    class _Inativo:
        is_active = False
        data_entrada = date(2025, 7, 1)

    ref = date(2026, 7, 1)
    assert user_is_auto_candidate(_SemData(), year=2026, month=7, ref_date=ref) is False
    assert user_is_auto_candidate(_Inativo(), year=2026, month=7, ref_date=ref) is False
