"""
Django settings for production.

Use: ``DJANGO_SETTINGS_MODULE=config.settings.prod``

Secrets, hosts, Redis and e-mail are loaded via django-environ in ``base``.
Database URL for PostgreSQL lands in T071.
"""

from .base import *  # noqa: F403

# Production must never run with DEBUG enabled, even if .env says otherwise.
DEBUG = False

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
