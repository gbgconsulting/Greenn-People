from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count
from django.db.models.deletion import ProtectedError
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.generic import CreateView, DeleteView, ListView, UpdateView
from django.views.generic.detail import SingleObjectMixin

from apps.core.mixins import HtmxPaginatedListMixin, RequiresAdminMixin
from apps.cycles.exceptions import CycleAlreadyOpenError, CycleNotOpenError
from apps.cycles.forms import CicloForm
from apps.cycles.models import Ciclo
from apps.cycles.services.cycle import close_cycle, open_cycle
from apps.goals.forms import ObjetivoEstrategicoForm
from apps.goals.models import ObjetivoEstrategico


class AdminCyclesMixin(LoginRequiredMixin, RequiresAdminMixin):
    """Auth + admin gate for cycle management views."""


class CicloNestedMixin(AdminCyclesMixin):
    """Resolve o ciclo pai a partir de ``ciclo_pk`` nas rotas aninhadas."""

    ciclo_url_kwarg = 'ciclo_pk'

    def dispatch(self, request, *args, **kwargs):
        self.ciclo = get_object_or_404(Ciclo, pk=kwargs[self.ciclo_url_kwarg])
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['ciclo'] = self.ciclo
        return context

    def get_success_url(self):
        return reverse(
            'cycles:objetivo_list',
            kwargs={self.ciclo_url_kwarg: self.ciclo.pk},
        )


class CicloListView(AdminCyclesMixin, HtmxPaginatedListMixin, ListView):
    model = Ciclo
    template_name = 'cycles/ciclo_list.html'
    partial_template_name = 'cycles/ciclo_list_partial.html'
    context_object_name = 'ciclos'

    def get_queryset(self):
        return (
            Ciclo.objects.annotate(avaliacoes_count=Count('avaliacoes'))
            .order_by('-data_inicio', 'nome')
        )


class CicloCreateView(AdminCyclesMixin, CreateView):
    model = Ciclo
    form_class = CicloForm
    template_name = 'cycles/ciclo_form.html'
    success_url = reverse_lazy('cycles:ciclo_list')

    def form_valid(self, form):
        form.instance.status = Ciclo.Status.ENCERRADO
        messages.success(self.request, 'Ciclo criado com sucesso.')
        return super().form_valid(form)


class CicloUpdateView(AdminCyclesMixin, UpdateView):
    model = Ciclo
    form_class = CicloForm
    template_name = 'cycles/ciclo_form.html'
    success_url = reverse_lazy('cycles:ciclo_list')

    def form_valid(self, form):
        messages.success(self.request, 'Ciclo atualizado com sucesso.')
        return super().form_valid(form)


class CicloDeleteView(AdminCyclesMixin, DeleteView):
    model = Ciclo
    template_name = 'cycles/ciclo_confirm_delete.html'
    success_url = reverse_lazy('cycles:ciclo_list')

    def form_valid(self, form):
        try:
            response = super().form_valid(form)
        except ProtectedError:
            messages.error(
                self.request,
                'Não é possível excluir este ciclo: há avaliações, '
                'objetivos ou outros vínculos. Encerre-o e mantenha o '
                'histórico.',
            )
            return HttpResponseRedirect(self.success_url)
        messages.success(self.request, 'Ciclo excluído com sucesso.')
        return response


class CicloOpenView(AdminCyclesMixin, SingleObjectMixin, View):
    """Abre o ciclo e cria Avaliacao para colaboradores ativos (FR-015/016)."""

    model = Ciclo
    http_method_names = ['post', 'options']

    def post(self, request, *args, **kwargs):
        ciclo = self.get_object()
        try:
            open_cycle(ciclo)
        except CycleAlreadyOpenError as exc:
            messages.error(request, str(exc))
        else:
            messages.success(
                request,
                f'Ciclo "{ciclo.nome}" aberto. Avaliações criadas para '
                'colaboradores ativos.',
            )
        return HttpResponseRedirect(reverse('cycles:ciclo_list'))


class CicloCloseView(AdminCyclesMixin, SingleObjectMixin, View):
    """Encerra manualmente o ciclo aberto (FR-017)."""

    model = Ciclo
    http_method_names = ['post', 'options']

    def post(self, request, *args, **kwargs):
        ciclo = self.get_object()
        try:
            close_cycle(ciclo)
        except CycleNotOpenError as exc:
            messages.error(request, str(exc))
        else:
            messages.success(
                request,
                f'Ciclo "{ciclo.nome}" encerrado. Etapas bloqueadas; '
                'avaliações incompletas marcadas para o indicador de conclusão.',
            )
        return HttpResponseRedirect(reverse('cycles:ciclo_list'))


class ObjetivoEstrategicoListView(CicloNestedMixin, HtmxPaginatedListMixin, ListView):
    model = ObjetivoEstrategico
    template_name = 'cycles/objetivo_list.html'
    partial_template_name = 'cycles/objetivo_list_partial.html'
    context_object_name = 'objetivos'

    def get_queryset(self):
        return (
            ObjetivoEstrategico.objects.filter(ciclo=self.ciclo)
            .annotate(metas_count=Count('metas'))
            .order_by('id')
        )


class ObjetivoEstrategicoCreateView(CicloNestedMixin, CreateView):
    model = ObjetivoEstrategico
    form_class = ObjetivoEstrategicoForm
    template_name = 'cycles/objetivo_form.html'

    def form_valid(self, form):
        form.instance.ciclo = self.ciclo
        messages.success(self.request, 'Objetivo estratégico criado com sucesso.')
        return super().form_valid(form)


class ObjetivoEstrategicoUpdateView(CicloNestedMixin, UpdateView):
    model = ObjetivoEstrategico
    form_class = ObjetivoEstrategicoForm
    template_name = 'cycles/objetivo_form.html'
    context_object_name = 'objetivo'

    def get_queryset(self):
        return ObjetivoEstrategico.objects.filter(ciclo=self.ciclo)

    def form_valid(self, form):
        messages.success(
            self.request,
            'Objetivo estratégico atualizado com sucesso.',
        )
        return super().form_valid(form)


class ObjetivoEstrategicoDeleteView(CicloNestedMixin, DeleteView):
    model = ObjetivoEstrategico
    template_name = 'cycles/objetivo_confirm_delete.html'
    context_object_name = 'objetivo'

    def get_queryset(self):
        return ObjetivoEstrategico.objects.filter(ciclo=self.ciclo)

    def form_valid(self, form):
        try:
            response = super().form_valid(form)
        except ProtectedError:
            messages.error(
                self.request,
                'Não é possível excluir este objetivo: há metas vinculadas. '
                'Remova ou reatribua as metas primeiro.',
            )
            return HttpResponseRedirect(self.get_success_url())
        messages.success(self.request, 'Objetivo estratégico excluído com sucesso.')
        return response
