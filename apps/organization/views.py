from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.db.models.deletion import ProtectedError
from django.http import HttpResponseRedirect
from django.urls import reverse, reverse_lazy
from django.views.generic import (
    CreateView,
    DeleteView,
    ListView,
    UpdateView,
)

from apps.accounts.models import CustomUser
from apps.core.mixins import RequiresAdminMixin
from apps.organization.forms import AreaForm, CargoForm, UserUpdateForm
from apps.organization.models import Area, Cargo


class AdminOrganizationMixin(LoginRequiredMixin, RequiresAdminMixin):
    """Auth + admin gate for organization management views."""


class AreaListView(AdminOrganizationMixin, ListView):
    model = Area
    template_name = 'organization/area_list.html'
    context_object_name = 'areas'
    paginate_by = 20

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
    model = Area
    template_name = 'organization/area_confirm_delete.html'
    success_url = reverse_lazy('organization:area_list')

    def form_valid(self, form):
        try:
            response = super().form_valid(form)
        except ProtectedError:
            messages.error(
                self.request,
                'Não é possível excluir esta área: ela possui vínculos '
                '(subáreas ou usuários). Desative-a ou remova os vínculos.',
            )
            return HttpResponseRedirect(self.success_url)
        messages.success(self.request, 'Área excluída com sucesso.')
        return response


class CargoListView(AdminOrganizationMixin, ListView):
    model = Cargo
    template_name = 'organization/cargo_list.html'
    context_object_name = 'cargos'
    paginate_by = 20

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
    model = Cargo
    template_name = 'organization/cargo_confirm_delete.html'
    success_url = reverse_lazy('organization:cargo_list')

    def form_valid(self, form):
        try:
            response = super().form_valid(form)
        except ProtectedError:
            messages.error(
                self.request,
                'Não é possível excluir este cargo: há usuários vinculados. '
                'Desative-o ou reatribua os colaboradores.',
            )
            return HttpResponseRedirect(self.success_url)
        messages.success(self.request, 'Cargo excluído com sucesso.')
        return response


class UserListView(AdminOrganizationMixin, ListView):
    model = CustomUser
    template_name = 'organization/user_list.html'
    context_object_name = 'users'
    paginate_by = 20

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

    def form_valid(self, form):
        messages.success(self.request, 'Usuário atualizado com sucesso.')
        return super().form_valid(form)

    def get_success_url(self):
        next_url = self.request.GET.get('next')
        if next_url == 'pending':
            return reverse('organization:user_pending')
        return str(self.success_url)


class PendingUsersListView(AdminOrganizationMixin, ListView):
    """Active users missing area and/or cargo (RF-04.2 / PRD 2.4.4)."""

    model = CustomUser
    template_name = 'organization/user_pending_list.html'
    context_object_name = 'users'
    paginate_by = 20

    def get_queryset(self):
        return (
            CustomUser.objects.filter(is_active=True)
            .filter(Q(area__isnull=True) | Q(cargo__isnull=True))
            .select_related('area', 'cargo', 'line_manager')
            .order_by('nome', 'email')
        )
