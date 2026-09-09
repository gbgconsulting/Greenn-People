"""
Shared Django settings for Greenn People.

Environment-specific overrides live in ``dev`` and ``prod``.
Sensitive values are loaded from the environment via django-environ.
"""

from pathlib import Path

import environ

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env(
    DEBUG=(bool, False),
    ALLOWED_HOSTS=(list, []),
    EMAIL_PORT=(int, 587),
    EMAIL_USE_TLS=(bool, True),
    REGISTRATION_ENABLED=(bool, False),
    SESSION_COOKIE_AGE=(int, 43200),
    PASSWORD_RESET_TIMEOUT=(int, 3600),
    RATE_LIMIT_LOGIN=(int, 5),
    RATE_LIMIT_LOGIN_PERIOD=(int, 60),
    RATE_LIMIT_PASSWORD_RESET=(int, 3),
    RATE_LIMIT_PASSWORD_RESET_PERIOD=(int, 300),
    RATE_LIMIT_REGISTER=(int, 3),
    RATE_LIMIT_REGISTER_PERIOD=(int, 3600),
    RATE_LIMIT_RESEND_CONFIRMATION=(int, 3),
    RATE_LIMIT_RESEND_CONFIRMATION_PERIOD=(int, 300),
)

environ.Env.read_env(BASE_DIR / '.env')


# Quick-start settings — secrets and hosts come from the environment.
# See https://docs.djangoproject.com/en/6.0/howto/deployment/checklist/

SECRET_KEY = env('SECRET_KEY')

DEBUG = env('DEBUG')

ALLOWED_HOSTS = env('ALLOWED_HOSTS')


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Domain apps
    'apps.core.apps.CoreConfig',
    'apps.accounts.apps.AccountsConfig',
    'apps.organization.apps.OrganizationConfig',
    'apps.competencies.apps.CompetenciesConfig',
    'apps.goals.apps.GoalsConfig',
    'apps.cycles.apps.CyclesConfig',
    'apps.reviews.apps.ReviewsConfig',
    'apps.pdi.apps.PdiConfig',
    'apps.talent.apps.TalentConfig',
    'apps.dashboard.apps.DashboardConfig',
    'apps.notifications.apps.NotificationsConfig',
    'apps.audit.apps.AuditConfig',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'apps.audit.middleware.AuditActorMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'apps.core.context_processors.ciclo_aberto',
                'apps.core.context_processors.leader_pending_badge',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'


# Database
# https://docs.djangoproject.com/en/6.0/ref/settings/#databases
# SQLite by default (local). Set DATABASE_URL for PostgreSQL (production).
# Schema uses only portable Django ORM features — no SQLite/Postgres exclusives.

_database_url = env.str('DATABASE_URL', default='')
if _database_url:
    DATABASES = {'default': env.db_url_config(_database_url)}
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }


# Password validation
# https://docs.djangoproject.com/en/6.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/6.0/topics/i18n/

LANGUAGE_CODE = 'pt-br'

TIME_ZONE = 'America/Sao_Paulo'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/6.0/howto/static-files/

STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static']

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

AUTH_USER_MODEL = 'accounts.CustomUser'

LOGIN_URL = 'accounts:login'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = 'accounts:login'


# Redis / Celery (broker and result backend; app in config/celery.py)

REDIS_URL = env('REDIS_URL', default='redis://127.0.0.1:6379/0')
CELERY_BROKER_URL = env('CELERY_BROKER_URL', default=REDIS_URL)
CELERY_RESULT_BACKEND = env('CELERY_RESULT_BACKEND', default=REDIS_URL)
CELERY_TIMEZONE = TIME_ZONE


# E-mail

EMAIL_HOST = env('EMAIL_HOST', default='localhost')
EMAIL_PORT = env('EMAIL_PORT')
EMAIL_HOST_USER = env('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD', default='')
EMAIL_USE_TLS = env('EMAIL_USE_TLS')
DEFAULT_FROM_EMAIL = env('DEFAULT_FROM_EMAIL', default='noreply@greenn.com.br')
# Origin for absolute links in e-mails (Celery / Beat have no HTTP request).
PUBLIC_BASE_URL = env('PUBLIC_BASE_URL', default='http://localhost:8000')

# RF-31 / Sprint 9.2.2 — days before deadline to send reminder e-mails
NOTIFICATION_REMINDER_DAYS = env.int('NOTIFICATION_REMINDER_DAYS', default=3)

# Sessão e reset de senha
SESSION_COOKIE_AGE = env('SESSION_COOKIE_AGE')
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
PASSWORD_RESET_TIMEOUT = env('PASSWORD_RESET_TIMEOUT')

# Cadastro self-service (desligado por default; habilitar em dev via .env)
REGISTRATION_ENABLED = env('REGISTRATION_ENABLED')

# Rate limiting (cache-backed — ver CACHES)
RATE_LIMIT_LOGIN = env('RATE_LIMIT_LOGIN')
RATE_LIMIT_LOGIN_PERIOD = env('RATE_LIMIT_LOGIN_PERIOD')
RATE_LIMIT_PASSWORD_RESET = env('RATE_LIMIT_PASSWORD_RESET')
RATE_LIMIT_PASSWORD_RESET_PERIOD = env('RATE_LIMIT_PASSWORD_RESET_PERIOD')
RATE_LIMIT_REGISTER = env('RATE_LIMIT_REGISTER')
RATE_LIMIT_REGISTER_PERIOD = env('RATE_LIMIT_REGISTER_PERIOD')
RATE_LIMIT_RESEND_CONFIRMATION = env('RATE_LIMIT_RESEND_CONFIRMATION')
RATE_LIMIT_RESEND_CONFIRMATION_PERIOD = env('RATE_LIMIT_RESEND_CONFIRMATION_PERIOD')

# Health check — token opcional (header X-Health-Token ou ?token=)
HEALTH_CHECK_TOKEN = env('HEALTH_CHECK_TOKEN', default='')

# Cache — locmem por default; produção sobrescreve para Redis (rate limit compartilhado)
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    },
}

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'redact_sensitive': {
            '()': 'apps.core.logging_filters.RedactSensitiveFilter',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'filters': ['redact_sensitive'],
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'apps.accounts.security': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.security': {
            'handlers': ['console'],
            'level': 'WARNING',
            'propagate': False,
        },
    },
}
