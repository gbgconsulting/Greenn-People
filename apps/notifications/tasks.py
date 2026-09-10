"""Celery tasks for deadline reminder e-mails (RF-31 / RF-32)."""

from __future__ import annotations

from datetime import date, timedelta

from celery import shared_task
from django.conf import settings
from django.utils import timezone

from apps.accounts.models import CustomUser
from apps.cycles.models import Ciclo
from apps.notifications.emails import (
    referencia_alerta_ciclo_ainda_aberto,
    referencia_atraso_pdi,
    referencia_digest_pdi_atrasos,
    referencia_feedback_continuo,
    referencia_lembrete_etapa,
    referencia_lembrete_pdi,
    send_alerta_ciclo_ainda_aberto_email,
    send_atraso_pdi_email,
    send_digest_pdi_atrasos_email,
    send_feedback_continuo_email,
    send_lembrete_etapa_email,
    send_lembrete_pdi_email,
)
from apps.notifications.models import NotificacaoLog, already_sent
from apps.pdi.models import AcaoPDI, PDI
from apps.pdi.services.overdue_metrics import aggregate_org_overdue_metrics
from apps.reviews.models import Avaliacao, FeedbackContinuo


def _reminder_days() -> int:
    return int(getattr(settings, 'NOTIFICATION_REMINDER_DAYS', 3))


def _target_date() -> date:
    return timezone.localdate() + timedelta(days=_reminder_days())


def _janela(target: date) -> str:
    return target.isoformat()


def _janela_semana_iso(today: date | None = None) -> str:
    """ISO week key ``YYYY-Www`` for digest dedupe (contract US4)."""
    if today is None:
        today = timezone.localdate()
    iso = today.isocalendar()
    return f'{iso.year}-W{iso.week:02d}'


def _is_etapa_eligible(avaliacao: Avaliacao, target: date) -> bool:
    """Re-check eligibility before send (pending may have been resolved)."""
    return (
        not avaliacao.concluida
        and avaliacao.usuario_id is not None
        and avaliacao.usuario.is_active
        and avaliacao.ciclo.status == Ciclo.Status.ABERTO
        and avaliacao.ciclo.data_fim == target
    )


def _is_pdi_eligible(acao: AcaoPDI, target: date) -> bool:
    """Re-check eligibility before send (pending may have been resolved)."""
    return (
        acao.status != AcaoPDI.Status.CONCLUIDA
        and acao.prazo == target
        and acao.pdi.usuario_id is not None
        and acao.pdi.usuario.is_active
        and acao.pdi.status != PDI.Status.ARQUIVADO
    )


def _is_atraso_pdi_eligible(acao: AcaoPDI) -> bool:
    """True if overdue alert may still be sent for this action."""
    return (
        acao.status == AcaoPDI.Status.ATRASADA
        and acao.pdi.usuario_id is not None
        and acao.pdi.status != PDI.Status.ARQUIVADO
    )


def _destinatarios_atraso_pdi(dono: CustomUser) -> list[CustomUser]:
    """Owner plus active distinct line manager (contract US2)."""
    destinatarios: list[CustomUser] = []
    if dono.is_active:
        destinatarios.append(dono)
    gestor = getattr(dono, 'line_manager', None)
    if (
        gestor is not None
        and gestor.is_active
        and gestor.pk != dono.pk
    ):
        destinatarios.append(gestor)
    return destinatarios


def _log_send(
    *,
    destinatario_id: int,
    tipo: str,
    referencia: str,
    janela: str,
    send_fn,
) -> str:
    """Execute ``send_fn`` and persist ``NotificacaoLog`` for success or failure."""
    try:
        send_fn()
    except Exception as exc:  # noqa: BLE001 — log any delivery failure
        NotificacaoLog.objects.create(
            destinatario_id=destinatario_id,
            tipo=tipo,
            referencia=referencia,
            janela=janela,
            status=NotificacaoLog.Status.FALHA,
            erro=str(exc)[:4000],
        )
        return 'falha'
    NotificacaoLog.objects.create(
        destinatario_id=destinatario_id,
        tipo=tipo,
        referencia=referencia,
        janela=janela,
        status=NotificacaoLog.Status.ENVIADO,
    )
    return 'enviado'


@shared_task(name='apps.notifications.tasks.enviar_lembrete_prazo_etapa')
def enviar_lembrete_prazo_etapa() -> dict:
    """Remind collaborators whose open-cycle evaluations end in N days.

    Uses ``Ciclo.data_fim`` as the stage-window deadline (RF-31). Skips
    evaluations already marked ``concluida``, ineligible pendings, and
    keys already logged as ``enviado`` for the same janela.
    """
    target = _target_date()
    janela = _janela(target)
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
    pulados = 0
    for avaliacao in queryset.iterator():
        referencia = referencia_lembrete_etapa(avaliacao)
        if already_sent(
            avaliacao.usuario_id,
            NotificacaoLog.Tipo.LEMBRETE_ETAPA,
            referencia,
            janela,
        ):
            pulados += 1
            continue
        # Fresh fetch avoids stale eligibility between query and send.
        avaliacao.refresh_from_db()
        avaliacao.usuario.refresh_from_db()
        avaliacao.ciclo.refresh_from_db()
        if not _is_etapa_eligible(avaliacao, target):
            pulados += 1
            continue
        result = _log_send(
            destinatario_id=avaliacao.usuario_id,
            tipo=NotificacaoLog.Tipo.LEMBRETE_ETAPA,
            referencia=referencia,
            janela=janela,
            send_fn=lambda a=avaliacao: send_lembrete_etapa_email(a),
        )
        if result == 'enviado':
            enviados += 1
        else:
            falhas += 1
    return {
        'enviados': enviados,
        'falhas': falhas,
        'pulados': pulados,
        'data_alvo': str(target),
    }


@shared_task(name='apps.notifications.tasks.enviar_lembrete_acao_pdi_vencendo')
def enviar_lembrete_acao_pdi_vencendo() -> dict:
    """Remind PDI owners about actions due in N days (US-08 / RF-31)."""
    target = _target_date()
    janela = _janela(target)
    queryset = (
        AcaoPDI.objects.filter(prazo=target)
        .exclude(status=AcaoPDI.Status.CONCLUIDA)
        .exclude(pdi__status=PDI.Status.ARQUIVADO)
        .filter(pdi__usuario__is_active=True)
        .select_related('pdi', 'pdi__usuario')
        .order_by('pk')
    )

    enviados = 0
    falhas = 0
    pulados = 0
    for acao in queryset.iterator():
        referencia = referencia_lembrete_pdi(acao)
        if already_sent(
            acao.pdi.usuario_id,
            NotificacaoLog.Tipo.LEMBRETE_PDI,
            referencia,
            janela,
        ):
            pulados += 1
            continue
        acao.refresh_from_db()
        acao.pdi.refresh_from_db()
        acao.pdi.usuario.refresh_from_db()
        if not _is_pdi_eligible(acao, target):
            pulados += 1
            continue
        result = _log_send(
            destinatario_id=acao.pdi.usuario_id,
            tipo=NotificacaoLog.Tipo.LEMBRETE_PDI,
            referencia=referencia,
            janela=janela,
            send_fn=lambda a=acao: send_lembrete_pdi_email(a),
        )
        if result == 'enviado':
            enviados += 1
        else:
            falhas += 1
    return {
        'enviados': enviados,
        'falhas': falhas,
        'pulados': pulados,
        'data_alvo': str(target),
    }


@shared_task(name='apps.notifications.tasks.enviar_alerta_acao_pdi_atrasada')
def enviar_alerta_acao_pdi_atrasada(acao_id: int) -> dict:
    """Alert PDI owner (+ line manager) when an action is overdue.

    Destinatários = dono ∪ ``line_manager(dono)`` se ativo e ≠ dono.
    Skips concluída / PDI arquivado / destinatário inativo. Dedupe diário via
    ``already_sent(tipo=atraso_pdi, referencia=acao_pdi:{id}, janela=ISO)``.
    Append-only ``NotificacaoLog`` through ``_log_send``. Does not touch
    ``lembrete_pdi``.
    """
    try:
        acao = AcaoPDI.objects.select_related(
            'pdi',
            'pdi__usuario',
            'pdi__usuario__line_manager',
        ).get(pk=acao_id)
    except AcaoPDI.DoesNotExist:
        return {
            'enviados': 0,
            'falhas': 0,
            'pulados': 0,
            'acao_id': acao_id,
            'resultado': 'ausente',
        }

    # Fresh fetch avoids stale eligibility between enqueue and send.
    acao.refresh_from_db()
    acao.pdi.refresh_from_db()
    acao.pdi.usuario.refresh_from_db()
    if acao.pdi.usuario.line_manager_id:
        acao.pdi.usuario.line_manager.refresh_from_db()

    if not _is_atraso_pdi_eligible(acao):
        return {
            'enviados': 0,
            'falhas': 0,
            'pulados': 0,
            'acao_id': acao_id,
            'resultado': 'ineligivel',
        }

    janela = timezone.localdate().isoformat()
    referencia = referencia_atraso_pdi(acao)
    tipo = NotificacaoLog.Tipo.ATRASO_PDI
    destinatarios = _destinatarios_atraso_pdi(acao.pdi.usuario)

    enviados = 0
    falhas = 0
    pulados = 0
    for destinatario in destinatarios:
        if already_sent(destinatario.pk, tipo, referencia, janela):
            pulados += 1
            continue
        if not destinatario.is_active:
            pulados += 1
            continue
        result = _log_send(
            destinatario_id=destinatario.pk,
            tipo=tipo,
            referencia=referencia,
            janela=janela,
            send_fn=lambda a=acao, d=destinatario: send_atraso_pdi_email(a, d),
        )
        if result == 'enviado':
            enviados += 1
        else:
            falhas += 1

    return {
        'enviados': enviados,
        'falhas': falhas,
        'pulados': pulados,
        'acao_id': acao_id,
        'janela': janela,
        'resultado': 'ok',
    }


@shared_task(name='apps.notifications.tasks.enviar_digest_pdi_atrasos')
def enviar_digest_pdi_atrasos() -> dict:
    """Weekly org digest of overdue PDIs for active admins (US4).

    Silent exit when org overdue count is zero. Otherwise loops active
    ``is_admin`` users with weekly dedupe
    ``already_sent(tipo=digest_pdi_atrasos, referencia=org:pdi_atrasos,
    janela=YYYY-Www)``. Append-only ``NotificacaoLog`` via ``_log_send``.
    """
    aggregation = aggregate_org_overdue_metrics()
    if not aggregation.has_atrasos:
        return {
            'enviados': 0,
            'falhas': 0,
            'pulados': 0,
            'resultado': 'silencio',
            'pdis_com_atraso': 0,
            'acoes_atrasadas': 0,
        }

    janela = _janela_semana_iso()
    referencia = referencia_digest_pdi_atrasos()
    tipo = NotificacaoLog.Tipo.DIGEST_PDI_ATRASOS
    destinatarios = (
        CustomUser.objects.filter(is_admin=True, is_active=True)
        .order_by('pk')
    )

    enviados = 0
    falhas = 0
    pulados = 0
    for destinatario in destinatarios.iterator():
        if already_sent(destinatario.pk, tipo, referencia, janela):
            pulados += 1
            continue
        result = _log_send(
            destinatario_id=destinatario.pk,
            tipo=tipo,
            referencia=referencia,
            janela=janela,
            send_fn=lambda d=destinatario, a=aggregation: (
                send_digest_pdi_atrasos_email(d, a)
            ),
        )
        if result == 'enviado':
            enviados += 1
        else:
            falhas += 1

    return {
        'enviados': enviados,
        'falhas': falhas,
        'pulados': pulados,
        'resultado': 'ok',
        'janela': janela,
        'pdis_com_atraso': aggregation.pdis_com_atraso,
        'acoes_atrasadas': aggregation.acoes_atrasadas,
    }


@shared_task(name='apps.notifications.tasks.enviar_alerta_ciclo_ainda_aberto')
def enviar_alerta_ciclo_ainda_aberto(usuario_id: int) -> dict:
    """Alert active admins that a collaborator still has an open cycle (US3).

    Destinatários = ``is_admin`` ativos. Dedupe diário via
    ``already_sent(tipo=alerta_ciclo_ainda_aberto, referencia=usuario:{id},
    janela=ISO)``. Append-only ``NotificacaoLog`` through ``_log_send``.
    Não matricula e não aborta o lote automático — só notifica RH.
    """
    try:
        usuario_alertado = CustomUser.objects.get(pk=usuario_id)
    except CustomUser.DoesNotExist:
        return {
            'enviados': 0,
            'falhas': 0,
            'pulados': 0,
            'usuario_id': usuario_id,
            'resultado': 'ausente',
        }

    ciclos_abertos = list(
        Ciclo.objects.filter(
            status=Ciclo.Status.ABERTO,
            avaliacoes__usuario_id=usuario_alertado.pk,
        )
        .distinct()
        .order_by('-data_inicio', '-pk'),
    )

    janela = timezone.localdate().isoformat()
    referencia = referencia_alerta_ciclo_ainda_aberto(usuario_alertado)
    tipo = NotificacaoLog.Tipo.ALERTA_CICLO_AINDA_ABERTO
    destinatarios = (
        CustomUser.objects.filter(is_admin=True, is_active=True)
        .order_by('pk')
    )

    enviados = 0
    falhas = 0
    pulados = 0
    for destinatario in destinatarios.iterator():
        if already_sent(destinatario.pk, tipo, referencia, janela):
            pulados += 1
            continue
        if not destinatario.email:
            pulados += 1
            continue
        result = _log_send(
            destinatario_id=destinatario.pk,
            tipo=tipo,
            referencia=referencia,
            janela=janela,
            send_fn=lambda d=destinatario: send_alerta_ciclo_ainda_aberto_email(
                d,
                usuario_alertado=usuario_alertado,
                ciclos_abertos=ciclos_abertos,
            ),
        )
        if result == 'enviado':
            enviados += 1
        else:
            falhas += 1

    return {
        'enviados': enviados,
        'falhas': falhas,
        'pulados': pulados,
        'usuario_id': usuario_id,
        'janela': janela,
        'resultado': 'ok',
    }


@shared_task(name='apps.notifications.tasks.enviar_notificacao_feedback_continuo')
def enviar_notificacao_feedback_continuo(feedback_id: int) -> str:
    """E-mail ao destinatário de um feedback contínuo (evento único, dedupe por id)."""
    try:
        feedback = FeedbackContinuo.objects.select_related(
            'destinatario',
            'autor',
        ).get(pk=feedback_id)
    except FeedbackContinuo.DoesNotExist:
        return 'ausente'

    if not feedback.destinatario_id or not feedback.destinatario.is_active:
        return 'ineligivel'

    referencia = referencia_feedback_continuo(feedback)
    janela = ''
    if already_sent(
        feedback.destinatario_id,
        NotificacaoLog.Tipo.FEEDBACK_CONTINUO,
        referencia,
        janela,
    ):
        return 'duplicado'

    return _log_send(
        destinatario_id=feedback.destinatario_id,
        tipo=NotificacaoLog.Tipo.FEEDBACK_CONTINUO,
        referencia=referencia,
        janela=janela,
        send_fn=lambda: send_feedback_continuo_email(feedback),
    )
