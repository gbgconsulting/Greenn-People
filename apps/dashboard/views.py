from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView

from apps.reviews.services.evaluation import build_fr005_context


class PersonalDashboardView(LoginRequiredMixin, TemplateView):
    """Painel pessoal com nivel esperado e nota atual (FR-005)."""

    template_name = 'dashboard/personal.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(build_fr005_context(self.request.user))
        return context
