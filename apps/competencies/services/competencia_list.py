"""Filtros e opções da listagem administrativa de competências."""

from __future__ import annotations

from typing import TypedDict

from django.db.models import Q, QuerySet

from apps.competencies.models import Competencia
from apps.organization.services.user_list import (
    STATUS_SEGMENT_OPTIONS,
    parse_search_filter,
    parse_status_filter,
)

__all__ = [
    'STATUS_SEGMENT_OPTIONS',
    'TipoFilterOption',
    'apply_competencia_list_filters',
    'get_allowed_tipo_values',
    'get_base_competencia_list_queryset',
    'get_tipo_filter_options',
    'parse_search_filter',
    'parse_status_filter',
    'parse_tipo_filter',
    'resolve_tipo_filter',
]

TIPO_FILTER_KEYS: frozenset[str] = frozenset(
    choice[0] for choice in Competencia.Tipo.choices
)


class TipoFilterOption(TypedDict):
    value: str
    label: str


def parse_tipo_filter(raw: str | None) -> str:
    """``?tipo=`` válido → chave; inválido → ``''`` (ignorado)."""
    value = (raw or '').strip()
    return value if value in TIPO_FILTER_KEYS else ''


def get_base_competencia_list_queryset() -> QuerySet[Competencia]:
    """Queryset base da listagem (sem filtros de UI)."""
    return Competencia.objects.select_related('escala').order_by('nome')


def get_allowed_tipo_values(
    base_qs: QuerySet[Competencia],
) -> frozenset[str]:
    return frozenset(base_qs.values_list('tipo', flat=True).distinct())


def get_tipo_filter_options(
    base_qs: QuerySet[Competencia],
) -> list[TipoFilterOption]:
    allowed = get_allowed_tipo_values(base_qs)
    if not allowed:
        return []
    return [
        {'value': value, 'label': label}
        for value, label in Competencia.Tipo.choices
        if value in allowed
    ]


def apply_competencia_list_filters(
    qs: QuerySet[Competencia],
    *,
    status: str = '',
    busca: str = '',
    tipo: str = '',
) -> QuerySet[Competencia]:
    """Filtros de lista sobre queryset já restrito (admin)."""
    if status == 'ativo':
        qs = qs.filter(is_active=True)
    elif status == 'inativo':
        qs = qs.filter(is_active=False)

    if busca:
        qs = qs.filter(
            Q(nome__icontains=busca) | Q(descricao__icontains=busca),
        )

    if tipo:
        qs = qs.filter(tipo=tipo)

    return qs


def resolve_tipo_filter(
    value: str,
    allowed_tipos: frozenset[str],
) -> str:
    """Só aplica tipo se existir no catálogo."""
    if not value:
        return ''
    return value if value in allowed_tipos else ''
