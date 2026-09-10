"""Prazo operacional de ciclos automáticos (20 dias corridos).

FR-006 / R4: ``data_fim = data_inicio + 20`` dias corridos na criação da
coorte. Atraso pós-prazo é **sinalizável** (rose na governança) sem
encerramento automático hard nesta feature.
"""

from __future__ import annotations

from datetime import date, timedelta

from django.db.models import QuerySet
from django.utils import timezone

from apps.cycles.models import Ciclo

PRAZO_DIAS_CORRIDOS = 20


def data_fim_from_inicio(data_inicio: date) -> date:
    """``data_fim`` = ativação + 20 dias corridos (não úteis)."""
    return data_inicio + timedelta(days=PRAZO_DIAS_CORRIDOS)


def is_prazo_estourado(
    ciclo: Ciclo,
    *,
    ref_date: date | None = None,
) -> bool:
    """True se o ciclo está ``aberto`` e ``ref_date`` é posterior a ``data_fim``.

    Rose na UI/governança só para este caso (atraso real) ou falha de rotina —
    nunca para alerta de ciclo ainda aberto (amber). Encerramento permanece
    manual; este predicado **não** fecha o ciclo.
    """
    if ciclo.status != Ciclo.Status.ABERTO or ciclo.data_fim is None:
        return False
    ref = ref_date if ref_date is not None else timezone.localdate()
    return ref > ciclo.data_fim


def ciclos_automaticos_em_atraso(
    *,
    ref_date: date | None = None,
) -> QuerySet[Ciclo]:
    """Ciclos automáticos abertos com prazo de 20 dias estourado (governança)."""
    ref = ref_date if ref_date is not None else timezone.localdate()
    return Ciclo.objects.filter(
        origem=Ciclo.Origem.AUTOMATICO,
        status=Ciclo.Status.ABERTO,
        data_fim__lt=ref,
    ).order_by('data_fim', 'nome')
