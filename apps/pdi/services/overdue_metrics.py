"""Métricas derivadas de atraso de ações de PDI (annotate / filtros).

Definições (data-model + research §4 / contracts/pdi-overdue-list):

- ``acoes_atrasadas_count``: count de ações ``status=atrasada``
- ``dias_atraso_max``: ``hoje - min(prazo)`` entre atrasadas com prazo;
  ``None`` se zero atrasadas elegíveis
- ``proximo_prazo``: ``min(prazo)`` entre ações não concluídas com prazo
- Faixas de ``dias_atraso_max``: ``1-7`` e ``8-30`` inclusivas nos
  extremos; ``30+`` aberto (``> 30``). Ação sem prazo fica fora.
"""

from __future__ import annotations

from datetime import date
from typing import Literal

from django.db.models import Count, Func, IntegerField, Min, Q, QuerySet, Value
from django.db.models.functions import Coalesce
from django.utils import timezone

from apps.pdi.models import AcaoPDI

FAIXA_1_7 = '1-7'
FAIXA_8_30 = '8-30'
FAIXA_30_PLUS = '30+'
FAIXAS_ATRASO = frozenset({FAIXA_1_7, FAIXA_8_30, FAIXA_30_PLUS})

FaixaAtraso = Literal['1-7', '8-30', '30+']

_FILTER_ATRASADA_COM_PRAZO = Q(
    acoes__status=AcaoPDI.Status.ATRASADA,
    acoes__prazo__isnull=False,
)
_FILTER_NAO_CONCLUIDA_COM_PRAZO = (
    ~Q(acoes__status=AcaoPDI.Status.CONCLUIDA)
    & Q(acoes__prazo__isnull=False)
)


class _DaysBetween(Func):
    """Diferença inteira de dias: ``end_date - start_date``.

    PostgreSQL: ``date - date`` → integer.
    SQLite: ``julianday`` arredondado para inteiro.
    """

    arity = 2
    output_field = IntegerField()

    def as_postgresql(self, compiler, connection, **extra_context):
        return super().as_sql(
            compiler,
            connection,
            template='(%(expressions)s)',
            arg_joiner=' - ',
            **extra_context,
        )

    def as_sqlite(self, compiler, connection, **extra_context):
        return super().as_sql(
            compiler,
            connection,
            template='CAST(julianday(%(expressions)s) AS INTEGER)',
            arg_joiner=') - julianday(',
            **extra_context,
        )


def faixa_atraso_from_dias(dias: int | None) -> FaixaAtraso | None:
    """Predicado de faixa a partir de ``dias_atraso_max``.

    Retorna ``None`` quando não há atraso elegível (``dias`` nulo ou ``< 1``).
    """
    if dias is None or dias < 1:
        return None
    if dias <= 7:
        return FAIXA_1_7
    if dias <= 30:
        return FAIXA_8_30
    return FAIXA_30_PLUS


def annotate_overdue_metrics(
    queryset: QuerySet,
    *,
    today: date | None = None,
) -> QuerySet:
    """Annotate queryset de ``PDI`` com métricas de atraso.

    Campos adicionados: ``acoes_atrasadas_count``, ``dias_atraso_max``,
    ``proximo_prazo``. Idempotente se chamado sobre queryset já anotado
    com os mesmos aliases (Django sobrescreve o annotate).
    """
    if today is None:
        today = timezone.localdate()

    return queryset.annotate(
        acoes_atrasadas_count=Coalesce(
            Count(
                'acoes',
                filter=Q(acoes__status=AcaoPDI.Status.ATRASADA),
                distinct=True,
            ),
            Value(0),
        ),
        dias_atraso_max=_DaysBetween(
            Value(today),
            Min('acoes__prazo', filter=_FILTER_ATRASADA_COM_PRAZO),
        ),
        proximo_prazo=Min(
            'acoes__prazo',
            filter=_FILTER_NAO_CONCLUIDA_COM_PRAZO,
        ),
    )


def filter_com_atrasadas(queryset: QuerySet) -> QuerySet:
    """Filtro ``atrasadas=1``: PDIs com ≥1 ação ``atrasada``."""
    return queryset.filter(acoes_atrasadas_count__gte=1)


def filter_faixa_atraso(
    queryset: QuerySet,
    faixa: str | None,
) -> QuerySet:
    """Filtra por ``faixa_atraso`` sobre annotate ``dias_atraso_max``.

    Faixa desconhecida ou vazia → queryset inalterado.
    Requer ``annotate_overdue_metrics`` prévio (ou alias equivalente).
    """
    if not faixa or faixa not in FAIXAS_ATRASO:
        return queryset

    if faixa == FAIXA_1_7:
        return queryset.filter(dias_atraso_max__gte=1, dias_atraso_max__lte=7)
    if faixa == FAIXA_8_30:
        return queryset.filter(dias_atraso_max__gte=8, dias_atraso_max__lte=30)
    return queryset.filter(dias_atraso_max__gt=30)
