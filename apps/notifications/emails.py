"""Render and send notification e-mails (subject/body templates)."""

from __future__ import annotations

from django.urls import reverse

from apps.core.emails import absolute_url, send_templated_email
from apps.cycles.models import Ciclo
from apps.pdi.models import AcaoPDI
from apps.reviews.models import Avaliacao, FeedbackContinuo


def referencia_lembrete_etapa(avaliacao: Avaliacao) -> str:
    """Stable pending key for stage-deadline reminders."""
    return f'avaliacao:{avaliacao.pk}'


def referencia_lembrete_pdi(acao: AcaoPDI) -> str:
    """Stable pending key for PDI action deadline reminders."""
    return f'acao_pdi:{acao.pk}'


def referencia_feedback_continuo(feedback: FeedbackContinuo) -> str:
    """Stable key for continuous-feedback notification."""
    return f'feedback_continuo:{feedback.pk}'


def send_lembrete_etapa_email(avaliacao: Avaliacao) -> None:
    """Send cycle-stage deadline reminder to the evaluation owner."""
    user = avaliacao.usuario
    ciclo: Ciclo = avaliacao.ciclo
    cta_url = absolute_url(
        reverse('reviews:detail', kwargs={'pk': avaliacao.pk}),
    )
    context = {
        'user': user,
        'avaliacao': avaliacao,
        'ciclo': ciclo,
        'etapa_label': avaliacao.get_etapa_display(),
        'data_fim': ciclo.data_fim,
        'cta_url': cta_url,
        'cta_label': 'Abrir minha avaliação',
    }
    subject = _subject('notifications/email/lembrete_etapa_subject.txt', context)
    send_templated_email(
        subject=subject,
        to=user.email,
        text_template='notifications/email/lembrete_etapa_body.txt',
        html_template='notifications/email/lembrete_etapa_body.html',
        context=context,
    )


def send_lembrete_pdi_email(acao: AcaoPDI) -> None:
    """Send PDI action deadline reminder to the PDI owner (US-08)."""
    user = acao.pdi.usuario
    cta_url = absolute_url(reverse('pdi:detail', kwargs={'pk': acao.pdi_id}))
    context = {
        'user': user,
        'acao': acao,
        'pdi': acao.pdi,
        'prazo': acao.prazo,
        'cta_url': cta_url,
        'cta_label': 'Abrir meu PDI',
    }
    subject = _subject('notifications/email/lembrete_pdi_subject.txt', context)
    send_templated_email(
        subject=subject,
        to=user.email,
        text_template='notifications/email/lembrete_pdi_body.txt',
        html_template='notifications/email/lembrete_pdi_body.html',
        context=context,
    )


def send_feedback_continuo_email(feedback: FeedbackContinuo) -> None:
    """Notify the recipient that a continuous feedback was registered."""
    user = feedback.destinatario
    cta_url = absolute_url(reverse('reviews:continuous_feedback_mine'))
    context = {
        'user': user,
        'feedback': feedback,
        'autor': feedback.autor,
        'cta_url': cta_url,
        'cta_label': 'Ler feedback e dar ciência',
    }
    subject = _subject(
        'notifications/email/feedback_continuo_subject.txt',
        context,
    )
    send_templated_email(
        subject=subject,
        to=user.email,
        text_template='notifications/email/feedback_continuo_body.txt',
        html_template='notifications/email/feedback_continuo_body.html',
        context=context,
    )


def _subject(template_name: str, context: dict) -> str:
    from django.template.loader import render_to_string

    return render_to_string(template_name, context).strip()
