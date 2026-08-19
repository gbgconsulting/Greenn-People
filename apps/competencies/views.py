from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.generic import (
    CreateView,
    DeleteView,
    ListView,
    UpdateView,
)
from django.views.generic.base import TemplateResponseMixin

from apps.competencies.forms import (
    CargoCompetenciaFormSet,
    CompetenciaForm,
    EscalaForm,
)
from apps.competencies.models import Competencia, Escala
from apps.core.mixins import HtmxPaginatedListMixin, RequiresAdminMixin
from apps.organization.models import Cargo


class AdminCompetenciesMixin(LoginRequiredMixin, RequiresAdminMixin):
    """Auth + admin gate for competencies management views."""


class EscalaListView(AdminCompetenciesMixin, HtmxPaginatedListMixin, ListView):
    model = Escala
    template_name = 'competencies/escala_list.html'
    partial_template_name = 'competencies/escala_list_partial.html'
    context_object_name = 'escalas'

    def get_queryset(self):
        return Escala.objects.order_by('nome')


class EscalaCreateView(AdminCompetenciesMixin, CreateView):
    model = Escala
    form_class = EscalaForm
    template_name = 'competencies/escala_form.html'
    success_url = reverse_lazy('competencies:escala_list')

    def form_valid(self, form):
        messages.success(self.request, 'Escala criada com sucesso.')
        return super().form_valid(form)


class EscalaUpdateView(AdminCompetenciesMixin, UpdateView):
    model = Escala
    form_class = EscalaForm
    template_name = 'competencies/escala_form.html'
    success_url = reverse_lazy('competencies:escala_list')

    def form_valid(self, form):
        messages.success(self.request, 'Escala atualizada com sucesso.')
        return super().form_valid(form)


class EscalaDeleteView(AdminCompetenciesMixin, DeleteView):
    """Soft-delete: sets ``is_active=False`` (no hard delete)."""

    model = Escala
    template_name = 'competencies/escala_confirm_delete.html'
    success_url = reverse_lazy('competencies:escala_list')

    def form_valid(self, form):
        self.object = self.get_object()
        self.object.is_active = False
        self.object.save(update_fields=['is_active', 'updated_at'])
        messages.success(self.request, 'Escala desativada com sucesso.')
        return HttpResponseRedirect(self.get_success_url())


class CompetenciaListView(AdminCompetenciesMixin, HtmxPaginatedListMixin, ListView):
    model = Competencia
    template_name = 'competencies/competencia_list.html'
    partial_template_name = 'competencies/competencia_list_partial.html'
    context_object_name = 'competencias'

    def get_queryset(self):
        return Competencia.objects.select_related('escala').order_by('nome')


class CompetenciaCreateView(AdminCompetenciesMixin, CreateView):
    model = Competencia
    form_class = CompetenciaForm
    template_name = 'competencies/competencia_form.html'
    success_url = reverse_lazy('competencies:competencia_list')

    def form_valid(self, form):
        messages.success(self.request, 'Competência criada com sucesso.')
        return super().form_valid(form)


class CompetenciaUpdateView(AdminCompetenciesMixin, UpdateView):
    model = Competencia
    form_class = CompetenciaForm
    template_name = 'competencies/competencia_form.html'
    success_url = reverse_lazy('competencies:competencia_list')

    def form_valid(self, form):
        messages.success(self.request, 'Competência atualizada com sucesso.')
        return super().form_valid(form)


class CompetenciaDeleteView(AdminCompetenciesMixin, DeleteView):
    """Soft-delete: sets ``is_active=False`` (no hard delete)."""

    model = Competencia
    template_name = 'competencies/competencia_confirm_delete.html'
    success_url = reverse_lazy('competencies:competencia_list')

    def form_valid(self, form):
        self.object = self.get_object()
        self.object.is_active = False
        self.object.save(update_fields=['is_active', 'updated_at'])
        messages.success(self.request, 'Competência desativada com sucesso.')
        return HttpResponseRedirect(self.get_success_url())


class CargoCompetenciaUpdateView(
    AdminCompetenciesMixin,
    TemplateResponseMixin,
    View,
):
    """Edit expected competencies and weights for a job position."""

    template_name = 'competencies/cargo_competencia_form.html'

    def dispatch(self, request, *args, **kwargs):
        self.cargo = get_object_or_404(Cargo, pk=kwargs['pk'])
        return super().dispatch(request, *args, **kwargs)

    def get_formset(self, data=None):
        return CargoCompetenciaFormSet(
            data=data,
            instance=self.cargo,
            queryset=self.cargo.cargo_competencias.select_related(
                'competencia',
                'competencia__escala',
            ).order_by('competencia__nome'),
        )

    def get(self, request, *args, **kwargs):
        formset = self.get_formset()
        return self.render_to_response(self.get_context_data(formset=formset))

    def post(self, request, *args, **kwargs):
        formset = self.get_formset(data=request.POST)
        if formset.is_valid():
            formset.save()
            messages.success(
                request,
                f'Perfil de competências de "{self.cargo.nome}" atualizado.',
            )
            return redirect(
                reverse('competencies:cargo_competencia_update', kwargs={
                    'pk': self.cargo.pk,
                }),
            )
        return self.render_to_response(self.get_context_data(formset=formset))

    def get_context_data(self, **kwargs):
        context = {
            'cargo': self.cargo,
            'formset': kwargs.get('formset'),
        }
        return context
