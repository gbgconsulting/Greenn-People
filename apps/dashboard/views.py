from decimal import Decimal

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Avg, Count, Q
from django.views.generic import ListView, TemplateView

from apps.accounts.models import CustomUser
from apps.accounts.services.scope import get_visible_users
from apps.core.mixins import (
    HtmxPaginatedListMixin,
    RequiresAdminMixin,
    RequiresLeaderMixin,
    RequiresManagerOrAdminMixin,
)
from apps.cycles.models import Ciclo
from apps.dashboard.chart_payloads import (
    SEM_AVALIACAO_KEY,
    SEM_AVALIACAO_LABEL,
    aderencia_distribution_payload,
    categorical_counts_payload,
    empty_series_payload,
)
from apps.dashboard.models import AderenciaSnapshot
from apps.dashboard.services.structure import (
    gaps_by_area,
    gaps_by_cargo,
    leaders_with_adherence,
)
from apps.goals.forms import get_open_ciclo
from apps.organization.models import Area, Cargo
from apps.reviews.models import Avaliacao
from apps.reviews.services.evaluation import build_fr005_context
from apps.talent.services.classification import get_visible_classification_for_collaborator

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
        context['classificacao'] = get_visible_classification_for_collaborator(
            self.request.user,
        )
        return context


class TeamDashboardView(
    LoginRequiredMixin,
    RequiresLeaderMixin,
    HtmxPaginatedListMixin,
    ListView,
):
    """Painel do time: lista colaboradores no escopo hierárquico (US2 / FR-006)."""

    template_name = 'dashboard/team.html'
    partial_template_name = 'dashboard/team_list_partial.html'
    context_object_name = 'membros'

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
        # Agregação do chart usa o queryset completo (R2/R3) — não object_list.
        context['chart_escopo_status'] = self._chart_escopo_status(ciclo)
        return context

    def _chart_escopo_status(self, ciclo: Ciclo | None) -> dict:
        """Conta etapas (+ sem_avaliacao) sobre todo get_visible_users do escopo.

        Empty honesto (has_data false + empty_state via _chart_block):
        sem ciclo / sem membros / sem avaliações úteis — sem série fictícia.
        """
        title = 'Status do escopo no ciclo'
        etapa_keys = [choice.value for choice in Avaliacao.Etapa]
        ordered_keys = [*etapa_keys, SEM_AVALIACAO_KEY]
        labels_by_key = {
            **dict(Avaliacao.Etapa.choices),
            SEM_AVALIACAO_KEY: SEM_AVALIACAO_LABEL,
        }

        if ciclo is None:
            # Sem ciclo: empty PT-BR — canvas não inicializa (FR-006 / T016).
            return empty_series_payload(
                chart_id='chart-escopo-status',
                chart_type='bar',
                title=title,
                empty_message=(
                    'Não há ciclo aberto para exibir o status do escopo.'
                ),
            )

        # Universo = get_queryset() completo; nunca só a página HTMX (FR-011 / R2).
        membro_ids = list(self.get_queryset().values_list('pk', flat=True))
        if not membro_ids:
            return empty_series_payload(
                chart_id='chart-escopo-status',
                chart_type='bar',
                title=title,
                empty_message=(
                    'Não há colaboradores no seu escopo para exibir status.'
                ),
            )

        etapa_por_usuario = dict(
            Avaliacao.objects.filter(
                ciclo=ciclo,
                usuario_id__in=membro_ids,
            ).values_list('usuario_id', 'etapa'),
        )
        if not etapa_por_usuario:
            # Membros sem avaliação no ciclo → empty honesto (sem só “sem_avaliacao”).
            return empty_series_payload(
                chart_id='chart-escopo-status',
                chart_type='bar',
                title=title,
                empty_message=(
                    'Não há dados de ciclo no seu escopo para exibir.'
                ),
            )

        key_counts = {key: 0 for key in ordered_keys}
        for usuario_id in membro_ids:
            etapa = etapa_por_usuario.get(usuario_id)
            if etapa is None or etapa not in key_counts:
                key_counts[SEM_AVALIACAO_KEY] += 1
            else:
                key_counts[etapa] += 1

        return categorical_counts_payload(
            key_counts,
            ordered_keys=ordered_keys,
            labels_by_key=labels_by_key,
            chart_id='chart-escopo-status',
            chart_type='bar',
            title=title,
            empty_message=(
                'Não há dados de ciclo no seu escopo para exibir.'
            ),
        )


class AdherenceListView(
    LoginRequiredMixin,
    RequiresManagerOrAdminMixin,
    HtmxPaginatedListMixin,
    ListView,
):
    """Lista snapshots de aderência (FR-018) — só leitura, sem recálculo síncrono."""

    model = AderenciaSnapshot
    template_name = 'dashboard/adherence.html'
    partial_template_name = 'dashboard/adherence_list_partial.html'
    context_object_name = 'snapshots'

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


class StructureDashboardView(LoginRequiredMixin, RequiresManagerOrAdminMixin, TemplateView):
    """Painel de estrutura: líderes, aderência e lacunas por área/cargo (FR-019 / RF-29)."""

    template_name = 'dashboard/structure.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        ciclo = self._resolve_ciclo()
        area_id = self._parse_optional_int('area')
        cargo_id = self._parse_optional_int('cargo')
        visible = get_visible_users(self.request.user).filter(is_active=True)

        context['ciclo_filtro'] = ciclo
        context['ciclo_aberto'] = get_open_ciclo()
        context['ciclos'] = Ciclo.objects.order_by('-data_inicio', 'nome')
        context['areas'] = Area.objects.filter(is_active=True).order_by('nome')
        context['cargos'] = Cargo.objects.filter(is_active=True).order_by('nivel', 'nome')
        context['filtro_area_id'] = area_id
        context['filtro_cargo_id'] = cargo_id
        context['lideres_resumo'] = leaders_with_adherence(
            visible,
            ciclo,
            area_id=area_id,
            cargo_id=cargo_id,
        )
        context['lacunas_por_area'] = gaps_by_area(
            visible,
            ciclo,
            area_id=area_id,
            cargo_id=cargo_id,
        )
        context['lacunas_por_cargo'] = gaps_by_cargo(
            visible,
            ciclo,
            area_id=area_id,
            cargo_id=cargo_id,
        )
        return context

    def _resolve_ciclo(self) -> Ciclo | None:
        ciclo_id = self.request.GET.get('ciclo')
        if ciclo_id:
            try:
                return Ciclo.objects.filter(pk=int(ciclo_id)).first()
            except (TypeError, ValueError):
                return get_open_ciclo()
        return get_open_ciclo()

    def _parse_optional_int(self, key: str) -> int | None:
        raw = self.request.GET.get(key)
        if not raw:
            return None
        try:
            return int(raw)
        except (TypeError, ValueError):
            return None


class AdminDashboardView(LoginRequiredMixin, RequiresAdminMixin, TemplateView):
    """Painel RH: conclusão do ciclo e aderência via snapshots (SC-006 / FR-018)."""

    template_name = 'dashboard/admin.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        ciclo_aberto = get_open_ciclo()
        ciclo_indicador = ciclo_aberto or (
            Ciclo.objects.filter(status=Ciclo.Status.ENCERRADO)
            .order_by('-data_fim', '-pk')
            .first()
        )
        context['ciclo_aberto'] = ciclo_aberto
        context['ciclo_indicador'] = ciclo_indicador
        context['ciclos_resumo'] = self._ciclos_resumo()
        context['avaliacoes_resumo'] = self._avaliacoes_resumo(ciclo_indicador)
        ciclo_aderencia = ciclo_aberto or ciclo_indicador
        context['aderencia_resumo'] = self._aderencia_resumo(ciclo_aderencia)
        context['snapshots_destaque'] = self._snapshots_destaque(ciclo_aderencia)
        context['chart_aderencia_distribuicao'] = (
            self._chart_aderencia_distribuicao(ciclo_aderencia)
        )
        context['chart_ciclo_progresso'] = self._chart_ciclo_progresso(
            ciclo_indicador,
        )
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

        # Campo persistido (congelado em close_cycle); durante ciclo aberto
        # também reflete ciência via FeedbackAcknowledgeView.
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

    def _chart_aderencia_distribuicao(self, ciclo: Ciclo | None) -> dict:
        """Conta snapshots do ciclo por faixa via `aderencia_status` (contrato admin)."""
        if ciclo is None:
            # Sem ciclo: empty honesto — sem faixas zeradas inventadas (FR-006).
            return empty_series_payload(
                chart_id='chart-aderencia-distribuicao',
                chart_type='doughnut_or_bar',
                title='Distribuição de aderência',
                empty_message=(
                    'Não há ciclo disponível para exibir a distribuição '
                    'de aderência.'
                ),
            )
        status_keys = [
            aderencia_status(percentual)
            for percentual in AderenciaSnapshot.objects.filter(
                ciclo=ciclo,
            ).values_list('percentual', flat=True)
        ]
        # Zero snapshots → has_data false + empty_message PT-BR do helper.
        return aderencia_distribution_payload(status_keys)

    def _chart_ciclo_progresso(self, ciclo: Ciclo | None) -> dict:
        """Conta avaliações do ciclo por `Avaliacao.Etapa` (contrato admin)."""
        if ciclo is None:
            # Sem ciclo: empty honesto — sem barras de etapa inventadas (FR-006).
            return empty_series_payload(
                chart_id='chart-ciclo-progresso',
                chart_type='bar',
                title='Progresso das avaliações no ciclo',
                empty_message=(
                    'Não há ciclo disponível para exibir o progresso '
                    'das avaliações.'
                ),
            )
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
        # Zero avaliações → has_data false + mensagem PT-BR (sem série fictícia).
        return categorical_counts_payload(
            key_counts,
            ordered_keys=etapa_keys,
            labels_by_key=labels_by_key,
            chart_id='chart-ciclo-progresso',
            chart_type='bar',
            title='Progresso das avaliações no ciclo',
            empty_message=(
                'Não há avaliações neste ciclo para exibir progresso.'
            ),
        )
