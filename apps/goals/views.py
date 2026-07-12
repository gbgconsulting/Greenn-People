import json

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.template.loader import render_to_string
from django.urls import reverse, reverse_lazy
from django.views.generic import (
    CreateView,
    DeleteView,
    ListView,
    TemplateView,
    UpdateView,
)

from apps.audit.services import log_scope_denied
from apps.competencies.models import CargoCompetencia
from apps.core.htmx import is_htmx
from apps.core.mixins import ScopedObjectMixin
from apps.goals.forms import (
    MetaForm,
    MetaProgressForm,
    get_avaliacao_for_user,
    get_open_ciclo,
    meta_content_editable,
    meta_progress_editable,
)
from apps.goals.models import Meta


def _meta_row_context(request, meta, progress_form=None):
    """Contexto compartilhado do partial `#meta-row-<pk>`."""
    avaliacao = get_avaliacao_for_user(meta.usuario)
    pode_progresso = (
        meta.usuario_id == request.user.pk
        and meta_progress_editable(avaliacao, meta)
    )
    if progress_form is None and pode_progresso:
        progress_form = MetaProgressForm(instance=meta)
    return {
        'meta': meta,
        'pode_editar_conteudo': meta_content_editable(avaliacao, meta),
        'pode_atualizar_progresso': pode_progresso,
        'progress_form': progress_form if pode_progresso else None,
    }


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

        ciclo_aberto = get_open_ciclo()
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


class MetaListView(LoginRequiredMixin, ScopedObjectMixin, ListView):
    """Listagem de metas no escopo do usuário, com filtro por status."""

    model = Meta
    template_name = 'goals/meta_list.html'
    context_object_name = 'metas'
    paginate_by = 20
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

        context.update(
            {
                'ciclo_aberto': ciclo,
                'status_filtro': self.request.GET.get('status', '').strip(),
                'status_choices': Meta.Status.choices,
                'pode_criar': meta_content_editable(avaliacao, meta=None)
                and avaliacao is not None
                and avaliacao.etapa == avaliacao.Etapa.INPUT_METAS,
                'meta_rows': meta_rows,
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
                'Só é possível cadastrar metas na etapa de input de metas '
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

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        if form.instance.status == Meta.Status.REPROVADA:
            form.instance.status = Meta.Status.PENDENTE
        messages.success(self.request, 'Meta atualizada com sucesso.')
        return super().form_valid(form)


class MetaDeleteView(LoginRequiredMixin, ScopedObjectMixin, DeleteView):
    """Exclusão de meta pendente na etapa de input de metas."""

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
                'Só é possível excluir metas pendentes na etapa de input de metas.',
            )
            return HttpResponseRedirect(reverse('goals:meta_list'))
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        messages.success(self.request, 'Meta excluída com sucesso.')
        return super().form_valid(form)


class MetaProgressUpdateView(LoginRequiredMixin, UpdateView):
    """Atualiza progresso da própria meta (etapa resultados; HTMX `#meta-row-<pk>`)."""

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
                        'resultados para metas aprovadas.'
                    ),
                    level='error',
                )
            messages.error(
                request,
                'O progresso só pode ser atualizado na etapa de resultados '
                'para metas aprovadas de um ciclo aberto.',
            )
            return HttpResponseRedirect(reverse('goals:meta_list'))
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        return reverse('goals:meta_list')

    def form_valid(self, form):
        self.object = form.save()
        if is_htmx(self.request):
            return _htmx_meta_row_response(
                self.request,
                self.object,
                message='Progresso atualizado com sucesso.',
                level='success',
            )
        messages.success(self.request, 'Progresso atualizado com sucesso.')
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
