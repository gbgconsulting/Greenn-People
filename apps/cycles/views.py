from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Avg, Count, Q
from django.db.models.deletion import ProtectedError
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView
from django.views.generic.detail import SingleObjectMixin

from apps.accounts.services.scope import get_visible_users
from apps.core.mixins import HtmxPaginatedListMixin, RequiresAdminMixin
from apps.cycles.exceptions import CycleAlreadyOpenError, CycleNotOpenError
from apps.cycles.forms import CicloForm
from apps.cycles.models import Ciclo
from apps.cycles.services.cycle import close_cycle, open_cycle
from apps.dashboard.chart_payloads import (
    CHART_TYPE_BAR_GROUPED,
    CHART_TYPE_BAR_HORIZONTAL,
    CHART_TYPE_DOUGHNUT,
    EMPTY_KIND_SEM_DADO,
    EMPTY_KIND_SEM_NOTA,
    aderencia_distribution_payload,
    categorical_counts_payload,
    empty_kind_message,
    empty_kind_payload,
    grouped_series_payload,
)
from apps.dashboard.models import AderenciaSnapshot
from apps.dashboard.services.structure import build_structure_coverage
from apps.dashboard.views import aderencia_status
from apps.goals.forms import ObjetivoEstrategicoForm, get_open_ciclo
from apps.goals.models import ObjetivoEstrategico
from apps.reviews.models import Avaliacao
from apps.reviews.services.guidance import build_rh_pre_open_checklist


def _rh_pre_open_checklist_context() -> dict:
    """T026 / FR-008: reusa ``build_rh_pre_open_checklist`` só como apresentação.

    Lê ``apps/reviews/services/guidance.py`` sem alterar advisory → hard-block.
    Nunca condiciona ``CicloOpenView`` / ``open_cycle`` / ``cycle.py``.
    """
    checklist = build_rh_pre_open_checklist()
    if not checklist.advisory_only:
        raise AssertionError(
            'rh_pre_open_checklist deve permanecer advisory_only=True '
            '(FR-008); não condicionar abertura de ciclo.',
        )
    return {
        'rh_pre_open_checklist': checklist,
        'rh_checklist_has_blockers': checklist.has_blockers,
    }


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


def _annotated_ciclos():
    return Ciclo.objects.annotate(avaliacoes_count=Count('avaliacoes'))


class CicloListView(AdminCyclesMixin, HtmxPaginatedListMixin, ListView):
    model = Ciclo
    template_name = 'cycles/ciclo_list.html'
    partial_template_name = 'cycles/ciclo_list_partial.html'
    context_object_name = 'ciclos'
    # paginate_by = 20 vem de HtmxPaginatedListMixin — não redefinir.

    def get_queryset(self):
        """Arquivo paginado; o aberto vai para ``ciclo_operacional``."""
        return (
            _annotated_ciclos()
            .filter(status=Ciclo.Status.ENCERRADO)
            .order_by('-data_inicio', 'nome')
        )

    def get_context_data(self, **kwargs):
        """Checklist RH avisório + destaque do ciclo aberto (T018).

        Não condiciona Abrir / ``CicloOpenView`` / ``open_cycle``.
        """
        context = super().get_context_data(**kwargs)
        context.update(_rh_pre_open_checklist_context())
        aberto = get_open_ciclo()
        if aberto is not None:
            aberto = _annotated_ciclos().filter(pk=aberto.pk).first()
        context['ciclo_operacional'] = aberto
        paginator = context.get('paginator')
        context['arquivo_total'] = paginator.count if paginator is not None else 0
        return context


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


class CicloDetailView(AdminCyclesMixin, DetailView):
    """Painel gerencial read-only do ciclo (US1 T019 / FR-007 / FR-009).

    AuthZ = ``AdminCyclesMixin`` (LoginRequired + RequiresAdmin). Sem
    ``ScopedObjectMixin`` — Ciclo não tem dono; precedente admin-only.
    Não toca ``CicloOpenView`` / ``close`` / ``cycle.py``. Sem rota nova.
    """

    model = Ciclo
    template_name = 'cycles/ciclo_detail.html'
    context_object_name = 'ciclo'

    def get_context_data(self, **kwargs):
        """KPI → pipeline principal → cobertura (Top-N) → empty desempenho.

        Checklist = reuse T026 de ``build_rh_pre_open_checklist`` (008 / FR-008);
        avisório — não condiciona Abrir ciclo / ``open_cycle``.
        Cobertura já corta Top-N via ``coverage_bar_payload`` (T005).
        """
        context = super().get_context_data(**kwargs)
        ciclo = self.object

        # Escopo já resolvido pelo AuthZ admin — builder só recebe visible.
        visible = get_visible_users(self.request.user).filter(is_active=True)
        cobertura = build_structure_coverage(visible, ciclo)
        sem_desempenho = self._cabecalhos_sem_desempenho(ciclo)

        context['chart_ciclo_progresso'] = self._chart_ciclo_progresso(ciclo)
        context['avaliacoes_resumo'] = self._avaliacoes_resumo(
            ciclo,
            sem_desempenho=sem_desempenho,
        )
        context['cobertura_resumo'] = cobertura['resumo']
        context['chart_cobertura_area'] = cobertura['chart_por_area']
        context['chart_cobertura_cargo'] = cobertura['chart_por_cargo']
        context['aderencia_resumo'] = self._aderencia_resumo(ciclo)
        context['chart_aderencia_distribuicao'] = (
            self._chart_aderencia_distribuicao(
                ciclo,
                sem_desempenho=sem_desempenho,
            )
        )
        context['chart_gaps_competencia'] = self._chart_gaps_competencia(
            sem_desempenho=sem_desempenho,
        )
        context.update(_rh_pre_open_checklist_context())
        return context

    def _cabecalhos_sem_desempenho(self, ciclo: Ciclo) -> bool:
        """True se há cabeçalhos e nenhum tem nota (legado 011 / FR-009)."""
        qs = Avaliacao.objects.filter(ciclo=ciclo)
        if not qs.exists():
            return False
        return not qs.filter(
            Q(nota_final_lider__isnull=False)
            | Q(nota_final_autoavaliacao__isnull=False),
        ).exists()

    def _avaliacoes_resumo(
        self,
        ciclo: Ciclo,
        *,
        sem_desempenho: bool,
    ) -> dict:
        totals = Avaliacao.objects.filter(ciclo=ciclo).aggregate(
            total=Count('pk'),
            concluidas=Count('pk', filter=Q(concluida=True)),
        )
        total = totals['total'] or 0
        concluidas = totals['concluidas'] or 0
        percentual = (
            (Decimal(concluidas) * Decimal('100') / Decimal(total)).quantize(
                Decimal('0.01'),
            )
            if total
            else None
        )
        return {
            'total': total,
            'concluidas': concluidas,
            'percentual_concluidas': percentual,
            'sem_desempenho': sem_desempenho,
        }

    def _aderencia_resumo(self, ciclo: Ciclo) -> dict:
        agg = AderenciaSnapshot.objects.filter(ciclo=ciclo).aggregate(
            media=Avg('percentual'),
            total_lideres=Count('pk'),
        )
        media = agg['media']
        if media is not None:
            media = Decimal(media).quantize(Decimal('0.01'))
        return {
            'media': media,
            'total_lideres': agg['total_lideres'] or 0,
            'status': aderencia_status(media),
        }

    def _chart_ciclo_progresso(self, ciclo: Ciclo) -> dict:
        """Contagem ``Avaliacao.etapa`` no ciclo → payload catálogo (US1)."""
        etapa_keys = [choice.value for choice in Avaliacao.Etapa]
        labels_by_key = dict(Avaliacao.Etapa.choices)
        key_counts = {
            row['etapa']: int(row['total'])
            for row in (
                Avaliacao.objects.filter(ciclo=ciclo)
                .values('etapa')
                .annotate(total=Count('pk'))
            )
        }
        return categorical_counts_payload(
            key_counts,
            ordered_keys=etapa_keys,
            labels_by_key=labels_by_key,
            chart_id='chart-ciclo-progresso',
            chart_type=CHART_TYPE_BAR_HORIZONTAL,
            title='Progresso das avaliações no ciclo',
            empty_message=(
                'Não há avaliações neste ciclo para exibir progresso.'
            ),
            highlight_max=True,
        )

    def _chart_aderencia_distribuicao(
        self,
        ciclo: Ciclo,
        *,
        sem_desempenho: bool,
    ) -> dict:
        """Doughnut só com ``AderenciaSnapshot`` real (T019).

        Sem snapshot: empty ``sem_nota`` se cabeçalho legado sem desempenho,
        senão ``sem_dado``. MUST NOT chamar ``compute_adherence``.
        """
        chart_type = CHART_TYPE_DOUGHNUT
        title = 'Distribuição de aderência'
        percentuais = list(
            AderenciaSnapshot.objects.filter(ciclo=ciclo).values_list(
                'percentual',
                flat=True,
            )
        )
        if not percentuais:
            kind = (
                EMPTY_KIND_SEM_NOTA if sem_desempenho else EMPTY_KIND_SEM_DADO
            )
            return empty_kind_payload(
                kind=kind,
                chart_id='chart-aderencia-distribuicao',
                chart_type=chart_type,
                title=title,
            )
        status_keys = [aderencia_status(percentual) for percentual in percentuais]
        return aderencia_distribution_payload(
            status_keys,
            chart_type=chart_type,
            title=title,
        )

    def _chart_gaps_competencia(self, *, sem_desempenho: bool) -> dict | None:
        """Gap esperado×nota: empty ``sem_nota`` no legado sem desempenho.

        Sem builder de gap no detalhe do ciclo — não inventa série. Ausente
        quando há nota (T020 cobre o recorte pessoal).
        """
        if not sem_desempenho:
            return None
        return grouped_series_payload(
            chart_id='chart-gaps-competencia',
            chart_type=CHART_TYPE_BAR_GROUPED,
            title='Esperado × nota por competência',
            labels=[],
            series=[],
            empty_message=empty_kind_message(EMPTY_KIND_SEM_NOTA),
            has_data=False,
        )


class CicloOpenView(AdminCyclesMixin, SingleObjectMixin, View):
    """Abre o ciclo e cria Avaliacao para colaboradores ativos (FR-015/016).

    Não lê ``build_rh_pre_open_checklist`` — checklist permanece avisório
    (T026 / FR-008); abertura segue só ``open_cycle`` / ``cycle.py``.
    """

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
