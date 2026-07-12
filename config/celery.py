"""
Celery application for Greenn People.

Broker and result backend come from Django settings
(``CELERY_BROKER_URL`` / ``CELERY_RESULT_BACKEND`` → Redis).
"""

import os

from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.dev')

app = Celery('config')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

# RF-32 / RF-32.1 — daily deadline checks (timezone = CELERY_TIMEZONE / TIME_ZONE)
# RF-26 — daily adherence snapshots for open cycles
app.conf.beat_schedule = {
    'mark-overdue-pdi-actions-daily': {
        'task': 'apps.pdi.tasks.mark_overdue_pdi_actions',
        'schedule': crontab(hour=0, minute=15),
    },
    'calculate-adherence-snapshots-daily': {
        'task': 'apps.dashboard.tasks.calculate_adherence_snapshots_daily',
        'schedule': crontab(hour=1, minute=0),
    },
}
