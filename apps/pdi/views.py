from __future__ import annotations

import json

from decimal import ROUND_HALF_UP, Decimal

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Max, Min, Q
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from django.template.loader import render_to_string
from django.urls import reverse
from django.views import View
from django.views.generic import CreateView, DetailView, ListView, UpdateView
from django.views.generic.detail import SingleObjectMixin

from apps.accounts.services.scope import (
    VISAO_EQUIPE,
    VISAO_PROPRIAS,
    apply_ownership_visao,
    can_view_team_ownership_list,
    ownership_visao_equipe_label,
    resolve_ownership_visao,
    user_in_scope,
)
from apps.audit.services import log_scope_denied
from apps.core.htmx import is_htmx
from apps.core.mixins import HtmxPaginatedListMixin, ScopedObjectMixin
from apps.pdi.forms import AcaoPDIForm, PDIForm
from apps.pdi.models import AcaoPDI, PDI
from apps.pdi.services.lifecycle import (
    PDINotArchivableError,
    archive_pdi,
    pdi_allows_action_mutations,
)
from apps.pdi.services.overdue_metrics import annotate_overdue_metrics
from apps.pdi.services.progress import _PROGRESS_QUANT, calculate_pdi_progress

_HUB_FILTER_CHOICES = (
    ('', 'Todos'),
    (PDI.Status.ATIVO, 'Em andamento'),
    (PDI.Status.CONCLUIDO, 'Concluídos'),
    (PDI.Status.ARQUIVADO, 'Arquivados'),
)


def _user_display_name(user) -> str:
    return user.nome or user.email


def _user_initials(user) -> str:
    name = (getattr(user, 'nome', None) or getattr(user, 'email', '') or '').strip()
    if not name:
        return '?'
    parts = name.split()
    if len(parts) >= 2:
        return f'{parts[0][0]}{parts[-1][0]}'.upper()
    return name[:2].upper()


def _progress_from_counts(concluidas: int, total: int) -> Decimal:
    if total == 0:
        return Decimal('0.00')
    return (Decimal(concluidas) * Decimal('100') / Decimal(total)).quantize(
        _PROGRESS_QUANT,
        rounding=ROUND_HALF_UP,
    )


def _hub_card_variant(pdi: PDI, total_acoes: int) -> str:
    if pdi.status == PDI.Status.CONCLUIDO:
        return 'concluido'
    if pdi.status == PDI.Status.ARQUIVADO:
        return 'arquivado'
    if total_acoes == 0:
        return 'aguardando'
    return 'em_andamento'


def _hub_cta_label(variant: str) -> str:
    return {
        'concluido': 'Ver relatório',
        'arquivado': 'Ver',
        'aguardando': 'Iniciar plano',
        'em_andamento': 'Gerenciar',
    }[variant]


def _hub_status_label(variant: str) -> str:
    return {
        'concluido': 'Concluído',
        'arquivado': 'Arquivado',
        'aguardando': 'Aguardando início',
        'em_andamento': 'Em andamento',
    }[variant]


def _hub_footer(pdi: PDI, *, is_self: bool) -> dict:
    """Pessoa de apoio exibida no card — derivada de dados reais, sem lógica na UI."""
    if is_self:
        gestor = getattr(pdi.usuario, 'line_manager', None)
        if gestor is not None:
            return {
                'label': 'Gestor',
                'nome': _user_display_name(gestor),
                'iniciais': _user_initials(gestor),
            }
    return {
        'label': 'Colaborador',
        'nome': _user_display_name(pdi.usuario),
        'iniciais': _user_initials(pdi.usuario),
    }


def _pdi_list_row(pdi: PDI, *, viewer_id: int) -> dict:
    total_acoes = int(getattr(pdi, 'total_acoes', 0) or 0)
    concluidas = int(getattr(pdi, 'acoes_concluidas', 0) or 0)
    progresso = _progress_from_counts(concluidas, total_acoes)
    is_self = pdi.usuario_id == viewer_id
    variant = _hub_card_variant(pdi, total_acoes)
    prazo_min = getattr(pdi, 'prazo_min', None)
    prazo_max = getattr(pdi, 'prazo_max', None)
    return {
        'pdi': pdi,
        'progresso': progresso,
        'progresso_pct': int(progresso),
        'is_self': is_self,
        'total_acoes': total_acoes,
        'acoes_concluidas': concluidas,
        'hub_variant': variant,
        'hub_status_label': _hub_status_label(variant),
        'hub_cta_label': _hub_cta_label(variant),
        'periodo_inicio': prazo_min or pdi.created_at.date(),
        'periodo_fim': prazo_max,
        'footer': _hub_footer(pdi, is_self=is_self),
        'pode_arquivar': pdi.status == PDI.Status.ATIVO,
    }


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


_ARCHIVED_MUTATION_MSG = 'Este PDI está arquivado e não aceita alterações.'


def _htmx_archived_block_response(request, pdi: PDI) -> HttpResponse:
    """Fecha modal (se houver) e avisa; não injeta lista no ``#modal-container``."""
    response = HttpResponse('')
    response['HX-Trigger'] = json.dumps(
        {
            'showMessage': {'message': _ARCHIVED_MUTATION_MSG, 'level': 'error'},
            'closeModal': True,
        },
    )
    return response


def _reject_if_archived(
    request,
    pdi: PDI,
    *,
    redirect_pk: int | None = None,
) -> HttpResponse | None:
    """Bloqueia mutações em PDI arquivado; UI não decide a regra."""
    if pdi_allows_action_mutations(pdi):
        return None
    if is_htmx(request):
        return _htmx_acao_list_response(
            request,
            pdi,
            message=_ARCHIVED_MUTATION_MSG,
            level='error',
            clear_modal=True,
        )
    messages.error(request, _ARCHIVED_MUTATION_MSG)
    return HttpResponseRedirect(
        reverse('pdi:detail', kwargs={'pk': redirect_pk or pdi.pk}),
    )


def _acoes_for_pdi(pdi: PDI):
    return (
        AcaoPDI.objects.filter(pdi_id=pdi.pk)
        .select_related('responsavel')
        .order_by('prazo', 'id')
    )


def _acao_progress_pct(acao: AcaoPDI) -> int:
    """Progresso exibido por ação — derivado do status no backend, não na UI."""
    return {
        AcaoPDI.Status.PENDENTE: 0,
        AcaoPDI.Status.EM_ANDAMENTO: 50,
        AcaoPDI.Status.ATRASADA: 40,
        AcaoPDI.Status.CONCLUIDA: 100,
    }.get(acao.status, 0)


def _acao_card_row(acao: AcaoPDI) -> dict:
    return {
        'acao': acao,
        'progresso_pct': _acao_progress_pct(acao),
        'responsavel_nome': _user_display_name(acao.responsavel),
    }


def _group_acoes(acoes) -> dict:
    """Agrupa ações por coluna do board — regra de negócio no backend."""
    em_andamento: list[dict] = []
    proximas: list[dict] = []
    concluidas: list[dict] = []
    for acao in acoes:
        row = _acao_card_row(acao)
        if acao.status == AcaoPDI.Status.CONCLUIDA:
            concluidas.append(row)
        elif acao.status == AcaoPDI.Status.PENDENTE:
            proximas.append(row)
        else:
            em_andamento.append(row)
    return {
        'acoes_em_andamento': em_andamento,
        'acoes_proximas': proximas,
        'acoes_concluidas': concluidas,
        'total_em_andamento': len(em_andamento),
        'total_acoes': len(em_andamento) + len(proximas) + len(concluidas),
    }


def _acao_list_context(pdi: PDI) -> dict:
    acoes = list(_acoes_for_pdi(pdi))
    return {
        'pdi': pdi,
        'acoes': acoes,
        'progresso': calculate_pdi_progress(pdi),
        'status_choices': AcaoPDI.Status.choices,
        'pode_editar_acoes': pdi_allows_action_mutations(pdi),
        **_group_acoes(acoes),
    }


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
    """Listagem de PDIs no escopo hierárquico do usuário.

    Fatia próprias vs equipe via ``?visao=`` (backend). Escopo base sempre
    via ``ScopedObjectMixin`` / ``get_visible_users``.
    """

    model = PDI
    template_name = 'pdi/pdi_list.html'
    partial_template_name = 'pdi/pdi_list_partial.html'
    context_object_name = 'pdis'
    scope_user_field = 'usuario'
    paginate_by = 6

    def _ownership_visao(self):
        return resolve_ownership_visao(
            self.request.user,
            self.request.GET.get('visao'),
        )

    def get_queryset(self):
        qs = (
            super()
            .get_queryset()
            .select_related(
                'usuario',
                'usuario__area',
                'usuario__cargo',
                'usuario__line_manager',
            )
            .annotate(
                total_acoes=Count('acoes', distinct=True),
                acoes_concluidas=Count(
                    'acoes',
                    filter=Q(acoes__status=AcaoPDI.Status.CONCLUIDA),
                    distinct=True,
                ),
                prazo_min=Min('acoes__prazo'),
                prazo_max=Max('acoes__prazo'),
            )
        )
        qs = annotate_overdue_metrics(qs)
        qs = qs.order_by('usuario__nome', 'usuario__email', '-created_at', 'id')
        qs = apply_ownership_visao(
            qs,
            self.request.user,
            self._ownership_visao(),
            user_field=self.scope_user_field,
        )
        status = self.request.GET.get('status', '').strip()
        if status in {c.value for c in PDI.Status}:
            qs = qs.filter(status=status)
            if status == PDI.Status.ATIVO:
                qs = qs.filter(total_acoes__gt=0)
        busca = self.request.GET.get('q', '').strip()
        if busca:
            qs = qs.filter(
                Q(titulo__icontains=busca)
                | Q(usuario__nome__icontains=busca)
                | Q(usuario__email__icontains=busca),
            )
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        viewer = self.request.user
        viewer_id = viewer.pk
        rows = [_pdi_list_row(pdi, viewer_id=viewer_id) for pdi in context['pdis']]
        status_filtro = self.request.GET.get('status', '').strip()
        busca = self.request.GET.get('q', '').strip()
        visao = self._ownership_visao()
        mostrar_toggle_visao = can_view_team_ownership_list(viewer)
        # Porta vazia só para colaborador puro sem PDIs (líder/admin veem o hub
        # com toggle mesmo sem PDI próprio).
        mostrar_empty_porta = (
            not rows
            and not status_filtro
            and not busca
            and not mostrar_toggle_visao
            and visao == VISAO_PROPRIAS
        )
        context.update(
            {
                'pdi_rows': rows,
                'status_filtro': status_filtro,
                'status_choices': PDI.Status.choices,
                'hub_filter_choices': _HUB_FILTER_CHOICES,
                'busca': busca,
                'pode_criar': True,
                'mostrar_empty_porta': mostrar_empty_porta,
                'visao': visao,
                'mostrar_toggle_visao': mostrar_toggle_visao,
                'visao_equipe_label': ownership_visao_equipe_label(viewer),
                'visao_proprias': VISAO_PROPRIAS,
                'visao_equipe': VISAO_EQUIPE,
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
        return reverse('pdi:list')


class PDIArchiveModalView(LoginRequiredMixin, ScopedObjectMixin, SingleObjectMixin, View):
    """Modal HTMX de confirmação de arquivamento (`#modal-container`)."""

    model = PDI
    scope_user_field = 'usuario'
    queryset = PDI.objects.select_related('usuario')
    http_method_names = ['get', 'head', 'options']

    def get(self, request, *args, **kwargs):
        pdi = self.get_object()
        if pdi.status != PDI.Status.ATIVO:
            if is_htmx(request):
                response = HttpResponse('')
                response['HX-Trigger'] = json.dumps(
                    {
                        'showMessage': {
                            'message': 'Somente planos ativos podem ser arquivados.',
                            'level': 'error',
                        },
                        'closeModal': True,
                    },
                )
                return response
            messages.error(request, 'Somente planos ativos podem ser arquivados.')
            return HttpResponseRedirect(reverse('pdi:list'))
        return render(
            request,
            'pdi/partials/pdi_archive_modal.html',
            {'pdi': pdi},
        )


class PDIArchiveView(LoginRequiredMixin, ScopedObjectMixin, SingleObjectMixin, View):
    """Arquiva PDI no escopo (soft-delete via status). POST only."""

    model = PDI
    scope_user_field = 'usuario'
    queryset = PDI.objects.select_related('usuario')
    http_method_names = ['post', 'options']

    def post(self, request, *args, **kwargs):
        pdi = self.get_object()
        list_url = reverse('pdi:list')
        try:
            archive_pdi(pdi)
        except PDINotArchivableError as exc:
            if is_htmx(request):
                response = HttpResponse('')
                response['HX-Trigger'] = json.dumps(
                    {
                        'showMessage': {'message': str(exc), 'level': 'error'},
                        'closeModal': True,
                    },
                )
                return response
            messages.error(request, str(exc))
            return HttpResponseRedirect(list_url)

        messages.success(
            request,
            'PDI arquivado. Você pode encontrá-lo no filtro Arquivados.',
        )
        if is_htmx(request):
            response = HttpResponse('')
            response['HX-Redirect'] = list_url
            return response
        return HttpResponseRedirect(list_url)


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
        acoes = list(_acoes_for_pdi(pdi))
        context.update(
            {
                'colaborador': pdi.usuario,
                'is_self': pdi.usuario_id == self.request.user.pk,
                'progresso': calculate_pdi_progress(pdi),
                'status_choices': AcaoPDI.Status.choices,
                'pode_editar_acoes': pdi_allows_action_mutations(pdi),
                **_group_acoes(acoes),
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
        if not pdi_allows_action_mutations(pdi):
            if is_htmx(request):
                return _htmx_archived_block_response(request, pdi)
            messages.error(request, _ARCHIVED_MUTATION_MSG)
            return HttpResponseRedirect(reverse('pdi:detail', kwargs={'pk': pdi.pk}))
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
        blocked = _reject_if_archived(request, pdi)
        if blocked is not None:
            return blocked
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
        if not pdi_allows_action_mutations(acao.pdi):
            if is_htmx(request):
                return _htmx_archived_block_response(request, acao.pdi)
            messages.error(request, _ARCHIVED_MUTATION_MSG)
            return HttpResponseRedirect(
                reverse('pdi:detail', kwargs={'pk': acao.pdi_id}),
            )
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

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        blocked = _reject_if_archived(request, self.object.pdi)
        if blocked is not None:
            return blocked
        return super().post(request, *args, **kwargs)

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
        blocked = _reject_if_archived(request, pdi)
        if blocked is not None:
            return blocked
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
        if not pdi_allows_action_mutations(acao.pdi):
            if is_htmx(request):
                return _htmx_acao_list_response(
                    request,
                    acao.pdi,
                    message=_ARCHIVED_MUTATION_MSG,
                    level='error',
                )
            messages.error(request, _ARCHIVED_MUTATION_MSG)
            return HttpResponseRedirect(
                reverse('pdi:detail', kwargs={'pk': acao.pdi_id}),
            )
        new_status = (request.POST.get('status') or '').strip()
        valid = {c.value for c in AcaoPDI.Status}

        if new_status not in valid:
            if is_htmx(request):
                return _htmx_acao_list_response(
                    request,
                    acao.pdi,
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
            return _htmx_acao_list_response(
                request,
                acao.pdi,
                message='Status da ação atualizado.',
            )
        messages.success(request, 'Status da ação atualizado.')
        return HttpResponseRedirect(
            reverse('pdi:detail', kwargs={'pk': acao.pdi_id}),
        )
