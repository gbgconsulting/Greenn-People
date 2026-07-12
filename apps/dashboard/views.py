from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, TemplateView

from apps.accounts.models import CustomUser
from apps.accounts.services.scope import get_visible_users
from apps.core.mixins import RequiresLeaderMixin
from apps.goals.forms import get_open_ciclo
from apps.reviews.models import Avaliacao
from apps.reviews.services.evaluation import build_fr005_context


class PersonalDashboardView(LoginRequiredMixin, TemplateView):
    """Painel pessoal com nivel esperado e nota atual (FR-005)."""

    template_name = 'dashboard/personal.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(build_fr005_context(self.request.user))
        return context


class TeamDashboardView(LoginRequiredMixin, RequiresLeaderMixin, ListView):
    """Painel do time: lista colaboradores no escopo hierárquico (US2 / FR-006)."""

    template_name = 'dashboard/team.html'
    context_object_name = 'membros'
    paginate_by = 20

    def get_queryset(self):
        return (
            get_visible_users(self.request.user)
            .exclude(pk=self.request.user.pk)
            .filter(is_active=True)
            .select_related('area', 'cargo')
            .order_by('nome', 'email')
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        ciclo = get_open_ciclo()
        context['ciclo_aberto'] = ciclo

        membros: list[CustomUser] = list(context['object_list'])
        avaliacoes_por_usuario: dict[int, Avaliacao] = {}
        if ciclo is not None and membros:
            avaliacoes_por_usuario = {
                avaliacao.usuario_id: avaliacao
                for avaliacao in Avaliacao.objects.filter(
                    ciclo=ciclo,
                    usuario_id__in=[m.pk for m in membros],
                ).select_related('ciclo')
            }

        context['membros_resumo'] = [
            {
                'usuario': membro,
                'avaliacao': avaliacoes_por_usuario.get(membro.pk),
            }
            for membro in membros
        ]
        return context
