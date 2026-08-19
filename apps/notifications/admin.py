from django.contrib import admin

from apps.notifications.models import NotificacaoLog


@admin.register(NotificacaoLog)
class NotificacaoLogAdmin(admin.ModelAdmin):
    """Read-only admin — delivery log is append-only (RF-31)."""

    list_display = (
        'created_at',
        'tipo',
        'status',
        'destinatario',
        'erro',
    )
    list_filter = ('tipo', 'status', 'created_at')
    search_fields = ('destinatario__email', 'destinatario__nome', 'erro')
    readonly_fields = (
        'destinatario',
        'tipo',
        'status',
        'erro',
        'created_at',
    )
    ordering = ('-created_at',)
    date_hierarchy = 'created_at'

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
