"""
Celery application for Greenn People.

Broker and result backend come from Django settings
(``CELERY_BROKER_URL`` / ``CELERY_RESULT_BACKEND`` → Redis).
"""

import os

from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.dev')

app = Celery('config')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()
