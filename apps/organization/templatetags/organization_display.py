from django import template

from apps.organization.services.display import format_cargo_nivel_label

register = template.Library()


@register.filter(name='cargo_nivel_label')
def cargo_nivel_label(value) -> str:
    """Rótulo de senioridade para templates."""
    if value is None:
        return '—'
    try:
        nivel = int(value)
    except (TypeError, ValueError):
        return '—'
    return format_cargo_nivel_label(nivel)
