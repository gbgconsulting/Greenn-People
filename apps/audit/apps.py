from django.apps import AppConfig


class AuditConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.audit'
    label = 'audit'
    verbose_name = 'Audit'

    def ready(self) -> None:
        from apps.audit.signals import connect_audit_signals

        connect_audit_signals()
