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
from apps.competencies.services.competencia_list import (
    STATUS_SEGMENT_OPTIONS,
    apply_competencia_list_filters,
    get_allowed_tipo_values,
    get_base_competencia_list_queryset,
    get_tipo_filter_options,
    parse_search_filter,
    parse_status_filter,
    parse_tipo_filter,
    resolve_tipo_filter,
)
from apps.core.mixins import HtmxPaginatedListMixin, RequiresAdminMixin
from apps.organization.models import Cargo
from apps.organization.services.navigation import resolve_admin_list_return_url


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

    def _parsed_filters(self):
        base_qs = get_base_competencia_list_queryset()
        status = parse_status_filter(self.request.GET.get('status'))
        busca = parse_search_filter(self.request.GET.get('busca'))
        tipo = resolve_tipo_filter(
            parse_tipo_filter(self.request.GET.get('tipo')),
            get_allowed_tipo_values(base_qs),
        )
        return base_qs, status, busca, tipo

    def get_queryset(self):
        base_qs, status, busca, tipo = self._parsed_filters()
        return apply_competencia_list_filters(
            base_qs,
            status=status,
            busca=busca,
            tipo=tipo,
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        base_qs, status, busca, tipo = self._parsed_filters()
        context.update(
            {
                'list_url': reverse('competencies:competencia_list'),
                'status_segment_options': STATUS_SEGMENT_OPTIONS,
                'filtro_status': status,
                'filtro_busca': busca,
                'filtro_tipo': tipo,
                'filtro_ativo': bool(busca or status or tipo),
                'filtro_avancado_ativo': bool(tipo),
                'filtro_avancado_count': 1 if tipo else 0,
                'tipo_options': get_tipo_filter_options(base_qs),
            },
        )
        return context


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

    def get_success_url(self):
        return resolve_admin_list_return_url(
            self.request,
            default=str(self.success_url),
        )


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

    def get_success_url(self):
        return resolve_admin_list_return_url(
            self.request,
            default=str(self.success_url),
        )


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
