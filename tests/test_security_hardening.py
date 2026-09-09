"""Testes de hardening de segurança (Fase 2)."""

from __future__ import annotations

import logging

import pytest
from django.core.cache import cache
from django.test import Client, override_settings
from django.urls import reverse

from tests.conftest import DEFAULT_PASSWORD


@pytest.fixture(autouse=True)
def _clear_rate_limit_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.mark.django_db
def test_login_rate_limit_blocks_excessive_attempts(colaborador):
    client = Client()
    url = reverse('accounts:login')
    with override_settings(RATE_LIMIT_LOGIN=2, RATE_LIMIT_LOGIN_PERIOD=60):
        for _ in range(2):
            client.post(
                url,
                {
                    'username': colaborador.email,
                    'password': 'wrong-password',
                },
            )
        resp = client.post(
            url,
            {
                'username': colaborador.email,
                'password': 'wrong-password',
            },
        )
    assert resp.status_code == 200
    assert 'Muitas tentativas' in resp.content.decode()


@pytest.mark.django_db
def test_login_rate_limit_allows_valid_login_after_failures(colaborador):
    client = Client()
    url = reverse('accounts:login')
    with override_settings(RATE_LIMIT_LOGIN=5, RATE_LIMIT_LOGIN_PERIOD=60):
        client.post(
            url,
            {'username': colaborador.email, 'password': 'wrong-password'},
        )
        resp = client.post(
            url,
            {'username': colaborador.email, 'password': DEFAULT_PASSWORD},
        )
    assert resp.status_code == 302


@pytest.mark.django_db
def test_registration_disabled_returns_404():
    client = Client()
    with override_settings(REGISTRATION_ENABLED=False):
        resp = client.get(reverse('accounts:register'))
    assert resp.status_code == 404


@pytest.mark.django_db
def test_password_reset_rate_limit(client):
    url = reverse('accounts:password_reset')
    with override_settings(
        RATE_LIMIT_PASSWORD_RESET=2,
        RATE_LIMIT_PASSWORD_RESET_PERIOD=300,
    ):
        for _ in range(2):
            client.post(url, {'email': 'someone@greenn.com.br'})
        resp = client.post(url, {'email': 'someone@greenn.com.br'})
    assert resp.status_code == 200
    assert 'Muitas tentativas' in resp.content.decode()


@pytest.mark.django_db
def test_health_without_token_when_unconfigured():
    client = Client()
    with override_settings(HEALTH_CHECK_TOKEN=''):
        resp = client.get(reverse('health'))
    assert resp.status_code == 200
    assert resp.json()['status'] == 'ok'


@pytest.mark.django_db
def test_health_requires_token_when_configured():
    client = Client()
    with override_settings(HEALTH_CHECK_TOKEN='secret-health-token'):
        assert client.get(reverse('health')).status_code == 404
        resp = client.get(
            reverse('health'),
            HTTP_X_HEALTH_TOKEN='secret-health-token',
        )
    assert resp.status_code == 200


@pytest.mark.django_db
def test_failed_login_is_logged(colaborador, caplog):
    client = Client()
    with caplog.at_level(logging.WARNING, logger='apps.accounts.security'):
        client.post(
            reverse('accounts:login'),
            {
                'username': colaborador.email,
                'password': 'wrong-password',
            },
        )
    assert any(
        'login_failed' in record.message for record in caplog.records
    )


def test_prod_allowed_hosts_rejects_wildcard():
    with pytest.raises(Exception) as exc_info:
        with override_settings(
            ALLOWED_HOSTS=['*'],
            DEBUG=False,
        ):
            from django.conf import settings as django_settings

            if not django_settings.ALLOWED_HOSTS or '*' in django_settings.ALLOWED_HOSTS:
                from django.core.exceptions import ImproperlyConfigured

                raise ImproperlyConfigured(
                    'ALLOWED_HOSTS must be set explicitly in production (no wildcard).',
                )
    assert 'ALLOWED_HOSTS' in str(exc_info.value)


@pytest.mark.django_db
def test_resend_confirmation_rate_limit(client):
    url = reverse('accounts:resend_confirmation')
    with override_settings(
        RATE_LIMIT_RESEND_CONFIRMATION=2,
        RATE_LIMIT_RESEND_CONFIRMATION_PERIOD=300,
    ):
        for _ in range(2):
            client.post(url, {'email': 'pending@greenn.com.br'})
        resp = client.post(url, {'email': 'pending@greenn.com.br'})
    assert resp.status_code == 200
    assert 'Muitas tentativas' in resp.content.decode()
