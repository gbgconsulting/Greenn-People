"""Context processors do shell (leitura apenas)."""

from __future__ import annotations

from typing import Any

from django.http import HttpRequest

from apps.goals.forms import get_open_ciclo


def ciclo_aberto(request: HttpRequest) -> dict[str, Any]:
    """Expõe o ciclo aberto para a topbar; anônimo não recebe bloco de ciclo."""
    if not getattr(request, 'user', None) or not request.user.is_authenticated:
        return {'ciclo_aberto': None}
    return {'ciclo_aberto': get_open_ciclo()}
