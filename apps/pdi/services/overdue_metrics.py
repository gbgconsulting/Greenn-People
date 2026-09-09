"""Métricas derivadas de atraso de ações de PDI (annotate / filtros).

Definições (data-model + research §4 / contracts/pdi-overdue-list):

- ``acoes_atrasadas_count``: count de ações ``status=atrasada``
- ``dias_atraso_max``: ``hoje - min(prazo)`` entre atrasadas com prazo;
  ``None`` se zero atrasadas elegíveis
- ``proximo_prazo``: ``min(prazo)`` entre ações não concluídas com prazo
- Faixas de ``dias_atraso_max``: ``1-7`` e ``8-30`` inclusivas nos
    extremos; ``30+`` aberto (``> 30``). Ação sem prazo fica fora.

Agregação org (digest US4 / research §5):

- Totais e top áreas/gestores só sobre PDIs **não arquivados**
- Ranking de foco por nº de ações ``atrasada`` (desc)

Widget dashboard (US5 / research §6):

- Contagem scoped via ``get_visible_users`` + fatia próprias/equipe
- Arquivados fora; AuthZ só no backend (template só renderiza números)
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import TYPE_CHECKING, Literal
from urllib.parse import urlencode

from django.db.models import Count, Func, IntegerField, Min, Q, QuerySet, Value
from django.db.models.functions import Coalesce
from django.urls import reverse
from django.utils import timezone

from apps.accounts.services.scope import (
    VISAO_EQUIPE,
    OwnershipVisao,
    apply_ownership_visao,
    get_visible_users,
    resolve_ownership_visao,
)
from apps.pdi.models import AcaoPDI, PDI

if TYPE_CHECKING:
    from apps.accounts.models import CustomUser

FAIXA_1_7 = '1-7'
FAIXA_8_30 = '8-30'
FAIXA_30_PLUS = '30+'
FAIXAS_ATRASO = frozenset({FAIXA_1_7, FAIXA_8_30, FAIXA_30_PLUS})

FaixaAtraso = Literal['1-7', '8-30', '30+']

# Top focos do digest RH (e-mail); charts usam DENSITY_TOP_N aparte.
DEFAULT_DIGEST_TOP_N = 5


@dataclass(frozen=True, slots=True)
class OverdueFocusItem:
    """Área ou gestor com concentração de ações atrasadas."""

    id: int
    nome: str
    acoes_atrasadas: int


@dataclass(frozen=True, slots=True)
class OrgOverdueAggregation:
    """Snapshot org de atrasos para digest (FR-009/010)."""

    pdis_com_atraso: int
    acoes_atrasadas: int
    top_areas: tuple[OverdueFocusItem, ...]
    top_gestores: tuple[OverdueFocusItem, ...]

    @property
    def has_atrasos(self) -> bool:
        return self.acoes_atrasadas > 0


@dataclass(frozen=True, slots=True)
class ScopedOverdueCounts:
    """Contagem de atrasos no escopo do viewer (widget dashboard US5)."""

    pdis_com_atraso: int
    acoes_atrasadas: int
    list_href: str

    @property
    def has_atrasos(self) -> bool:
        return self.acoes_atrasadas > 0 or self.pdis_com_atraso > 0

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


def _acoes_atrasadas_org_qs() -> QuerySet:
    """Ações ``atrasada`` em PDI não arquivado (base do digest org)."""
    return AcaoPDI.objects.filter(
        status=AcaoPDI.Status.ATRASADA,
    ).exclude(pdi__status=PDI.Status.ARQUIVADO)


def _top_focos(
    queryset: QuerySet,
    *,
    group_id: str,
    group_nome: str,
    top_n: int,
) -> tuple[OverdueFocusItem, ...]:
    if top_n <= 0:
        return ()

    rows = (
        queryset.values(group_id, group_nome)
        .annotate(acoes_atrasadas=Count('id'))
        .order_by('-acoes_atrasadas', group_nome)[:top_n]
    )
    return tuple(
        OverdueFocusItem(
            id=int(row[group_id]),
            nome=str(row[group_nome] or ''),
            acoes_atrasadas=int(row['acoes_atrasadas']),
        )
        for row in rows
        if row[group_id] is not None
    )


def aggregate_org_overdue_metrics(
    *,
    top_n: int = DEFAULT_DIGEST_TOP_N,
) -> OrgOverdueAggregation:
    """Agrega atrasos da organização para o digest RH (US4).

    Inclui apenas PDIs não arquivados. Top áreas/gestores ordenados por
    nº de ações atrasadas (desc); donos sem área ou sem gestor ficam de
    fora dos rankings, mas entram nos totais.
    """
    base = _acoes_atrasadas_org_qs()
    acoes_atrasadas = base.count()
    if acoes_atrasadas == 0:
        return OrgOverdueAggregation(
            pdis_com_atraso=0,
            acoes_atrasadas=0,
            top_areas=(),
            top_gestores=(),
        )

    pdis_com_atraso = base.values('pdi_id').distinct().count()
    top_areas = _top_focos(
        base.filter(pdi__usuario__area_id__isnull=False),
        group_id='pdi__usuario__area_id',
        group_nome='pdi__usuario__area__nome',
        top_n=top_n,
    )
    top_gestores = _top_focos(
        base.filter(pdi__usuario__line_manager_id__isnull=False),
        group_id='pdi__usuario__line_manager_id',
        group_nome='pdi__usuario__line_manager__nome',
        top_n=top_n,
    )
    return OrgOverdueAggregation(
        pdis_com_atraso=pdis_com_atraso,
        acoes_atrasadas=acoes_atrasadas,
        top_areas=top_areas,
        top_gestores=top_gestores,
    )


def overdue_filtered_list_href(*, visao: OwnershipVisao = VISAO_EQUIPE) -> str:
    """Href relativo da listagem PDI com ``atrasadas=1`` (CTA do widget)."""
    query = urlencode({'visao': visao, 'atrasadas': '1'})
    return f'{reverse("pdi:list")}?{query}'


def _acoes_atrasadas_scoped_qs(
    viewer: CustomUser,
    *,
    visao: OwnershipVisao,
) -> QuerySet:
    """Ações ``atrasada`` em PDI não arquivado, donos no escopo + fatia."""
    qs = (
        AcaoPDI.objects.filter(status=AcaoPDI.Status.ATRASADA)
        .exclude(pdi__status=PDI.Status.ARQUIVADO)
        .filter(pdi__usuario__in=get_visible_users(viewer))
    )
    return apply_ownership_visao(qs, viewer, visao, user_field='pdi__usuario')


def count_scoped_overdue_metrics(
    viewer: CustomUser,
    *,
    visao: str | OwnershipVisao | None = VISAO_EQUIPE,
) -> ScopedOverdueCounts:
    """Conta PDIs/ações atrasadas no escopo do ``viewer`` (US5).

    AuthZ: ``get_visible_users`` + ``resolve_ownership_visao`` (query string
    não autoriza). Arquivados fora. ``list_href`` aponta para a listagem
    filtrada; a view de listagem revalida o escopo.
    """
    resolved = resolve_ownership_visao(viewer, visao)
    base = _acoes_atrasadas_scoped_qs(viewer, visao=resolved)
    acoes_atrasadas = base.count()
    if acoes_atrasadas == 0:
        return ScopedOverdueCounts(
            pdis_com_atraso=0,
            acoes_atrasadas=0,
            list_href=overdue_filtered_list_href(visao=resolved),
        )
    pdis_com_atraso = base.values('pdi_id').distinct().count()
    return ScopedOverdueCounts(
        pdis_com_atraso=pdis_com_atraso,
        acoes_atrasadas=acoes_atrasadas,
        list_href=overdue_filtered_list_href(visao=resolved),
    )
