from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import QuerySet
from django.views.generic import ListView

from apps.core.mixins import RequiresAdminMixin
from apps.notifications.models import NotificacaoLog


class AdminNotificationsMixin(LoginRequiredMixin, RequiresAdminMixin):
    """Auth + admin gate for notification log consultation."""


class NotificacaoLogListView(AdminNotificationsMixin, ListView):
    """Consulta de envios de e-mail (RF-31) — falhas e sucessos."""

    model = NotificacaoLog
    template_name = 'notifications/notificacaolog_list.html'
    context_object_name = 'logs'
    paginate_by = 20

    def get_queryset(self) -> QuerySet[NotificacaoLog]:
        qs = (
            NotificacaoLog.objects.select_related('destinatario')
            .order_by('-created_at')
        )

        status = self.request.GET.get('status', '').strip()
        if status and status in NotificacaoLog.Status.values:
            qs = qs.filter(status=status)

        tipo = self.request.GET.get('tipo', '').strip()
        if tipo and tipo in NotificacaoLog.Tipo.values:
            qs = qs.filter(tipo=tipo)

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                'status_choices': NotificacaoLog.Status.choices,
                'tipo_choices': NotificacaoLog.Tipo.choices,
                'filtro_status': self.request.GET.get('status', '').strip(),
                'filtro_tipo': self.request.GET.get('tipo', '').strip(),
            },
        )
        return context
