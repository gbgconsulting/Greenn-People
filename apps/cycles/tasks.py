"""Celery tasks for automatic cycle admission (feature 018)."""

from __future__ import annotations

from datetime import date, datetime

from celery import shared_task
from django.utils import timezone

from apps.core.calendar_br import first_business_day_of_month
from apps.cycles.models import AutoCycleEvent, AutoCycleRun
from apps.cycles.services.auto_cohort import open_auto_cohort


def _resolve_data_referencia(
    data_referencia: date | str | None,
) -> date:
    """Clock injetável: ``None`` → hoje local; ISO string ou ``date`` em testes."""
    if data_referencia is None:
        return timezone.localdate()
    if isinstance(data_referencia, datetime):
        return data_referencia.date()
    if isinstance(data_referencia, date):
        return data_referencia
    return date.fromisoformat(data_referencia)


@shared_task(name='apps.cycles.tasks.run_auto_cycle_admission_daily')
def run_auto_cycle_admission_daily(
    data_referencia: date | str | None = None,
) -> dict:
    """Rotina diária de abertura automática por admissão.

    1. Cria ``AutoCycleRun`` com a data de referência.
    2. Se não for o 1º dia útil do mês → ``noop`` + event ``noop_dia``.
    3. Senão orquestra elegíveis + abertura idempotente via ``open_auto_cohort``.

    ``data_referencia`` opcional (``date`` ou ISO ``YYYY-MM-DD``) injeta o clock
    para testes / ops. O Beat chama sem args → ``timezone.localdate()``.
    """
    ref = _resolve_data_referencia(data_referencia)
    run = _execute_auto_cycle_admission(ref)
    return {
        'run_id': run.pk,
        'status': run.status,
        'data_referencia': run.data_referencia.isoformat(),
        'era_primeiro_dia_util': run.era_primeiro_dia_util,
        'matriculados': run.matriculados,
        'ciclo_id': run.ciclo_id,
    }


def _execute_auto_cycle_admission(data_referencia: date) -> AutoCycleRun:
    """Núcleo síncrono da rotina (testável sem broker)."""
    primeiro = first_business_day_of_month(
        data_referencia.year,
        data_referencia.month,
    )
    era_primeiro = data_referencia == primeiro

    run = AutoCycleRun.objects.create(
        executado_em=timezone.now(),
        data_referencia=data_referencia,
        era_primeiro_dia_util=era_primeiro,
        status=AutoCycleRun.Status.NOOP,
    )

    if not era_primeiro:
        run.mensagem = (
            f'{data_referencia.isoformat()} não é o 1º dia útil do mês '
            f'({primeiro.isoformat()}); rotina em noop.'
        )
        run.save(update_fields=['mensagem', 'updated_at'])
        AutoCycleEvent.objects.create(
            run=run,
            tipo=AutoCycleEvent.Tipo.NOOP_DIA,
            payload={
                'data_referencia': data_referencia.isoformat(),
                'primeiro_dia_util': primeiro.isoformat(),
            },
        )
        return run

    open_auto_cohort(run, data_referencia=data_referencia)
    run.refresh_from_db()
    return run
