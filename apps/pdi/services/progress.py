"""Cálculo de progresso do PDI (contracts/calculation-contract.md)."""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

from django.db.models import Count, Q

from apps.pdi.models import AcaoPDI, PDI

_PROGRESS_QUANT = Decimal('0.01')


def calculate_pdi_progress(pdi: PDI) -> Decimal:
    """Percentual de ações com status=concluida sobre o total.

    Returns:
        Decimal de 0 a 100 (duas casas). Sem ações, retorna ``0.00``.
    """
    stats = pdi.acoes.aggregate(
        total=Count('id'),
        concluidas=Count(
            'id',
            filter=Q(status=AcaoPDI.Status.CONCLUIDA),
        ),
    )
    total = stats['total'] or 0
    if total == 0:
        return Decimal('0.00')

    concluidas = stats['concluidas'] or 0
    return (Decimal(concluidas) * Decimal('100') / Decimal(total)).quantize(
        _PROGRESS_QUANT,
        rounding=ROUND_HALF_UP,
    )
