from django.contrib import messages
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse, reverse_lazy
from django.utils.http import url_has_allowed_host_and_scheme
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
from apps.organization.services.area_list import (
    STATUS_SEGMENT_OPTIONS as AREA_STATUS_SEGMENT_OPTIONS,
    apply_area_list_filters,
    build_hierarchical_area_rows,
    get_allowed_parent_area_ids,
    get_base_area_list_queryset,
    get_parent_filter_options,
    parse_search_filter as parse_area_search_filter,
    parse_status_filter as parse_area_status_filter,
    resolve_parent_filter,
)
from apps.organization.services.cargo_list import (
    apply_cargo_list_filters,
    get_allowed_nivel_values,
    get_base_cargo_list_queryset,
    get_nivel_filter_options_for_queryset,
    parse_nivel_filter,
    resolve_nivel_filter,
)
from apps.organization.services.navigation import resolve_admin_list_return_url
from apps.organization.services.user_list import (
    apply_pending_user_list_filters,
    apply_user_list_filters,
    get_area_filter_options,
    get_base_pending_user_list_queryset,
    get_base_user_list_queryset,
    get_allowed_area_ids,
    get_allowed_cargo_ids,
    get_allowed_manager_ids,
    get_cargo_filter_options,
    get_manager_filter_options,
    parse_int_filter,
    parse_pendencia_filter,
    parse_search_filter,
    parse_status_filter,
    resolve_id_filter,
    PENDENCIA_SEGMENT_OPTIONS,
    STATUS_SEGMENT_OPTIONS,
)
from apps.reviews.services.guidance import (
    KIND_CARGO_MISSING_COMPETENCIES,
    build_rh_pre_open_checklist,
)


class AdminOrganizationMixin(LoginRequiredMixin, RequiresAdminMixin):
    """Auth + admin gate for organization management views."""


class AreaListView(AdminOrganizationMixin, HtmxPaginatedListMixin, ListView):
    model = Area
    template_name = 'organization/area_list.html'
    partial_template_name = 'organization/area_list_partial.html'
    context_object_name = 'area_rows'

    def _parsed_filters(self):
        base_qs = get_base_area_list_queryset()
        status = parse_area_status_filter(self.request.GET.get('status'))
        busca = parse_area_search_filter(self.request.GET.get('busca'))
        parent_id = resolve_parent_filter(
            parse_int_filter(self.request.GET.get('parent')),
            get_allowed_parent_area_ids(base_qs),
        )
        return base_qs, status, busca, parent_id

    def get_queryset(self):
        base_qs, status, busca, parent_id = self._parsed_filters()
        return apply_area_list_filters(
            base_qs,
            status=status,
            busca=busca,
            parent_id=parent_id,
        )

    def paginate_queryset(self, queryset, page_size):
        rows = build_hierarchical_area_rows(queryset)
        paginator = Paginator(rows, page_size)
        page_kwarg = self.page_kwarg
        page = self.request.GET.get(page_kwarg) or 1
        try:
            page_obj = paginator.page(page)
        except PageNotAnInteger:
            page_obj = paginator.page(1)
        except EmptyPage:
            page_obj = paginator.page(paginator.num_pages)
        return (paginator, page_obj, page_obj.object_list, page_obj.has_other_pages())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        base_qs, status, busca, parent_id = self._parsed_filters()
        context.update(
            {
                'list_url': reverse('organization:area_list'),
                'status_segment_options': AREA_STATUS_SEGMENT_OPTIONS,
                'filtro_status': status,
                'filtro_busca': busca,
                'filtro_parent_id': parent_id,
                'filtro_ativo': bool(busca or status or parent_id),
                'filtro_avancado_ativo': bool(parent_id),
                'filtro_avancado_count': 1 if parent_id else 0,
                'parent_options': get_parent_filter_options(base_qs),
            },
        )
        return context


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

    def get_success_url(self):
        return resolve_admin_list_return_url(
            self.request,
            default=str(self.success_url),
        )


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

    def get_success_url(self):
        return resolve_admin_list_return_url(
            self.request,
            default=str(self.success_url),
        )


class CargoListView(AdminOrganizationMixin, HtmxPaginatedListMixin, ListView):
    model = Cargo
    template_name = 'organization/cargo_list.html'
    partial_template_name = 'organization/cargo_list_partial.html'
    context_object_name = 'cargos'

    def _parsed_filters(self):
        base_qs = get_base_cargo_list_queryset()
        status = parse_status_filter(self.request.GET.get('status'))
        busca = parse_search_filter(self.request.GET.get('busca'))
        nivel = resolve_nivel_filter(
            parse_nivel_filter(self.request.GET.get('nivel')),
            get_allowed_nivel_values(base_qs),
        )
        return base_qs, status, busca, nivel

    def get_queryset(self):
        base_qs, status, busca, nivel = self._parsed_filters()
        return apply_cargo_list_filters(
            base_qs,
            status=status,
            busca=busca,
            nivel=nivel,
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        base_qs, status, busca, nivel = self._parsed_filters()
        context.update(
            {
                'list_url': reverse('organization:cargo_list'),
                'status_segment_options': STATUS_SEGMENT_OPTIONS,
                'filtro_status': status,
                'filtro_busca': busca,
                'filtro_nivel': nivel,
                'filtro_ativo': bool(busca or status or nivel),
                'filtro_avancado_ativo': bool(nivel),
                'filtro_avancado_count': 1 if nivel else 0,
                'nivel_options': get_nivel_filter_options_for_queryset(base_qs),
            },
        )
        return context


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

    def get_success_url(self):
        return resolve_admin_list_return_url(
            self.request,
            default=str(self.success_url),
        )


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

    def get_success_url(self):
        return resolve_admin_list_return_url(
            self.request,
            default=str(self.success_url),
        )


class UserListView(AdminOrganizationMixin, HtmxPaginatedListMixin, ListView):
    model = CustomUser
    template_name = 'organization/user_list.html'
    partial_template_name = 'organization/user_list_partial.html'
    context_object_name = 'users'

    def get_queryset(self):
        base_qs = get_base_user_list_queryset()
        status = parse_status_filter(self.request.GET.get('status'))
        busca = parse_search_filter(self.request.GET.get('busca'))
        area_id = resolve_id_filter(
            parse_int_filter(self.request.GET.get('area')),
            get_allowed_area_ids(base_qs),
        )
        gestor_id = resolve_id_filter(
            parse_int_filter(self.request.GET.get('gestor')),
            get_allowed_manager_ids(base_qs),
        )
        cargo_id = resolve_id_filter(
            parse_int_filter(self.request.GET.get('cargo')),
            get_allowed_cargo_ids(base_qs),
        )
        return apply_user_list_filters(
            base_qs,
            status=status,
            busca=busca,
            area_id=area_id,
            gestor_id=gestor_id,
            cargo_id=cargo_id,
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        base_qs = get_base_user_list_queryset()
        status = parse_status_filter(self.request.GET.get('status'))
        busca = parse_search_filter(self.request.GET.get('busca'))
        area_id = resolve_id_filter(
            parse_int_filter(self.request.GET.get('area')),
            get_allowed_area_ids(base_qs),
        )
        gestor_id = resolve_id_filter(
            parse_int_filter(self.request.GET.get('gestor')),
            get_allowed_manager_ids(base_qs),
        )
        cargo_id = resolve_id_filter(
            parse_int_filter(self.request.GET.get('cargo')),
            get_allowed_cargo_ids(base_qs),
        )
        context.update(
            {
                'list_url': reverse('organization:user_list'),
                'status_segment_options': STATUS_SEGMENT_OPTIONS,
                'filtro_status': status,
                'filtro_busca': busca,
                'filtro_area_id': area_id,
                'filtro_gestor_id': gestor_id,
                'filtro_cargo_id': cargo_id,
                'filtro_ativo': bool(
                    busca or status or area_id or gestor_id or cargo_id,
                ),
                'filtro_avancado_ativo': bool(area_id or gestor_id or cargo_id),
                'filtro_avancado_count': sum(
                    1 for value in (area_id, gestor_id, cargo_id) if value
                ),
                'area_options': get_area_filter_options(base_qs),
                'gestor_options': get_manager_filter_options(base_qs),
                'cargo_options': get_cargo_filter_options(base_qs),
            },
        )
        return context


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
        return self._resolve_user_update_return_url()

    def _resolve_user_update_return_url(self) -> str:
        next_url = self.request.POST.get('next') or self.request.GET.get('next')
        if next_url == 'pending':
            return reverse('organization:user_pending')
        if (
            next_url
            and url_has_allowed_host_and_scheme(
                url=next_url,
                allowed_hosts={self.request.get_host()},
                require_https=self.request.is_secure(),
            )
        ):
            return next_url
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
        base_qs = get_base_pending_user_list_queryset()
        pendencia = parse_pendencia_filter(self.request.GET.get('pendencia'))
        busca = parse_search_filter(self.request.GET.get('busca'))
        area_id = resolve_id_filter(
            parse_int_filter(self.request.GET.get('area')),
            get_allowed_area_ids(base_qs),
        )
        gestor_id = resolve_id_filter(
            parse_int_filter(self.request.GET.get('gestor')),
            get_allowed_manager_ids(base_qs),
        )
        cargo_id = resolve_id_filter(
            parse_int_filter(self.request.GET.get('cargo')),
            get_allowed_cargo_ids(base_qs),
        )
        return apply_pending_user_list_filters(
            base_qs,
            pendencia=pendencia,
            busca=busca,
            area_id=area_id,
            gestor_id=gestor_id,
            cargo_id=cargo_id,
        )

    def get_context_data(self, **kwargs):
        """Contexto avisório do checklist RH (FR-011) — só apresentação.

        Não condiciona abertura de ciclo; reforça links de correção e
        contexto pré-abertura nesta superfície de vínculos pendentes.
        """
        context = super().get_context_data(**kwargs)
        base_qs = get_base_pending_user_list_queryset()
        pendencia = parse_pendencia_filter(self.request.GET.get('pendencia'))
        busca = parse_search_filter(self.request.GET.get('busca'))
        area_id = resolve_id_filter(
            parse_int_filter(self.request.GET.get('area')),
            get_allowed_area_ids(base_qs),
        )
        gestor_id = resolve_id_filter(
            parse_int_filter(self.request.GET.get('gestor')),
            get_allowed_manager_ids(base_qs),
        )
        cargo_id = resolve_id_filter(
            parse_int_filter(self.request.GET.get('cargo')),
            get_allowed_cargo_ids(base_qs),
        )
        checklist = build_rh_pre_open_checklist()
        context['rh_pre_open_checklist'] = checklist
        context['rh_checklist_has_blockers'] = checklist.has_blockers
        context['rh_has_cargo_blockers'] = any(
            item.kind == KIND_CARGO_MISSING_COMPETENCIES
            for item in checklist.items
        )
        context.update(
            {
                'list_url': reverse('organization:user_pending'),
                'pendencia_segment_options': PENDENCIA_SEGMENT_OPTIONS,
                'filtro_pendencia': pendencia,
                'filtro_busca': busca,
                'filtro_area_id': area_id,
                'filtro_gestor_id': gestor_id,
                'filtro_cargo_id': cargo_id,
                'filtro_ativo': bool(
                    busca or pendencia or area_id or gestor_id or cargo_id,
                ),
                'filtro_avancado_ativo': bool(area_id or gestor_id or cargo_id),
                'filtro_avancado_count': sum(
                    1 for value in (area_id, gestor_id, cargo_id) if value
                ),
                'area_options': get_area_filter_options(base_qs),
                'gestor_options': get_manager_filter_options(base_qs),
                'cargo_options': get_cargo_filter_options(base_qs),
            },
        )
        return context
