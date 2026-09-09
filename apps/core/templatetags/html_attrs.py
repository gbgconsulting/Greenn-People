"""Filtros de template para atributos HTML com mitigação básica de XSS."""

from __future__ import annotations

from django import template
from django.utils.safestring import mark_safe

register = template.Library()

_FORBIDDEN_FRAGMENTS = (
    '<',
    '>',
    'javascript:',
    'onerror',
    'onload',
    '<script',
    '&#',
)


@register.filter(name='validated_attrs')
def validated_attrs(value: str | None) -> str:
    """Permite só atributos estáticos de confiança; bloqueia payloads óbvios."""
    if not value:
        return ''
    text = str(value).strip()
    lower = text.lower()
    for fragment in _FORBIDDEN_FRAGMENTS:
        if fragment in lower:
            return ''
    return mark_safe(text)
