from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView

from apps.competencies.models import CargoCompetencia
from apps.cycles.models import Ciclo
from apps.goals.models import Meta


class ExpectationsView(LoginRequiredMixin, TemplateView):
    """Página de expectativas do colaborador (FR-001, FR-002)."""

    template_name = 'goals/expectations.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        cargo = user.cargo
        if user.cargo_id:
            competencias_cargo = list(
                CargoCompetencia.objects.filter(cargo_id=user.cargo_id)
                .select_related('competencia', 'competencia__escala')
                .order_by('competencia__nome'),
            )
        else:
            competencias_cargo = []

        vinculo_pendente = cargo is None or not competencias_cargo

        ciclo_aberto = (
            Ciclo.objects.filter(status=Ciclo.Status.ABERTO)
            .order_by('-data_inicio')
            .first()
        )
        if ciclo_aberto is not None:
            metas = list(
                Meta.objects.filter(
                    usuario=user,
                    objetivo_estrategico__ciclo=ciclo_aberto,
                )
                .select_related('objetivo_estrategico')
                .order_by('objetivo_estrategico_id', 'id'),
            )
        else:
            metas = []

        context.update(
            {
                'cargo': cargo,
                'competencias_cargo': competencias_cargo,
                'vinculo_pendente': vinculo_pendente,
                'ciclo_aberto': ciclo_aberto,
                'metas': metas,
            },
        )
        return context
