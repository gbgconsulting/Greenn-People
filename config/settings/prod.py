"""
Django settings for production.

Use: ``DJANGO_SETTINGS_MODULE=config.settings.prod``

Secrets, hosts, Redis and e-mail are loaded via django-environ in ``base``.
PostgreSQL is required via ``DATABASE_URL`` (e.g. postgresql://user:pass@host:5432/db).
"""

from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F403

# Production must never run with DEBUG enabled, even if .env says otherwise.
DEBUG = False

if not ALLOWED_HOSTS or '*' in ALLOWED_HOSTS:  # noqa: F405
    raise ImproperlyConfigured(
        'ALLOWED_HOSTS must be set explicitly in production (no wildcard).',
    )

# Require an explicit database URL — do not fall back to SQLite in production.
DATABASES = {
    'default': env.db('DATABASE_URL'),  # noqa: F405
}

# Static files — destination of ``collectstatic``; served by WhiteNoise behind WSGI
# (single-container deploy). Alternative: reverse-proxy — see docs/ops/static.md.
STATIC_ROOT = BASE_DIR / 'staticfiles'  # noqa: F405

MIDDLEWARE = list(MIDDLEWARE)  # noqa: F405 — copy from base before insert
_security = 'django.middleware.security.SecurityMiddleware'
MIDDLEWARE.insert(
    MIDDLEWARE.index(_security) + 1,
    'whitenoise.middleware.WhiteNoiseMiddleware',
)
MIDDLEWARE.append('apps.core.middleware.SecurityHeadersMiddleware')

STORAGES = {
    'default': {
        'BACKEND': 'django.core.files.storage.FileSystemStorage',
    },
    'staticfiles': {
        'BACKEND': 'whitenoise.storage.CompressedStaticFilesStorage',
    },
}

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

# Cadastro self-service desligado em produção (RH provisiona contas)
REGISTRATION_ENABLED = env.bool('REGISTRATION_ENABLED', default=False)  # noqa: F405

# Rate limit compartilhado entre workers via Redis (db/1)
_cache_redis = REDIS_URL.replace('/0', '/1') if '/0' in REDIS_URL else f'{REDIS_URL}/1'  # noqa: F405
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': _cache_redis,
    },
}
