"""População canônica de gestores elegíveis para aderência da liderança.

Aderência mede compliance de quem **gerencia time ativo** — não autores
pontuais, ex-gestores inativos nem colaboradores do ciclo.
"""

from __future__ import annotations

from django.db.models import Count, Q, QuerySet

from apps.accounts.models import CustomUser
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
    """PKs de gestores elegíveis — fan-out Celery e filtros em lote."""
    return set(eligible_leader_queryset().values_list('pk', flat=True))


def filter_adherence_snapshots(
    qs: QuerySet[AderenciaSnapshot],
) -> QuerySet[AderenciaSnapshot]:
    """Restringe snapshots a gestores elegíveis (população canônica)."""
    return qs.filter(lider__in=eligible_leader_queryset())
