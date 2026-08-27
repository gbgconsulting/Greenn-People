from decimal import Decimal

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
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
    CHART_TYPE_BAR,
    CHART_TYPE_BAR_HORIZONTAL,
    CHART_TYPE_DOUGHNUT,
    CHART_TYPE_RADAR,
    DENSITY_TOP_N,
    EMPTY_KIND_COPY,
    EMPTY_KIND_ESCOPO,
    EMPTY_KIND_OPERACIONAL,
    EMPTY_KIND_SEM_DADO,
    EMPTY_KIND_SEM_NOTA,
    SEM_AVALIACAO_KEY,
    SEM_AVALIACAO_LABEL,
    aderencia_distribution_payload,
    categorical_counts_payload,
    empty_kind_payload,
    grouped_series_payload,
    top_n_with_others,
)
from apps.dashboard.models import AderenciaSnapshot
from apps.dashboard.services.ciclo_options import (
    grouped_ciclo_options,
    grouped_ciclo_options_for_user,
    resolve_operational_ciclo,
    resolve_personal_ciclo,
)
from apps.dashboard.services.history import (
    build_history_kpis,
    build_stage_history,
    is_history_mode,
    resolve_history_ciclo_selecionado,
    resolve_history_ciclos,
)
from apps.dashboard.services.structure import (
    build_structure_coverage,
    distinct_cargo_count,
    gaps_by_area,
    gaps_by_cargo,
    leaders_with_adherence,
    partition_gap_rows,
)
from apps.goals.forms import get_open_ciclo
from apps.organization.models import Area, Cargo
from apps.reviews.models import Avaliacao
from apps.reviews.services.evaluation import build_fr005_context
from apps.reviews.services.guidance import (
    build_stage_stepper,
    detect_owner_correction_kind,
    resolve_next_step,
)
from apps.talent.services.classification import get_visible_classification_for_collaborator

# KPI liderança (PRD): ≥ 80% alta; faixa intermediária; abaixo = baixa.
_ADERENCIA_ALTA = Decimal('80')
_ADERENCIA_MEDIA = Decimal('50')
_ADERENCIA_NIVEL_FILTERS = frozenset({'alta', 'media', 'baixa'})


def aderencia_status(percentual: Decimal | None) -> str:
    """Map adherence % to badge_status keys: alta | media | baixa."""
    if percentual is None:
        return 'baixa'
    if percentual >= _ADERENCIA_ALTA:
        return 'alta'
    if percentual >= _ADERENCIA_MEDIA:
        return 'media'
    return 'baixa'


def parse_optional_int(request, key: str) -> int | None:
    """Parse GET ``key`` as int; vazio/inválido → None (não quebra o filtro)."""
    raw = request.GET.get(key)
    if not raw:
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


class PersonalDashboardView(LoginRequiredMixin, TemplateView):
    """Painel pessoal com nivel esperado e nota atual (FR-005)."""

    template_name = 'dashboard/personal.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        # Badge / “há aberto?” — nunca o ciclo só porque veio em ?ciclo=.
        ciclo_aberto = get_open_ciclo()
        # Dados: aberto (se participa), ou arquivo só com ?ciclo= explícito
        # e participação (nunca lista/exibe ciclo alheio).
        ciclo = resolve_personal_ciclo(self.request, user)
        fr005 = build_fr005_context(user, ciclo=ciclo)
        # Defesa em profundidade: avaliação no contexto só pode ser do request.user.
        avaliacao = fr005.get('avaliacao')
        if avaliacao is not None and avaliacao.usuario_id != user.pk:
            raise PermissionDenied
        # build_fr005 nomeia o ciclo resolvido como ciclo_aberto — corrigir badge.
        fr005['ciclo_aberto'] = ciclo_aberto
        context.update(fr005)
        context['ciclo_selecionado'] = ciclo
        context['ciclo_filtro'] = ciclo
        context['grouped_ciclo_options'] = grouped_ciclo_options_for_user(
            user,
            q=self.request.GET.get('q'),
        )
        context['classificacao'] = get_visible_classification_for_collaborator(
            user,
        )
        context['chart_gaps_competencia'] = self._chart_gaps_competencia(context)
        context.update(self._guidance_presentation_context(context, ciclo=ciclo))
        return context

    def _guidance_role(self) -> str:
        """Papel de apresentação a partir de flags já existentes (sem AuthZ nova)."""
        user = self.request.user
        if getattr(user, 'is_admin', False):
            return 'rh'
        if user.is_leader:
            return 'lider'
        return 'colaborador'

    def _guidance_presentation_context(
        self,
        fr005: dict,
        *,
        ciclo: Ciclo | None,
    ) -> dict:
        """Injeta ``next_step`` + ``stage_stepper`` só via ``guidance.py`` (FR-013).

        CTA de avanço só no ciclo **aberto** exibido. Arquivo = leitura
        (``concluida``), sem inventar etapa no encerrado.
        """
        avaliacao = fr005.get('avaliacao')
        viewing_open = (
            ciclo is not None and ciclo.status == Ciclo.Status.ABERTO
        )

        etapa = None
        avaliacao_pk = None
        concluida = False
        owner_correction_kind = None
        if avaliacao is not None:
            etapa = avaliacao.etapa
            avaliacao_pk = avaliacao.pk
            concluida = bool(avaliacao.concluida)
            # FR-009 / T028: painel do dono após reprovação (leitura).
            owner_correction_kind = detect_owner_correction_kind(avaliacao)

        if viewing_open:
            has_open_ciclo = True
            # Contrato: vínculo ou avaliação pendente → copy sem CTA inventado.
            vinculo_pendente = bool(fr005.get('vinculo_pendente')) or (
                avaliacao is None
            )
        elif avaliacao is not None:
            # Ciclo encerrado com participação: leitura (sem CTA de avanço).
            has_open_ciclo = True
            concluida = True
            vinculo_pendente = False
            owner_correction_kind = None
        else:
            has_open_ciclo = False
            vinculo_pendente = bool(fr005.get('vinculo_pendente'))

        return {
            'next_step': resolve_next_step(
                role=self._guidance_role(),
                etapa=etapa,
                avaliacao_pk=avaliacao_pk,
                has_open_ciclo=has_open_ciclo,
                vinculo_pendente=vinculo_pendente,
                concluida=concluida,
                owner_correction_kind=owner_correction_kind,
            ),
            'stage_stepper': build_stage_stepper(
                etapa=etapa,
                has_open_ciclo=has_open_ciclo,
                vinculo_pendente=vinculo_pendente,
                concluida=concluida,
            ),
        }

    def _chart_gaps_competencia(self, fr005: dict) -> dict:
        """Radar esperado × nota a partir de ``competencias_resumo`` (US1).

        Type canônico ``radar`` (chart-catalog) — só apresentação; mesmo
        shape multi-série de ``bar_grouped``. Empty honesto via kinds D (012)
        + ``_chart_block``: vínculo pendente / lista vazia → ``sem_dado``;
        nenhuma nota comparável → ``sem_nota``. Densidade: Top-N por |gap|
        só entre competências **com nota**; resto omitido (sem média / sem
        rótulo ``Outros``). ``null`` em ``nota_atual`` permanece null — não
        vira 0 (FR-006). MUST NOT ler ``visao=`` (FR-016 — pessoal sem tendência).
        """
        title = 'Esperado × nota por competência'
        chart_type = CHART_TYPE_RADAR
        chart_id = 'chart-gaps-competencia'

        if fr005.get('vinculo_pendente'):
            return empty_kind_payload(
                kind=EMPTY_KIND_SEM_DADO,
                chart_id=chart_id,
                chart_type=chart_type,
                title=title,
            )

        competencias: list[dict] = list(fr005.get('competencias_resumo') or [])
        if not competencias:
            return empty_kind_payload(
                kind=EMPTY_KIND_SEM_DADO,
                chart_id=chart_id,
                chart_type=chart_type,
                title=title,
            )

        # Sem nenhuma nota → empty honesto (não desenhar só níveis esperados).
        if all(item.get('nota_atual') is None for item in competencias):
            return empty_kind_payload(
                kind=EMPTY_KIND_SEM_NOTA,
                chart_id=chart_id,
                chart_type=chart_type,
                title=title,
            )

        # Top-N por |gap| com nota; resto omitido (sem média inventada).
        dense = top_n_with_others(
            competencias,
            n=DENSITY_TOP_N,
            strategy='gap',
        )

        labels: list[str] = []
        esperado_values: list[float | None] = []
        nota_values: list[float | None] = []
        for item in dense:
            competencia = item.get('competencia')
            labels.append(
                getattr(competencia, 'nome', '') if competencia is not None else '',
            )
            nivel = item.get('nivel_esperado')
            esperado_values.append(float(nivel) if nivel is not None else None)
            nota = item.get('nota_atual')
            # null permanece null — não vira 0 inventado (FR-006 / contrato).
            nota_values.append(float(nota) if nota is not None else None)

        return grouped_series_payload(
            chart_id=chart_id,
            chart_type=chart_type,
            title=title,
            labels=labels,
            series=[
                {
                    'key': 'nivel_esperado',
                    'label': 'Nível esperado',
                    'values': esperado_values,
                },
                {
                    'key': 'nota_atual',
                    'label': 'Nota atual',
                    'values': nota_values,
                },
            ],
            empty_message=EMPTY_KIND_COPY[EMPTY_KIND_SEM_NOTA],
            has_data=True,
            total=len(labels),
        )


# Etapas em que o líder típico atua (mesmo conjunto do destaque amber no drill-down).
_TEAM_ATTENTION_ETAPAS = frozenset({
    Avaliacao.Etapa.AVALIACAO,
    Avaliacao.Etapa.APROVACAO_METAS,
    Avaliacao.Etapa.APROVACAO_RESULTADOS,
})
_TEAM_ATTENTION_PRIORITY = {
    Avaliacao.Etapa.AVALIACAO: 0,
    Avaliacao.Etapa.APROVACAO_METAS: 1,
    Avaliacao.Etapa.APROVACAO_RESULTADOS: 2,
}
# Densidade do ranking de atenção (eixo longo) — mesmo teto Top-N (N=8).
_TEAM_DESTAQUE_LIMIT = DENSITY_TOP_N

# Chips / barras do gráfico "Estágios do ciclo" — rótulos curtos alinhados ao chart.
_TEAM_ETAPA_CHIP_LABELS: dict[str, str] = {
    Avaliacao.Etapa.INPUT_METAS: 'Metas',
    Avaliacao.Etapa.APROVACAO_METAS: 'Aprov. metas',
    Avaliacao.Etapa.RESULTADOS: 'Resultados',
    Avaliacao.Etapa.APROVACAO_RESULTADOS: 'Aprov. result.',
    Avaliacao.Etapa.AVALIACAO: 'Avaliação',
    Avaliacao.Etapa.FEEDBACK: 'Feedback',
    SEM_AVALIACAO_KEY: 'Sem aval.',
}
_TEAM_ETAPA_FILTER_KEYS: frozenset[str] = frozenset(_TEAM_ETAPA_CHIP_LABELS)


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
    # Drill compacto ao lado do chart — evita scroll longo; paginação HTMX.
    paginate_by = DENSITY_TOP_N

    def get_base_queryset(self):
        """Escopo hierárquico completo — charts/KPIs MUST NOT usar filtros de lista."""
        # Escopo só do request.user — MUST NOT chamar get_visible_users de outro.
        return (
            get_visible_users(self.request.user)
            .exclude(pk=self.request.user.pk)
            .filter(is_active=True)
            .select_related('area', 'cargo')
            .order_by('nome', 'email')
        )

    def get_queryset(self):
        """Lista paginada: escopo + ``?busca=`` / ``?etapa=`` (só operacional)."""
        qs = self.get_base_queryset()
        busca = (self.request.GET.get('busca') or '').strip()
        if busca:
            qs = qs.filter(
                Q(nome__icontains=busca) | Q(cargo__nome__icontains=busca),
            )

        etapa = self._resolved_etapa_filter()
        if etapa:
            ciclo = resolve_operational_ciclo(self.request)
            if ciclo is None:
                qs = qs if etapa == SEM_AVALIACAO_KEY else qs.none()
            elif etapa == SEM_AVALIACAO_KEY:
                qs = qs.exclude(
                    pk__in=Avaliacao.objects.filter(ciclo=ciclo).values(
                        'usuario_id',
                    ),
                )
            else:
                qs = qs.filter(
                    pk__in=Avaliacao.objects.filter(
                        ciclo=ciclo,
                        etapa=etapa,
                    ).values('usuario_id'),
                )
        return qs

    def _resolved_etapa_filter(self) -> str:
        """``?etapa=`` válido só fora do modo histórico; inválido → ignorado."""
        if is_history_mode(self.request):
            return ''
        raw = (self.request.GET.get('etapa') or '').strip()
        if raw in _TEAM_ETAPA_FILTER_KEYS:
            return raw
        return ''

    def _resolved_busca_filter(self) -> str:
        return (self.request.GET.get('busca') or '').strip()

    def _inject_list_filters(self, context: dict) -> None:
        """Estado de busca/chips/contador para o partial HTMX."""
        busca = self._resolved_busca_filter()
        etapa = self._resolved_etapa_filter()
        context['filtro_busca'] = busca
        context['filtro_etapa'] = etapa
        context['filtro_ativo'] = bool(busca or etapa)
        context['filtro_busca_e_etapa'] = bool(busca and etapa)
        context['etapa_chips'] = [
            {'key': key, 'label': label}
            for key, label in _TEAM_ETAPA_CHIP_LABELS.items()
        ]
        # Total do escopo (sem filtros de lista) — "N de M colaboradores".
        context['total_escopo_lista'] = self.get_base_queryset().count()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Badge / “há aberto?” — nunca o ciclo só porque veio em ?ciclo=.
        ciclo_aberto = get_open_ciclo()
        # Dados: aberto, ou arquivo só com ?ciclo= explícito (T008 / T024).
        # MUST NOT cair no último encerrado em silêncio (FR-001 / FR-002).
        ciclo = resolve_operational_ciclo(self.request)
        context['ciclo_aberto'] = ciclo_aberto
        context['ciclo_selecionado'] = ciclo
        context['grouped_ciclo_options'] = grouped_ciclo_options(
            q=self.request.GET.get('q'),
        )
        context['visao'] = None
        context['chart_stage_history'] = None
        context['history_kpis'] = None
        self._inject_list_filters(context)

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

        # US3 / T031: tendência etapa/conclusão só com intenção explícita (GET).
        if is_history_mode(self.request):
            visible = self.get_base_queryset()
            janela = resolve_history_ciclos(self.request)
            ciclo_hist = resolve_history_ciclo_selecionado(self.request)
            if ciclo_hist is not None:
                context['ciclo_selecionado'] = ciclo_hist
            elif len(janela) == 1:
                context['ciclo_selecionado'] = janela[0]
            context['visao'] = 'historico'
            context['chart_stage_history'] = build_stage_history(visible, janela)
            context['history_kpis'] = build_history_kpis(visible, janela)
            # Aderência/gap não são o visual principal nesta fatia.
            context['chart_escopo_status'] = empty_kind_payload(
                kind=EMPTY_KIND_SEM_NOTA,
                chart_id='chart-escopo-status',
                chart_type=CHART_TYPE_BAR,
                title='Estágios do ciclo',
            )
            context['team_resumo'] = {
                'total_escopo': visible.count(),
                'aguardando_acao': None,
                'sem_avaliacao': None,
                'has_ciclo': False,
            }
            context['destaque_atencao'] = []
            return context

        # Agregação do chart/KPIs/destaque usa queryset completo (R2/R3) — não object_list.
        key_counts, etapa_por_usuario, membro_ids = self._scope_status_counts(ciclo)
        context['chart_escopo_status'] = self._chart_escopo_status(
            ciclo,
            key_counts=key_counts,
            membro_ids=membro_ids,
            etapa_por_usuario=etapa_por_usuario,
        )
        context['team_resumo'] = self._team_resumo(
            ciclo,
            key_counts=key_counts,
            membro_ids=membro_ids,
            etapa_por_usuario=etapa_por_usuario,
        )
        context['destaque_atencao'] = self._destaque_atencao(
            ciclo,
            etapa_por_usuario=etapa_por_usuario,
        )
        return context

    def _scope_status_counts(
        self,
        ciclo: Ciclo | None,
    ) -> tuple[dict[str, int] | None, dict[int, str], list[int]]:
        """Contagens etapa (+ sem_avaliacao) sobre todo o escopo visível.

        Retorna ``(key_counts, etapa_por_usuario, membro_ids)``.
        ``key_counts`` is ``None`` when empty honesto (sem ciclo / sem
        membros / sem avaliações no ciclo) — mesmos critérios do chart US1.
        """
        etapa_keys = [choice.value for choice in Avaliacao.Etapa]
        ordered_keys = [*etapa_keys, SEM_AVALIACAO_KEY]

        if ciclo is None:
            return None, {}, []

        membro_ids = list(self.get_base_queryset().values_list('pk', flat=True))
        if not membro_ids:
            return None, {}, []

        etapa_por_usuario = dict(
            Avaliacao.objects.filter(
                ciclo=ciclo,
                usuario_id__in=membro_ids,
            ).values_list('usuario_id', 'etapa'),
        )
        if not etapa_por_usuario:
            return None, {}, membro_ids

        key_counts = {key: 0 for key in ordered_keys}
        for usuario_id in membro_ids:
            etapa = etapa_por_usuario.get(usuario_id)
            if etapa is None or etapa not in key_counts:
                key_counts[SEM_AVALIACAO_KEY] += 1
            else:
                key_counts[etapa] += 1
        return key_counts, etapa_por_usuario, membro_ids

    def _team_resumo(
        self,
        ciclo: Ciclo | None,
        *,
        key_counts: dict[str, int] | None,
        membro_ids: list[int],
        etapa_por_usuario: dict[int, str],
    ) -> dict:
        """KPIs de apresentação (contagens etapa / pendências) — FR-004 / Freeze C.

        Só agrega o que já está no escopo; sem predicados AuthZ novos.
        """
        total_escopo = (
            len(membro_ids) if membro_ids else self.get_base_queryset().count()
        )
        if ciclo is None:
            return {
                'total_escopo': total_escopo,
                'aguardando_acao': None,
                'sem_avaliacao': None,
                'has_ciclo': False,
            }
        if key_counts is None:
            # Ciclo aberto mas sem avaliações úteis / escopo vazio.
            sem = total_escopo if total_escopo and not etapa_por_usuario else 0
            return {
                'total_escopo': total_escopo,
                'aguardando_acao': 0,
                'sem_avaliacao': sem,
                'has_ciclo': True,
            }
        aguardando = sum(
            key_counts.get(etapa, 0) for etapa in _TEAM_ATTENTION_ETAPAS
        )
        return {
            'total_escopo': total_escopo,
            'aguardando_acao': aguardando,
            'sem_avaliacao': key_counts.get(SEM_AVALIACAO_KEY, 0),
            'has_ciclo': True,
        }

    def _destaque_atencao(
        self,
        ciclo: Ciclo | None,
        *,
        etapa_por_usuario: dict[int, str],
    ) -> list[dict]:
        """Ranking acionável de quem precisa de atenção (FR-005).

        Subconjunto do escopo já visível em etapas de ação do líder; links
        para URLs já existentes. Limitado para leitura no first glance.
        """
        if ciclo is None or not etapa_por_usuario:
            return []

        attention_ids = [
            uid
            for uid, etapa in etapa_por_usuario.items()
            if etapa in _TEAM_ATTENTION_ETAPAS
        ]
        if not attention_ids:
            return []

        usuarios = {
            u.pk: u
            for u in self.get_base_queryset().filter(pk__in=attention_ids)
        }
        avaliacoes = {
            av.usuario_id: av
            for av in Avaliacao.objects.filter(
                ciclo=ciclo,
                usuario_id__in=attention_ids,
            ).select_related('ciclo')
        }

        items: list[dict] = []
        for usuario_id in attention_ids:
            usuario = usuarios.get(usuario_id)
            avaliacao = avaliacoes.get(usuario_id)
            if usuario is None or avaliacao is None:
                continue
            items.append({'usuario': usuario, 'avaliacao': avaliacao})

        items.sort(
            key=lambda item: (
                _TEAM_ATTENTION_PRIORITY.get(item['avaliacao'].etapa, 99),
                (item['usuario'].nome or '').lower(),
                (item['usuario'].email or '').lower(),
            ),
        )
        return items[:_TEAM_DESTAQUE_LIMIT]

    def _chart_escopo_status(
        self,
        ciclo: Ciclo | None,
        *,
        key_counts: dict[str, int] | None = None,
        membro_ids: list[int] | None = None,
        etapa_por_usuario: dict[int, str] | None = None,
    ) -> dict:
        """Conta etapas (+ sem_avaliacao) sobre todo get_visible_users do escopo.

        Pipeline fechado (sem Top-N). Barras verticais compactas (visão líder)
        monocromáticas com amber no gargalo — só apresentação.

        Empty honesto (has_data false + empty_state via _chart_block):
        sem ciclo resolvido → ``operacional``; sem membros → ``escopo``;
        sem avaliações úteis → ``sem_dado`` — sem série fictícia.
        """
        title = 'Estágios do ciclo'
        chart_type = CHART_TYPE_BAR
        chart_id = 'chart-escopo-status'
        etapa_keys = [choice.value for choice in Avaliacao.Etapa]
        ordered_keys = [*etapa_keys, SEM_AVALIACAO_KEY]
        # Rótulos curtos no eixo X — evita sobreposição no canvas do painel.
        labels_by_key = _TEAM_ETAPA_CHIP_LABELS

        if ciclo is None:
            return empty_kind_payload(
                kind=EMPTY_KIND_OPERACIONAL,
                chart_id=chart_id,
                chart_type=chart_type,
                title=title,
            )

        if membro_ids is None or etapa_por_usuario is None or key_counts is None:
            key_counts, etapa_por_usuario, membro_ids = self._scope_status_counts(
                ciclo,
            )

        if not membro_ids:
            return empty_kind_payload(
                kind=EMPTY_KIND_ESCOPO,
                chart_id=chart_id,
                chart_type=chart_type,
                title=title,
            )

        if key_counts is None:
            return empty_kind_payload(
                kind=EMPTY_KIND_SEM_DADO,
                chart_id=chart_id,
                chart_type=chart_type,
                title=title,
            )

        payload = categorical_counts_payload(
            key_counts,
            ordered_keys=ordered_keys,
            labels_by_key=labels_by_key,
            chart_id=chart_id,
            chart_type=chart_type,
            title=title,
            empty_message=EMPTY_KIND_COPY[EMPTY_KIND_SEM_DADO],
            highlight_max=True,
        )
        # Insight 1 linha do gargalo (DS storytelling) — mesmos counts, sem métrica nova.
        if payload.get('has_data'):
            values = list(payload.get('values') or [])
            labels = list(payload.get('labels') or [])
            if values and labels and any(v > 0 for v in values):
                max_index = max(range(len(values)), key=lambda i: values[i])
                gargalo = labels[max_index]
                payload['insight'] = (
                    f'Mais pessoas estão em {gargalo} — concentre a atenção aí.'
                )
        return payload


class AdherenceListView(
    LoginRequiredMixin,
    RequiresManagerOrAdminMixin,
    HtmxPaginatedListMixin,
    ListView,
):
    """Lista snapshots de aderência (FR-018) — só leitura, sem recálculo síncrono.

    US2 / T027: default ``resolve_operational_ciclo``; KPI + distribuição a
    partir do QS de escopo/ciclo/área (sem filtro de nível). Lista paginada
    HTMX ordenada por % ASC; ``?nivel=`` e ``?area=`` filtram no servidor.
    MUST NOT chamar ``compute_adherence`` / tasks.
    """

    model = AderenciaSnapshot
    template_name = 'dashboard/adherence.html'
    partial_template_name = 'dashboard/adherence_list_partial.html'
    context_object_name = 'snapshots'

    def get_queryset(self):
        qs = self._scoped_queryset()
        nivel = self._parse_nivel_filter()
        if nivel is not None:
            qs = self._apply_nivel_filter(qs, nivel)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Badge / “há aberto?” — nunca o ciclo só porque veio em ?ciclo=.
        ciclo_aberto = get_open_ciclo()
        # Dados: aberto, ou arquivo só com ?ciclo= explícito (T008 / T027).
        # MUST NOT cair no último encerrado em silêncio (FR-001 / FR-002).
        ciclo = self._resolve_ciclo()
        area_id = parse_optional_int(self.request, 'area')
        context['ciclo_filtro'] = ciclo
        context['ciclo_selecionado'] = ciclo
        context['ciclo_aberto'] = ciclo_aberto
        context['grouped_ciclo_options'] = grouped_ciclo_options(
            q=self.request.GET.get('q'),
        )
        # Mesmo catálogo de áreas da Estrutura — AuthZ continua no QS de líderes.
        context['areas'] = Area.objects.filter(is_active=True).order_by('nome')
        context['filtro_area_id'] = area_id
        context['filtro_nivel'] = self._parse_nivel_filter()
        context['snapshots_resumo'] = [
            {
                'snapshot': snap,
                'status': aderencia_status(snap.percentual),
            }
            for snap in context['object_list']
        ]
        # KPIs / pills: AuthZ + ciclo + área — não o filtro de nível nem a página.
        qs_scope = self._scoped_queryset()
        context['aderencia_resumo'] = self._aderencia_resumo_from_qs(qs_scope, ciclo)
        return context

    def _scoped_queryset(self):
        """Snapshots do ciclo/escopo AuthZ (+ área), % ASC — sem ``?nivel=``."""
        qs = (
            AderenciaSnapshot.objects.select_related('lider', 'lider__area', 'ciclo')
            .order_by('percentual', 'lider__nome', 'lider__email')
        )

        ciclo = self._resolve_ciclo()
        if ciclo is not None:
            qs = qs.filter(ciclo=ciclo)

        area_id = parse_optional_int(self.request, 'area')
        if area_id is not None:
            qs = qs.filter(lider__area_id=area_id)

        user = self.request.user
        if not getattr(user, 'is_admin', False):
            visible = get_visible_users(user)
            qs = qs.filter(lider__in=visible)

        return qs

    def _parse_nivel_filter(self) -> str | None:
        raw = (self.request.GET.get('nivel') or '').strip().lower()
        if raw in _ADERENCIA_NIVEL_FILTERS:
            return raw
        return None

    def _apply_nivel_filter(self, qs, nivel: str):
        if nivel == 'alta':
            return qs.filter(percentual__gte=_ADERENCIA_ALTA)
        if nivel == 'media':
            return qs.filter(
                percentual__gte=_ADERENCIA_MEDIA,
                percentual__lt=_ADERENCIA_ALTA,
            )
        if nivel == 'baixa':
            return qs.filter(percentual__lt=_ADERENCIA_MEDIA)
        return qs

    def _aderencia_resumo_from_qs(self, qs, ciclo: Ciclo | None) -> dict:
        """Agrega média/total/faixas só a partir de snapshots já filtrados."""
        if ciclo is None:
            return {
                'media': None,
                'total_lideres': 0,
                'alta': None,
                'media_n': None,
                'baixa': None,
                'status': 'baixa',
                'has_ciclo': False,
            }
        agg = qs.aggregate(
            media=Avg('percentual'),
            total_lideres=Count('pk'),
            alta=Count('pk', filter=Q(percentual__gte=_ADERENCIA_ALTA)),
            media_n=Count(
                'pk',
                filter=Q(
                    percentual__gte=_ADERENCIA_MEDIA,
                    percentual__lt=_ADERENCIA_ALTA,
                ),
            ),
            baixa=Count('pk', filter=Q(percentual__lt=_ADERENCIA_MEDIA)),
        )
        media = agg['media']
        if media is not None:
            media = Decimal(media).quantize(Decimal('0.01'))
        return {
            'media': media,
            'total_lideres': agg['total_lideres'] or 0,
            'alta': agg['alta'] or 0,
            'media_n': agg['media_n'] or 0,
            'baixa': agg['baixa'] or 0,
            'status': aderencia_status(media),
            'has_ciclo': True,
        }

    def _resolve_ciclo(self) -> Ciclo | None:
        """Default aberto; ``?ciclo=`` só intenção explícita (T008 / T027)."""
        return resolve_operational_ciclo(self.request)


class StructureDashboardView(LoginRequiredMixin, RequiresManagerOrAdminMixin, TemplateView):
    """Painel de estrutura: cobertura (Freeze B) + lacunas secundárias (FR-019 / FR-006)."""

    template_name = 'dashboard/structure.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Badge / “há aberto?” — nunca o ciclo só porque veio em ?ciclo=.
        ciclo_aberto = get_open_ciclo()
        # Dados: aberto, ou arquivo só com ?ciclo= explícito (T008 / T026).
        # MUST NOT cair no último encerrado em silêncio (FR-001 / FR-002).
        ciclo = resolve_operational_ciclo(self.request)
        area_id = parse_optional_int(self.request, 'area')
        cargo_id = parse_optional_int(self.request, 'cargo')
        # AuthZ inalterada — mesmo QS; builder só recebe visible já resolvido.
        visible = get_visible_users(self.request.user).filter(is_active=True)

        cobertura = build_structure_coverage(
            visible,
            ciclo,
            area_id=area_id,
            cargo_id=cargo_id,
        )

        context['ciclo_filtro'] = ciclo
        context['ciclo_selecionado'] = ciclo
        context['ciclo_aberto'] = ciclo_aberto
        context['grouped_ciclo_options'] = grouped_ciclo_options(
            q=self.request.GET.get('q'),
        )
        context['areas'] = Area.objects.filter(is_active=True).order_by('nome')
        context['cargos'] = Cargo.objects.filter(is_active=True).order_by('nivel', 'nome')
        context['filtro_area_id'] = area_id
        context['filtro_cargo_id'] = cargo_id
        context['cobertura_resumo'] = cobertura['resumo']
        context['chart_cobertura_area'] = cobertura['chart_por_area']
        context['chart_cobertura_cargo'] = cobertura['chart_por_cargo']
        context['lideres_resumo'] = [
            {
                **item,
                'status': (
                    aderencia_status(item['snapshot'].percentual)
                    if item.get('snapshot') is not None
                    else None
                ),
            }
            for item in leaders_with_adherence(
                visible,
                ciclo,
                area_id=area_id,
                cargo_id=cargo_id,
            )
        ]
        lacunas_area_prio, lacunas_area_rest = partition_gap_rows(
            gaps_by_area(
                visible,
                ciclo,
                area_id=area_id,
                cargo_id=cargo_id,
            ),
        )
        # Uma lista só (exceção primeiro); o toggle da UI é só “Ver tabela”.
        context['lacunas_por_area'] = lacunas_area_prio + lacunas_area_rest

        mostrar_lacunas_por_cargo = (
            distinct_cargo_count(
                visible,
                area_id=area_id,
                cargo_id=cargo_id,
            )
            > 1
        )
        context['mostrar_lacunas_por_cargo'] = mostrar_lacunas_por_cargo
        if mostrar_lacunas_por_cargo:
            lacunas_cargo_prio, lacunas_cargo_rest = partition_gap_rows(
                gaps_by_cargo(
                    visible,
                    ciclo,
                    area_id=area_id,
                    cargo_id=cargo_id,
                ),
            )
            context['lacunas_por_cargo'] = lacunas_cargo_prio + lacunas_cargo_rest
        else:
            context['lacunas_por_cargo'] = []
        return context


class AdminDashboardView(LoginRequiredMixin, RequiresAdminMixin, TemplateView):
    """Painel RH: pipeline do ciclo operacional (FR-004 / SC-006)."""

    template_name = 'dashboard/admin.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Badge / “há aberto?” — nunca o ciclo só porque veio em ?ciclo=.
        ciclo_aberto = get_open_ciclo()
        # Visão operacional: só o ciclo aberto — arquivo fica no histórico.
        ciclo = ciclo_aberto
        context['ciclo_aberto'] = ciclo_aberto
        context['ciclo_indicador'] = ciclo
        # Seletor agrupado (T017): ?ciclo= só na query; não persiste na home.
        context['grouped_ciclo_options'] = grouped_ciclo_options(
            q=self.request.GET.get('q'),
        )
        context['ciclo_selecionado'] = ciclo
        context['ciclos_resumo'] = self._ciclos_resumo()
        context['visao'] = None
        context['chart_stage_history'] = None
        context['history_kpis'] = None

        # US3 / T031: tendência org só com GET ``visao=historico`` (sem path novo).
        if is_history_mode(self.request):
            visible = get_visible_users(self.request.user).filter(is_active=True)
            janela = resolve_history_ciclos(self.request)
            ciclo_hist = resolve_history_ciclo_selecionado(self.request)
            if ciclo_hist is not None:
                context['ciclo_selecionado'] = ciclo_hist
            elif len(janela) == 1:
                context['ciclo_selecionado'] = janela[0]
            context['visao'] = 'historico'
            context['chart_stage_history'] = build_stage_history(visible, janela)
            context['history_kpis'] = build_history_kpis(visible, janela)
            # KPIs operacionais / pipeline do aberto ficam de lado no modo.
            context['ciclo_kpis'] = {
                'has_ciclo': False,
                'total': None,
                'gargalo_label': None,
                'gargalo_count': None,
                'pendencias': None,
                'sem_avaliacao': None,
            }
            context['avaliacoes_resumo'] = self._avaliacoes_resumo(None)
            context['aderencia_resumo'] = self._aderencia_resumo(None)
            context['snapshots_destaque'] = []
            # Pipeline não é série de desempenho: ``sem_nota`` fica só na aderência.
            # Slot operacional fica de lado no histórico — empty ``sem_dado`` no context.
            context['chart_ciclo_progresso'] = empty_kind_payload(
                kind=EMPTY_KIND_SEM_DADO,
                chart_id='chart-ciclo-progresso',
                chart_type=CHART_TYPE_BAR_HORIZONTAL,
                title='Progresso das avaliações no ciclo',
            )
            # Aderência: empty na janela multi-ciclo; plotável se um ciclo só.
            if len(janela) == 1:
                context['chart_aderencia_distribuicao'] = (
                    self._chart_aderencia_distribuicao(janela[0])
                )
                context['aderencia_resumo'] = self._aderencia_resumo(janela[0])
            else:
                context['chart_aderencia_distribuicao'] = empty_kind_payload(
                    kind=EMPTY_KIND_SEM_NOTA,
                    chart_id='chart-aderencia-distribuicao',
                    chart_type=CHART_TYPE_DOUGHNUT,
                    title='Distribuição de aderência',
                )
            return context

        context['ciclo_kpis'] = self._ciclo_kpis(ciclo)
        context['avaliacoes_resumo'] = self._avaliacoes_resumo(ciclo)
        context['aderencia_resumo'] = self._aderencia_resumo(ciclo)
        context['snapshots_destaque'] = self._snapshots_destaque(ciclo)
        context['chart_aderencia_distribuicao'] = (
            self._chart_aderencia_distribuicao(ciclo)
        )
        context['chart_ciclo_progresso'] = self._chart_ciclo_progresso(ciclo)
        return context

    def _ciclos_resumo(self) -> dict:
        """Copy de arquivo — nunca % de governança (FR-004 / T015)."""
        return {
            'arquivo_total': Ciclo.objects.filter(
                status=Ciclo.Status.ENCERRADO,
            ).count(),
        }

    def _ciclo_kpis(self, ciclo: Ciclo | None) -> dict:
        """1–3 KPIs do ciclo resolvido (aberto ou ``?ciclo=``) — FR-004.

        Totais/gargalo de pipeline, pendências e sem avaliação. Sem
        ``percentual_encerrados``. Não chama ``get_visible_users``: o
        universo é o mesmo de ``open_cycle`` (usuários ativos).
        """
        if ciclo is None:
            return {
                'has_ciclo': False,
                'total': None,
                'gargalo_label': None,
                'gargalo_count': None,
                'pendencias': None,
                'sem_avaliacao': None,
            }

        totals = Avaliacao.objects.filter(ciclo=ciclo).aggregate(
            total=Count('pk'),
            concluidas=Count('pk', filter=Q(concluida=True)),
        )
        total = totals['total'] or 0
        concluidas = totals['concluidas'] or 0

        etapa_counts = {
            row['etapa']: int(row['total'])
            for row in (
                Avaliacao.objects.filter(ciclo=ciclo)
                .values('etapa')
                .annotate(total=Count('pk'))
            )
            if row['etapa']
        }
        gargalo_label = None
        gargalo_count = None
        if etapa_counts:
            gargalo_key = max(etapa_counts, key=etapa_counts.get)
            if etapa_counts[gargalo_key] > 0:
                gargalo_label = dict(Avaliacao.Etapa.choices).get(
                    gargalo_key,
                    gargalo_key,
                )
                gargalo_count = etapa_counts[gargalo_key]

        eligible = CustomUser.objects.filter(is_active=True).count()
        cobertos = (
            Avaliacao.objects.filter(ciclo=ciclo, usuario__is_active=True)
            .values('usuario_id')
            .distinct()
            .count()
        )
        return {
            'has_ciclo': True,
            'total': total,
            'gargalo_label': gargalo_label,
            'gargalo_count': gargalo_count,
            'pendencias': total - concluidas,
            'sem_avaliacao': max(0, eligible - cobertos),
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
        """Doughnut só com ``AderenciaSnapshot`` real (T016).

        Type canônico ``doughnut`` + ``total`` no centro — Status Triad
        inalterada. Sem snapshot: empty ``sem_dado`` (não inventa fatias).
        Sem ciclo resolvido: empty ``operacional`` (não plota arquivo).
        MUST NOT chamar ``compute_adherence``.
        """
        chart_type = CHART_TYPE_DOUGHNUT
        title = 'Distribuição de aderência'
        if ciclo is None:
            return empty_kind_payload(
                kind=EMPTY_KIND_OPERACIONAL,
                chart_id='chart-aderencia-distribuicao',
                chart_type=chart_type,
                title=title,
            )
        percentuais = list(
            AderenciaSnapshot.objects.filter(ciclo=ciclo).values_list(
                'percentual',
                flat=True,
            )
        )
        if not percentuais:
            return empty_kind_payload(
                kind=EMPTY_KIND_SEM_DADO,
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

    def _chart_ciclo_progresso(self, ciclo: Ciclo | None) -> dict:
        """Conta avaliações do ciclo por `Avaliacao.Etapa` (US1).

        Barras horizontais expressivas + amber no maior volume (acabamento);
        counts e chaves de etapa inalterados (FR-001 / data-model).
        Zero avaliações → empty ``sem_dado`` (012 / Freeze D) — sem copy ad hoc.
        """
        chart_type = CHART_TYPE_BAR_HORIZONTAL
        title = 'Progresso das avaliações no ciclo'
        chart_id = 'chart-ciclo-progresso'
        if ciclo is None:
            # Sem aberto / sem ?ciclo=: empty operacional (não plota arquivo).
            return empty_kind_payload(
                kind=EMPTY_KIND_OPERACIONAL,
                chart_id=chart_id,
                chart_type=chart_type,
                title=title,
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
        if not key_counts or sum(key_counts.values()) == 0:
            return empty_kind_payload(
                kind=EMPTY_KIND_SEM_DADO,
                chart_id=chart_id,
                chart_type=chart_type,
                title=title,
            )
        return categorical_counts_payload(
            key_counts,
            ordered_keys=etapa_keys,
            labels_by_key=labels_by_key,
            chart_id=chart_id,
            chart_type=chart_type,
            title=title,
            empty_message=EMPTY_KIND_COPY[EMPTY_KIND_SEM_DADO],
            highlight_max=True,
        )
