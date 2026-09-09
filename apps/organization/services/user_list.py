"""Filtros e opções da listagem administrativa de usuários."""

from __future__ import annotations

from typing import TypedDict

from django.db.models import Q, QuerySet

from apps.accounts.models import CustomUser
from apps.organization.models import Area, Cargo

SEARCH_MAX_LEN = 100

STATUS_FILTER_KEYS: frozenset[str] = frozenset({'ativo', 'inativo'})

STATUS_SEGMENT_OPTIONS: list[tuple[str, str]] = [
    ('', 'Todos'),
    ('ativo', 'Ativo'),
    ('inativo', 'Inativo'),
]


PENDENCIA_FILTER_KEYS: frozenset[str] = frozenset({'ambos', 'area', 'cargo'})

PENDENCIA_SEGMENT_OPTIONS: list[tuple[str, str]] = [
    ('', 'Todos'),
    ('ambos', 'Área e cargo'),
    ('area', 'Só área'),
    ('cargo', 'Só cargo'),
]


class AreaFilterOption(TypedDict):
    pk: int
    nome: str


class ManagerFilterOption(TypedDict):
    pk: int
    nome: str


class CargoFilterOption(TypedDict):
    pk: int
    nome: str


def parse_status_filter(raw: str | None) -> str:
    """``?status=`` válido → chave; inválido → ``''`` (ignorado)."""
    value = (raw or '').strip()
    return value if value in STATUS_FILTER_KEYS else ''


def parse_int_filter(raw: str | None) -> int | None:
    """``?area=`` / ``?gestor=`` / ``?cargo=`` como int; vazio/inválido → ``None``."""
    if not raw:
        return None
    try:
        parsed = int(raw)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


def parse_search_filter(raw: str | None) -> str:
    """Normaliza busca textual; descarta entradas excessivamente longas."""
    value = (raw or '').strip()
    if len(value) > SEARCH_MAX_LEN:
        return value[:SEARCH_MAX_LEN]
    return value


def parse_pendencia_filter(raw: str | None) -> str:
    """``?pendencia=`` válido → chave; inválido → ``''`` (ignorado)."""
    value = (raw or '').strip()
    return value if value in PENDENCIA_FILTER_KEYS else ''


def get_base_user_list_queryset() -> QuerySet[CustomUser]:
    """Queryset base da listagem (sem filtros de UI)."""
    return (
        CustomUser.objects.select_related('area', 'cargo', 'line_manager')
        .order_by('nome', 'email')
    )


def get_allowed_area_ids(base_qs: QuerySet[CustomUser]) -> frozenset[int]:
    return frozenset(
        base_qs.exclude(area_id__isnull=True)
        .values_list('area_id', flat=True)
        .distinct(),
    )


def get_allowed_manager_ids(base_qs: QuerySet[CustomUser]) -> frozenset[int]:
    return frozenset(
        base_qs.exclude(line_manager_id__isnull=True)
        .values_list('line_manager_id', flat=True)
        .distinct(),
    )


def get_allowed_cargo_ids(base_qs: QuerySet[CustomUser]) -> frozenset[int]:
    return frozenset(
        base_qs.exclude(cargo_id__isnull=True)
        .values_list('cargo_id', flat=True)
        .distinct(),
    )


def resolve_id_filter(
    value: int | None,
    allowed_ids: frozenset[int],
) -> int | None:
    """Só aplica ID se pertencer ao conjunto permitido (derivado do catálogo)."""
    if value is None:
        return None
    return value if value in allowed_ids else None


def get_area_filter_options(
    base_qs: QuerySet[CustomUser],
) -> list[AreaFilterOption]:
    allowed = get_allowed_area_ids(base_qs)
    if not allowed:
        return []
    return [
        {'pk': row['pk'], 'nome': row['nome']}
        for row in Area.objects.filter(pk__in=allowed, is_active=True)
        .order_by('nome')
        .values('pk', 'nome')
    ]


def get_manager_filter_options(
    base_qs: QuerySet[CustomUser],
) -> list[ManagerFilterOption]:
    allowed = get_allowed_manager_ids(base_qs)
    if not allowed:
        return []
    return [
        {'pk': row['pk'], 'nome': row['nome']}
        for row in CustomUser.objects.filter(pk__in=allowed)
        .order_by('nome')
        .values('pk', 'nome')
    ]


def get_cargo_filter_options(
    base_qs: QuerySet[CustomUser],
) -> list[CargoFilterOption]:
    allowed = get_allowed_cargo_ids(base_qs)
    if not allowed:
        return []
    return [
        {'pk': row['pk'], 'nome': row['nome']}
        for row in Cargo.objects.filter(pk__in=allowed, is_active=True)
        .order_by('nivel', 'nome')
        .values('pk', 'nome')
    ]


def get_base_pending_user_list_queryset() -> QuerySet[CustomUser]:
    """Queryset base de colaboradores ativos sem área e/ou cargo."""
    return (
        CustomUser.objects.filter(is_active=True)
        .filter(Q(area__isnull=True) | Q(cargo__isnull=True))
        .select_related('area', 'cargo', 'line_manager')
        .order_by('nome', 'email')
    )


def apply_pendencia_filter(
    qs: QuerySet[CustomUser],
    pendencia: str = '',
) -> QuerySet[CustomUser]:
    """Segmento de tipo de pendência sobre queryset já restrito."""
    if pendencia == 'ambos':
        return qs.filter(area__isnull=True, cargo__isnull=True)
    if pendencia == 'area':
        return qs.filter(area__isnull=True, cargo__isnull=False)
    if pendencia == 'cargo':
        return qs.filter(cargo__isnull=True, area__isnull=False)
    return qs


def _apply_search_and_id_filters(
    qs: QuerySet[CustomUser],
    *,
    busca: str = '',
    area_id: int | None = None,
    gestor_id: int | None = None,
    cargo_id: int | None = None,
) -> QuerySet[CustomUser]:
    if busca:
        qs = qs.filter(Q(nome__icontains=busca) | Q(email__icontains=busca))

    if area_id is not None:
        qs = qs.filter(area_id=area_id)

    if gestor_id is not None:
        qs = qs.filter(line_manager_id=gestor_id)

    if cargo_id is not None:
        qs = qs.filter(cargo_id=cargo_id)

    return qs


def apply_user_list_filters(
    qs: QuerySet[CustomUser],
    *,
    status: str = '',
    busca: str = '',
    area_id: int | None = None,
    gestor_id: int | None = None,
    cargo_id: int | None = None,
) -> QuerySet[CustomUser]:
    """Filtros de lista sobre queryset já restrito (admin)."""
    if status == 'ativo':
        qs = qs.filter(is_active=True)
    elif status == 'inativo':
        qs = qs.filter(is_active=False)

    return _apply_search_and_id_filters(
        qs,
        busca=busca,
        area_id=area_id,
        gestor_id=gestor_id,
        cargo_id=cargo_id,
    )


def apply_pending_user_list_filters(
    qs: QuerySet[CustomUser],
    *,
    pendencia: str = '',
    busca: str = '',
    area_id: int | None = None,
    gestor_id: int | None = None,
    cargo_id: int | None = None,
) -> QuerySet[CustomUser]:
    """Filtros da listagem de vínculos pendentes (admin)."""
    qs = apply_pendencia_filter(qs, pendencia)
    return _apply_search_and_id_filters(
        qs,
        busca=busca,
        area_id=area_id,
        gestor_id=gestor_id,
        cargo_id=cargo_id,
    )
