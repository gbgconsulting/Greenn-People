"""Filtros, hierarquia e metadados da listagem administrativa de áreas."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from django.db.models import Count, Q, QuerySet

from apps.organization.models import Area
from apps.organization.services.user_list import (
    STATUS_SEGMENT_OPTIONS,
    parse_search_filter,
    parse_status_filter,
)

__all__ = [
    'STATUS_SEGMENT_OPTIONS',
    'AreaListRow',
    'apply_area_list_filters',
    'build_hierarchical_area_rows',
    'get_allowed_parent_area_ids',
    'get_base_area_list_queryset',
    'get_parent_filter_options',
    'parse_search_filter',
    'parse_status_filter',
    'resolve_parent_filter',
]


@dataclass(frozen=True, slots=True)
class AreaListRow:
    """Linha da tabela com profundidade hierárquica."""

    area: Area
    depth: int


def get_base_area_list_queryset() -> QuerySet[Area]:
    """Queryset base da listagem (sem filtros de UI)."""
    return (
        Area.objects.select_related('parent')
        .annotate(
            colaboradores_count=Count(
                'usuarios',
                filter=Q(usuarios__is_active=True),
            ),
        )
        .order_by('nome')
    )


def get_allowed_parent_area_ids(base_qs: QuerySet[Area]) -> frozenset[int]:
    return frozenset(
        base_qs.exclude(parent_id__isnull=True)
        .values_list('parent_id', flat=True)
        .distinct(),
    )


def get_parent_filter_options(
    base_qs: QuerySet[Area],
) -> QuerySet[Area]:
    """Áreas que são pai de ao menos uma área no catálogo."""
    allowed = get_allowed_parent_area_ids(base_qs)
    if not allowed:
        return Area.objects.none()
    return base_qs.filter(pk__in=allowed).order_by('nome')


def apply_area_list_filters(
    qs: QuerySet[Area],
    *,
    status: str = '',
    busca: str = '',
    parent_id: int | None = None,
) -> QuerySet[Area]:
    """Filtros de lista sobre queryset já restrito (admin)."""
    if status == 'ativo':
        qs = qs.filter(is_active=True)
    elif status == 'inativo':
        qs = qs.filter(is_active=False)

    if busca:
        qs = qs.filter(nome__icontains=busca)

    if parent_id is not None:
        qs = qs.filter(parent_id=parent_id)

    return qs


def build_hierarchical_area_rows(areas: QuerySet[Area]) -> list[AreaListRow]:
    """Ordena áreas em profundidade-primeiro, preservando filhos sob o pai."""
    catalog = list(areas)
    if not catalog:
        return []

    by_id = {area.pk: area for area in catalog}
    children_map: dict[int, list[Area]] = defaultdict(list)
    roots: list[Area] = []

    for area in catalog:
        parent_id = area.parent_id
        if parent_id is not None and parent_id in by_id:
            children_map[parent_id].append(area)
        else:
            roots.append(area)

    sort_key = lambda area: area.nome.casefold()
    roots.sort(key=sort_key)
    for children in children_map.values():
        children.sort(key=sort_key)

    rows: list[AreaListRow] = []

    def walk(area: Area, depth: int) -> None:
        rows.append(AreaListRow(area=area, depth=depth))
        for child in children_map.get(area.pk, []):
            walk(child, depth + 1)

    for root in roots:
        walk(root, 0)

    return rows


def resolve_parent_filter(
    value: int | None,
    allowed_parent_ids: frozenset[int],
) -> int | None:
    """Só aplica filtro de área pai se existir no catálogo."""
    if value is None:
        return None
    return value if value in allowed_parent_ids else None
