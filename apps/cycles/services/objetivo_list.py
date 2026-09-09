"""Filtros da listagem de objetivos estratégicos por ciclo."""

from __future__ import annotations

from django.db.models import Count, QuerySet

from apps.goals.models import ObjetivoEstrategico
from apps.organization.services.user_list import parse_search_filter

__all__ = [
    'apply_objetivo_list_filters',
    'get_base_objetivo_list_queryset',
    'parse_search_filter',
]


def get_base_objetivo_list_queryset(ciclo) -> QuerySet[ObjetivoEstrategico]:
    """Queryset base da listagem (ciclo já validado na view)."""
    return (
        ObjetivoEstrategico.objects.filter(ciclo=ciclo)
        .annotate(metas_count=Count('metas'))
        .order_by('id')
    )


def apply_objetivo_list_filters(
    qs: QuerySet[ObjetivoEstrategico],
    *,
    busca: str = '',
) -> QuerySet[ObjetivoEstrategico]:
    """Filtros de lista sobre queryset já restrito ao ciclo."""
    if busca:
        qs = qs.filter(descricao__icontains=busca)
    return qs
