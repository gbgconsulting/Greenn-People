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
# RF-31 — reminder e-mails (stage / PDI) N days before deadline
# RF-26 — daily adherence snapshots for open cycles
# US4 — weekly org digest of overdue PDIs for admins (same morning window as reminders)
# 018 — abertura automática de ciclo por admissão (após overdue PDI; HTTP não é disparo)
app.conf.beat_schedule = {
    'mark-overdue-pdi-actions-daily': {
        'task': 'apps.pdi.tasks.mark_overdue_pdi_actions',
        'schedule': crontab(hour=0, minute=15),
    },
    'auto-cycle-admission-daily': {
        'task': 'apps.cycles.tasks.run_auto_cycle_admission_daily',
        'schedule': crontab(hour=0, minute=30),
    },
    'enviar-lembrete-prazo-etapa-daily': {
        'task': 'apps.notifications.tasks.enviar_lembrete_prazo_etapa',
        'schedule': crontab(hour=8, minute=0),
    },
    'enviar-lembrete-acao-pdi-vencendo-daily': {
        'task': 'apps.notifications.tasks.enviar_lembrete_acao_pdi_vencendo',
        'schedule': crontab(hour=8, minute=15),
    },
    'enviar-digest-pdi-atrasos-weekly': {
        'task': 'apps.notifications.tasks.enviar_digest_pdi_atrasos',
        'schedule': crontab(hour=8, minute=30, day_of_week='monday'),
    },
    'calculate-adherence-snapshots-daily': {
        'task': 'apps.dashboard.tasks.calculate_adherence_snapshots_daily',
        'schedule': crontab(hour=1, minute=0),
    },
}
