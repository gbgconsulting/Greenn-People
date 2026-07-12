from django.contrib import admin

from apps.audit.models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    """Read-only admin — RF-35 append-only (no add/change/delete)."""

    list_display = (
        'created_at',
        'acao',
        'usuario',
        'entity_type',
        'entity_id',
        'campo',
        'valor_anterior',
        'valor_novo',
    )
    list_filter = ('acao', 'entity_type', 'created_at')
    search_fields = ('entity_type', 'campo', 'valor_anterior', 'valor_novo')
    readonly_fields = (
        'usuario',
        'acao',
        'entity_type',
        'entity_id',
        'campo',
        'valor_anterior',
        'valor_novo',
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
