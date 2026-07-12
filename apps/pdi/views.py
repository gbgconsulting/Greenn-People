from __future__ import annotations

import json

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from django.template.loader import render_to_string
from django.urls import reverse
from django.views import View
from django.views.generic import CreateView, DetailView, ListView, UpdateView
from django.views.generic.detail import SingleObjectMixin

from apps.accounts.services.scope import user_in_scope
from apps.audit.services import log_scope_denied
from apps.core.htmx import is_htmx
from apps.core.mixins import HtmxPaginatedListMixin, ScopedObjectMixin
from apps.pdi.forms import AcaoPDIForm, PDIForm
from apps.pdi.models import AcaoPDI, PDI
from apps.pdi.services.progress import calculate_pdi_progress


def _get_scoped_pdi(request, pk: int) -> PDI:
    """Retorna PDI no escopo; IDOR → Http404 + ``log_scope_denied``."""
    try:
        pdi = PDI.objects.select_related('usuario').get(pk=pk)
    except PDI.DoesNotExist as exc:
        raise Http404() from exc
    if not user_in_scope(request.user, pdi.usuario_id):
        log_scope_denied(request.user, pdi)
        raise Http404()
    return pdi


def _acoes_for_pdi(pdi: PDI):
    return (
        AcaoPDI.objects.filter(pdi_id=pdi.pk)
        .select_related('responsavel')
        .order_by('prazo', 'id')
    )


def _acao_list_context(pdi: PDI) -> dict:
    return {
        'pdi': pdi,
        'acoes': _acoes_for_pdi(pdi),
        'progresso': calculate_pdi_progress(pdi),
        'status_choices': AcaoPDI.Status.choices,
    }


def _acao_row_context(acao: AcaoPDI) -> dict:
    return {
        'acao': acao,
        'status_choices': AcaoPDI.Status.choices,
    }


def _htmx_acao_row_response(
    request,
    acao: AcaoPDI,
    *,
    message: str | None = None,
    level: str = 'success',
) -> HttpResponse:
    html = render_to_string(
        'pdi/partials/acao_row.html',
        _acao_row_context(acao),
        request=request,
    )
    response = HttpResponse(html)
    if message:
        response['HX-Trigger'] = json.dumps(
            {'showMessage': {'message': message, 'level': level}},
        )
    return response


def _htmx_acao_list_response(
    request,
    pdi: PDI,
    *,
    message: str | None = None,
    level: str = 'success',
    clear_modal: bool = False,
) -> HttpResponse:
    html = render_to_string(
        'pdi/acao_list_partial.html',
        _acao_list_context(pdi),
        request=request,
    )
    response = HttpResponse(html)
    triggers: dict = {}
    if message:
        triggers['showMessage'] = {'message': message, 'level': level}
    if clear_modal:
        triggers['closeModal'] = True
    if triggers:
        response['HX-Trigger'] = json.dumps(triggers)
    return response


def _htmx_modal_form_response(
    request,
    template_name: str,
    context: dict,
) -> HttpResponse:
    """Re-renderiza o modal com erros; retarget para ``#modal-container``."""
    response = render(request, template_name, context)
    response['HX-Retarget'] = '#modal-container'
    response['HX-Reswap'] = 'innerHTML'
    return response


class PDIListView(LoginRequiredMixin, ScopedObjectMixin, HtmxPaginatedListMixin, ListView):
    """Listagem de PDIs no escopo hierárquico do usuário."""

    model = PDI
    template_name = 'pdi/pdi_list.html'
    partial_template_name = 'pdi/pdi_list_partial.html'
    context_object_name = 'pdis'
    scope_user_field = 'usuario'

    def get_queryset(self):
        qs = (
            super()
            .get_queryset()
            .select_related('usuario', 'usuario__area', 'usuario__cargo')
            .order_by('usuario__nome', 'usuario__email', '-created_at', 'id')
        )
        status = self.request.GET.get('status', '').strip()
        if status in {c.value for c in PDI.Status}:
            qs = qs.filter(status=status)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        rows = []
        for pdi in context['pdis']:
            rows.append(
                {
                    'pdi': pdi,
                    'progresso': calculate_pdi_progress(pdi),
                    'is_self': pdi.usuario_id == self.request.user.pk,
                },
            )
        context.update(
            {
                'pdi_rows': rows,
                'status_filtro': self.request.GET.get('status', '').strip(),
                'status_choices': PDI.Status.choices,
                'pode_criar': True,
            },
        )
        return context


class PDICreateView(LoginRequiredMixin, ScopedObjectMixin, CreateView):
    """Cadastro de PDI para o próprio usuário ou colaborador no escopo."""

    model = PDI
    form_class = PDIForm
    template_name = 'pdi/pdi_form.html'
    scope_user_field = 'usuario'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context['mostrar_usuario'] = bool(
            getattr(user, 'is_leader', False)
            or getattr(user, 'is_manager', False)
            or getattr(user, 'is_admin', False),
        )
        return context

    def form_valid(self, form):
        messages.success(self.request, 'PDI criado com sucesso.')
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('pdi:detail', kwargs={'pk': self.object.pk})


class PDIDetailView(LoginRequiredMixin, ScopedObjectMixin, DetailView):
    """Detalhe do PDI no escopo; IDOR → Http404 + ``log_scope_denied``."""

    model = PDI
    template_name = 'pdi/pdi_detail.html'
    context_object_name = 'pdi'
    scope_user_field = 'usuario'
    queryset = PDI.objects.select_related(
        'usuario',
        'usuario__area',
        'usuario__cargo',
        'usuario__line_manager',
    )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        pdi = self.object
        context.update(
            {
                'colaborador': pdi.usuario,
                'is_self': pdi.usuario_id == self.request.user.pk,
                'progresso': calculate_pdi_progress(pdi),
                'acoes': _acoes_for_pdi(pdi),
                'status_choices': AcaoPDI.Status.choices,
            },
        )
        return context


class AcaoPDIPartialListView(LoginRequiredMixin, View):
    """Partial HTMX da lista de ações (`#acao-list`)."""

    http_method_names = ['get', 'head', 'options']

    def get(self, request, pk):
        pdi = _get_scoped_pdi(request, pk)
        return render(request, 'pdi/acao_list_partial.html', _acao_list_context(pdi))


class AcaoPDICreateModalView(LoginRequiredMixin, View):
    """Modal HTMX de criação de ação (`#modal-container`)."""

    http_method_names = ['get', 'head', 'options']

    def get(self, request, pk):
        pdi = _get_scoped_pdi(request, pk)
        form = AcaoPDIForm(user=request.user, pdi=pdi)
        return render(
            request,
            'pdi/partials/acao_create_modal.html',
            {'form': form, 'pdi': pdi},
        )


class AcaoPDICreateView(LoginRequiredMixin, View):
    """Cria ação de PDI; em HTMX retorna ``acao_list_partial.html``."""

    http_method_names = ['post', 'options']

    def post(self, request, pk):
        pdi = _get_scoped_pdi(request, pk)
        form = AcaoPDIForm(request.POST, user=request.user, pdi=pdi)
        if form.is_valid():
            acao = form.save(commit=False)
            acao.pdi = pdi
            acao.status = AcaoPDI.Status.PENDENTE
            acao.save()
            if is_htmx(request):
                return _htmx_acao_list_response(
                    request,
                    pdi,
                    message='Ação criada com sucesso.',
                    clear_modal=True,
                )
            messages.success(request, 'Ação criada com sucesso.')
            return HttpResponseRedirect(reverse('pdi:detail', kwargs={'pk': pdi.pk}))

        if is_htmx(request):
            return _htmx_modal_form_response(
                request,
                'pdi/partials/acao_create_modal.html',
                {'form': form, 'pdi': pdi},
            )
        messages.error(request, 'Não foi possível criar a ação. Verifique os campos.')
        return HttpResponseRedirect(reverse('pdi:detail', kwargs={'pk': pdi.pk}))


class AcaoPDIUpdateModalView(LoginRequiredMixin, ScopedObjectMixin, SingleObjectMixin, View):
    """Modal HTMX de edição de ação."""

    model = AcaoPDI
    scope_user_field = 'pdi__usuario'
    queryset = AcaoPDI.objects.select_related('pdi', 'pdi__usuario', 'responsavel')
    http_method_names = ['get', 'head', 'options']

    def get(self, request, *args, **kwargs):
        acao = self.get_object()
        form = AcaoPDIForm(
            instance=acao,
            user=request.user,
            pdi=acao.pdi,
        )
        return render(
            request,
            'pdi/partials/acao_edit_modal.html',
            {'form': form, 'acao': acao, 'pdi': acao.pdi},
        )


class AcaoPDIUpdateView(LoginRequiredMixin, ScopedObjectMixin, UpdateView):
    """Atualiza descrição/responsável/prazo; HTMX → lista de ações."""

    model = AcaoPDI
    form_class = AcaoPDIForm
    scope_user_field = 'pdi__usuario'
    queryset = AcaoPDI.objects.select_related('pdi', 'pdi__usuario', 'responsavel')
    http_method_names = ['post', 'options']

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        kwargs['pdi'] = self.object.pdi
        return kwargs

    def form_valid(self, form):
        self.object = form.save()
        pdi = self.object.pdi
        if is_htmx(self.request):
            return _htmx_acao_list_response(
                self.request,
                pdi,
                message='Ação atualizada com sucesso.',
                clear_modal=True,
            )
        messages.success(self.request, 'Ação atualizada com sucesso.')
        return HttpResponseRedirect(reverse('pdi:detail', kwargs={'pk': pdi.pk}))

    def form_invalid(self, form):
        if is_htmx(self.request):
            return _htmx_modal_form_response(
                self.request,
                'pdi/partials/acao_edit_modal.html',
                {'form': form, 'acao': self.object, 'pdi': self.object.pdi},
            )
        messages.error(
            self.request,
            'Não foi possível atualizar a ação. Verifique os campos.',
        )
        return HttpResponseRedirect(
            reverse('pdi:detail', kwargs={'pk': self.object.pdi_id}),
        )


class AcaoPDIDeleteView(LoginRequiredMixin, ScopedObjectMixin, SingleObjectMixin, View):
    """Exclui ação de PDI; HTMX → lista de ações."""

    model = AcaoPDI
    scope_user_field = 'pdi__usuario'
    queryset = AcaoPDI.objects.select_related('pdi', 'pdi__usuario')
    http_method_names = ['post', 'options']

    def post(self, request, *args, **kwargs):
        acao = self.get_object()
        pdi = acao.pdi
        acao.delete()
        if is_htmx(request):
            return _htmx_acao_list_response(
                request,
                pdi,
                message='Ação removida com sucesso.',
            )
        messages.success(request, 'Ação removida com sucesso.')
        return HttpResponseRedirect(reverse('pdi:detail', kwargs={'pk': pdi.pk}))


class AcaoPDIStatusUpdateView(LoginRequiredMixin, ScopedObjectMixin, SingleObjectMixin, View):
    """Atualiza status inline da ação (HTMX); persiste ``updated_at`` e auditoria."""

    model = AcaoPDI
    scope_user_field = 'pdi__usuario'
    queryset = AcaoPDI.objects.select_related(
        'pdi',
        'pdi__usuario',
        'responsavel',
    )
    http_method_names = ['post', 'options']

    def post(self, request, *args, **kwargs):
        acao = self.get_object()
        new_status = (request.POST.get('status') or '').strip()
        valid = {c.value for c in AcaoPDI.Status}

        if new_status not in valid:
            if is_htmx(request):
                return _htmx_acao_row_response(
                    request,
                    acao,
                    message='Status inválido.',
                    level='error',
                )
            messages.error(request, 'Status inválido.')
            return HttpResponseRedirect(
                reverse('pdi:detail', kwargs={'pk': acao.pdi_id}),
            )

        if acao.status != new_status:
            acao.status = new_status
            # ``updated_at`` (auto_now) só atualiza se incluído em update_fields.
            acao.save(update_fields=['status', 'updated_at'])

        if is_htmx(request):
            return _htmx_acao_row_response(
                request,
                acao,
                message='Status da ação atualizado.',
            )
        messages.success(request, 'Status da ação atualizado.')
        return HttpResponseRedirect(
            reverse('pdi:detail', kwargs={'pk': acao.pdi_id}),
        )
