"""Celery tasks for leadership adherence snapshots (RF-26)."""

from __future__ import annotations

from celery import shared_task
from django.utils import timezone

from apps.accounts.models import CustomUser
from apps.cycles.models import Ciclo
from apps.dashboard.models import AderenciaSnapshot
from apps.dashboard.services.adherence import compute_adherence
from apps.dashboard.services.eligible_leaders import eligible_leader_ids


def _leader_ids_for_ciclo(ciclo: Ciclo) -> set[int]:
    """Gestores ativos com time ativo que recebem snapshot neste ciclo."""
    del ciclo
    return eligible_leader_ids()


@shared_task(name='apps.dashboard.tasks.calculate_adherence_snapshot')
def calculate_adherence_snapshot(lider_id: int, ciclo_id: int) -> str:
    """Compute adherence % for one leader/cycle and upsert ``AderenciaSnapshot``.

    Attribution uses AuditLog / autor / responsavel — never current line_manager.
    """
    if not CustomUser.objects.filter(pk=lider_id).exists():
        return f'skip: lider {lider_id} not found'
    if not Ciclo.objects.filter(pk=ciclo_id).exists():
        return f'skip: ciclo {ciclo_id} not found'

    percentual, componentes = compute_adherence(lider_id, ciclo_id)
    now = timezone.now()
    AderenciaSnapshot.objects.update_or_create(
        lider_id=lider_id,
        ciclo_id=ciclo_id,
        defaults={
            'percentual': percentual,
            'componentes': componentes,
            'calculado_em': now,
        },
    )
    return f'ok: lider={lider_id} ciclo={ciclo_id} percentual={percentual}'


@shared_task(name='apps.dashboard.tasks.calculate_adherence_snapshots_daily')
def calculate_adherence_snapshots_daily() -> int:
    """Fan-out daily Beat job: enqueue snapshot calc for open cycles × leaders."""
    enqueued = 0
    for ciclo in Ciclo.objects.filter(status=Ciclo.Status.ABERTO).iterator():
        for lider_id in _leader_ids_for_ciclo(ciclo):
            calculate_adherence_snapshot.delay(lider_id, ciclo.pk)
            enqueued += 1
    return enqueued
