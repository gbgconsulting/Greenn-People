"""Feedback contínuo: AuthZ, isolamento de ciclo e ciência."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from django.urls import reverse

from apps.reviews.models import Feedback, FeedbackContinuo
from apps.reviews.services.continuous_feedback import (
    continuous_feedback_create_allowed,
    continuous_feedback_list_allowed,
)


@pytest.mark.django_db
def test_create_allowed_lider_para_colaborador(lider, colaborador):
    assert continuous_feedback_create_allowed(lider, colaborador) is True


@pytest.mark.django_db
def test_create_denied_self(colaborador):
    assert continuous_feedback_create_allowed(colaborador, colaborador) is False


@pytest.mark.django_db
def test_create_denied_fora_do_escopo(lider, admin):
    # admin é line_manager do lider — lider não vê o admin como destinatário
    assert continuous_feedback_create_allowed(lider, admin) is False


@pytest.mark.django_db
def test_list_allowed_self_and_scope(lider, colaborador, admin):
    assert continuous_feedback_list_allowed(colaborador, colaborador) is True
    assert continuous_feedback_list_allowed(lider, colaborador) is True
    assert continuous_feedback_list_allowed(colaborador, lider) is False


@pytest.mark.django_db
def test_create_view_lider_ok(client, lider, colaborador):
    client.force_login(lider)
    url = reverse(
        'reviews:continuous_feedback_create',
        kwargs={'user_id': colaborador.pk},
    )
    with patch(
        'apps.notifications.tasks.enviar_notificacao_feedback_continuo.delay',
    ):
        resp = client.post(url, {'conteudo': 'Ótimo trabalho neste mês.'})
    assert resp.status_code == 302
    feedback = FeedbackContinuo.objects.get(destinatario=colaborador)
    assert feedback.autor_id == lider.pk
    assert feedback.conteudo == 'Ótimo trabalho neste mês.'
    assert feedback.ciente_em is None


@pytest.mark.django_db
def test_create_view_fora_do_escopo_404(client, lider, admin):
    client.force_login(lider)
    url = reverse(
        'reviews:continuous_feedback_create',
        kwargs={'user_id': admin.pk},
    )
    resp = client.post(url, {'conteudo': 'Tentativa indevida.'})
    assert resp.status_code == 404
    assert FeedbackContinuo.objects.count() == 0


@pytest.mark.django_db
def test_create_view_colaborador_self_404(client, colaborador):
    client.force_login(colaborador)
    url = reverse(
        'reviews:continuous_feedback_create',
        kwargs={'user_id': colaborador.pk},
    )
    resp = client.get(url)
    assert resp.status_code == 404


@pytest.mark.django_db
def test_list_view_idor_404(client, lider, colaborador):
    FeedbackContinuo.objects.create(
        autor=lider,
        destinatario=colaborador,
        conteudo='Privado',
    )
    # Colaborador não pode listar feedbacks de outro destinatário
    client.force_login(colaborador)
    url = reverse(
        'reviews:continuous_feedback_list',
        kwargs={'user_id': lider.pk},
    )
    resp = client.get(url)
    assert resp.status_code == 404


@pytest.mark.django_db
def test_acknowledge_exige_declaracao_e_apenas_destinatario(
    client,
    lider,
    colaborador,
    admin,
):
    feedback = FeedbackContinuo.objects.create(
        autor=lider,
        destinatario=colaborador,
        conteudo='Feedback contínuo pendente.',
    )
    ack_url = reverse(
        'reviews:continuous_feedback_acknowledge',
        kwargs={'pk': feedback.pk},
    )

    client.force_login(colaborador)
    resp = client.post(ack_url, follow=True)
    assert resp.status_code == 200
    feedback.refresh_from_db()
    assert feedback.ciente_em is None

    client.force_login(admin)
    resp_admin = client.post(ack_url, {'declaro_ciencia': 'on'})
    assert resp_admin.status_code == 404
    feedback.refresh_from_db()
    assert feedback.ciente_em is None

    client.force_login(colaborador)
    resp_ok = client.post(ack_url, {'declaro_ciencia': 'on'}, follow=True)
    assert resp_ok.status_code == 200
    feedback.refresh_from_db()
    assert feedback.ciente_em is not None


@pytest.mark.django_db
def test_continuous_feedback_nao_altera_avaliacao_concluida(
    client,
    lider,
    colaborador,
    avaliacao,
):
    avaliacao.concluida = False
    avaliacao.save(update_fields=['concluida', 'updated_at'])

    client.force_login(lider)
    url = reverse(
        'reviews:continuous_feedback_create',
        kwargs={'user_id': colaborador.pk},
    )
    with patch(
        'apps.notifications.tasks.enviar_notificacao_feedback_continuo.delay',
    ):
        client.post(url, {'conteudo': 'Fora do ciclo.'})

    feedback = FeedbackContinuo.objects.get(destinatario=colaborador)
    client.force_login(colaborador)
    client.post(
        reverse(
            'reviews:continuous_feedback_acknowledge',
            kwargs={'pk': feedback.pk},
        ),
        {'declaro_ciencia': 'on'},
    )

    avaliacao.refresh_from_db()
    assert avaliacao.concluida is False
    assert Feedback.objects.filter(avaliacao=avaliacao).count() == 0


@pytest.mark.django_db
def test_mine_redirect(client, colaborador):
    client.force_login(colaborador)
    resp = client.get(reverse('reviews:continuous_feedback_mine'))
    assert resp.status_code == 302
    assert resp['Location'] == reverse(
        'reviews:continuous_feedback_list',
        kwargs={'user_id': colaborador.pk},
    )


@pytest.mark.django_db
def test_team_mostra_cta_enviar_feedback(client, lider, colaborador, ciclo_aberto):
    client.force_login(lider)
    resp = client.get(reverse('dashboard:team'))
    assert resp.status_code == 200
    html = resp.content.decode()
    assert 'Enviar feedback' in html
    assert reverse(
        'reviews:continuous_feedback_create',
        kwargs={'user_id': colaborador.pk},
    ) in html


@pytest.mark.django_db
def test_notificacao_email_feedback_continuo(lider, colaborador, settings, mailoutbox):
    settings.EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
    feedback = FeedbackContinuo.objects.create(
        autor=lider,
        destinatario=colaborador,
        conteudo='Conteúdo para notificar.',
    )
    from apps.notifications.models import NotificacaoLog
    from apps.notifications.tasks import enviar_notificacao_feedback_continuo

    result = enviar_notificacao_feedback_continuo(feedback.pk)
    assert result == 'enviado'
    assert len(mailoutbox) == 1
    assert colaborador.email in mailoutbox[0].to
    assert 'feedback' in mailoutbox[0].subject.lower()
    log = NotificacaoLog.objects.get(
        destinatario=colaborador,
        tipo=NotificacaoLog.Tipo.FEEDBACK_CONTINUO,
        referencia=f'feedback_continuo:{feedback.pk}',
    )
    assert log.status == NotificacaoLog.Status.ENVIADO

    # Dedupe: segundo envio não dispara outro e-mail
    result2 = enviar_notificacao_feedback_continuo(feedback.pk)
    assert result2 == 'duplicado'
    assert len(mailoutbox) == 1
