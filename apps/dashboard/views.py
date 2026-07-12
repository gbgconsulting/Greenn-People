from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView


class PersonalDashboardView(LoginRequiredMixin, TemplateView):
    """Shell autenticado mínimo do painel pessoal (rota `/`)."""

    template_name = 'dashboard/personal.html'
