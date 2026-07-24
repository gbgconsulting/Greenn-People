from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse, reverse_lazy
from django.views.generic import (
    CreateView,
    DeleteView,
    FormView,
    ListView,
    UpdateView,
)

from apps.accounts.models import CustomUser
from apps.accounts.services.offboarding import reassign_direct_reports
from apps.core.mixins import HtmxPaginatedListMixin, RequiresAdminMixin
from apps.organization.forms import (
    AreaForm,
    CargoForm,
    ReassignDirectReportsForm,
    UserUpdateForm,
)
from apps.organization.models import Area, Cargo


class AdminOrganizationMixin(LoginRequiredMixin, RequiresAdminMixin):
    """Auth + admin gate for organization management views."""


class AreaListView(AdminOrganizationMixin, HtmxPaginatedListMixin, ListView):
    model = Area
    template_name = 'organization/area_list.html'
    partial_template_name = 'organization/area_list_partial.html'
    context_object_name = 'areas'

    def get_queryset(self):
        return (
            Area.objects.select_related('parent')
            .order_by('nome')
        )


class AreaCreateView(AdminOrganizationMixin, CreateView):
    model = Area
    form_class = AreaForm
    template_name = 'organization/area_form.html'
    success_url = reverse_lazy('organization:area_list')

    def form_valid(self, form):
        messages.success(self.request, 'Área criada com sucesso.')
        return super().form_valid(form)


class AreaUpdateView(AdminOrganizationMixin, UpdateView):
    model = Area
    form_class = AreaForm
    template_name = 'organization/area_form.html'
    success_url = reverse_lazy('organization:area_list')

    def form_valid(self, form):
        messages.success(self.request, 'Área atualizada com sucesso.')
        return super().form_valid(form)


class AreaDeleteView(AdminOrganizationMixin, DeleteView):
    """Soft-delete: sets ``is_active=False`` (no hard delete)."""

    model = Area
    template_name = 'organization/area_confirm_delete.html'
    success_url = reverse_lazy('organization:area_list')

    def form_valid(self, form):
        self.object = self.get_object()
        self.object.is_active = False
        self.object.save(update_fields=['is_active', 'updated_at'])
        messages.success(self.request, 'Área desativada com sucesso.')
        return HttpResponseRedirect(self.get_success_url())


class CargoListView(AdminOrganizationMixin, HtmxPaginatedListMixin, ListView):
    model = Cargo
    template_name = 'organization/cargo_list.html'
    partial_template_name = 'organization/cargo_list_partial.html'
    context_object_name = 'cargos'

    def get_queryset(self):
        return Cargo.objects.order_by('nivel', 'nome')


class CargoCreateView(AdminOrganizationMixin, CreateView):
    model = Cargo
    form_class = CargoForm
    template_name = 'organization/cargo_form.html'
    success_url = reverse_lazy('organization:cargo_list')

    def form_valid(self, form):
        messages.success(self.request, 'Cargo criado com sucesso.')
        return super().form_valid(form)


class CargoUpdateView(AdminOrganizationMixin, UpdateView):
    model = Cargo
    form_class = CargoForm
    template_name = 'organization/cargo_form.html'
    success_url = reverse_lazy('organization:cargo_list')

    def form_valid(self, form):
        messages.success(self.request, 'Cargo atualizado com sucesso.')
        return super().form_valid(form)


class CargoDeleteView(AdminOrganizationMixin, DeleteView):
    """Soft-delete: sets ``is_active=False`` (no hard delete)."""

    model = Cargo
    template_name = 'organization/cargo_confirm_delete.html'
    success_url = reverse_lazy('organization:cargo_list')

    def form_valid(self, form):
        self.object = self.get_object()
        self.object.is_active = False
        self.object.save(update_fields=['is_active', 'updated_at'])
        messages.success(self.request, 'Cargo desativado com sucesso.')
        return HttpResponseRedirect(self.get_success_url())


class UserListView(AdminOrganizationMixin, HtmxPaginatedListMixin, ListView):
    model = CustomUser
    template_name = 'organization/user_list.html'
    partial_template_name = 'organization/user_list_partial.html'
    context_object_name = 'users'

    def get_queryset(self):
        return (
            CustomUser.objects.select_related('area', 'cargo', 'line_manager')
            .order_by('nome', 'email')
        )


class UserUpdateView(AdminOrganizationMixin, UpdateView):
    model = CustomUser
    form_class = UserUpdateForm
    template_name = 'organization/user_form.html'
    context_object_name = 'edited_user'
    success_url = reverse_lazy('organization:user_list')

    def get_queryset(self):
        return CustomUser.objects.select_related(
            'area',
            'cargo',
            'line_manager',
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.object
        ctx['active_direct_reports'] = CustomUser.objects.filter(
            line_manager_id=user.pk,
            is_active=True,
        ).order_by('nome')
        return ctx

    def form_valid(self, form):
        try:
            response = super().form_valid(form)
        except ValidationError as exc:
            form.add_error(None, exc)
            return self.form_invalid(form)
        messages.success(self.request, 'Usuário atualizado com sucesso.')
        return response

    def get_success_url(self):
        next_url = self.request.GET.get('next')
        if next_url == 'pending':
            return reverse('organization:user_pending')
        return str(self.success_url)


class ReassignDirectReportsView(AdminOrganizationMixin, FormView):
    """Reatribui em lote os liderados ativos de um gestor (offboarding)."""

    form_class = ReassignDirectReportsForm
    template_name = 'organization/reassign_reports.html'

    def dispatch(self, request, *args, **kwargs):
        self.from_manager = get_object_or_404(CustomUser, pk=kwargs['pk'])
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['from_manager'] = self.from_manager
        return kwargs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['from_manager'] = self.from_manager
        ctx['direct_reports'] = CustomUser.objects.filter(
            line_manager_id=self.from_manager.pk,
            is_active=True,
        ).order_by('nome', 'email')
        return ctx

    def form_valid(self, form):
        reports = CustomUser.objects.filter(
            line_manager_id=self.from_manager.pk,
            is_active=True,
        )
        if not reports.exists():
            messages.info(
                self.request,
                'Este colaborador não possui liderados ativos para reatribuir.',
            )
            return HttpResponseRedirect(self.get_success_url())

        try:
            count = reassign_direct_reports(
                from_manager=self.from_manager,
                to_manager=form.cleaned_data['to_manager'],
                actor=self.request.user,
            )
        except ValidationError as exc:
            form.add_error(None, exc)
            return self.form_invalid(form)

        messages.success(
            self.request,
            f'{count} liderado(s) reatribuído(s) com sucesso.',
        )
        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        return reverse(
            'organization:user_update',
            kwargs={'pk': self.from_manager.pk},
        )


class PendingUsersListView(AdminOrganizationMixin, HtmxPaginatedListMixin, ListView):
    """Active users missing area and/or cargo (RF-04.2 / PRD 2.4.4)."""

    model = CustomUser
    template_name = 'organization/user_pending_list.html'
    partial_template_name = 'organization/user_pending_list_partial.html'
    context_object_name = 'users'

    def get_queryset(self):
        return (
            CustomUser.objects.filter(is_active=True)
            .filter(Q(area__isnull=True) | Q(cargo__isnull=True))
            .select_related('area', 'cargo', 'line_manager')
            .order_by('nome', 'email')
        )
