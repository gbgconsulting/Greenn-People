"""Formatação de nota final para UI (valor persistido permanece em [0, 1])."""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal
from typing import Any

_PERCENT_QUANT = Decimal('1')
_MISSING = '—'


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
