"""Context processors do shell (leitura apenas)."""

from __future__ import annotations

from typing import Any

from django.http import HttpRequest

from apps.goals.forms import get_open_ciclo
from apps.reviews.services.pending_counts import (
    LeaderPendingBadge,
    resolve_leader_pending_badge,
)


def ciclo_aberto(request: HttpRequest) -> dict[str, Any]:
    """Expõe o ciclo aberto para a topbar; anônimo não recebe bloco de ciclo."""
    if not getattr(request, 'user', None) or not request.user.is_authenticated:
        return {'ciclo_aberto': None}
    return {'ciclo_aberto': get_open_ciclo()}


def leader_pending_badge(request: HttpRequest) -> dict[str, Any]:
    """Expõe ``LeaderPendingBadge`` para a nav (FR-006); só leitura.

    Request autenticado: deriva via ``resolve_leader_pending_badge`` (reusa
    escopo/predicados existentes — sem AuthZ nova). Anônimo: total zero.
    """
    empty = LeaderPendingBadge(
        total=0, aprovacoes=0, avaliacoes=0, feedbacks=0
    )
    if not getattr(request, 'user', None) or not request.user.is_authenticated:
        return {'leader_pending_badge': empty}
    return {
        'leader_pending_badge': resolve_leader_pending_badge(request.user),
    }
