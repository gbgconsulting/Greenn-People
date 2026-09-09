"""Celery tasks for PDI (deadlines / overdue status)."""

from __future__ import annotations

from celery import shared_task
from django.db import transaction
from django.utils import timezone

from apps.pdi.models import AcaoPDI, PDI


@shared_task(name='apps.pdi.tasks.mark_overdue_pdi_actions')
def mark_overdue_pdi_actions() -> int:
    """Mark non-completed PDI actions as ``atrasada`` when ``prazo < today``.

    Skips ``concluida`` and already-``atrasada`` rows. Uses per-row ``save`` so
    ``updated_at`` and audit signals stay consistent with HTMX status updates.
    Planos arquivados ficam fora do recálculo de atraso.

    Após cada marcação, enfileira ``enviar_alerta_acao_pdi_atrasada`` (dono +
    gestor). Não altera ``enviar_lembrete_acao_pdi_vencendo`` / ``lembrete_pdi``.
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
        .exclude(pdi__status=PDI.Status.ARQUIVADO)
        .order_by('pk')
    )

    updated = 0
    for acao in queryset.iterator():
        acao.status = AcaoPDI.Status.ATRASADA
        acao.save(update_fields=['status', 'updated_at'])
        acao_id = acao.pk

        def _enqueue_alerta(aid: int = acao_id) -> None:
            from apps.notifications.tasks import enviar_alerta_acao_pdi_atrasada

            enviar_alerta_acao_pdi_atrasada.delay(aid)

        transaction.on_commit(_enqueue_alerta)
        updated += 1
    return updated
