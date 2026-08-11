import json

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.template.loader import render_to_string
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.generic import (
    CreateView,
    DeleteView,
    ListView,
    TemplateView,
    UpdateView,
)
from django.views.generic.detail import SingleObjectMixin

from apps.audit.context import audit_actor
from apps.audit.services import log_scope_denied
from apps.core.htmx import is_htmx
from apps.core.mixins import HtmxPaginatedListMixin, ScopedObjectMixin
from apps.cycles.services.stage import can_advance
from apps.goals.forms import (
    MetaForm,
    MetaProgressForm,
    get_avaliacao_for_user,
    get_open_ciclo,
    meta_approval_actionable,
    meta_content_editable,
    meta_progress_editable,
)
from apps.goals.models import Meta
from apps.goals.services.approval import (
    approve_meta,
    approve_resultado,
    reject_meta,
    reject_resultado,
)
from apps.reviews.models import Avaliacao
from apps.reviews.services.evaluation import build_fr005_context

_COLLABORATOR_ADVANCE_ETAPAS = frozenset(
    {
        Avaliacao.Etapa.INPUT_METAS,
        Avaliacao.Etapa.RESULTADOS,
    },
)


def _proximo_passo_pos_reprovacao(avaliacao, meta, *, is_owner, pode_progresso):
    """Hint + rótulos de CTA quando o item está reprovado (FR-007 / T021).

    Fonte de verdade da copy pós-reprovação em listagem, form e partials de metas.
    Não altera predicados de aprovação/elegibilidade.
    """
    defaults = {
        'item_reprovado': False,
        'proximo_passo_hint': '',
        'rotulo_editar': 'Editar',
        'rotulo_salvar_progresso': 'Salvar',
        'rotulo_aprovar': 'Aprovar',
        'mostrar_link_editar': True,
    }
    if avaliacao is None:
        return defaults

    if (
        avaliacao.etapa == Avaliacao.Etapa.APROVACAO_METAS
        and meta.status == Meta.Status.REPROVADA
    ):
        if is_owner and meta_content_editable(avaliacao, meta):
            return {
                **defaults,
                'item_reprovado': True,
                'proximo_passo_hint': (
                    'Corrija a meta e salve para reenviar à aprovação.'
                ),
                'rotulo_editar': 'Corrigir',
            }
        return {
            **defaults,
            'item_reprovado': True,
            'mostrar_link_editar': False,
            'proximo_passo_hint': (
                'Aguardando o colaborador corrigir esta meta para reaprovação.'
            ),
        }

    if (
        avaliacao.etapa == Avaliacao.Etapa.APROVACAO_RESULTADOS
        and meta.status_resultado == Meta.StatusResultado.REPROVADO
    ):
        if is_owner and pode_progresso:
            return {
                **defaults,
                'item_reprovado': True,
                'mostrar_link_editar': False,
                'proximo_passo_hint': (
                    'Ajuste o progresso e clique em «Corrigir e reenviar».'
                ),
                'rotulo_salvar_progresso': 'Corrigir e reenviar',
            }
        return {
            **defaults,
            'item_reprovado': True,
            'mostrar_link_editar': False,
            'proximo_passo_hint': (
                'Aguardando o colaborador corrigir o resultado para reaprovação.'
            ),
        }

    return defaults


def _meta_row_context(request, meta, progress_form=None):
    """Contexto compartilhado do partial `#meta-row-<pk>`."""
    avaliacao = get_avaliacao_for_user(meta.usuario)
    is_owner = meta.usuario_id == request.user.pk
    pode_progresso = is_owner and meta_progress_editable(avaliacao, meta)
    if progress_form is None and pode_progresso:
        progress_form = MetaProgressForm(instance=meta)

    cta = _proximo_passo_pos_reprovacao(
        avaliacao,
        meta,
        is_owner=is_owner,
        pode_progresso=pode_progresso,
    )
    return {
        'meta': meta,
        'pode_editar_conteudo': meta_content_editable(avaliacao, meta),
        'pode_atualizar_progresso': pode_progresso,
        'pode_aprovar': meta_approval_actionable(avaliacao, meta, request.user),
        'progress_form': progress_form if pode_progresso else None,
        'badge_status': (
            meta.status_resultado
            if avaliacao is not None
            and avaliacao.etapa == Avaliacao.Etapa.APROVACAO_RESULTADOS
            else meta.status
        ),
        'badge_label': (
            meta.get_status_resultado_display()
            if avaliacao is not None
            and avaliacao.etapa == Avaliacao.Etapa.APROVACAO_RESULTADOS
            else meta.get_status_display()
        ),
        **cta,
    }


def _apply_meta_approval(meta, approver, *, approve: bool) -> Meta:
    """Aprova ou reprova meta/resultado conforme a etapa da avaliação.

    Rejeita item já decidido ou etapa inelegível sem gravar AuditLog de sucesso
    (FR-014/FR-015 / ``contracts/admin-approval-contract.md``). O ator do
    AuditLog é o aprovador autenticado via ``audit_actor``.
    """
    avaliacao = get_avaliacao_for_user(meta.usuario)
    if avaliacao is None:
        raise PermissionDenied(
            'Não há avaliação em ciclo aberto para este colaborador.',
        )

    # UI e POST devem alinhar: só pendente na etapa correta (evita sucesso falso).
    if not meta_approval_actionable(avaliacao, meta, approver):
        raise PermissionDenied(
            'Não é possível aprovar ou reprovar: item já decidido '
            'ou etapa inelegível.',
        )

    with audit_actor(approver):
        if avaliacao.etapa == Avaliacao.Etapa.APROVACAO_METAS:
            return (
                approve_meta(meta, approver)
                if approve
                else reject_meta(meta, approver)
            )

        if avaliacao.etapa == Avaliacao.Etapa.APROVACAO_RESULTADOS:
            if approve:
                return approve_resultado(meta, approver)
            return reject_resultado(meta, approver)

    raise PermissionDenied(
        'Aprovação só é permitida nas etapas de aprovação de metas ou resultados.',
    )


def _htmx_meta_row_response(
    request,
    meta,
    progress_form=None,
    message=None,
    level='success',
):
    context = _meta_row_context(request, meta, progress_form=progress_form)
    html = render_to_string(
        'goals/partials/meta_row.html',
        context,
        request=request,
    )
    response = HttpResponse(html)
    if message:
        response['HX-Trigger'] = json.dumps(
            {
                'showMessage': {
                    'message': message,
                    'level': level,
                },
            },
        )
    return response


class ExpectationsView(LoginRequiredMixin, TemplateView):
    """Pagina de expectativas do colaborador (FR-001, FR-002, FR-005)."""

    template_name = 'goals/expectations.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        fr005 = build_fr005_context(user)
        ciclo_aberto = fr005['ciclo_aberto']

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

        context.update(fr005)
        context['metas'] = metas
        return context


class MetaListView(LoginRequiredMixin, ScopedObjectMixin, HtmxPaginatedListMixin, ListView):
    """Listagem de metas no escopo do usuário, com filtro por status."""

    model = Meta
    template_name = 'goals/meta_list.html'
    partial_template_name = 'goals/meta_list_partial.html'
    context_object_name = 'metas'
    scope_user_field = 'usuario'

    def get_queryset(self):
        qs = (
            super()
            .get_queryset()
            .select_related(
                'usuario',
                'objetivo_estrategico',
                'objetivo_estrategico__ciclo',
            )
            .order_by('objetivo_estrategico_id', 'id')
        )
        ciclo = get_open_ciclo()
        if ciclo is not None:
            qs = qs.filter(objetivo_estrategico__ciclo=ciclo)

        status = self.request.GET.get('status', '').strip()
        if status in {c.value for c in Meta.Status}:
            qs = qs.filter(status=status)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        ciclo = get_open_ciclo()
        avaliacao = get_avaliacao_for_user(self.request.user, ciclo)

        meta_rows = [
            _meta_row_context(self.request, meta) for meta in context['metas']
        ]

        # FR-007: resumo de página reutiliza o mesmo hint do helper (sem copy paralela).
        proximo_passo_lista_hint = ''
        for row in meta_rows:
            if not row.get('item_reprovado') or not row.get('proximo_passo_hint'):
                continue
            if row.get('mostrar_link_editar') or row.get('pode_atualizar_progresso'):
                proximo_passo_lista_hint = row['proximo_passo_hint']
                break
            if not proximo_passo_lista_hint:
                proximo_passo_lista_hint = row['proximo_passo_hint']

        pode_avancar = False
        rotulo_avanco = ''
        motivo_bloqueio_avanco = ''
        avaliacao_pk = None
        if (
            avaliacao is not None
            and avaliacao.usuario_id == self.request.user.pk
            and avaliacao.etapa in _COLLABORATOR_ADVANCE_ETAPAS
        ):
            avaliacao_pk = avaliacao.pk
            ok, motivo = can_advance(avaliacao)
            pode_avancar = ok
            motivo_bloqueio_avanco = '' if ok else motivo
            if avaliacao.etapa == Avaliacao.Etapa.INPUT_METAS:
                rotulo_avanco = 'Enviar metas para aprovação'
            else:
                rotulo_avanco = 'Enviar resultados para aprovação'

        context.update(
            {
                'ciclo_aberto': ciclo,
                'status_filtro': self.request.GET.get('status', '').strip(),
                'status_choices': Meta.Status.choices,
                'pode_criar': meta_content_editable(avaliacao, meta=None)
                and avaliacao is not None
                and avaliacao.etapa == avaliacao.Etapa.INPUT_METAS,
                'meta_rows': meta_rows,
                'proximo_passo_lista_hint': proximo_passo_lista_hint,
                'avaliacao_pk': avaliacao_pk,
                'pode_avancar': pode_avancar,
                'avanco_desabilitado': not pode_avancar,
                'rotulo_avanco': rotulo_avanco,
                'motivo_bloqueio_avanco': motivo_bloqueio_avanco,
            },
        )
        return context


class MetaCreateView(LoginRequiredMixin, CreateView):
    """Cadastro de meta pelo colaborador (etapa input_metas)."""

    model = Meta
    form_class = MetaForm
    template_name = 'goals/meta_form.html'
    success_url = reverse_lazy('goals:meta_list')

    def dispatch(self, request, *args, **kwargs):
        avaliacao = get_avaliacao_for_user(request.user)
        if not meta_content_editable(avaliacao, meta=None) or (
            avaliacao is not None
            and avaliacao.etapa != avaliacao.Etapa.INPUT_METAS
        ):
            messages.error(
                request,
                'Só é possível cadastrar metas na etapa de metas '
                'de um ciclo aberto.',
            )
            return HttpResponseRedirect(reverse('goals:meta_list'))
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.instance.usuario = self.request.user
        form.instance.status = Meta.Status.PENDENTE
        form.instance.status_resultado = Meta.StatusResultado.PENDENTE
        messages.success(self.request, 'Meta criada com sucesso.')
        return super().form_valid(form)


class MetaUpdateView(LoginRequiredMixin, ScopedObjectMixin, UpdateView):
    """Edição de meta pendente/reprovada no escopo (ScopedObjectMixin)."""

    model = Meta
    form_class = MetaForm
    template_name = 'goals/meta_form.html'
    success_url = reverse_lazy('goals:meta_list')
    scope_user_field = 'usuario'
    context_object_name = 'meta'

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        self.object = self.get_object()
        avaliacao = get_avaliacao_for_user(self.object.usuario)
        if not meta_content_editable(avaliacao, self.object):
            messages.error(
                request,
                'Esta meta não pode ser editada na etapa atual.',
            )
            return HttpResponseRedirect(reverse('goals:meta_list'))
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        meta = self.object
        avaliacao = get_avaliacao_for_user(meta.usuario)
        is_owner = meta.usuario_id == self.request.user.pk
        pode_progresso = is_owner and meta_progress_editable(avaliacao, meta)
        cta = _proximo_passo_pos_reprovacao(
            avaliacao,
            meta,
            is_owner=is_owner,
            pode_progresso=pode_progresso,
        )
        context.update(cta)
        # Alias legado do template: mesma semântica de ``item_reprovado``.
        context['meta_reprovada'] = cta['item_reprovado']
        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        era_reprovada = self.object.status == Meta.Status.REPROVADA
        response = super().form_valid(form)
        if era_reprovada:
            messages.success(
                self.request,
                'Meta corrigida e reenviada para aprovação.',
            )
        else:
            messages.success(self.request, 'Meta atualizada com sucesso.')
        return response


class MetaDeleteView(LoginRequiredMixin, ScopedObjectMixin, DeleteView):
    """Exclusão de meta pendente na etapa de metas."""

    model = Meta
    template_name = 'goals/meta_confirm_delete.html'
    success_url = reverse_lazy('goals:meta_list')
    scope_user_field = 'usuario'
    context_object_name = 'meta'

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        self.object = self.get_object()
        avaliacao = get_avaliacao_for_user(self.object.usuario)
        pode_excluir = (
            meta_content_editable(avaliacao, self.object)
            and self.object.status == Meta.Status.PENDENTE
            and avaliacao is not None
            and avaliacao.etapa == avaliacao.Etapa.INPUT_METAS
        )
        if not pode_excluir:
            messages.error(
                request,
                'Só é possível excluir metas pendentes na etapa de metas.',
            )
            return HttpResponseRedirect(reverse('goals:meta_list'))
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        messages.success(self.request, 'Meta excluída com sucesso.')
        return super().form_valid(form)


class MetaProgressUpdateView(LoginRequiredMixin, UpdateView):
    """Atualiza progresso da própria meta (resultados / pós-reprovação; HTMX)."""

    model = Meta
    form_class = MetaProgressForm
    template_name = 'goals/meta_progress_form.html'
    context_object_name = 'meta'
    http_method_names = ['get', 'post', 'head', 'options']

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        if obj.usuario_id != self.request.user.pk:
            log_scope_denied(self.request.user, obj)
            raise Http404()
        return obj

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        self.object = self.get_object()
        avaliacao = get_avaliacao_for_user(self.object.usuario)
        if not meta_progress_editable(avaliacao, self.object):
            if is_htmx(request):
                return _htmx_meta_row_response(
                    request,
                    self.object,
                    message=(
                        'O progresso só pode ser atualizado na etapa de '
                        'resultados ou após reprovação de um resultado.'
                    ),
                    level='error',
                )
            messages.error(
                request,
                'O progresso só pode ser atualizado na etapa de resultados '
                'ou após reprovação de um resultado em ciclo aberto.',
            )
            return HttpResponseRedirect(reverse('goals:meta_list'))
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        return reverse('goals:meta_list')

    def form_valid(self, form):
        era_resultado_reprovado = (
            self.object.status_resultado == Meta.StatusResultado.REPROVADO
        )
        self.object = form.save()
        if is_htmx(self.request):
            return _htmx_meta_row_response(
                self.request,
                self.object,
                message=(
                    'Resultado corrigido e reenviado para aprovação.'
                    if era_resultado_reprovado
                    else 'Progresso atualizado com sucesso.'
                ),
                level='success',
            )
        messages.success(
            self.request,
            (
                'Resultado corrigido e reenviado para aprovação.'
                if era_resultado_reprovado
                else 'Progresso atualizado com sucesso.'
            ),
        )
        return HttpResponseRedirect(self.get_success_url())

    def form_invalid(self, form):
        if is_htmx(self.request):
            return _htmx_meta_row_response(
                self.request,
                self.object,
                progress_form=form,
                message='Não foi possível atualizar o progresso. Verifique o valor.',
                level='error',
            )
        return super().form_invalid(form)


class _MetaApprovalBaseView(
    LoginRequiredMixin,
    ScopedObjectMixin,
    SingleObjectMixin,
    View,
):
    """Base POST para aprovar/reprovar meta (HTMX `#meta-row-<pk>`)."""

    model = Meta
    queryset = Meta.objects.select_related(
        'usuario',
        'objetivo_estrategico',
    )
    scope_user_field = 'usuario'
    http_method_names = ['post', 'options']
    approve: bool = True
    success_message: str = ''
    error_fallback: str = 'Não foi possível concluir a aprovação.'

    def post(self, request, *args, **kwargs):
        meta = self.get_object()
        try:
            meta = _apply_meta_approval(meta, request.user, approve=self.approve)
        except PermissionDenied as exc:
            message = str(exc) or self.error_fallback
            if is_htmx(request):
                return _htmx_meta_row_response(
                    request,
                    meta,
                    message=message,
                    level='error',
                )
            messages.error(request, message)
            return HttpResponseRedirect(reverse('goals:meta_list'))

        if is_htmx(request):
            return _htmx_meta_row_response(
                request,
                meta,
                message=self.success_message,
                level='success',
            )
        messages.success(request, self.success_message)
        return HttpResponseRedirect(reverse('goals:meta_list'))


class MetaApproveView(_MetaApprovalBaseView):
    """Aprova meta ou resultado (líder / admin sem gestor)."""

    approve = True
    success_message = 'Aprovado com sucesso.'
    error_fallback = 'Não foi possível aprovar.'


class MetaRejectView(_MetaApprovalBaseView):
    """Reprova meta ou resultado (líder / admin sem gestor)."""

    approve = False
    success_message = 'Reprovado com sucesso.'
    error_fallback = 'Não foi possível reprovar.'
