"""Celery tasks for PDI (deadlines / overdue status)."""

from __future__ import annotations

from celery import shared_task
from django.utils import timezone

from apps.pdi.models import AcaoPDI


@shared_task(name='apps.pdi.tasks.mark_overdue_pdi_actions')
def mark_overdue_pdi_actions() -> int:
    """Mark non-completed PDI actions as ``atrasada`` when ``prazo < today``.

    Skips ``concluida`` and already-``atrasada`` rows. Uses per-row ``save`` so
    ``updated_at`` and audit signals stay consistent with HTMX status updates.
    """
    today = timezone.localdate()
    queryset = (
        AcaoPDI.objects.filter(prazo__lt=today)
        .exclude(
            status__in=[
                AcaoPDI.Status.CONCLUIDA,
                AcaoPDI.Status.ATRASADA,
            ]
        )
        .order_by('pk')
    )

    updated = 0
    for acao in queryset.iterator():
        acao.status = AcaoPDI.Status.ATRASADA
        acao.save(update_fields=['status', 'updated_at'])
        updated += 1
    return updated
