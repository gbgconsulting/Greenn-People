"""
Django settings for production.

Use: ``DJANGO_SETTINGS_MODULE=config.settings.prod``

Secrets, hosts, Redis and database URL will be loaded via django-environ (T003/T071).
"""

from .base import *  # noqa: F403

DEBUG = False

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
