"""Render and send notification e-mails (subject/body templates)."""

from __future__ import annotations

from urllib.parse import urlencode

from django.urls import reverse

from apps.accounts.models import CustomUser
from apps.core.emails import absolute_url, send_templated_email
from apps.cycles.models import Ciclo
from apps.pdi.models import AcaoPDI
from apps.pdi.services.overdue_metrics import OrgOverdueAggregation
from apps.reviews.models import Avaliacao, FeedbackContinuo

REFERENCIA_DIGEST_PDI_ATRASOS = 'org:pdi_atrasos'


def referencia_lembrete_etapa(avaliacao: Avaliacao) -> str:
    """Stable pending key for stage-deadline reminders."""
    return f'avaliacao:{avaliacao.pk}'


def referencia_lembrete_pdi(acao: AcaoPDI) -> str:
    """Stable pending key for PDI action deadline reminders."""
    return f'acao_pdi:{acao.pk}'


def referencia_atraso_pdi(acao: AcaoPDI) -> str:
    """Stable key for overdue PDI-action alerts (dono + gestor)."""
    return f'acao_pdi:{acao.pk}'


def referencia_digest_pdi_atrasos() -> str:
    """Stable org-level key for weekly overdue digest (US4)."""
    return REFERENCIA_DIGEST_PDI_ATRASOS


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


def send_atraso_pdi_email(acao: AcaoPDI, destinatario: CustomUser) -> None:
    """Send overdue PDI-action alert to one recipient (owner or line manager)."""
    cta_url = absolute_url(reverse('pdi:detail', kwargs={'pk': acao.pdi_id}))
    context = {
        'user': destinatario,
        'acao': acao,
        'pdi': acao.pdi,
        'prazo': acao.prazo,
        'cta_url': cta_url,
        'cta_label': 'Abrir PDI',
    }
    subject = _subject('notifications/email/atraso_pdi_subject.txt', context)
    send_templated_email(
        subject=subject,
        to=destinatario.email,
        text_template='notifications/email/atraso_pdi_body.txt',
        html_template='notifications/email/atraso_pdi_body.html',
        context=context,
    )


def send_digest_pdi_atrasos_email(
    destinatario: CustomUser,
    aggregation: OrgOverdueAggregation,
) -> None:
    """Send weekly org overdue digest to one active admin (US4)."""
    list_path = reverse('pdi:list')
    query = urlencode({'visao': 'equipe', 'atrasadas': '1'})
    cta_url = absolute_url(f'{list_path}?{query}')
    context = {
        'user': destinatario,
        'pdis_com_atraso': aggregation.pdis_com_atraso,
        'acoes_atrasadas': aggregation.acoes_atrasadas,
        'top_areas': aggregation.top_areas,
        'top_gestores': aggregation.top_gestores,
        'cta_url': cta_url,
        'cta_label': 'Ver PDIs com atrasadas',
    }
    subject = _subject(
        'notifications/email/digest_pdi_atrasos_subject.txt',
        context,
    )
    send_templated_email(
        subject=subject,
        to=destinatario.email,
        text_template='notifications/email/digest_pdi_atrasos_body.txt',
        html_template='notifications/email/digest_pdi_atrasos_body.html',
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
