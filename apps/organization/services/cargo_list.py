"""Filtros e opções da listagem administrativa de cargos."""

from __future__ import annotations

from django.db.models import Count, QuerySet

from apps.organization.models import Cargo
from apps.organization.services.display import get_nivel_filter_options
from apps.organization.services.user_list import (
    STATUS_SEGMENT_OPTIONS,
    parse_search_filter,
    parse_status_filter,
)

__all__ = [
    'STATUS_SEGMENT_OPTIONS',
    'apply_cargo_list_filters',
    'get_allowed_nivel_values',
    'get_base_cargo_list_queryset',
    'get_nivel_filter_options_for_queryset',
    'parse_nivel_filter',
    'parse_search_filter',
    'parse_status_filter',
]


def parse_nivel_filter(raw: str | None) -> int | None:
    """``?nivel=`` como int positivo; vazio/inválido → ``None``."""
    if not raw:
        return None
    try:
        parsed = int(raw)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


def get_base_cargo_list_queryset() -> QuerySet[Cargo]:
    """Queryset base da listagem (sem filtros de UI)."""
    return (
        Cargo.objects.annotate(
            competencias_vinculadas=Count('cargo_competencias'),
        )
        .order_by('nivel', 'nome')
    )


def get_allowed_nivel_values(base_qs: QuerySet[Cargo]) -> frozenset[int]:
    return frozenset(base_qs.values_list('nivel', flat=True).distinct())


def get_nivel_filter_options_for_queryset(
    base_qs: QuerySet[Cargo],
) -> list[dict[str, int | str]]:
    return get_nivel_filter_options(get_allowed_nivel_values(base_qs))


def apply_cargo_list_filters(
    qs: QuerySet[Cargo],
    *,
    status: str = '',
    busca: str = '',
    nivel: int | None = None,
) -> QuerySet[Cargo]:
    """Filtros de lista sobre queryset já restrito (admin)."""
    if status == 'ativo':
        qs = qs.filter(is_active=True)
    elif status == 'inativo':
        qs = qs.filter(is_active=False)

    if busca:
        qs = qs.filter(nome__icontains=busca)

    if nivel is not None:
        qs = qs.filter(nivel=nivel)

    return qs


def resolve_nivel_filter(
    value: int | None,
    allowed_niveis: frozenset[int],
) -> int | None:
    """Só aplica nível se existir no catálogo."""
    if value is None:
        return None
    return value if value in allowed_niveis else None
