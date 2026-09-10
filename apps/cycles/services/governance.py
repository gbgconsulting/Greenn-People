"""Queries agregadas de governança RH do automático (US4 / FR-015).

Somente leitura a partir de ``AutoCycleRun`` / ``AutoCycleEvent``.
**Não** dispara lote nem altera estado — AuthZ fica nas views
(``RequiresAdminMixin`` / ``AdminCyclesMixin``).

Contrato: ``contracts/governance-surface-contract.md``.
Copy RH (FR-022): rótulos em linguagem de produto, sem jargão de stack.
"""

from __future__ import annotations

from calendar import monthrange
from dataclasses import dataclass
from datetime import date
from typing import Any

from django.db.models import Count, QuerySet
from django.utils import timezone

from apps.cycles.models import AutoCycleEvent, AutoCycleRun, Ciclo
from apps.cycles.services.prazo import ciclos_automaticos_em_atraso

__all__ = [
    'GovernanceKPIs',
    'GovernancePeriodSnapshot',
    'ciclos_em_atraso_prazo',
    'count_distinct_users_by_tipo',
    'events_for_period',
    'get_governance_snapshot',
    'kpis_for_period',
    'latest_run_for_period',
    'resolve_period',
    'runs_for_period',
    'snapshot_as_context',
]


@dataclass(frozen=True)
class GovernanceKPIs:
    """Contagens do período para o strip de KPIs (Status Triad).

    Semântica visual (contrato UI):
    - entrantes → emerald (sucesso do lote)
    - pendencias_sem_admissao / alertas_ciclo_aberto → amber (atenção)
    - falhas / atrasos_prazo → rose (crítico operacional)
    """

    entrantes: int
    pendencias_sem_admissao: int
    alertas_ciclo_aberto: int
    falhas: int
    atrasos_prazo: int
    runs_total: int
    runs_sucesso: int
    runs_parcial: int
    runs_falha: int
    runs_noop: int


@dataclass(frozen=True)
class GovernancePeriodSnapshot:
    """Pacote pronto para a superfície de governança (views/templates)."""

    periodo_inicio: date
    periodo_fim: date
    kpis: GovernanceKPIs
    runs: QuerySet[AutoCycleRun]
    entrantes: QuerySet[AutoCycleEvent]
    pendencias_sem_admissao: QuerySet[AutoCycleEvent]
    alertas_ciclo_aberto: QuerySet[AutoCycleEvent]
    falhas: QuerySet[AutoCycleEvent]
    ciclos_em_atraso: QuerySet[Ciclo]
    ultimo_run: AutoCycleRun | None


def resolve_period(
    *,
    year: int | None = None,
    month: int | None = None,
    inicio: date | None = None,
    fim: date | None = None,
    ref_date: date | None = None,
) -> tuple[date, date]:
    """Resolve ``[inicio, fim]`` inclusivo para filtrar ``data_referencia``.

    Precedência:
    1. ``inicio`` + ``fim`` explícitos
    2. ``year`` + ``month`` (mês civil completo)
    3. Mês civil de ``ref_date`` (default: hoje local)
    """
    if inicio is not None and fim is not None:
        if inicio > fim:
            raise ValueError('periodo_inicio não pode ser posterior a periodo_fim.')
        return inicio, fim

    if year is not None and month is not None:
        last_day = monthrange(year, month)[1]
        return date(year, month, 1), date(year, month, last_day)

    ref = ref_date if ref_date is not None else timezone.localdate()
    last_day = monthrange(ref.year, ref.month)[1]
    return date(ref.year, ref.month, 1), date(ref.year, ref.month, last_day)


def runs_for_period(
    periodo_inicio: date,
    periodo_fim: date,
) -> QuerySet[AutoCycleRun]:
    """Execuções cuja ``data_referencia`` cai no período (ordenado recente→antigo)."""
    return AutoCycleRun.objects.filter(
        data_referencia__gte=periodo_inicio,
        data_referencia__lte=periodo_fim,
    ).select_related('ciclo').order_by('-executado_em', '-id')


def events_for_period(
    periodo_inicio: date,
    periodo_fim: date,
    *,
    tipo: str | None = None,
) -> QuerySet[AutoCycleEvent]:
    """Eventos de runs do período, com joins para listagem RH."""
    qs = (
        AutoCycleEvent.objects.filter(
            run__data_referencia__gte=periodo_inicio,
            run__data_referencia__lte=periodo_fim,
        )
        .select_related('usuario', 'ciclo', 'run')
        .order_by('-criado_em', '-id')
    )
    if tipo is not None:
        qs = qs.filter(tipo=tipo)
    return qs


def count_distinct_users_by_tipo(
    periodo_inicio: date,
    periodo_fim: date,
    tipo: str,
) -> int:
    """Conta pessoas distintas com event do ``tipo`` no período.

    Evita inflar KPI quando a rotina reexecuta e grava o mesmo caso de novo
    (ex.: pendência sem admissão em reprocesso idempotente).
    """
    return (
        events_for_period(periodo_inicio, periodo_fim, tipo=tipo)
        .exclude(usuario_id=None)
        .values('usuario_id')
        .distinct()
        .count()
    )


def ciclos_em_atraso_prazo(
    *,
    ref_date: date | None = None,
) -> QuerySet[Ciclo]:
    """Ciclos automáticos abertos com prazo de 20 dias estourado (rose)."""
    return ciclos_automaticos_em_atraso(ref_date=ref_date)


def latest_run_for_period(
    periodo_inicio: date,
    periodo_fim: date,
) -> AutoCycleRun | None:
    """Última execução do período (ou ``None`` se não houve run)."""
    return runs_for_period(periodo_inicio, periodo_fim).first()


def kpis_for_period(
    periodo_inicio: date,
    periodo_fim: date,
    *,
    ref_date: date | None = None,
) -> GovernanceKPIs:
    """Agrega KPIs do período a partir de runs/events (+ atraso vivo)."""
    runs_qs = runs_for_period(periodo_inicio, periodo_fim)
    status_counts = {
        row['status']: row['n']
        for row in runs_qs.values('status').annotate(n=Count('id'))
    }

    falhas_eventos = events_for_period(
        periodo_inicio,
        periodo_fim,
        tipo=AutoCycleEvent.Tipo.FALHA,
    ).count()

    return GovernanceKPIs(
        entrantes=count_distinct_users_by_tipo(
            periodo_inicio,
            periodo_fim,
            AutoCycleEvent.Tipo.MATRICULA,
        ),
        pendencias_sem_admissao=count_distinct_users_by_tipo(
            periodo_inicio,
            periodo_fim,
            AutoCycleEvent.Tipo.PENDENCIA_SEM_ADMISSAO,
        ),
        alertas_ciclo_aberto=count_distinct_users_by_tipo(
            periodo_inicio,
            periodo_fim,
            AutoCycleEvent.Tipo.ALERTA_CICLO_ABERTO,
        ),
        falhas=falhas_eventos,
        atrasos_prazo=ciclos_em_atraso_prazo(ref_date=ref_date).count(),
        runs_total=runs_qs.count(),
        runs_sucesso=status_counts.get(AutoCycleRun.Status.SUCESSO, 0),
        runs_parcial=status_counts.get(AutoCycleRun.Status.PARCIAL, 0),
        runs_falha=status_counts.get(AutoCycleRun.Status.FALHA, 0),
        runs_noop=status_counts.get(AutoCycleRun.Status.NOOP, 0),
    )


def get_governance_snapshot(
    *,
    year: int | None = None,
    month: int | None = None,
    inicio: date | None = None,
    fim: date | None = None,
    ref_date: date | None = None,
) -> GovernancePeriodSnapshot:
    """Monta o snapshot completo do período para a superfície RH.

    Views devem apenas aplicar AuthZ e renderizar — sem abrir coorte.
    """
    periodo_inicio, periodo_fim = resolve_period(
        year=year,
        month=month,
        inicio=inicio,
        fim=fim,
        ref_date=ref_date,
    )
    atraso_ref = ref_date if ref_date is not None else timezone.localdate()
    return GovernancePeriodSnapshot(
        periodo_inicio=periodo_inicio,
        periodo_fim=periodo_fim,
        kpis=kpis_for_period(
            periodo_inicio,
            periodo_fim,
            ref_date=atraso_ref,
        ),
        runs=runs_for_period(periodo_inicio, periodo_fim),
        entrantes=events_for_period(
            periodo_inicio,
            periodo_fim,
            tipo=AutoCycleEvent.Tipo.MATRICULA,
        ),
        pendencias_sem_admissao=events_for_period(
            periodo_inicio,
            periodo_fim,
            tipo=AutoCycleEvent.Tipo.PENDENCIA_SEM_ADMISSAO,
        ),
        alertas_ciclo_aberto=events_for_period(
            periodo_inicio,
            periodo_fim,
            tipo=AutoCycleEvent.Tipo.ALERTA_CICLO_ABERTO,
        ),
        falhas=events_for_period(
            periodo_inicio,
            periodo_fim,
            tipo=AutoCycleEvent.Tipo.FALHA,
        ),
        ciclos_em_atraso=ciclos_em_atraso_prazo(ref_date=atraso_ref),
        ultimo_run=latest_run_for_period(periodo_inicio, periodo_fim),
    )


def snapshot_as_context(snapshot: GovernancePeriodSnapshot) -> dict[str, Any]:
    """Contexto de template com chaves estáveis em português RH (FR-022)."""
    k = snapshot.kpis
    return {
        'periodo_inicio': snapshot.periodo_inicio,
        'periodo_fim': snapshot.periodo_fim,
        'kpis': {
            'entrantes': k.entrantes,
            'sem_admissao': k.pendencias_sem_admissao,
            'alertas': k.alertas_ciclo_aberto,
            'falhas': k.falhas,
            'atrasos_prazo': k.atrasos_prazo,
            'runs_total': k.runs_total,
            'runs_sucesso': k.runs_sucesso,
            'runs_parcial': k.runs_parcial,
            'runs_falha': k.runs_falha,
            'runs_noop': k.runs_noop,
        },
        'runs': snapshot.runs,
        'entrantes': snapshot.entrantes,
        'pendencias_sem_admissao': snapshot.pendencias_sem_admissao,
        'alertas_ciclo_aberto': snapshot.alertas_ciclo_aberto,
        'falhas': snapshot.falhas,
        'ciclos_em_atraso': snapshot.ciclos_em_atraso,
        'ultimo_run': snapshot.ultimo_run,
    }
