"""T015 [US1]: predicado de marco automático + 015 intacto.

Contrato: ``specs/018-auto-cycle-admission/contracts/marco-eligibility-contract.md``
"""

from __future__ import annotations

from datetime import date, timedelta
from types import SimpleNamespace

import pytest
from django.utils import timezone

from apps.accounts.models import CustomUser
from apps.cycles.models import Ciclo
from apps.cycles.services.eligibility import user_eligible_for_ciclo
from apps.cycles.services.marco import (
    list_auto_marco_candidates,
    next_future_marco,
    user_blocked_by_open_cycle,
    user_eligible_for_auto_enrollment,
    user_eligible_for_auto_marco,
    user_is_auto_candidate,
)
from apps.reviews.models import Avaliacao

DEFAULT_PASSWORD = 'TestPass123!'
REF_JUL = date(2026, 7, 1)


def _make_user(
    *,
    email: str,
    lider,
    area,
    cargo_colab,
    data_entrada: date | None,
    is_active: bool = True,
) -> CustomUser:
    return CustomUser.objects.create_user(
        email=email,
        password=DEFAULT_PASSWORD,
        nome=email.split('@')[0],
        cargo=cargo_colab,
        area=area,
        line_manager=lider,
        data_entrada=data_entrada,
        is_active=is_active,
        email_confirmado_em=timezone.now(),
    )


# --- next_future_marco (puro) -------------------------------------------------


def test_next_future_marco_same_month_as_admission():
    assert next_future_marco(date(2026, 7, 15), REF_JUL) == (2026, 7)


def test_next_future_marco_six_month_series():
    """Admitido em jan → marcos jan/jul; em jul/2026 o próximo é jul."""
    assert next_future_marco(date(2026, 1, 10), REF_JUL) == (2026, 7)


def test_next_future_marco_skips_past_marcos_bootstrap():
    """Legado jan/2022 com ref set/2026 → próximo = jan/2027 (zero backfill)."""
    assert next_future_marco(date(2022, 1, 5), date(2026, 9, 15)) == (2027, 1)


def test_next_future_marco_never_before_ref_month():
    """Nunca retorna mês < mês(ref) na série."""
    y, m = next_future_marco(date(2020, 3, 1), date(2026, 7, 20))
    assert (y, m) >= (2026, 7)


def test_next_future_marco_day_of_admission_ignored():
    """Comparação só por (ano, mês)."""
    assert next_future_marco(date(2026, 1, 1), REF_JUL) == next_future_marco(
        date(2026, 1, 31),
        REF_JUL,
    )


# --- predicado automático -----------------------------------------------------


@pytest.mark.django_db
def test_user_is_auto_candidate_july_marco(lider, area, cargo_colab):
    elegivel = _make_user(
        email='marco-jul@test.greenn.com.br',
        lider=lider,
        area=area,
        cargo_colab=cargo_colab,
        data_entrada=date(2026, 1, 15),
    )
    agosto = _make_user(
        email='marco-ago@test.greenn.com.br',
        lider=lider,
        area=area,
        cargo_colab=cargo_colab,
        data_entrada=date(2026, 2, 15),
    )
    assert user_is_auto_candidate(
        elegivel, year=2026, month=7, ref_date=REF_JUL,
    )
    assert user_eligible_for_auto_marco(
        elegivel, year=2026, month=7, ref_date=REF_JUL,
    )
    assert not user_is_auto_candidate(
        agosto, year=2026, month=7, ref_date=REF_JUL,
    )


@pytest.mark.django_db
def test_user_is_auto_candidate_rejects_inactive_and_sem_data(
    lider, area, cargo_colab,
):
    inativo = _make_user(
        email='inativo-marco@test.greenn.com.br',
        lider=lider,
        area=area,
        cargo_colab=cargo_colab,
        data_entrada=date(2026, 1, 15),
        is_active=False,
    )
    sem_data = _make_user(
        email='semdata-marco@test.greenn.com.br',
        lider=lider,
        area=area,
        cargo_colab=cargo_colab,
        data_entrada=None,
    )
    assert not user_is_auto_candidate(
        inativo, year=2026, month=7, ref_date=REF_JUL,
    )
    assert not user_is_auto_candidate(
        sem_data, year=2026, month=7, ref_date=REF_JUL,
    )


@pytest.mark.django_db
def test_user_blocked_by_open_cycle_and_enrollment_predicate(
    lider, area, cargo_colab,
):
    user = _make_user(
        email='blocked-marco@test.greenn.com.br',
        lider=lider,
        area=area,
        cargo_colab=cargo_colab,
        data_entrada=date(2026, 1, 15),
    )
    assert not user_blocked_by_open_cycle(user)
    assert user_eligible_for_auto_enrollment(
        user, year=2026, month=7, ref_date=REF_JUL,
    )

    ciclo = Ciclo.objects.create(
        nome='Ciclo aberto bloqueio',
        data_inicio=REF_JUL - timedelta(days=10),
        data_fim=REF_JUL + timedelta(days=10),
        status=Ciclo.Status.ABERTO,
        origem=Ciclo.Origem.MANUAL,
        admitidos_ate=REF_JUL,
    )
    Avaliacao.objects.create(
        ciclo=ciclo,
        usuario=user,
        etapa=Avaliacao.Etapa.INPUT_METAS,
    )
    assert user_blocked_by_open_cycle(user)
    assert not user_eligible_for_auto_enrollment(
        user, year=2026, month=7, ref_date=REF_JUL,
    )


@pytest.mark.django_db
def test_list_auto_marco_candidates_filters_by_marco(
    lider, area, cargo_colab,
):
    """Lider fixture (jan/2020) também é candidato a jul — isola via queryset."""
    jul_a = _make_user(
        email='lista-jul-a@test.greenn.com.br',
        lider=lider,
        area=area,
        cargo_colab=cargo_colab,
        data_entrada=date(2026, 1, 10),
    )
    jul_b = _make_user(
        email='lista-jul-b@test.greenn.com.br',
        lider=lider,
        area=area,
        cargo_colab=cargo_colab,
        data_entrada=date(2025, 7, 1),
    )
    ago = _make_user(
        email='lista-ago@test.greenn.com.br',
        lider=lider,
        area=area,
        cargo_colab=cargo_colab,
        data_entrada=date(2026, 2, 10),
    )
    qs = CustomUser.objects.filter(pk__in=[jul_a.pk, jul_b.pk, ago.pk])
    found = list_auto_marco_candidates(
        year=2026, month=7, ref_date=REF_JUL, queryset=qs,
    )
    ids = {u.pk for u in found}
    assert ids == {jul_a.pk, jul_b.pk}
    assert ago.pk not in ids


# --- predicado manual 015 intacto ---------------------------------------------


@pytest.mark.django_db
def test_manual_015_predicate_untouched(lider, area, cargo_colab):
    """015: ativo ∧ data_entrada ∧ data_entrada ≤ admitidos_ate."""
    cutoff = date(2024, 6, 30)
    ciclo = SimpleNamespace(admitidos_ate=cutoff)

    ok = _make_user(
        email='015-ok@test.greenn.com.br',
        lider=lider,
        area=area,
        cargo_colab=cargo_colab,
        data_entrada=cutoff,
    )
    late = _make_user(
        email='015-late@test.greenn.com.br',
        lider=lider,
        area=area,
        cargo_colab=cargo_colab,
        data_entrada=cutoff + timedelta(days=1),
    )
    sem = _make_user(
        email='015-sem@test.greenn.com.br',
        lider=lider,
        area=area,
        cargo_colab=cargo_colab,
        data_entrada=None,
    )
    assert user_eligible_for_ciclo(ok, ciclo) is True
    assert user_eligible_for_ciclo(late, ciclo) is False
    assert user_eligible_for_ciclo(sem, ciclo) is False

    ciclo_sem_corte = SimpleNamespace(admitidos_ate=None)
    assert user_eligible_for_ciclo(ok, ciclo_sem_corte) is False
