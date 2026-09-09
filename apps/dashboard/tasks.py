"""Celery tasks for leadership adherence snapshots (RF-26)."""

from __future__ import annotations

from celery import shared_task
from django.utils import timezone

from apps.accounts.models import CustomUser
from apps.cycles.models import Ciclo
from apps.dashboard.models import AderenciaSnapshot
from apps.dashboard.services.adherence import compute_adherence
from apps.dashboard.services.eligible_leaders import leader_ids_with_team_in_ciclo


def _leader_ids_for_ciclo(ciclo: Ciclo) -> set[int]:
    """Gestores elegíveis com liderados matriculados neste ciclo."""
    return leader_ids_with_team_in_ciclo(ciclo)


@shared_task(name='apps.dashboard.tasks.calculate_adherence_snapshot')
def calculate_adherence_snapshot(lider_id: int, ciclo_id: int) -> str:
    """Compute adherence % for one leader/cycle and upsert ``AderenciaSnapshot``.

    Attribution uses AuditLog / autor / responsavel — never current line_manager.
    Gestores sem time no ciclo têm snapshot removido.
    """
    if not CustomUser.objects.filter(pk=lider_id).exists():
        return f'skip: lider {lider_id} not found'
    ciclo = Ciclo.objects.filter(pk=ciclo_id).first()
    if ciclo is None:
        return f'skip: ciclo {ciclo_id} not found'

    if lider_id not in _leader_ids_for_ciclo(ciclo):
        deleted, _ = AderenciaSnapshot.objects.filter(
            lider_id=lider_id,
            ciclo_id=ciclo_id,
        ).delete()
        if deleted:
            return f'skip: lider {lider_id} sem time no ciclo (snapshot removido)'
        return f'skip: lider {lider_id} sem time no ciclo'

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
    label = 'neutro' if percentual is None else f'percentual={percentual}'
    return f'ok: lider={lider_id} ciclo={ciclo_id} {label}'


@shared_task(name='apps.dashboard.tasks.calculate_adherence_snapshots_daily')
def calculate_adherence_snapshots_daily() -> int:
    """Fan-out daily Beat job: enqueue snapshot calc for open cycles × leaders."""
    enqueued = 0
    for ciclo in Ciclo.objects.filter(status=Ciclo.Status.ABERTO).iterator():
        for lider_id in _leader_ids_for_ciclo(ciclo):
            calculate_adherence_snapshot.delay(lider_id, ciclo.pk)
            enqueued += 1
    return enqueued
