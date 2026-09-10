"""T015 [US1]: lote no 1º dia útil, idempotência e noop de dia não-útil.

Quickstart V1/V2; contratos auto-cohort-open + SC-001 / SC-005.
"""

from __future__ import annotations

from datetime import date, timedelta

import pytest
from django.utils import timezone

from apps.accounts.models import CustomUser
from apps.audit.models import AuditLog
from apps.core.calendar_br import first_business_day_of_month
from apps.cycles.models import AutoCycleEvent, AutoCycleRun, Ciclo
from apps.cycles.tasks import run_auto_cycle_admission_daily
from apps.reviews.models import Avaliacao

DEFAULT_PASSWORD = 'TestPass123!'

# jul/2026: 01/07 = quarta → 1º dia útil
REF_FIRST = date(2026, 7, 1)
REF_NOT_FIRST = date(2026, 7, 15)
MARCO_JUL = date(2026, 7, 1)


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


def _seed_v1(lider, area, cargo_colab) -> dict:
    """10 marco julho + 2 sem data + 2 marco agosto (+ inativo julho)."""
    # Isola fixtures admin/lider (jan/2020 = candidatos jul) do lote.
    CustomUser.objects.filter(pk=lider.pk).update(data_entrada=date(2026, 2, 1))
    lider.refresh_from_db()
    if lider.line_manager_id:
        CustomUser.objects.filter(pk=lider.line_manager_id).update(
            data_entrada=date(2026, 2, 1),
        )

    elegiveis = [
        _make_user(
            email=f'jul-{i:02d}@test.greenn.com.br',
            lider=lider,
            area=area,
            cargo_colab=cargo_colab,
            data_entrada=date(2026, 1, 10 + (i % 15)),
        )
        for i in range(10)
    ]
    sem_data = [
        _make_user(
            email=f'sem-{i}@test.greenn.com.br',
            lider=lider,
            area=area,
            cargo_colab=cargo_colab,
            data_entrada=None,
        )
        for i in range(2)
    ]
    agosto = [
        _make_user(
            email=f'ago-{i}@test.greenn.com.br',
            lider=lider,
            area=area,
            cargo_colab=cargo_colab,
            data_entrada=date(2026, 2, 10 + i),
        )
        for i in range(2)
    ]
    inativo = _make_user(
        email='inativo-jul@test.greenn.com.br',
        lider=lider,
        area=area,
        cargo_colab=cargo_colab,
        data_entrada=date(2026, 1, 20),
        is_active=False,
    )
    return {
        'elegiveis': elegiveis,
        'sem_data': sem_data,
        'agosto': agosto,
        'inativo': inativo,
    }


@pytest.mark.django_db
def test_first_business_day_july_2026_is_day_one():
    assert first_business_day_of_month(2026, 7) == REF_FIRST


@pytest.mark.django_db
def test_lote_abre_coorte_e_matricula_elegiveis(lider, area, cargo_colab):
    """V1 / SC-001: 1 ciclo automático + exatamente 10 Avaliações."""
    seed = _seed_v1(lider, area, cargo_colab)

    result = run_auto_cycle_admission_daily(data_referencia=REF_FIRST)

    assert result['status'] == AutoCycleRun.Status.SUCESSO
    assert result['era_primeiro_dia_util'] is True
    assert result['matriculados'] == 10

    ciclos = Ciclo.objects.filter(
        origem=Ciclo.Origem.AUTOMATICO,
        marco_competencia=MARCO_JUL,
    )
    assert ciclos.count() == 1
    ciclo = ciclos.get()
    assert ciclo.status == Ciclo.Status.ABERTO
    assert ciclo.data_inicio == REF_FIRST
    assert ciclo.data_fim == REF_FIRST + timedelta(days=20)
    assert 'Jul/2026' in ciclo.nome

    assert Avaliacao.objects.filter(ciclo=ciclo).count() == 10
    for user in seed['elegiveis']:
        assert Avaliacao.objects.filter(ciclo=ciclo, usuario=user).exists()
    for user in seed['sem_data'] + seed['agosto'] + [seed['inativo']]:
        assert not Avaliacao.objects.filter(ciclo=ciclo, usuario=user).exists()

    run = AutoCycleRun.objects.get(pk=result['run_id'])
    assert run.excluidos_sem_admissao == 2
    assert run.events.filter(
        tipo=AutoCycleEvent.Tipo.PENDENCIA_SEM_ADMISSAO,
    ).count() == 2
    assert run.events.filter(tipo=AutoCycleEvent.Tipo.COORTE_CRIADA).exists()
    assert run.events.filter(tipo=AutoCycleEvent.Tipo.MATRICULA).count() == 10

    # FR-016 / T026: AuditLog CREATE na coorte + events com quem/quando/por quê.
    create_logs = AuditLog.objects.filter(
        acao=AuditLog.Acao.CREATE,
        entity_type='cycles.Ciclo',
        entity_id=ciclo.pk,
    )
    assert create_logs.count() >= 1
    campos = set(create_logs.values_list('campo', flat=True))
    assert {'origem', 'marco_competencia', 'data_inicio', 'data_fim', 'status'} <= campos
    assert create_logs.filter(campo='origem', valor_novo=Ciclo.Origem.AUTOMATICO).exists()

    coorte_ev = run.events.get(tipo=AutoCycleEvent.Tipo.COORTE_CRIADA)
    assert coorte_ev.payload.get('motivo') == 'abertura_automatica_marco'
    assert coorte_ev.payload.get('ator') == 'sistema_beat'
    assert coorte_ev.payload.get('run_id') == run.pk
    assert coorte_ev.criado_em is not None

    pend = run.events.filter(tipo=AutoCycleEvent.Tipo.PENDENCIA_SEM_ADMISSAO).first()
    assert pend is not None
    assert pend.usuario_id is not None
    assert pend.payload.get('motivo') == 'data_entrada_ausente'

    mat = run.events.filter(tipo=AutoCycleEvent.Tipo.MATRICULA).first()
    assert mat is not None
    assert mat.usuario_id is not None
    assert mat.payload.get('motivo') == 'elegivel_marco_admissao'


@pytest.mark.django_db
def test_idempotencia_reexecucao_mesmo_dia(lider, area, cargo_colab):
    """V2 / SC-005: reexecução → 0 ciclos/Avaliações duplicados."""
    seed = _seed_v1(lider, area, cargo_colab)

    first = run_auto_cycle_admission_daily(data_referencia=REF_FIRST)
    second = run_auto_cycle_admission_daily(data_referencia=REF_FIRST)

    assert first['status'] == AutoCycleRun.Status.SUCESSO
    assert second['status'] == AutoCycleRun.Status.SUCESSO
    assert second['matriculados'] == 0  # já existiam; sem create novo

    assert (
        Ciclo.objects.filter(
            origem=Ciclo.Origem.AUTOMATICO,
            marco_competencia=MARCO_JUL,
        ).count()
        == 1
    )
    ciclo = Ciclo.objects.get(
        origem=Ciclo.Origem.AUTOMATICO,
        marco_competencia=MARCO_JUL,
    )
    assert Avaliacao.objects.filter(ciclo=ciclo).count() == 10

    run2 = AutoCycleRun.objects.get(pk=second['run_id'])
    assert run2.events.filter(tipo=AutoCycleEvent.Tipo.COORTE_REUSADA).exists()
    assert not run2.events.filter(tipo=AutoCycleEvent.Tipo.COORTE_CRIADA).exists()
    assert run2.events.filter(tipo=AutoCycleEvent.Tipo.MATRICULA).count() == 0

    # Idempotência: CREATE AuditLog só na primeira materialização (6 campos).
    assert (
        AuditLog.objects.filter(
            acao=AuditLog.Acao.CREATE,
            entity_type='cycles.Ciclo',
            entity_id=ciclo.pk,
        ).count()
        == 6
    )

    reused = run2.events.get(tipo=AutoCycleEvent.Tipo.COORTE_REUSADA)
    assert reused.payload.get('motivo') == 'idempotencia_mesmo_marco'

    for user in seed['elegiveis']:
        assert Avaliacao.objects.filter(ciclo=ciclo, usuario=user).count() == 1


@pytest.mark.django_db
def test_noop_em_dia_nao_util(lider, area, cargo_colab):
    """Dia ≠ 1º útil → noop + event noop_dia; zero coorte/matrícula."""
    _seed_v1(lider, area, cargo_colab)

    result = run_auto_cycle_admission_daily(data_referencia=REF_NOT_FIRST)

    assert result['status'] == AutoCycleRun.Status.NOOP
    assert result['era_primeiro_dia_util'] is False
    assert result['matriculados'] == 0
    assert result['ciclo_id'] is None

    run = AutoCycleRun.objects.get(pk=result['run_id'])
    assert run.events.filter(tipo=AutoCycleEvent.Tipo.NOOP_DIA).count() == 1
    assert not Ciclo.objects.filter(origem=Ciclo.Origem.AUTOMATICO).exists()
    assert Avaliacao.objects.count() == 0


@pytest.mark.django_db
def test_noop_nao_atrasa_coorte_ja_aberta(lider, area, cargo_colab):
    """Após lote no 1º útil, dia seguinte em noop não cria segundo ciclo."""
    _seed_v1(lider, area, cargo_colab)
    run_auto_cycle_admission_daily(data_referencia=REF_FIRST)

    result = run_auto_cycle_admission_daily(data_referencia=REF_NOT_FIRST)
    assert result['status'] == AutoCycleRun.Status.NOOP
    assert (
        Ciclo.objects.filter(
            origem=Ciclo.Origem.AUTOMATICO,
            marco_competencia=MARCO_JUL,
        ).count()
        == 1
    )
