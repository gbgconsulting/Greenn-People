"""Sinais de segurança — registro de tentativas de login falhas."""

from __future__ import annotations

import logging

from django.contrib.auth.signals import user_login_failed
from django.dispatch import receiver

from apps.core.ratelimit import get_client_ip

logger = logging.getLogger('apps.accounts.security')


@receiver(user_login_failed)
def log_user_login_failed(sender, credentials, request, **kwargs):
    """Registra falha de autenticação sem expor a senha."""
    ip = get_client_ip(request) if request is not None else 'unknown'
    username = credentials.get('username', '')
    logger.warning(
        'login_failed ip=%s username=%s',
        ip,
        username,
    )
