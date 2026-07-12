from decimal import Decimal

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Avg, Count, Exists, OuterRef, Q
from django.views.generic import ListView, TemplateView

from apps.accounts.models import CustomUser
from apps.accounts.services.scope import get_visible_users
from apps.core.mixins import RequiresAdminMixin, RequiresLeaderMixin, RequiresManagerOrAdminMixin
from apps.cycles.models import Ciclo
from apps.dashboard.models import AderenciaSnapshot
from apps.goals.forms import get_open_ciclo
from apps.reviews.models import Avaliacao, Feedback
from apps.reviews.services.evaluation import build_fr005_context

# KPI liderança (PRD): ≥ 80% alta; faixa intermediária; abaixo = baixa.
_ADERENCIA_ALTA = Decimal('80')
_ADERENCIA_MEDIA = Decimal('50')


def aderencia_status(percentual: Decimal | None) -> str:
    """Map adherence % to badge_status keys: alta | media | baixa."""
    if percentual is None:
        return 'baixa'
    if percentual >= _ADERENCIA_ALTA:
        return 'alta'
    if percentual >= _ADERENCIA_MEDIA:
        return 'media'
    return 'baixa'


class PersonalDashboardView(LoginRequiredMixin, TemplateView):
    """Painel pessoal com nivel esperado e nota atual (FR-005)."""

    template_name = 'dashboard/personal.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(build_fr005_context(self.request.user))
        return context


class TeamDashboardView(LoginRequiredMixin, RequiresLeaderMixin, ListView):
    """Painel do time: lista colaboradores no escopo hierárquico (US2 / FR-006)."""

    template_name = 'dashboard/team.html'
    context_object_name = 'membros'
    paginate_by = 20

    def get_queryset(self):
        return (
            get_visible_users(self.request.user)
            .exclude(pk=self.request.user.pk)
            .filter(is_active=True)
            .select_related('area', 'cargo')
            .order_by('nome', 'email')
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        ciclo = get_open_ciclo()
        context['ciclo_aberto'] = ciclo

        membros: list[CustomUser] = list(context['object_list'])
        avaliacoes_por_usuario: dict[int, Avaliacao] = {}
        if ciclo is not None and membros:
            avaliacoes_por_usuario = {
                avaliacao.usuario_id: avaliacao
                for avaliacao in Avaliacao.objects.filter(
                    ciclo=ciclo,
                    usuario_id__in=[m.pk for m in membros],
                ).select_related('ciclo')
            }

        context['membros_resumo'] = [
            {
                'usuario': membro,
                'avaliacao': avaliacoes_por_usuario.get(membro.pk),
            }
            for membro in membros
        ]
        return context


class AdherenceListView(LoginRequiredMixin, RequiresManagerOrAdminMixin, ListView):
    """Lista snapshots de aderência (FR-018) — só leitura, sem recálculo síncrono."""

    model = AderenciaSnapshot
    template_name = 'dashboard/adherence.html'
    context_object_name = 'snapshots'
    paginate_by = 20

    def get_queryset(self):
        qs = (
            AderenciaSnapshot.objects.select_related('lider', 'lider__area', 'ciclo')
            .order_by('-percentual', 'lider__nome', 'lider__email')
        )

        ciclo = self._resolve_ciclo()
        if ciclo is not None:
            qs = qs.filter(ciclo=ciclo)

        user = self.request.user
        if not getattr(user, 'is_admin', False):
            visible = get_visible_users(user)
            qs = qs.filter(lider__in=visible)

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        ciclo = self._resolve_ciclo()
        context['ciclo_filtro'] = ciclo
        context['ciclo_aberto'] = get_open_ciclo()
        context['ciclos'] = Ciclo.objects.order_by('-data_inicio', 'nome')
        context['snapshots_resumo'] = [
            {
                'snapshot': snap,
                'status': aderencia_status(snap.percentual),
            }
            for snap in context['object_list']
        ]
        return context

    def _resolve_ciclo(self) -> Ciclo | None:
        ciclo_id = self.request.GET.get('ciclo')
        if ciclo_id:
            try:
                return Ciclo.objects.filter(pk=int(ciclo_id)).first()
            except (TypeError, ValueError):
                return get_open_ciclo()
        return get_open_ciclo()


class AdminDashboardView(LoginRequiredMixin, RequiresAdminMixin, TemplateView):
    """Painel RH: conclusão do ciclo e aderência via snapshots (SC-006 / FR-018)."""

    template_name = 'dashboard/admin.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        ciclo = get_open_ciclo()
        context['ciclo_aberto'] = ciclo
        context['ciclos_resumo'] = self._ciclos_resumo()
        context['avaliacoes_resumo'] = self._avaliacoes_resumo(ciclo)
        context['aderencia_resumo'] = self._aderencia_resumo(ciclo)
        context['snapshots_destaque'] = self._snapshots_destaque(ciclo)
        return context

    def _ciclos_resumo(self) -> dict:
        totals = Ciclo.objects.aggregate(
            total=Count('pk'),
            abertos=Count('pk', filter=Q(status=Ciclo.Status.ABERTO)),
            encerrados=Count('pk', filter=Q(status=Ciclo.Status.ENCERRADO)),
        )
        total = totals['total'] or 0
        encerrados = totals['encerrados'] or 0
        percentual = (
            (Decimal(encerrados) * Decimal('100') / Decimal(total)).quantize(
                Decimal('0.01'),
            )
            if total
            else None
        )
        return {
            'total': total,
            'abertos': totals['abertos'] or 0,
            'encerrados': encerrados,
            'percentual_encerrados': percentual,
        }

    def _avaliacoes_resumo(self, ciclo: Ciclo | None) -> dict:
        if ciclo is None:
            return {
                'total': 0,
                'concluidas': 0,
                'percentual_concluidas': None,
            }

        feedback_ciente = Feedback.objects.filter(
            avaliacao_id=OuterRef('pk'),
            tipo=Feedback.Tipo.LIDER,
            ciente_em__isnull=False,
        )
        qs = Avaliacao.objects.filter(ciclo=ciclo).annotate(
            concluida=Exists(feedback_ciente),
        )
        totals = qs.aggregate(
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
        }

    def _aderencia_resumo(self, ciclo: Ciclo | None) -> dict:
        if ciclo is None:
            return {
                'media': None,
                'total_lideres': 0,
                'status': 'baixa',
            }
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

    def _snapshots_destaque(self, ciclo: Ciclo | None) -> list[dict]:
        if ciclo is None:
            return []
        qs = (
            AderenciaSnapshot.objects.filter(ciclo=ciclo)
            .select_related('lider', 'lider__area')
            .order_by('percentual', 'lider__nome')[:10]
        )
        return [
            {
                'snapshot': snap,
                'status': aderencia_status(snap.percentual),
            }
            for snap in qs
        ]
