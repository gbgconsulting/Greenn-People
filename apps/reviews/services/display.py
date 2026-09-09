"""Formatação de nota final para UI (valor persistido permanece em [0, 1])."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from typing import Any, Literal

_PERCENT_QUANT = Decimal('1')
_MISSING = '—'

NotaLiderTone = Literal['success', 'warning', 'neutral']
NotaLiderTrend = Literal['up', 'equal', 'down'] | None


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


def format_nivel_display(value: Any) -> str:
    """Nível discreto (ex.: 3.00) → ``3``. Ausência → ``—``."""
    if value is None or value == '':
        return _MISSING
    try:
        normalized = Decimal(str(value)).normalize()
    except (TypeError, ValueError, ArithmeticError):
        return str(value)
    text = format(normalized, 'f')
    if '.' in text:
        text = text.rstrip('0').rstrip('.')
    return text


def nota_lider_tone(nota_lider: Any, nivel_esperado: Any) -> NotaLiderTone:
    """Tom visual da nota do líder vs. nível esperado (UI só consome)."""
    if nota_lider is None or nota_lider == '' or nivel_esperado is None or nivel_esperado == '':
        return 'neutral'
    try:
        nota = Decimal(str(nota_lider))
        esperado = Decimal(str(nivel_esperado))
    except (TypeError, ValueError, ArithmeticError):
        return 'neutral'
    if nota >= esperado:
        return 'success'
    return 'warning'


def nota_lider_trend(nota_lider: Any, nota_autoavaliacao: Any) -> NotaLiderTrend:
    """Tendência líder vs. autoavaliação (UI só consome)."""
    if (
        nota_lider is None
        or nota_lider == ''
        or nota_autoavaliacao is None
        or nota_autoavaliacao == ''
    ):
        return None
    try:
        lider = Decimal(str(nota_lider))
        auto = Decimal(str(nota_autoavaliacao))
    except (TypeError, ValueError, ArithmeticError):
        return None
    if lider > auto:
        return 'up'
    if lider < auto:
        return 'down'
    return 'equal'


@dataclass(frozen=True)
class CompetenciaLinhaDisplay:
    """DTO de apresentação para uma linha de competência no detalhe operacional."""

    linha: Any
    nota_lider_tone: NotaLiderTone
    nota_lider_trend: NotaLiderTrend


def build_competencia_linha_display(linha: Any) -> CompetenciaLinhaDisplay:
    """Monta DTO de apresentação — sem regra de negócio nova."""
    return CompetenciaLinhaDisplay(
        linha=linha,
        nota_lider_tone=nota_lider_tone(
            linha.nota_lider,
            linha.nivel_esperado_utilizado,
        ),
        nota_lider_trend=nota_lider_trend(
            linha.nota_lider,
            linha.nota_autoavaliacao,
        ),
    )


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
