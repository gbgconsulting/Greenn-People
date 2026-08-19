"""Filtros de apresentação de avaliação (nota final como percentual)."""

from __future__ import annotations

from django import template

from apps.reviews.services.display import format_nota_percentual

register = template.Library()


@register.filter(name='nota_percentual')
def nota_percentual(value) -> str:
    """Nota final [0, 1] → ``75%`` (half-up). Vazio → ``—``."""
    return format_nota_percentual(value)
