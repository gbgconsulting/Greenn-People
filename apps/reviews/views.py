import json

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.http import Http404, HttpResponseRedirect
from django.urls import reverse
from django.utils import timezone
from django.views import View
from django.db.models import Q
from django.views.generic import CreateView, DetailView, ListView

from apps.accounts.services.scope import user_in_scope
from apps.audit.services import log_scope_denied
from apps.core.htmx import is_htmx
from apps.core.mixins import HtmxPaginatedListMixin, ScopedObjectMixin
from apps.cycles.exceptions import CycleClosedError, StageTransitionError
from apps.cycles.models import Ciclo
from apps.cycles.services.stage import advance_stage, can_advance
from apps.goals.forms import get_open_ciclo
from apps.goals.models import Meta
from apps.reviews.exceptions import CalculationError
from apps.reviews.forms import (
    FeedbackForm,
    LeaderAssessmentFormSet,
    SelfAssessmentFormSet,
    can_acknowledge_feedback,
    can_leader_assess,
    feedback_create_allowed,
    feedback_destinatario,
    leader_assessment_editable,
    leader_assessment_permitted,
    resolve_feedback_tipo,
    self_assessment_editable,
)
from apps.reviews.models import Avaliacao, AvaliacaoCompetencia, Feedback
from apps.reviews.services.evaluation import (
    MSG_AUTOAVALIACAO_ENVIO_INCOMPLETO,
    MSG_AUTOAVALIACAO_INCOMPLETA,
    MSG_AUTOAVALIACAO_JA_ENVIADA,
    calcular_nota_final_lider,
    self_assessment_complete,
    self_assessment_submitted,
    self_assessment_viewable,
    submit_self_assessment,
)
from apps.reviews.services.collaborator_history import (
    build_collaborator_history_rows,
    is_collaborator_history_view,
)
from apps.reviews.services.team_avaliacao_list import (
    apply_team_list_filters,
    build_team_avaliacao_rows,
    get_allowed_area_ids,
    get_area_filter_options,
    is_team_avaliacao_list_view,
    parse_area_filter,
    parse_etapa_filter,
    parse_status_filter,
    resolve_area_filter,
    STATUS_FILTER_CHIPS,
    STATUS_SEGMENT_OPTIONS,
    ETAPA_FILTER_CHIPS,
)
from apps.reviews.services.feedback_display import build_feedback_resumo
from apps.reviews.services.guidance import (
    build_stage_stepper,
    detect_owner_correction_kind,
    resolve_next_step,
)

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

_ADVANCE_LABELS = {
    Avaliacao.Etapa.INPUT_METAS: 'Enviar metas para aprovação',
    Avaliacao.Etapa.APROVACAO_METAS: 'Liberar etapa de resultados',
    Avaliacao.Etapa.RESULTADOS: 'Enviar resultados para aprovação',
    Avaliacao.Etapa.APROVACAO_RESULTADOS: 'Liberar etapa de avaliação',
    Avaliacao.Etapa.AVALIACAO: 'Avançar para feedback',
}


def _advance_context(user, avaliacao: Avaliacao) -> dict:
    """Contexto de avanço de etapa conforme ator (colaborador ou líder)."""
    etapa = avaliacao.etapa
    pode_atuar = False

    if etapa in _COLLABORATOR_ADVANCE_ETAPAS:
        pode_atuar = avaliacao.usuario_id == user.pk
    elif etapa in _LEADER_ADVANCE_ETAPAS:
        pode_atuar = can_leader_assess(user, avaliacao)

    if not pode_atuar:
        return {
            'pode_avancar': False,
            'avanco_desabilitado': True,
            'rotulo_avanco': '',
            'motivo_bloqueio_avanco': '',
        }

    ok, motivo = can_advance(avaliacao)
    return {
        'pode_avancar': ok,
        'avanco_desabilitado': not ok,
        'rotulo_avanco': _ADVANCE_LABELS.get(etapa, 'Avançar etapa'),
        'motivo_bloqueio_avanco': '' if ok else motivo,
    }


class AvaliacaoListView(LoginRequiredMixin, ScopedObjectMixin, HtmxPaginatedListMixin, ListView):
    """Listagem de avaliações no escopo (ciclo aberto quando houver).

    Colaboradores sem time veem histórico pessoal de ciclos («Minhas Avaliações»).
    """

    model = Avaliacao
    template_name = 'reviews/avaliacao_list.html'
    partial_template_name = 'reviews/avaliacao_list_partial.html'
    collaborator_template_name = 'reviews/avaliacao_list_colaborador.html'
    collaborator_partial_template_name = 'reviews/avaliacao_list_colaborador_partial.html'
    context_object_name = 'avaliacoes'
    scope_user_field = 'usuario'

    def get_template_names(self) -> list[str]:
        if is_collaborator_history_view(self.request.user):
            if is_htmx(self.request):
                return [self.collaborator_partial_template_name]
            return [self.collaborator_template_name]
        return super().get_template_names()

    def get_paginate_by(self, queryset=None):
        if is_collaborator_history_view(self.request.user):
            return 10
        return self.paginate_by

    def _get_scoped_team_base_queryset(self):
        """Escopo hierárquico + ciclo aberto — base para filtros e opções de área."""
        qs = (
            super()
            .get_queryset()
            .select_related(
                'ciclo',
                'usuario',
                'usuario__area',
                'usuario__cargo',
            )
        )
        ciclo = get_open_ciclo()
        if ciclo is not None:
            qs = qs.filter(ciclo=ciclo)
        return qs.order_by('usuario__nome', 'usuario__email', 'id')

    def get_queryset(self):
        qs = (
            super()
            .get_queryset()
            .select_related(
                'ciclo',
                'usuario',
                'usuario__area',
                'usuario__cargo',
            )
        )
        user = self.request.user
        if is_collaborator_history_view(user):
            return qs.filter(usuario_id=user.pk).order_by(
                '-ciclo__data_inicio',
                '-ciclo__pk',
                '-id',
            )

        base_qs = self._get_scoped_team_base_queryset()
        allowed_area_ids = get_allowed_area_ids(base_qs)
        status = parse_status_filter(self.request.GET.get('status'))
        etapa = parse_etapa_filter(self.request.GET.get('etapa'))
        area_id = resolve_area_filter(
            parse_area_filter(self.request.GET.get('area')),
            allowed_area_ids,
        )

        qs = apply_team_list_filters(
            base_qs,
            status=status,
            etapa=etapa,
            area_id=area_id,
        )

        busca = (self.request.GET.get('busca') or '').strip()
        if busca:
            qs = qs.filter(
                Q(usuario__nome__icontains=busca)
                | Q(usuario__email__icontains=busca),
            )
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        if is_collaborator_history_view(user):
            context.update(
                {
                    'lista_colaborador': True,
                    'historico_rows': build_collaborator_history_rows(
                        context['avaliacoes'],
                    ),
                },
            )
            return context

        busca = (self.request.GET.get('busca') or '').strip()
        base_qs = self._get_scoped_team_base_queryset()
        allowed_area_ids = get_allowed_area_ids(base_qs)
        status = parse_status_filter(self.request.GET.get('status'))
        etapa = parse_etapa_filter(self.request.GET.get('etapa'))
        area_id = resolve_area_filter(
            parse_area_filter(self.request.GET.get('area')),
            allowed_area_ids,
        )
        context.update(
            {
                'lista_colaborador': False,
                'lista_time': is_team_avaliacao_list_view(user),
                'ciclo_aberto': get_open_ciclo(),
                'filtro_busca': busca,
                'filtro_status': status,
                'filtro_etapa': etapa,
                'filtro_area_id': area_id,
                'filtro_ativo': bool(busca or status or etapa or area_id),
                'filtro_avancado_ativo': bool(etapa or area_id),
                'status_segment_options': STATUS_SEGMENT_OPTIONS,
                'status_chips': STATUS_FILTER_CHIPS,
                'etapa_chips': ETAPA_FILTER_CHIPS,
                'area_options': get_area_filter_options(base_qs),
                'total_escopo_lista': base_qs.count(),
                'avaliacao_rows': build_team_avaliacao_rows(
                    context['avaliacoes'],
                    user,
                ),
            },
        )
        return context


class AvaliacaoDetailView(LoginRequiredMixin, ScopedObjectMixin, DetailView):
    """Detalhe da avaliação no escopo; IDOR → Http404 + ``log_scope_denied``."""

    model = Avaliacao
    template_name = 'reviews/avaliacao_detail.html'
    collaborator_template_name = 'reviews/avaliacao_detail_colaborador.html'
    context_object_name = 'avaliacao'
    scope_user_field = 'usuario'
    queryset = Avaliacao.objects.select_related(
        'ciclo',
        'usuario',
        'usuario__area',
        'usuario__cargo',
        'usuario__line_manager',
    )

    def get_template_names(self):
        avaliacao = self.object
        if avaliacao.usuario_id == self.request.user.pk:
            return [self.collaborator_template_name]
        return [self.template_name]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        avaliacao = self.object
        user = self.request.user
        is_self = avaliacao.usuario_id == user.pk
        linhas = (
            AvaliacaoCompetencia.objects.filter(avaliacao_id=avaliacao.pk)
            .select_related('competencia', 'competencia__escala')
            .order_by('competencia__nome')
        )
        context_payload = {
            'colaborador': avaliacao.usuario,
            'is_self': is_self,
            'linhas': linhas,
            'pode_autoavaliar': (
                is_self and self_assessment_editable(avaliacao)
            ),
            'pode_ver_autoavaliacao': (
                is_self
                and self_assessment_viewable(avaliacao)
                and self_assessment_submitted(avaliacao)
            ),
            'pode_avaliar_lider': (
                not is_self
                and can_leader_assess(user, avaliacao)
                and leader_assessment_permitted(avaliacao)
            ),
            'pode_criar_feedback': feedback_create_allowed(user, avaliacao),
            **_advance_context(user, avaliacao),
            **self._guidance_presentation_context(
                avaliacao,
                is_self=is_self,
            ),
        }
        context.update(context_payload)
        return context

    def _guidance_role(self, *, is_self: bool) -> str:
        """Papel de apresentação no hub (sem AuthZ nova).

        Sujeito da avaliação → colaborador; demais: admin→rh, líder→lider.
        """
        if is_self:
            return 'colaborador'
        user = self.request.user
        if getattr(user, 'is_admin', False):
            return 'rh'
        if user.is_leader:
            return 'lider'
        return 'colaborador'

    def _guidance_presentation_context(
        self,
        avaliacao: Avaliacao,
        *,
        is_self: bool,
    ) -> dict:
        """Injeta ``next_step`` + ``stage_stepper`` só via ``guidance.py`` (FR-013)."""
        ciclo_aberto = avaliacao.ciclo.status == Ciclo.Status.ABERTO
        if ciclo_aberto:
            has_open_ciclo = True
            concluida = bool(avaliacao.concluida)
            vinculo_pendente = False
            owner_correction_kind = (
                detect_owner_correction_kind(avaliacao) if is_self else None
            )
        else:
            # Ciclo encerrado com participação: leitura (paridade com Meu Painel).
            has_open_ciclo = True
            concluida = True
            vinculo_pendente = False
            owner_correction_kind = None

        role = self._guidance_role(is_self=is_self)
        auto_submitted = None
        if avaliacao.etapa == Avaliacao.Etapa.AVALIACAO:
            auto_submitted = self_assessment_submitted(avaliacao)
        return {
            'next_step': resolve_next_step(
                role=role,
                etapa=avaliacao.etapa,
                avaliacao_pk=avaliacao.pk,
                has_open_ciclo=has_open_ciclo,
                vinculo_pendente=vinculo_pendente,
                concluida=concluida,
                owner_correction_kind=owner_correction_kind,
                self_assessment_submitted=auto_submitted,
            ),
            'stage_stepper': build_stage_stepper(
                etapa=avaliacao.etapa,
                has_open_ciclo=has_open_ciclo,
                vinculo_pendente=vinculo_pendente,
                concluida=concluida,
            ),
        }


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
        return Avaliacao.objects.select_related(
            'ciclo',
            'usuario',
            'usuario__cargo',
        )

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        self.object = self.get_object()
        if request.method == 'POST':
            if not self_assessment_editable(self.object):
                if self_assessment_submitted(self.object):
                    messages.error(request, MSG_AUTOAVALIACAO_JA_ENVIADA)
                else:
                    messages.error(
                        request,
                        'A autoavaliação só está disponível na etapa de avaliação '
                        'de um ciclo aberto.',
                    )
                return HttpResponseRedirect(reverse('dashboard:personal'))
        elif not self_assessment_viewable(self.object):
            messages.error(
                request,
                'A autoavaliação só está disponível na etapa de avaliação '
                'de um ciclo aberto.',
            )
            return HttpResponseRedirect(reverse('dashboard:personal'))
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        action = request.POST.get('action', 'save')
        pode_editar = self_assessment_editable(self.object)
        formset = SelfAssessmentFormSet(
            request.POST,
            queryset=self._linhas_queryset(),
            form_kwargs={'editable': pode_editar},
        )
        if action == 'submit':
            return self._post_submit(request, formset)
        return self._post_save(request, formset)

    def _post_save(self, request, formset):
        if formset.is_valid():
            formset.save()
            messages.success(request, 'Autoavaliação salva com sucesso.')
            return HttpResponseRedirect(
                reverse('reviews:self_assessment', kwargs={'pk': self.object.pk}),
            )

        context = self.get_context_data(object=self.object, formset=formset)
        return self.render_to_response(context)

    def _post_submit(self, request, formset):
        if not formset.is_valid():
            context = self.get_context_data(object=self.object, formset=formset)
            return self.render_to_response(context)

        formset.save()
        if not self_assessment_complete(self.object):
            messages.error(request, MSG_AUTOAVALIACAO_ENVIO_INCOMPLETO)
            return HttpResponseRedirect(
                reverse('reviews:self_assessment', kwargs={'pk': self.object.pk}),
            )

        try:
            submit_self_assessment(self.object)
        except ValidationError as exc:
            messages.error(request, exc.messages[0])
            return HttpResponseRedirect(
                reverse('reviews:self_assessment', kwargs={'pk': self.object.pk}),
            )

        messages.success(
            request,
            'Autoavaliação enviada com sucesso. Não é mais possível alterá-la.',
        )
        return HttpResponseRedirect(
            reverse('reviews:self_assessment', kwargs={'pk': self.object.pk}),
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        pode_editar = self_assessment_editable(self.object)
        formset = kwargs.get('formset')
        if formset is None:
            formset = SelfAssessmentFormSet(
                queryset=self._linhas_queryset(),
                form_kwargs={'editable': pode_editar},
            )

        context.update(
            {
                'formset': formset,
                'pode_editar': pode_editar,
                'autoavaliacao_enviada': self_assessment_submitted(self.object),
                'linhas_vazias': len(formset.forms) == 0,
                'colaborador': self.object.usuario,
                'metas_ciclo': self._metas_ciclo(),
                **self._progress_flags(formset),
            },
        )
        return context

    def _metas_ciclo(self):
        return (
            Meta.objects.filter(
                usuario_id=self.object.usuario_id,
                objetivo_estrategico__ciclo_id=self.object.ciclo_id,
            )
            .select_related('objetivo_estrategico')
            .order_by('id')
        )

    @staticmethod
    def _nota_autoavaliacao_presente(form) -> bool:
        """True se a linha já tem nota de autoavaliação (formset bound ou instance)."""
        if form.is_bound:
            raw = form.data.get(form.add_prefix('nota_autoavaliacao'), '')
            if isinstance(raw, str):
                return raw.strip() != ''
            return raw is not None
        return form.instance.nota_autoavaliacao is not None

    def _progress_flags(self, formset) -> dict:
        """Flags de progresso para UI (T026) — só leitura de formset/queryset.

        Conta linhas sem ``nota_autoavaliacao``. Não chama ``calcular_nota_*``.
        """
        total = len(formset.forms)
        if total == 0:
            qs = self._linhas_queryset()
            total = qs.count()
            restantes = qs.filter(nota_autoavaliacao__isnull=True).count()
        else:
            restantes = sum(
                1
                for form in formset.forms
                if not self._nota_autoavaliacao_presente(form)
            )
        preenchidas = total - restantes
        return {
            'notas_total': total,
            'notas_preenchidas': preenchidas,
            'notas_restantes': restantes,
            'avaliacao_progresso_completo': total > 0 and restantes == 0,
        }

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
    queryset = Avaliacao.objects.select_related(
        'ciclo',
        'usuario',
        'usuario__area',
        'usuario__cargo',
    )
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

        if not leader_assessment_permitted(self.object):
            messages.error(request, MSG_AUTOAVALIACAO_INCOMPLETA)
            return HttpResponseRedirect(reverse('dashboard:personal'))

        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        if not can_leader_assess(request.user, self.object):
            return HttpResponseRedirect(reverse('dashboard:personal'))

        if not leader_assessment_permitted(self.object):
            messages.error(request, MSG_AUTOAVALIACAO_INCOMPLETA)
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
                'autoavaliacao_enviada_em': self.object.autoavaliacao_enviada_em,
                'metas_ciclo': self._metas_ciclo(),
                'rotulos_por_form': self._rotulos_por_form_json(formset),
                'pode_avancar': pode_avancar,
                'avanco_desabilitado': not pode_avancar,
                'motivo_bloqueio_avanco': motivo_bloqueio_avanco,
                **self._progress_flags(formset),
            },
        )
        return context

    @staticmethod
    def _rotulos_por_form_json(formset) -> str:
        """Mapa field_name → rótulos da escala (só UI; validação permanece no backend)."""
        payload = {}
        for form in formset.forms:
            competencia = getattr(form.instance, 'competencia', None)
            escala = getattr(competencia, 'escala', None) if competencia else None
            rotulos = getattr(escala, 'rotulos_por_nivel', None) or {}
            payload[form.add_prefix('nota_lider')] = {
                str(chave): str(valor) for chave, valor in rotulos.items()
            }
        return json.dumps(payload)

    def _metas_ciclo(self):
        return (
            Meta.objects.filter(
                usuario_id=self.object.usuario_id,
                objetivo_estrategico__ciclo_id=self.object.ciclo_id,
            )
            .select_related('objetivo_estrategico')
            .order_by('id')
        )

    @staticmethod
    def _nota_lider_presente(form) -> bool:
        """True se a linha já tem nota do líder (formset bound ou instance)."""
        if form.is_bound:
            raw = form.data.get(form.add_prefix('nota_lider'), '')
            if isinstance(raw, str):
                return raw.strip() != ''
            return raw is not None
        return form.instance.nota_lider is not None

    def _progress_flags(self, formset) -> dict:
        """Flags de progresso para UI (FR-008) — só leitura de formset/queryset.

        Conta linhas sem ``nota_lider``. Não chama ``calcular_nota_*``.
        """
        total = len(formset.forms)
        if total == 0:
            # Formset vazio: cair no queryset para consistência com o banco.
            qs = self._linhas_queryset()
            total = qs.count()
            restantes = qs.filter(nota_lider__isnull=True).count()
        else:
            restantes = sum(
                1 for form in formset.forms if not self._nota_lider_presente(form)
            )
        preenchidas = total - restantes
        return {
            'notas_total': total,
            'notas_preenchidas': preenchidas,
            'notas_restantes': restantes,
            'avaliacao_progresso_completo': total > 0 and restantes == 0,
        }

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
            Avaliacao.objects.select_related(
                'ciclo',
                'usuario',
                'usuario__line_manager',
            ).get(pk=pk)
        )
    except Avaliacao.DoesNotExist as exc:
        raise Http404() from exc

    if not user_in_scope(request.user, avaliacao.usuario_id):
        log_scope_denied(request.user, avaliacao)
        raise Http404()
    return avaliacao


class FeedbackListView(LoginRequiredMixin, ScopedObjectMixin, HtmxPaginatedListMixin, ListView):
    """Histórico de feedbacks da avaliação (escopo ``avaliacao__usuario``)."""

    model = Feedback
    template_name = 'reviews/feedback_list.html'
    partial_template_name = 'reviews/feedback_list_partial.html'
    context_object_name = 'feedbacks'
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

        feedback_pendente_ciencia = None
        feedback_lider = None
        if user.pk == self.avaliacao.usuario_id:
            lider_feedbacks = (
                Feedback.objects.filter(
                    avaliacao_id=self.avaliacao.pk,
                    tipo=Feedback.Tipo.LIDER,
                )
                .select_related('autor')
                .order_by('-created_at', 'id')
            )
            feedback_lider = lider_feedbacks.first()
            for feedback in lider_feedbacks:
                if can_acknowledge_feedback(user, feedback):
                    feedback_pendente_ciencia = feedback
                    break

        context.update(
            {
                'avaliacao': self.avaliacao,
                'colaborador': self.avaliacao.usuario,
                'feedback_rows': rows,
                'feedback_lider': feedback_lider,
                'feedback_pendente_ciencia': feedback_pendente_ciencia,
                'feedback_resumo': build_feedback_resumo(self.avaliacao),
                'is_colaborador_view': user.pk == self.avaliacao.usuario_id,
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
        destinatario, destinatario_rotulo = feedback_destinatario(
            self.avaliacao,
            self.request.user,
        )
        context.update(
            {
                'avaliacao': self.avaliacao,
                'colaborador': self.avaliacao.usuario,
                'destinatario': destinatario,
                'destinatario_rotulo': destinatario_rotulo,
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

        if request.POST.get('declaro_ciencia') != 'on':
            messages.error(
                request,
                'Confirme que leu o feedback antes de dar ciência.',
            )
            return HttpResponseRedirect(list_url)

        feedback.ciente_em = timezone.now()
        feedback.save(update_fields=['ciente_em', 'updated_at'])

        avaliacao = feedback.avaliacao
        if not avaliacao.concluida:
            avaliacao.concluida = True
            avaliacao.save(update_fields=['concluida', 'updated_at'])

        messages.success(request, 'Ciência registrada com sucesso.')
        return HttpResponseRedirect(list_url)
