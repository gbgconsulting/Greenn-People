"""
Django settings for local development.

Use: ``DJANGO_SETTINGS_MODULE=config.settings.dev``
"""

from .base import *  # noqa: F403

DEBUG = True

ALLOWED_HOSTS = ['localhost', '127.0.0.1']

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Dev local: cadastro self-service habilitado por default
REGISTRATION_ENABLED = env.bool('REGISTRATION_ENABLED', default=True)  # noqa: F405
