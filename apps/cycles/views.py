from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count
from django.db.models.deletion import ProtectedError
from django.http import HttpResponseRedirect
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.generic import CreateView, DeleteView, ListView, UpdateView
from django.views.generic.detail import SingleObjectMixin

from apps.core.mixins import RequiresAdminMixin
from apps.cycles.exceptions import CycleAlreadyOpenError, CycleNotOpenError
from apps.cycles.forms import CicloForm
from apps.cycles.models import Ciclo
from apps.cycles.services.cycle import close_cycle, open_cycle


class AdminCyclesMixin(LoginRequiredMixin, RequiresAdminMixin):
    """Auth + admin gate for cycle management views."""


class CicloListView(AdminCyclesMixin, ListView):
    model = Ciclo
    template_name = 'cycles/ciclo_list.html'
    context_object_name = 'ciclos'
    paginate_by = 20

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
                f'Ciclo "{ciclo.nome}" encerrado. Nenhuma etapa pode avançar.',
            )
        return HttpResponseRedirect(reverse('cycles:ciclo_list'))
