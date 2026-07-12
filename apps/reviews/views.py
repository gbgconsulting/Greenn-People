from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import Http404, HttpResponseRedirect
from django.urls import reverse
from django.utils import timezone
from django.views import View
from django.views.generic import CreateView, DetailView, ListView

from apps.accounts.services.scope import user_in_scope
from apps.audit.services import log_scope_denied
from apps.core.mixins import ScopedObjectMixin
from apps.cycles.exceptions import CycleClosedError, StageTransitionError
from apps.cycles.services.stage import advance_stage, can_advance
from apps.reviews.exceptions import CalculationError
from apps.reviews.forms import (
    FeedbackForm,
    LeaderAssessmentFormSet,
    SelfAssessmentFormSet,
    can_acknowledge_feedback,
    can_leader_assess,
    feedback_create_allowed,
    leader_assessment_editable,
    resolve_feedback_tipo,
    self_assessment_editable,
)
from apps.reviews.models import Avaliacao, AvaliacaoCompetencia, Feedback
from apps.reviews.services.evaluation import calcular_nota_final_lider

# Transições que o próprio colaborador dispara (T036 / US1).
_COLLABORATOR_ADVANCE_ETAPAS = frozenset(
    {
        Avaliacao.Etapa.INPUT_METAS,
        Avaliacao.Etapa.RESULTADOS,
    },
)

# Transições que o líder (ou admin sem gestor) dispara (T044 / US2).
# ``aprovacao_resultados`` → ``avaliacao`` cria snapshots via ``advance_stage``.
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
    ``resultados`` → ``aprovacao_resultados``.

    Líder (T044): ``aprovacao_metas`` → ``resultados``,
    ``aprovacao_resultados`` → ``avaliacao`` (side-effect de snapshots),
    ``avaliacao`` → ``feedback``.

    A mudança de ``etapa`` é auditada via signals + ``audit_actor`` em
    ``advance_stage``.
    """

    http_method_names = ['post', 'options']

    def post(self, request, *args, **kwargs):
        avaliacao = self._get_avaliacao()
        if not self._authorize(request, avaliacao):
            return HttpResponseRedirect(self._redirect_url(request, avaliacao))

        try:
            avaliacao = advance_stage(avaliacao, actor=request.user)
        except CycleClosedError:
            messages.error(
                request,
                'Ciclo encerrado; não é possível avançar etapas.',
            )
        except StageTransitionError as exc:
            messages.error(request, str(exc))
        else:
            messages.success(request, 'Etapa avançada com sucesso.')

        return HttpResponseRedirect(self._redirect_url(request, avaliacao))

    def _get_avaliacao(self) -> Avaliacao:
        try:
            return (
                Avaliacao.objects.select_related(
                    'ciclo',
                    'usuario',
                    'usuario__line_manager',
                ).get(pk=self.kwargs['pk'])
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
            if not user_in_scope(user, avaliacao.usuario_id):
                log_scope_denied(user, avaliacao)
                raise Http404()
            if not can_leader_assess(user, avaliacao):
                messages.error(
                    request,
                    'Somente o gestor direto (ou um administrador, se o '
                    'colaborador não tiver gestor) pode avançar nesta etapa.',
                )
                return False
            return True

        messages.error(request, 'Não há etapa seguinte para avançar.')
        return False

    def _redirect_url(self, request, avaliacao: Avaliacao | None = None) -> str:
        nxt = request.POST.get('next') or request.GET.get('next')
        if nxt and nxt.startswith('/') and not nxt.startswith('//'):
            return nxt

        if (
            avaliacao is not None
            and avaliacao.etapa == Avaliacao.Etapa.AVALIACAO
            and can_leader_assess(request.user, avaliacao)
        ):
            return reverse(
                'reviews:leader_assessment',
                kwargs={'pk': avaliacao.pk},
            )

        if (
            avaliacao is not None
            and avaliacao.etapa == Avaliacao.Etapa.FEEDBACK
        ):
            return reverse(
                'reviews:feedback_list',
                kwargs={'pk': avaliacao.pk},
            )

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

        pode_avancar = False
        motivo_bloqueio_avanco = ''
        if can_leader_assess(self.request.user, self.object):
            ok, motivo = can_advance(self.object)
            pode_avancar = ok
            motivo_bloqueio_avanco = '' if ok else motivo

        context.update(
            {
                'formset': formset,
                'pode_editar': True,
                'linhas_vazias': len(formset.forms) == 0,
                'colaborador': self.object.usuario,
                'nota_final_lider': self.object.nota_final_lider,
                'pode_avancar': pode_avancar,
                'avanco_desabilitado': not pode_avancar,
                'motivo_bloqueio_avanco': motivo_bloqueio_avanco,
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


def _get_avaliacao_in_scope(request, pk: int) -> Avaliacao:
    """Carrega avaliação no escopo; IDOR → 404 + auditoria."""
    try:
        avaliacao = (
            Avaliacao.objects.select_related('ciclo', 'usuario').get(pk=pk)
        )
    except Avaliacao.DoesNotExist as exc:
        raise Http404() from exc

    if not user_in_scope(request.user, avaliacao.usuario_id):
        log_scope_denied(request.user, avaliacao)
        raise Http404()
    return avaliacao


class FeedbackListView(LoginRequiredMixin, ScopedObjectMixin, ListView):
    """Histórico de feedbacks da avaliação (escopo ``avaliacao__usuario``)."""

    model = Feedback
    template_name = 'reviews/feedback_list.html'
    context_object_name = 'feedbacks'
    paginate_by = 20
    scope_user_field = 'avaliacao__usuario'

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        self.avaliacao = _get_avaliacao_in_scope(request, self.kwargs['pk'])
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .filter(avaliacao_id=self.avaliacao.pk)
            .select_related(
                'autor',
                'avaliacao',
                'avaliacao__usuario',
                'avaliacao__ciclo',
            )
            .order_by('-created_at', 'id')
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        rows = []
        for feedback in context['feedbacks']:
            rows.append(
                {
                    'feedback': feedback,
                    'pode_dar_ciencia': can_acknowledge_feedback(user, feedback),
                },
            )
        context.update(
            {
                'avaliacao': self.avaliacao,
                'colaborador': self.avaliacao.usuario,
                'feedback_rows': rows,
                'pode_criar': feedback_create_allowed(user, self.avaliacao),
            },
        )
        return context


class FeedbackCreateView(LoginRequiredMixin, CreateView):
    """Registro de feedback (colaborador ou líder) no escopo da avaliação."""

    model = Feedback
    form_class = FeedbackForm
    template_name = 'reviews/feedback_form.html'

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()

        self.avaliacao = _get_avaliacao_in_scope(request, self.kwargs['pk'])
        if not feedback_create_allowed(request.user, self.avaliacao):
            messages.error(
                request,
                'Só é possível registrar feedback em um ciclo aberto '
                'para avaliações no seu escopo.',
            )
            return HttpResponseRedirect(
                reverse(
                    'reviews:feedback_list',
                    kwargs={'pk': self.avaliacao.pk},
                ),
            )
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['avaliacao'] = self.avaliacao
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                'avaliacao': self.avaliacao,
                'colaborador': self.avaliacao.usuario,
            },
        )
        return context

    def form_valid(self, form):
        form.instance.avaliacao = self.avaliacao
        form.instance.autor = self.request.user
        form.instance.tipo = resolve_feedback_tipo(
            self.request.user,
            self.avaliacao,
        )
        messages.success(self.request, 'Feedback registrado com sucesso.')
        return super().form_valid(form)

    def get_success_url(self):
        return reverse(
            'reviews:feedback_list',
            kwargs={'pk': self.avaliacao.pk},
        )


class FeedbackAcknowledgeView(LoginRequiredMixin, View):
    """Colaborador dá ciência ao feedback do líder (``ciente_em``; escopo Self)."""

    http_method_names = ['post', 'options']

    def post(self, request, *args, **kwargs):
        try:
            feedback = (
                Feedback.objects.select_related(
                    'avaliacao',
                    'avaliacao__usuario',
                ).get(pk=self.kwargs['pk'])
            )
        except Feedback.DoesNotExist as exc:
            raise Http404() from exc

        if feedback.avaliacao.usuario_id != request.user.pk:
            log_scope_denied(request.user, feedback)
            raise Http404()

        list_url = reverse(
            'reviews:feedback_list',
            kwargs={'pk': feedback.avaliacao_id},
        )

        if feedback.tipo != Feedback.Tipo.LIDER:
            messages.error(
                request,
                'Somente o feedback do líder exige ciência do colaborador.',
            )
            return HttpResponseRedirect(list_url)

        if feedback.ciente_em is not None:
            messages.info(request, 'Você já deu ciência a este feedback.')
            return HttpResponseRedirect(list_url)

        feedback.ciente_em = timezone.now()
        feedback.save(update_fields=['ciente_em', 'updated_at'])
        messages.success(request, 'Ciência registrada com sucesso.')
        return HttpResponseRedirect(list_url)
