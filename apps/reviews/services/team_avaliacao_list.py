"""Montagem da listagem «Avaliações» (líder / gestor / RH)."""

from __future__ import annotations

from typing import Any, TypedDict

from django.db.models import Q, QuerySet

from apps.organization.models import Area
from apps.reviews.models import Avaliacao
from apps.reviews.services.collaborator_history import is_collaborator_history_view
from apps.reviews.forms import (
    can_leader_assess,
    leader_assessment_permitted,
    self_assessment_editable,
)
from apps.reviews.services.evaluation import (
    self_assessment_submitted,
    self_assessment_viewable,
)


class TeamAvaliacaoRow(TypedDict):
    avaliacao: Avaliacao
    is_self: bool
    status_label: str
    status_variant: str
    iniciais: str
    pode_autoavaliar: bool
    pode_ver_autoavaliacao: bool
    pode_avaliar_lider: bool


class AreaFilterOption(TypedDict):
    pk: int
    nome: str


STATUS_FILTER_KEYS: frozenset[str] = frozenset({'concluido', 'em_andamento', 'pendente'})

STATUS_SEGMENT_OPTIONS: list[tuple[str, str]] = [
    ('', 'Todas'),
    ('pendente', 'Pendente'),
    ('em_andamento', 'Em Andamento'),
    ('concluido', 'Concluída'),
]

# Compatibilidade com testes/templates legados.
STATUS_FILTER_CHIPS: list[tuple[str, str]] = [
    (key, label) for key, label in STATUS_SEGMENT_OPTIONS if key
]

ETAPA_FILTER_KEYS: frozenset[str] = frozenset(
    choice.value for choice in Avaliacao.Etapa
)

ETAPA_FILTER_CHIPS: list[tuple[str, str]] = [
    (Avaliacao.Etapa.INPUT_METAS, 'Metas'),
    (Avaliacao.Etapa.APROVACAO_METAS, 'Aprov. metas'),
    (Avaliacao.Etapa.RESULTADOS, 'Resultados'),
    (Avaliacao.Etapa.APROVACAO_RESULTADOS, 'Aprov. result.'),
    (Avaliacao.Etapa.AVALIACAO, 'Avaliação'),
    (Avaliacao.Etapa.FEEDBACK, 'Feedback'),
]


def is_team_avaliacao_list_view(user) -> bool:
    """True para líder, gestor ou admin (visão operacional de time)."""
    return not is_collaborator_history_view(user)


def parse_status_filter(raw: str | None) -> str:
    """``?status=`` válido → chave; inválido → ``''`` (ignorado)."""
    value = (raw or '').strip()
    return value if value in STATUS_FILTER_KEYS else ''


def parse_etapa_filter(raw: str | None) -> str:
    """``?etapa=`` válido → chave; inválido → ``''`` (ignorado)."""
    value = (raw or '').strip()
    return value if value in ETAPA_FILTER_KEYS else ''


def parse_area_filter(raw: str | None) -> int | None:
    """``?area=`` como int; vazio/inválido → ``None``."""
    if not raw:
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def get_allowed_area_ids(scoped_qs: QuerySet[Avaliacao]) -> frozenset[int]:
    """Áreas presentes no escopo (base sem filtros de lista)."""
    return frozenset(
        scoped_qs.exclude(usuario__area_id__isnull=True)
        .values_list('usuario__area_id', flat=True)
        .distinct(),
    )


def resolve_area_filter(
    area_id: int | None,
    allowed_area_ids: frozenset[int],
) -> int | None:
    """Só aplica ``area_id`` se pertencer ao escopo visível."""
    if area_id is None:
        return None
    return area_id if area_id in allowed_area_ids else None


def get_area_filter_options(
    scoped_qs: QuerySet[Avaliacao],
) -> list[AreaFilterOption]:
    """Opções de área derivadas do escopo — nunca expõe áreas alheias."""
    allowed = get_allowed_area_ids(scoped_qs)
    if not allowed:
        return []
    return [
        {'pk': row['pk'], 'nome': row['nome']}
        for row in Area.objects.filter(pk__in=allowed, is_active=True)
        .order_by('nome')
        .values('pk', 'nome')
    ]


def apply_team_list_filters(
    qs: QuerySet[Avaliacao],
    *,
    status: str = '',
    etapa: str = '',
    area_id: int | None = None,
) -> QuerySet[Avaliacao]:
    """Filtros de lista sobre queryset já restrito ao escopo."""
    if etapa:
        qs = qs.filter(etapa=etapa)
    elif status == 'concluido':
        qs = qs.filter(Q(concluida=True) | Q(etapa=Avaliacao.Etapa.FEEDBACK))
    elif status == 'em_andamento':
        qs = qs.filter(concluida=False, etapa=Avaliacao.Etapa.AVALIACAO)
    elif status == 'pendente':
        qs = qs.filter(
            concluida=False,
            etapa__in=[
                Avaliacao.Etapa.APROVACAO_METAS,
                Avaliacao.Etapa.APROVACAO_RESULTADOS,
            ],
        )

    if area_id is not None:
        qs = qs.filter(usuario__area_id=area_id)

    return qs


def user_initials(user) -> str:
    """Iniciais do colaborador (até duas letras) para avatar placeholder."""
    name = (getattr(user, 'nome', None) or getattr(user, 'email', '') or '').strip()
    if not name:
        return '?'
    parts = name.split()
    if len(parts) >= 2:
        return f'{parts[0][0]}{parts[-1][0]}'.upper()
    return name[:2].upper()


def resolve_team_avaliacao_status(avaliacao: Avaliacao) -> tuple[str, str]:
    """Rótulo e variante de badge simplificados (mock lista líder)."""
    if avaliacao.concluida or avaliacao.etapa == Avaliacao.Etapa.FEEDBACK:
        return 'Concluída', 'concluido'

    if avaliacao.etapa == Avaliacao.Etapa.AVALIACAO:
        return 'Em Andamento', 'em_andamento'

    if avaliacao.etapa in {
        Avaliacao.Etapa.APROVACAO_METAS,
        Avaliacao.Etapa.APROVACAO_RESULTADOS,
    }:
        return 'Pendente', 'pendente'

    return avaliacao.get_etapa_display(), 'em_andamento'


def build_team_avaliacao_rows(
    avaliacoes: list[Avaliacao] | Any,
    requesting_user,
) -> list[TeamAvaliacaoRow]:
    """Linhas da tabela operacional com flags de ação (backend decide permissões)."""
    rows: list[TeamAvaliacaoRow] = []
    for avaliacao in avaliacoes:
        is_self = avaliacao.usuario_id == requesting_user.pk
        status_label, status_variant = resolve_team_avaliacao_status(avaliacao)
        rows.append(
            {
                'avaliacao': avaliacao,
                'is_self': is_self,
                'status_label': status_label,
                'status_variant': status_variant,
                'iniciais': user_initials(avaliacao.usuario),
                'pode_autoavaliar': (
                    is_self and self_assessment_editable(avaliacao)
                ),
                'pode_ver_autoavaliacao': (
                    is_self
                    and self_assessment_viewable(avaliacao)
                    and self_assessment_submitted(avaliacao)
                ),
                'pode_avaliar_lider': (
                    not is_self
                    and can_leader_assess(requesting_user, avaliacao)
                    and leader_assessment_permitted(avaliacao)
                ),
            },
        )
    return rows
