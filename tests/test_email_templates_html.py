"""E-mails HTML multipart — lembretes e helper core (RF-31 / US-08)."""

from __future__ import annotations

from datetime import timedelta

import pytest
from django.core import mail
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone

from apps.core.emails import absolute_url
from apps.notifications.emails import (
    send_lembrete_etapa_email,
    send_lembrete_pdi_email,
)
from apps.pdi.models import AcaoPDI, PDI


@pytest.fixture
def pdi(colaborador) -> PDI:
    return PDI.objects.create(
        usuario=colaborador,
        titulo='PDI HTML',
    )


@pytest.mark.django_db
@override_settings(
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    PUBLIC_BASE_URL='https://people.example.com',
)
def test_lembrete_pdi_envia_texto_e_html(pdi, colaborador):
    prazo = timezone.localdate() + timedelta(days=3)
    acao = AcaoPDI.objects.create(
        pdi=pdi,
        descricao='Workshop de feedback',
        responsavel=colaborador,
        prazo=prazo,
        status=AcaoPDI.Status.PENDENTE,
    )

    send_lembrete_pdi_email(acao)

    assert len(mail.outbox) == 1
    message = mail.outbox[0]
    assert message.to == [colaborador.email]
    assert 'Workshop de feedback' in message.body
    expected = absolute_url(reverse('pdi:detail', kwargs={'pk': pdi.pk}))
    assert expected in message.body
    assert expected.startswith('https://people.example.com/')

    alternatives = message.alternatives
    assert len(alternatives) == 1
    html, mimetype = alternatives[0]
    assert mimetype == 'text/html'
    assert 'Greenn People' in html
    assert 'Abrir meu PDI' in html
    assert expected in html
    assert 'Workshop de feedback' in html


@pytest.mark.django_db
@override_settings(
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    PUBLIC_BASE_URL='https://people.example.com',
)
def test_lembrete_pdi_html_escapa_conteudo_do_usuario(pdi, colaborador):
    """UI never decides; template autoescape keeps XSS out of HTML part."""
    prazo = timezone.localdate() + timedelta(days=3)
    acao = AcaoPDI.objects.create(
        pdi=pdi,
        descricao='<script>alert(1)</script>',
        responsavel=colaborador,
        prazo=prazo,
        status=AcaoPDI.Status.PENDENTE,
    )

    send_lembrete_pdi_email(acao)

    html = mail.outbox[0].alternatives[0][0]
    assert '<script>alert(1)</script>' not in html
    assert '&lt;script&gt;alert(1)&lt;/script&gt;' in html


@pytest.mark.django_db
@override_settings(
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    PUBLIC_BASE_URL='https://people.example.com',
)
def test_lembrete_etapa_envia_texto_e_html(avaliacao, ciclo_aberto):
    send_lembrete_etapa_email(avaliacao)

    assert len(mail.outbox) == 1
    message = mail.outbox[0]
    expected = absolute_url(
        reverse('reviews:detail', kwargs={'pk': avaliacao.pk}),
    )
    assert expected in message.body
    html = message.alternatives[0][0]
    assert 'Abrir minha avaliação' in html
    assert expected in html
    assert ciclo_aberto.nome in html


def test_absolute_url_usa_public_base_url():
    with override_settings(PUBLIC_BASE_URL='https://app.greenn.com.br/'):
        assert absolute_url('/pdi/1/') == 'https://app.greenn.com.br/pdi/1/'
        assert absolute_url('pdi/1/') == 'https://app.greenn.com.br/pdi/1/'
