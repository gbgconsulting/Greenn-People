"""Render and send notification e-mails (subject/body templates)."""

from __future__ import annotations

from django.core.mail import send_mail
from django.template.loader import render_to_string

from apps.cycles.models import Ciclo
from apps.pdi.models import AcaoPDI
from apps.reviews.models import Avaliacao


def referencia_lembrete_etapa(avaliacao: Avaliacao) -> str:
    """Stable pending key for stage-deadline reminders."""
    return f'avaliacao:{avaliacao.pk}'


def referencia_lembrete_pdi(acao: AcaoPDI) -> str:
    """Stable pending key for PDI action deadline reminders."""
    return f'acao_pdi:{acao.pk}'


def send_lembrete_etapa_email(avaliacao: Avaliacao) -> None:
    """Send cycle-stage deadline reminder to the evaluation owner."""
    user = avaliacao.usuario
    ciclo: Ciclo = avaliacao.ciclo
    context = {
        'user': user,
        'avaliacao': avaliacao,
        'ciclo': ciclo,
        'etapa_label': avaliacao.get_etapa_display(),
        'data_fim': ciclo.data_fim,
    }
    subject = render_to_string(
        'notifications/email/lembrete_etapa_subject.txt',
        context,
    ).strip()
    body = render_to_string(
        'notifications/email/lembrete_etapa_body.txt',
        context,
    )
    send_mail(
        subject,
        body,
        None,
        [user.email],
        fail_silently=False,
    )


def send_lembrete_pdi_email(acao: AcaoPDI) -> None:
    """Send PDI action deadline reminder to the PDI owner (US-08)."""
    user = acao.pdi.usuario
    context = {
        'user': user,
        'acao': acao,
        'pdi': acao.pdi,
        'prazo': acao.prazo,
    }
    subject = render_to_string(
        'notifications/email/lembrete_pdi_subject.txt',
        context,
    ).strip()
    body = render_to_string(
        'notifications/email/lembrete_pdi_body.txt',
        context,
    )
    send_mail(
        subject,
        body,
        None,
        [user.email],
        fail_silently=False,
    )
