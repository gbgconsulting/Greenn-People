"""Formatação de nota final para UI (valor persistido permanece em [0, 1])."""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal
from typing import Any

_PERCENT_QUANT = Decimal('1')
_MISSING = '—'


def escala_rotulo(escala, nota: Any) -> str:
    """Rótulo da escala para ``nota`` (ex.: ``4`` → ``Excede o Esperado``)."""
    if escala is None or nota is None or nota == '':
        return ''
    rotulos = getattr(escala, 'rotulos_por_nivel', None) or {}
    if not rotulos:
        return ''
    try:
        chave = str(int(nota))
    except (TypeError, ValueError):
        chave = str(nota)
    return str(rotulos.get(chave, '') or '')


def format_nota_percentual(value: Any) -> str:
    """Converte nota final normalizada (0–1) em percentual inteiro, como os gráficos.

    ``0.7500`` → ``75%``. Ausência → ``—``. Não altera o valor gravado.
    """
    if value is None or value == '':
        return _MISSING
    percent = (Decimal(str(value)) * Decimal('100')).quantize(
        _PERCENT_QUANT,
        rounding=ROUND_HALF_UP,
    )
    return f'{int(percent)}%'


_SCALE_CINCO = Decimal('5')
_SCALE_ONE_DECIMAL = Decimal('0.1')


def format_nota_escala_cinco(value: Any) -> str:
    """Nota normalizada (0–1) → valor na escala 1–5 com uma casa decimal.

    ``0.8400`` → ``4.2``. Ausência → ``—``.
    """
    if value is None or value == '':
        return _MISSING
    escala = (Decimal(str(value)) * _SCALE_CINCO).quantize(
        _SCALE_ONE_DECIMAL,
        rounding=ROUND_HALF_UP,
    )
    normalized = escala.normalize()
    text = format(normalized, 'f')
    if '.' in text:
        text = text.rstrip('0').rstrip('.')
    return text
