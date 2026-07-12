from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import Http404, HttpResponseRedirect
from django.urls import reverse
from django.views import View
from django.views.generic import DetailView

from apps.audit.services import log_scope_denied
from apps.core.mixins import ScopedObjectMixin
from apps.cycles.exceptions import CycleClosedError, StageTransitionError
from apps.cycles.services.stage import advance_stage
from apps.reviews.exceptions import CalculationError
from apps.reviews.forms import (
    LeaderAssessmentFormSet,
    SelfAssessmentFormSet,
    can_leader_assess,
    leader_assessment_editable,
    self_assessment_editable,
)
from apps.reviews.models import Avaliacao, AvaliacaoCompetencia
from apps.reviews.services.evaluation import calcular_nota_final_lider

# Transições que o próprio colaborador dispara (T036 / US1).
_COLLABORATOR_ADVANCE_ETAPAS = frozenset(
    {
        Avaliacao.Etapa.INPUT_METAS,
        Avaliacao.Etapa.RESULTADOS,
    },
)

# Transições de líder — permissão e fluxo completados em T044.
_LEADER_ADVANCE_ETAPAS = frozenset(
    {
        Avaliacao.Etapa.APROVACAO_METAS,
        Avaliacao.Etapa.APROVACAO_RESULTADOS,
        Avaliacao.Etapa.AVALIACAO,
    },
)


class AdvanceStageView(LoginRequiredMixin, View):
    """Avança a etapa agregada da avaliação (POST).

    Colaborador (T036): ``input_metas`` → ``aprovacao_metas``,
    ``resultados`` → ``aprovacao_resultados``. A mudança de ``etapa`` é
    auditada via signals + ``audit_actor`` em ``advance_stage``.
    """

    http_method_names = ['post', 'options']

    def post(self, request, *args, **kwargs):
        avaliacao = self._get_avaliacao()
        if not self._authorize(request, avaliacao):
            return HttpResponseRedirect(self._redirect_url(request))

        try:
            advance_stage(avaliacao, actor=request.user)
        except CycleClosedError:
            messages.error(
                request,
                'Ciclo encerrado; não é possível avançar etapas.',
            )
        except StageTransitionError as exc:
            messages.error(request, str(exc))
        else:
            messages.success(request, 'Etapa avançada com sucesso.')

        return HttpResponseRedirect(self._redirect_url(request))

    def _get_avaliacao(self) -> Avaliacao:
        try:
            return (
                Avaliacao.objects.select_related('ciclo', 'usuario')
                .get(pk=self.kwargs['pk'])
            )
        except Avaliacao.DoesNotExist as exc:
            raise Http404() from exc

    def _authorize(self, request, avaliacao: Avaliacao) -> bool:
        """Garante ator permitido para a etapa atual; IDOR → 404 + audit."""
        etapa = avaliacao.etapa
        user = request.user

        if etapa in _COLLABORATOR_ADVANCE_ETAPAS:
            if avaliacao.usuario_id != user.pk:
                log_scope_denied(user, avaliacao)
                raise Http404()
            return True

        if etapa in _LEADER_ADVANCE_ETAPAS:
            messages.error(
                request,
                'Somente o líder pode avançar nesta etapa.',
            )
            return False

        messages.error(request, 'Não há etapa seguinte para avançar.')
        return False

    def _redirect_url(self, request) -> str:
        nxt = request.POST.get('next') or request.GET.get('next')
        if nxt and nxt.startswith('/') and not nxt.startswith('//'):
            return nxt
        return reverse('goals:meta_list')


class SelfAssessmentView(LoginRequiredMixin, DetailView):
    """Autoavaliação do colaborador (etapa ``avaliacao``; escopo Self)."""

    model = Avaliacao
    template_name = 'reviews/self_assessment.html'
    context_object_name = 'avaliacao'
    http_method_names = ['get', 'post', 'head', 'options']

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        if obj.usuario_id != self.request.user.pk:
            log_scope_denied(self.request.user, obj)
            raise Http404()
        return obj

    def get_queryset(self):
        return Avaliacao.objects.select_related('ciclo', 'usuario')

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        self.object = self.get_object()
        if not self_assessment_editable(self.object):
            messages.error(
                request,
                'A autoavaliação só está disponível na etapa de avaliação '
                'de um ciclo aberto.',
            )
            return HttpResponseRedirect(reverse('dashboard:personal'))
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        formset = SelfAssessmentFormSet(
            request.POST,
            queryset=self._linhas_queryset(),
        )
        if formset.is_valid():
            formset.save()
            messages.success(request, 'Autoavaliação salva com sucesso.')
            return HttpResponseRedirect(
                reverse('reviews:self_assessment', kwargs={'pk': self.object.pk}),
            )

        context = self.get_context_data(object=self.object, formset=formset)
        return self.render_to_response(context)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        formset = kwargs.get('formset')
        if formset is None:
            formset = SelfAssessmentFormSet(queryset=self._linhas_queryset())

        context.update(
            {
                'formset': formset,
                'pode_editar': True,
                'linhas_vazias': len(formset.forms) == 0,
            },
        )
        return context

    def _linhas_queryset(self):
        return (
            AvaliacaoCompetencia.objects.filter(avaliacao_id=self.object.pk)
            .select_related(
                'avaliacao',
                'avaliacao__ciclo',
                'competencia',
                'competencia__escala',
            )
            .order_by('competencia__nome')
        )


class LeaderAssessmentView(LoginRequiredMixin, ScopedObjectMixin, DetailView):
    """Avaliação do líder por competências (etapa ``avaliacao``; escopo Leader)."""

    model = Avaliacao
    queryset = Avaliacao.objects.select_related('ciclo', 'usuario')
    template_name = 'reviews/leader_assessment.html'
    context_object_name = 'avaliacao'
    scope_user_field = 'usuario'
    http_method_names = ['get', 'post', 'head', 'options']

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        if obj.usuario_id == self.request.user.pk:
            log_scope_denied(self.request.user, obj)
            raise Http404()
        return obj

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()

        self.object = self.get_object()

        if not can_leader_assess(request.user, self.object):
            messages.error(
                request,
                'Somente o gestor direto (ou um administrador, se o '
                'colaborador não tiver gestor) pode avaliar competências.',
            )
            return HttpResponseRedirect(reverse('dashboard:personal'))

        if not leader_assessment_editable(self.object):
            messages.error(
                request,
                'A avaliação do líder só está disponível na etapa de avaliação '
                'de um ciclo aberto.',
            )
            return HttpResponseRedirect(reverse('dashboard:personal'))

        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        if not can_leader_assess(request.user, self.object):
            return HttpResponseRedirect(reverse('dashboard:personal'))

        formset = LeaderAssessmentFormSet(
            request.POST,
            queryset=self._linhas_queryset(),
        )
        if formset.is_valid():
            formset.save()
            self._atualizar_nota_final()
            return HttpResponseRedirect(
                reverse(
                    'reviews:leader_assessment',
                    kwargs={'pk': self.object.pk},
                ),
            )

        context = self.get_context_data(object=self.object, formset=formset)
        return self.render_to_response(context)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        formset = kwargs.get('formset')
        if formset is None:
            formset = LeaderAssessmentFormSet(queryset=self._linhas_queryset())

        context.update(
            {
                'formset': formset,
                'pode_editar': True,
                'linhas_vazias': len(formset.forms) == 0,
                'colaborador': self.object.usuario,
                'nota_final_lider': self.object.nota_final_lider,
            },
        )
        return context

    def _linhas_queryset(self):
        return (
            AvaliacaoCompetencia.objects.filter(avaliacao_id=self.object.pk)
            .select_related(
                'avaliacao',
                'avaliacao__ciclo',
                'competencia',
                'competencia__escala',
            )
            .order_by('competencia__nome')
        )

    def _atualizar_nota_final(self) -> None:
        """Recalcula ``nota_final_lider`` quando todas as notas estão preenchidas."""
        linhas = AvaliacaoCompetencia.objects.filter(avaliacao_id=self.object.pk)
        incompleta = (
            not linhas.exists()
            or linhas.filter(nota_lider__isnull=True).exists()
        )
        if incompleta:
            if self.object.nota_final_lider is not None:
                self.object.nota_final_lider = None
                self.object.save(update_fields=['nota_final_lider', 'updated_at'])
            messages.success(
                self.request,
                'Avaliação do líder salva. Preencha todas as competências '
                'para calcular a nota final.',
            )
            return

        try:
            calcular_nota_final_lider(self.object)
        except CalculationError as exc:
            messages.warning(
                self.request,
                f'Avaliação salva, mas não foi possível calcular a nota final: {exc}',
            )
            return

        messages.success(
            self.request,
            'Avaliação do líder salva. Nota final calculada com sucesso.',
        )
