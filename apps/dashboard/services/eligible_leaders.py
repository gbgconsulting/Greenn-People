"""População canônica de gestores elegíveis para aderência da liderança.

Aderência mede compliance de quem **gerencia time ativo no ciclo** — não autores
pontuais, ex-gestores inativos nem gestores sem liderados matriculados.
"""

from __future__ import annotations

from django.db.models import Count, Q, QuerySet

from apps.accounts.models import CustomUser
from apps.cycles.models import Ciclo
from apps.dashboard.models import AderenciaSnapshot


def eligible_leader_queryset() -> QuerySet[CustomUser]:
    """Gestores ativos com pelo menos um liderado direto ativo."""
    return (
        CustomUser.objects.filter(is_active=True)
        .annotate(
            n_liderados_ativos=Count(
                'direct_reports',
                filter=Q(direct_reports__is_active=True),
            ),
        )
        .filter(n_liderados_ativos__gte=1)
        .order_by('nome', 'email')
    )


def eligible_leader_ids() -> set[int]:
    """PKs de gestores elegíveis — filtros em lote."""
    return set(eligible_leader_queryset().values_list('pk', flat=True))


def leader_ids_with_team_in_ciclo(ciclo: Ciclo) -> set[int]:
    """Gestores elegíveis com ≥1 liderado direto matriculado no ciclo."""
    lider_pks = (
        CustomUser.objects.filter(
            is_active=True,
            line_manager__isnull=False,
            line_manager__is_active=True,
            avaliacoes__ciclo_id=ciclo.pk,
        )
        .values_list('line_manager_id', flat=True)
        .distinct()
    )
    return set(
        eligible_leader_queryset()
        .filter(pk__in=lider_pks)
        .values_list('pk', flat=True),
    )


def filter_adherence_snapshots(
    qs: QuerySet[AderenciaSnapshot],
    *,
    ciclo: Ciclo | None = None,
) -> QuerySet[AderenciaSnapshot]:
    """Restringe snapshots a gestores elegíveis (e, se informado, no ciclo)."""
    qs = qs.filter(lider__in=eligible_leader_queryset())
    if ciclo is not None:
        qs = qs.filter(lider_id__in=leader_ids_with_team_in_ciclo(ciclo))
    return qs
