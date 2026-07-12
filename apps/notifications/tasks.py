"""Celery tasks for deadline reminder e-mails (RF-31 / RF-32)."""

from __future__ import annotations

from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.utils import timezone

from apps.cycles.models import Ciclo
from apps.notifications.emails import (
    send_lembrete_etapa_email,
    send_lembrete_pdi_email,
)
from apps.notifications.models import NotificacaoLog
from apps.pdi.models import AcaoPDI
from apps.reviews.models import Avaliacao


def _reminder_days() -> int:
    return int(getattr(settings, 'NOTIFICATION_REMINDER_DAYS', 3))


def _target_date():
    return timezone.localdate() + timedelta(days=_reminder_days())


def _log_send(
    *,
    destinatario_id: int,
    tipo: str,
    send_fn,
) -> str:
    """Execute ``send_fn`` and persist ``NotificacaoLog`` for success or failure."""
    try:
        send_fn()
    except Exception as exc:  # noqa: BLE001 — log any delivery failure
        NotificacaoLog.objects.create(
            destinatario_id=destinatario_id,
            tipo=tipo,
            status=NotificacaoLog.Status.FALHA,
            erro=str(exc)[:4000],
        )
        return 'falha'
    NotificacaoLog.objects.create(
        destinatario_id=destinatario_id,
        tipo=tipo,
        status=NotificacaoLog.Status.ENVIADO,
    )
    return 'enviado'


@shared_task(name='apps.notifications.tasks.enviar_lembrete_prazo_etapa')
def enviar_lembrete_prazo_etapa() -> dict:
    """Remind collaborators whose open-cycle evaluations end in N days.

    Uses ``Ciclo.data_fim`` as the stage-window deadline (RF-31). Skips
    evaluations already marked ``concluida``.
    """
    target = _target_date()
    queryset = (
        Avaliacao.objects.filter(
            concluida=False,
            ciclo__status=Ciclo.Status.ABERTO,
            ciclo__data_fim=target,
            usuario__is_active=True,
        )
        .select_related('usuario', 'ciclo')
        .order_by('pk')
    )

    enviados = 0
    falhas = 0
    for avaliacao in queryset.iterator():
        result = _log_send(
            destinatario_id=avaliacao.usuario_id,
            tipo=NotificacaoLog.Tipo.LEMBRETE_ETAPA,
            send_fn=lambda a=avaliacao: send_lembrete_etapa_email(a),
        )
        if result == 'enviado':
            enviados += 1
        else:
            falhas += 1
    return {'enviados': enviados, 'falhas': falhas, 'data_alvo': str(target)}


@shared_task(name='apps.notifications.tasks.enviar_lembrete_acao_pdi_vencendo')
def enviar_lembrete_acao_pdi_vencendo() -> dict:
    """Remind PDI owners about actions due in N days (US-08 / RF-31)."""
    target = _target_date()
    queryset = (
        AcaoPDI.objects.filter(prazo=target)
        .exclude(status=AcaoPDI.Status.CONCLUIDA)
        .filter(pdi__usuario__is_active=True)
        .select_related('pdi', 'pdi__usuario')
        .order_by('pk')
    )

    enviados = 0
    falhas = 0
    for acao in queryset.iterator():
        result = _log_send(
            destinatario_id=acao.pdi.usuario_id,
            tipo=NotificacaoLog.Tipo.LEMBRETE_PDI,
            send_fn=lambda a=acao: send_lembrete_pdi_email(a),
        )
        if result == 'enviado':
            enviados += 1
        else:
            falhas += 1
    return {'enviados': enviados, 'falhas': falhas, 'data_alvo': str(target)}
