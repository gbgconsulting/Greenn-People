from datetime import datetime, time
from datetime import date as date_cls

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import QuerySet
from django.utils import timezone
from django.views.generic import ListView

from apps.accounts.models import CustomUser
from apps.audit.models import AuditLog
from apps.core.mixins import RequiresAdminMixin


class AdminAuditMixin(LoginRequiredMixin, RequiresAdminMixin):
    """Auth + admin gate for audit consultation views."""


class AuditLogListView(AdminAuditMixin, ListView):
    """Consulta de auditoria (RF-34) — filtros: usuário, ação e período."""

    model = AuditLog
    template_name = 'audit/auditlog_list.html'
    context_object_name = 'logs'
    paginate_by = 20

    def get_queryset(self) -> QuerySet[AuditLog]:
        qs = AuditLog.objects.select_related('usuario').order_by('-created_at')

        usuario_id = self.request.GET.get('usuario', '').strip()
        if usuario_id.isdigit():
            qs = qs.filter(usuario_id=int(usuario_id))

        acao = self.request.GET.get('acao', '').strip()
        if acao and acao in AuditLog.Acao.values:
            qs = qs.filter(acao=acao)

        data_inicio = self._parse_date(self.request.GET.get('data_inicio', ''))
        if data_inicio is not None:
            start = timezone.make_aware(datetime.combine(data_inicio, time.min))
            qs = qs.filter(created_at__gte=start)

        data_fim = self._parse_date(self.request.GET.get('data_fim', ''))
        if data_fim is not None:
            end = timezone.make_aware(datetime.combine(data_fim, time.max))
            qs = qs.filter(created_at__lte=end)

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                'acao_choices': AuditLog.Acao.choices,
                'usuarios': CustomUser.objects.order_by('nome', 'email'),
                'filtro_usuario': self.request.GET.get('usuario', '').strip(),
                'filtro_acao': self.request.GET.get('acao', '').strip(),
                'filtro_data_inicio': self.request.GET.get('data_inicio', '').strip(),
                'filtro_data_fim': self.request.GET.get('data_fim', '').strip(),
            },
        )
        return context

    @staticmethod
    def _parse_date(raw: str) -> date_cls | None:
        value = (raw or '').strip()
        if not value:
            return None
        try:
            return date_cls.fromisoformat(value)
        except ValueError:
            return None
