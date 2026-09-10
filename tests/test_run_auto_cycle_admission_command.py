"""T035: management command ops/teste com ``--date`` (não substitui Beat)."""

from __future__ import annotations

from datetime import date
from io import StringIO

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from apps.cycles.models import AutoCycleEvent, AutoCycleRun

# jul/2026: 01/07 = 1º dia útil; 15/07 = noop
REF_NOT_FIRST = date(2026, 7, 15)


@pytest.mark.django_db
def test_run_auto_cycle_admission_command_noop_com_date():
    """``--date`` injeta o clock; dia não-útil → noop (mesmo núcleo da Beat)."""
    out = StringIO()
    call_command(
        'run_auto_cycle_admission',
        '--date',
        REF_NOT_FIRST.isoformat(),
        stdout=out,
    )

    text = out.getvalue()
    assert 'ops/teste' in text.lower() or 'Celery Beat' in text
    assert 'status=noop' in text
    assert REF_NOT_FIRST.isoformat() in text

    run = AutoCycleRun.objects.get()
    assert run.status == AutoCycleRun.Status.NOOP
    assert run.data_referencia == REF_NOT_FIRST
    assert AutoCycleEvent.objects.filter(
        run=run,
        tipo=AutoCycleEvent.Tipo.NOOP_DIA,
    ).exists()


@pytest.mark.django_db
def test_run_auto_cycle_admission_command_date_invalido():
    with pytest.raises(CommandError, match='--date inválido'):
        call_command('run_auto_cycle_admission', '--date', '10/09/2026')
