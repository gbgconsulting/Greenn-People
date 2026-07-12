from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponseRedirect
from django.urls import reverse, reverse_lazy
from django.views.generic import (
    CreateView,
    DeleteView,
    ListView,
    TemplateView,
    UpdateView,
)

from apps.competencies.models import CargoCompetencia
from apps.core.mixins import ScopedObjectMixin
from apps.goals.forms import (
    MetaForm,
    get_avaliacao_for_user,
    get_open_ciclo,
    meta_content_editable,
)
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
        context.update(
            {
                'ciclo_aberto': ciclo,
                'status_filtro': self.request.GET.get('status', '').strip(),
                'status_choices': Meta.Status.choices,
                'pode_criar': meta_content_editable(avaliacao, meta=None)
                and avaliacao is not None
                and avaliacao.etapa == avaliacao.Etapa.INPUT_METAS,
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
