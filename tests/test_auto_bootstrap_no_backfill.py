"""T017 [US2]: bootstrap zero-backfill — FR-005 / SC-002 / quickstart V3.

Admissão antiga; go-live no meio do mês; legado sem data; pós-correção
sem recuperar marcos passados.
"""

from __future__ import annotations

from datetime import date

import pytest
from django.utils import timezone

from apps.accounts.models import CustomUser
from apps.core.calendar_br import first_business_day_of_month
from apps.cycles.models import AutoCycleEvent, AutoCycleRun, Ciclo
from apps.cycles.services.marco import next_future_marco, user_is_auto_candidate
from apps.cycles.tasks import run_auto_cycle_admission_daily
from apps.reviews.models import Avaliacao

DEFAULT_PASSWORD = 'TestPass123!'

# Legado: admitido jan/2022; ref set/2026 → próximo marco = jan/2027
ADMISSAO_ANTIGA = date(2022, 1, 5)
REF_SET_MID = date(2026, 9, 15)
REF_SET_FIRST = date(2026, 9, 1)  # 1º dia útil de set/2026
REF_JAN2027_FIRST = date(2027, 1, 4)  # 1º dia útil de jan/2027
MARCO_JAN2027 = date(2027, 1, 1)


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


def _isolate_fixtures(lider) -> None:
    """Fixtures admin/líder (jan/2020) não devem poluir o lote do marco."""
    CustomUser.objects.filter(pk=lider.pk).update(data_entrada=date(2026, 2, 1))
    lider.refresh_from_db()
    if lider.line_manager_id:
        CustomUser.objects.filter(pk=lider.line_manager_id).update(
            data_entrada=date(2026, 2, 1),
        )


def test_first_business_days_for_v3_dates():
    assert first_business_day_of_month(2026, 9) == REF_SET_FIRST
    assert first_business_day_of_month(2027, 1) == REF_JAN2027_FIRST


def test_next_future_marco_legado_jan2022_ref_set2026():
    """V3: admitido jan/2022 + ref set/2026 → jan/2027 (zero k passados)."""
    assert next_future_marco(ADMISSAO_ANTIGA, REF_SET_MID) == (2027, 1)
    assert next_future_marco(ADMISSAO_ANTIGA, REF_SET_FIRST) == (2027, 1)


@pytest.mark.django_db
def test_legado_zero_ciclos_atrasados_em_setembro(lider, area, cargo_colab):
    """SC-002: rotina em set/2026 não materializa marcos 2022–2026."""
    _isolate_fixtures(lider)
    legado = _make_user(
        email='legado-jan2022@test.greenn.com.br',
        lider=lider,
        area=area,
        cargo_colab=cargo_colab,
        data_entrada=ADMISSAO_ANTIGA,
    )

    # 1º dia útil de set: abre coorte set se houver candidatos set — legado não é.
    result_first = run_auto_cycle_admission_daily(data_referencia=REF_SET_FIRST)
    assert result_first['status'] == AutoCycleRun.Status.SUCESSO
    assert result_first['matriculados'] == 0
    assert result_first['ciclo_id'] is None

    # Meio do mês: noop; ainda zero materialização atrasada.
    result_mid = run_auto_cycle_admission_daily(data_referencia=REF_SET_MID)
    assert result_mid['status'] == AutoCycleRun.Status.NOOP

    assert not Ciclo.objects.filter(origem=Ciclo.Origem.AUTOMATICO).exists()
    assert Avaliacao.objects.count() == 0
    assert not user_is_auto_candidate(
        legado, year=2026, month=9, ref_date=REF_SET_FIRST,
    )
    assert user_is_auto_candidate(
        legado, year=2027, month=1, ref_date=REF_JAN2027_FIRST,
    )


@pytest.mark.django_db
def test_legado_entra_so_no_primeiro_dia_util_do_proximo_marco(
    lider, area, cargo_colab,
):
    """V3: entra só no 1º dia útil de jan/2027 — 1 ciclo + 1 Avaliação."""
    _isolate_fixtures(lider)
    legado = _make_user(
        email='legado-jan2027@test.greenn.com.br',
        lider=lider,
        area=area,
        cargo_colab=cargo_colab,
        data_entrada=ADMISSAO_ANTIGA,
    )

    # Antes do marco: zero.
    run_auto_cycle_admission_daily(data_referencia=REF_SET_FIRST)
    assert Avaliacao.objects.count() == 0

    result = run_auto_cycle_admission_daily(
        data_referencia=REF_JAN2027_FIRST,
    )
    assert result['status'] == AutoCycleRun.Status.SUCESSO
    assert result['matriculados'] == 1

    ciclos = Ciclo.objects.filter(
        origem=Ciclo.Origem.AUTOMATICO,
        marco_competencia=MARCO_JAN2027,
    )
    assert ciclos.count() == 1
    ciclo = ciclos.get()
    assert Avaliacao.objects.filter(ciclo=ciclo, usuario=legado).count() == 1
    # Nenhum ciclo automático de marcos “atrasados” (2022–2026).
    assert (
        Ciclo.objects.filter(origem=Ciclo.Origem.AUTOMATICO)
        .exclude(marco_competencia=MARCO_JAN2027)
        .count()
        == 0
    )


@pytest.mark.django_db
def test_meio_do_mes_nao_abre_marco_atrasado(lider, area, cargo_colab):
    """Go-live após 1º dia útil: mês corrente não abre “atrasado” (R5)."""
    _isolate_fixtures(lider)
    # Admitido mar/2026 → em set/2026 o próximo marco é set/2026.
    candidata_set = _make_user(
        email='marco-set-atrasado@test.greenn.com.br',
        lider=lider,
        area=area,
        cargo_colab=cargo_colab,
        data_entrada=date(2026, 3, 10),
    )
    assert next_future_marco(
        candidata_set.data_entrada, REF_SET_MID,
    ) == (2026, 9)

    result = run_auto_cycle_admission_daily(data_referencia=REF_SET_MID)
    assert result['status'] == AutoCycleRun.Status.NOOP
    assert result['matriculados'] == 0
    assert result['ciclo_id'] is None

    run = AutoCycleRun.objects.get(pk=result['run_id'])
    assert run.events.filter(tipo=AutoCycleEvent.Tipo.NOOP_DIA).exists()
    assert not Ciclo.objects.filter(origem=Ciclo.Origem.AUTOMATICO).exists()
    assert Avaliacao.objects.count() == 0


@pytest.mark.django_db
def test_legado_sem_data_permanece_fora(lider, area, cargo_colab):
    """Sem data_entrada: fora do automático até cadastrar (FR-003 + bootstrap)."""
    _isolate_fixtures(lider)
    sem_data = _make_user(
        email='legado-sem-data@test.greenn.com.br',
        lider=lider,
        area=area,
        cargo_colab=cargo_colab,
        data_entrada=None,
    )

    for ref in (REF_SET_FIRST, REF_SET_MID, REF_JAN2027_FIRST):
        run_auto_cycle_admission_daily(data_referencia=ref)

    assert not Avaliacao.objects.filter(usuario=sem_data).exists()
    # Em jan/2027: run com pendência, sem ciclo se só há sem-data.
    assert not Ciclo.objects.filter(
        origem=Ciclo.Origem.AUTOMATICO,
        marco_competencia=MARCO_JAN2027,
    ).exists()


@pytest.mark.django_db
def test_pos_correcao_data_entrada_nao_recupera_passado(
    lider, area, cargo_colab,
):
    """Correção de admissão: só próximo marco futuro a partir da correção."""
    _isolate_fixtures(lider)
    user = _make_user(
        email='correcao-entrada@test.greenn.com.br',
        lider=lider,
        area=area,
        cargo_colab=cargo_colab,
        data_entrada=None,
    )

    # Sem data em set: fora.
    run_auto_cycle_admission_daily(data_referencia=REF_SET_FIRST)
    assert Avaliacao.objects.filter(usuario=user).count() == 0

    # Corrige para jan/2022 em set/2026 → próximo = jan/2027; zero backfill.
    user.data_entrada = ADMISSAO_ANTIGA
    user.save(update_fields=['data_entrada'])
    user.refresh_from_db()
    assert next_future_marco(user.data_entrada, REF_SET_MID) == (2027, 1)

    run_auto_cycle_admission_daily(data_referencia=REF_SET_MID)
    assert Avaliacao.objects.filter(usuario=user).count() == 0
    assert not Ciclo.objects.filter(origem=Ciclo.Origem.AUTOMATICO).exists()

    # Só materializa no 1º dia útil do próximo marco futuro.
    result = run_auto_cycle_admission_daily(
        data_referencia=REF_JAN2027_FIRST,
    )
    assert result['status'] == AutoCycleRun.Status.SUCESSO
    assert result['matriculados'] == 1
    assert Avaliacao.objects.filter(usuario=user).count() == 1
    assert (
        Ciclo.objects.filter(origem=Ciclo.Origem.AUTOMATICO).count() == 1
    )
    assert Ciclo.objects.get(
        origem=Ciclo.Origem.AUTOMATICO,
    ).marco_competencia == MARCO_JAN2027
