"""Filtros de apresentação de avaliação (nota final como percentual)."""

from __future__ import annotations

from django import template

from apps.reviews.services.display import escala_rotulo, format_nota_percentual

register = template.Library()


@register.filter(name='nota_percentual')
def nota_percentual(value) -> str:
    """Nota final [0, 1] → ``75%`` (half-up). Vazio → ``—``."""
    return format_nota_percentual(value)


@register.filter(name='escala_rotulo')
def escala_rotulo_filter(escala, nota) -> str:
    """Rótulo textual da escala para uma nota discreta."""
    return escala_rotulo(escala, nota)


@register.inclusion_tag('reviews/partials/rating_scale_readonly.html')
def rating_scale_readonly(escala, selected_value, aria_label='Nota atribuída'):
    """Botões de escala somente leitura (coluna de autoavaliação do líder)."""
    minimo = escala.valor_minimo
    maximo = escala.valor_maximo
    selected = None
    if selected_value is not None and selected_value != '':
        try:
            selected = int(selected_value)
        except (TypeError, ValueError):
            selected = selected_value
    return {
        'options': range(minimo, maximo + 1),
        'selected': selected,
        'aria_label': aria_label,
        'rotulo': escala_rotulo(escala, selected_value),
    }
