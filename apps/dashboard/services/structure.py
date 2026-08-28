"""Aggregações de estrutura, cobertura e lacunas (FR-019 / RF-29 / FR-006).

Cobertura = composição de Counts sobre ``visible`` já resolvido + presença de
``Avaliacao`` no ciclo (mesma regra “tem avaliação” do team chart). O caller
passa o QS; este módulo **nunca** chama ``get_visible_users``.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Literal

from django.db.models import Avg, Count, DecimalField, ExpressionWrapper, F, Q, QuerySet

from apps.accounts.models import CustomUser
from apps.cycles.models import Ciclo
from apps.dashboard.models import AderenciaSnapshot
from apps.dashboard.services.eligible_leaders import eligible_leader_queryset
from apps.reviews.models import AvaliacaoCompetencia

_QUANT = Decimal('0.01')

CoverageDimension = Literal['area', 'cargo']


def _apply_structure_filters(
    visible: QuerySet[CustomUser],
    *,
    area_id: int | None = None,
    cargo_id: int | None = None,
) -> QuerySet[CustomUser]:
    """Filtros de área/cargo sobre o QS já escopado (sem AuthZ nova)."""
    qs = visible
    if area_id is not None:
        qs = qs.filter(area_id=area_id)
    if cargo_id is not None:
        qs = qs.filter(cargo_id=cargo_id)
    return qs


def _coverage_percent(com_avaliacao: int, total: int) -> Decimal | None:
    """% cobertos = com_avaliacao / total × 100 (só composição de counts)."""
    if total <= 0:
        return None
    return (Decimal(com_avaliacao) * Decimal('100') / Decimal(total)).quantize(
        _QUANT,
    )


def _coverage_row(
    *,
    group_id: int | None,
    group_nome: str | None,
    fallback_nome: str,
    id_key: str,
    nome_key: str,
    total: int,
    com_avaliacao: int,
) -> dict:
    sem = max(int(total) - int(com_avaliacao), 0)
    return {
        id_key: group_id,
        nome_key: group_nome or fallback_nome,
        'total': int(total),
        'com_avaliacao': int(com_avaliacao),
        'sem_avaliacao': sem,
        'percentual': _coverage_percent(int(com_avaliacao), int(total)),
    }


def leaders_in_scope(visible: QuerySet[CustomUser]) -> QuerySet[CustomUser]:
    """Gestores elegíveis visíveis com pelo menos um liderado ativo no escopo."""
    visible_ids = visible.values('pk')
    lider_ids = (
        CustomUser.objects.filter(
            line_manager_id__isnull=False,
            pk__in=visible_ids,
            is_active=True,
        )
        .values_list('line_manager_id', flat=True)
        .distinct()
    )
    return (
        eligible_leader_queryset()
        .filter(pk__in=lider_ids)
        .filter(pk__in=visible.values('pk'))
        .select_related('area', 'cargo')
        .order_by('nome', 'email')
    )


def leaders_with_adherence(
    visible: QuerySet[CustomUser],
    ciclo: Ciclo | None,
    *,
    area_id: int | None = None,
    cargo_id: int | None = None,
) -> list[dict]:
    """Líderes da estrutura com snapshot de aderência do ciclo (se houver).

    ``colaboradores`` = diretos no mesmo ``visible`` (escopo AuthZ já resolvido).
    Ordena por % ASC (pior primeiro); sem snapshot vem antes de qualquer %.
    """
    lideres = leaders_in_scope(visible)
    if area_id is not None:
        lideres = lideres.filter(area_id=area_id)
    if cargo_id is not None:
        lideres = lideres.filter(cargo_id=cargo_id)

    lider_pks = list(lideres.values_list('pk', flat=True))
    colaborador_counts: dict[int, int] = {
        row['line_manager_id']: int(row['n'])
        for row in (
            visible.filter(line_manager_id__in=lider_pks)
            .values('line_manager_id')
            .annotate(n=Count('pk'))
        )
    }

    snapshots: dict[int, AderenciaSnapshot] = {}
    if ciclo is not None:
        snapshots = {
            snap.lider_id: snap
            for snap in AderenciaSnapshot.objects.filter(
                ciclo=ciclo,
                lider_id__in=lider_pks,
            ).select_related('lider')
        }

    rows = [
        {
            'lider': lider,
            'snapshot': snapshots.get(lider.pk),
            'colaboradores': colaborador_counts.get(lider.pk, 0),
        }
        for lider in lideres
    ]
    # Pior aderência primeiro; sem snapshot = exceção (antes de qualquer %).
    rows.sort(
        key=lambda item: (
            item['snapshot'].percentual
            if item.get('snapshot') is not None
            else Decimal('-1'),
            (item['lider'].nome or item['lider'].email or '').lower(),
        ),
    )
    return rows


def partition_gap_rows(
    rows: list[dict],
) -> tuple[list[dict], list[dict]]:
    """Separa lacunas acionáveis (média > 0) das demais (ocultas no toggle)."""
    prioritarias: list[dict] = []
    restantes: list[dict] = []
    for row in rows:
        lacuna = row.get('media_lacuna')
        if lacuna is not None and lacuna > 0:
            prioritarias.append(row)
        else:
            restantes.append(row)
    return prioritarias, restantes


def _competency_lines_qs(
    visible: QuerySet[CustomUser],
    ciclo: Ciclo,
    *,
    area_id: int | None = None,
    cargo_id: int | None = None,
) -> QuerySet[AvaliacaoCompetencia]:
    qs = AvaliacaoCompetencia.objects.filter(
        avaliacao__ciclo=ciclo,
        avaliacao__usuario__in=visible,
        nota_lider__isnull=False,
    ).annotate(
        lacuna=ExpressionWrapper(
            F('nivel_esperado_utilizado') - F('nota_lider'),
            output_field=DecimalField(max_digits=10, decimal_places=2),
        ),
    )
    if area_id is not None:
        qs = qs.filter(avaliacao__usuario__area_id=area_id)
    if cargo_id is not None:
        qs = qs.filter(avaliacao__usuario__cargo_id=cargo_id)
    return qs


def _quantize_avg(value) -> Decimal | None:
    if value is None:
        return None
    return Decimal(value).quantize(_QUANT)


def distinct_cargo_count(
    visible: QuerySet[CustomUser],
    *,
    area_id: int | None = None,
    cargo_id: int | None = None,
) -> int:
    """Quantidade de cargos distintos no escopo filtrado (inclui ``NULL`` como um)."""
    qs = _apply_structure_filters(
        visible,
        area_id=area_id,
        cargo_id=cargo_id,
    )
    return qs.values('cargo_id').distinct().count()


def coverage_summary(
    visible: QuerySet[CustomUser],
    ciclo: Ciclo | None,
    *,
    area_id: int | None = None,
    cargo_id: int | None = None,
) -> dict:
    """KPI de cobertura no escopo filtrado (FR-006 / FR-013).

    Conta usuários em ``visible`` vs presença de ``Avaliacao`` no ciclo —
    sem recalcular fórmula de nota/aderência.
    """
    qs = _apply_structure_filters(
        visible,
        area_id=area_id,
        cargo_id=cargo_id,
    )
    total = qs.count()
    if ciclo is None:
        return {
            'total': total,
            'com_avaliacao': None,
            'sem_avaliacao': None,
            'percentual': None,
            'has_ciclo': False,
        }

    agg = qs.aggregate(
        com_avaliacao=Count(
            'avaliacoes',
            filter=Q(avaliacoes__ciclo=ciclo),
            distinct=True,
        ),
    )
    com = int(agg['com_avaliacao'] or 0)
    return {
        'total': total,
        'com_avaliacao': com,
        'sem_avaliacao': max(total - com, 0),
        'percentual': _coverage_percent(com, total),
        'has_ciclo': True,
    }


def _coverage_by_dimension(
    visible: QuerySet[CustomUser],
    ciclo: Ciclo | None,
    *,
    dimension: CoverageDimension,
    area_id: int | None = None,
    cargo_id: int | None = None,
) -> list[dict]:
    """Agrupa cobertura por área ou cargo sobre ``visible`` + ciclo."""
    if ciclo is None:
        return []

    qs = _apply_structure_filters(
        visible,
        area_id=area_id,
        cargo_id=cargo_id,
    )
    if not qs.exists():
        return []

    if dimension == 'area':
        id_field, nome_field = 'area_id', 'area__nome'
        id_key, nome_key = 'area_id', 'area_nome'
        fallback = 'Sem área'
        order = 'area__nome'
    else:
        id_field, nome_field = 'cargo_id', 'cargo__nome'
        id_key, nome_key = 'cargo_id', 'cargo_nome'
        fallback = 'Sem cargo'
        order = 'cargo__nome'

    raw_rows = (
        qs.values(id_field, nome_field)
        .annotate(
            total=Count('id', distinct=True),
            com_avaliacao=Count(
                'avaliacoes',
                filter=Q(avaliacoes__ciclo=ciclo),
                distinct=True,
            ),
        )
        .order_by(order)
    )

    rows = [
        _coverage_row(
            group_id=row[id_field],
            group_nome=row[nome_field],
            fallback_nome=fallback,
            id_key=id_key,
            nome_key=nome_key,
            total=row['total'],
            com_avaliacao=row['com_avaliacao'] or 0,
        )
        for row in raw_rows
    ]
    # Pior cobertura primeiro (gargalo acionável); desempate pelo nome.
    rows.sort(
        key=lambda r: (
            r['percentual'] if r['percentual'] is not None else Decimal('101'),
            (r[nome_key] or '').lower(),
        ),
    )
    return rows


def coverage_by_area(
    visible: QuerySet[CustomUser],
    ciclo: Ciclo | None,
    *,
    area_id: int | None = None,
    cargo_id: int | None = None,
) -> list[dict]:
    """Cobertura (% com Avaliacao) agrupada por área no escopo."""
    return _coverage_by_dimension(
        visible,
        ciclo,
        dimension='area',
        area_id=area_id,
        cargo_id=cargo_id,
    )


def coverage_by_cargo(
    visible: QuerySet[CustomUser],
    ciclo: Ciclo | None,
    *,
    area_id: int | None = None,
    cargo_id: int | None = None,
) -> list[dict]:
    """Cobertura (% com Avaliacao) agrupada por cargo no escopo."""
    return _coverage_by_dimension(
        visible,
        ciclo,
        dimension='cargo',
        area_id=area_id,
        cargo_id=cargo_id,
    )


def build_structure_coverage(
    visible: QuerySet[CustomUser],
    ciclo: Ciclo | None,
    *,
    area_id: int | None = None,
    cargo_id: int | None = None,
) -> dict:
    """Pacote read-only: KPI + rows área/cargo + payloads de chart (FR-006).

    Recebe ``visible`` já resolvido. Payloads no shape canônico via
    ``chart_payloads.coverage_bar_payload``.
    """
    # Import local evita ciclo com views/payloads em startup.
    from apps.dashboard.chart_payloads import (
        EMPTY_KIND_COPY,
        EMPTY_KIND_ESCOPO,
        EMPTY_KIND_OPERACIONAL,
        EMPTY_KIND_SEM_DADO,
        coverage_bar_payload,
    )

    resumo = coverage_summary(
        visible,
        ciclo,
        area_id=area_id,
        cargo_id=cargo_id,
    )
    por_area = coverage_by_area(
        visible,
        ciclo,
        area_id=area_id,
        cargo_id=cargo_id,
    )
    por_cargo = coverage_by_cargo(
        visible,
        ciclo,
        area_id=area_id,
        cargo_id=cargo_id,
    )

    # Empty canônico (T006): operacional / escopo / sem_dado — sem série fictícia.
    empty_ciclo = EMPTY_KIND_COPY[EMPTY_KIND_OPERACIONAL]
    empty_escopo = EMPTY_KIND_COPY[EMPTY_KIND_ESCOPO]
    empty_dados = EMPTY_KIND_COPY[EMPTY_KIND_SEM_DADO]

    if ciclo is None:
        chart_area = coverage_bar_payload(
            [],
            chart_id='chart-cobertura-area',
            title='Cobertura por área',
            label_key='area_nome',
            empty_message=empty_ciclo,
        )
        chart_cargo = coverage_bar_payload(
            [],
            chart_id='chart-cobertura-cargo',
            title='Cobertura por cargo',
            label_key='cargo_nome',
            empty_message=empty_ciclo,
        )
    elif resumo['total'] == 0:
        chart_area = coverage_bar_payload(
            [],
            chart_id='chart-cobertura-area',
            title='Cobertura por área',
            label_key='area_nome',
            empty_message=empty_escopo,
        )
        chart_cargo = coverage_bar_payload(
            [],
            chart_id='chart-cobertura-cargo',
            title='Cobertura por cargo',
            label_key='cargo_nome',
            empty_message=empty_escopo,
        )
    else:
        chart_area = coverage_bar_payload(
            por_area,
            chart_id='chart-cobertura-area',
            title='Cobertura por área',
            label_key='area_nome',
            empty_message=empty_dados,
        )
        chart_cargo = coverage_bar_payload(
            por_cargo,
            chart_id='chart-cobertura-cargo',
            title='Cobertura por cargo',
            label_key='cargo_nome',
            empty_message=empty_dados,
        )

    return {
        'resumo': resumo,
        'por_area': por_area,
        'por_cargo': por_cargo,
        'chart_por_area': chart_area,
        'chart_por_cargo': chart_cargo,
    }


def gaps_by_area(
    visible: QuerySet[CustomUser],
    ciclo: Ciclo | None,
    *,
    area_id: int | None = None,
    cargo_id: int | None = None,
) -> list[dict]:
    """Lacunas médias por área × competência (nota_lider < nível esperado)."""
    if ciclo is None:
        return []

    rows = (
        _competency_lines_qs(
            visible,
            ciclo,
            area_id=area_id,
            cargo_id=cargo_id,
        )
        .values(
            'avaliacao__usuario__area_id',
            'avaliacao__usuario__area__nome',
            'competencia_id',
            'competencia__nome',
        )
        .annotate(
            media_nota=Avg('nota_lider'),
            media_esperado=Avg('nivel_esperado_utilizado'),
            media_lacuna=Avg('lacuna'),
            total=Count('pk'),
            com_lacuna=Count('pk', filter=Q(lacuna__gt=0)),
        )
        .order_by('-media_lacuna', 'avaliacao__usuario__area__nome', 'competencia__nome')
    )

    return [
        {
            'area_id': row['avaliacao__usuario__area_id'],
            'area_nome': row['avaliacao__usuario__area__nome'] or 'Sem área',
            'competencia_id': row['competencia_id'],
            'competencia_nome': row['competencia__nome'],
            'media_nota': _quantize_avg(row['media_nota']),
            'media_esperado': _quantize_avg(row['media_esperado']),
            'media_lacuna': _quantize_avg(row['media_lacuna']),
            'total': row['total'],
            'com_lacuna': row['com_lacuna'],
        }
        for row in rows
    ]


def gaps_by_cargo(
    visible: QuerySet[CustomUser],
    ciclo: Ciclo | None,
    *,
    area_id: int | None = None,
    cargo_id: int | None = None,
) -> list[dict]:
    """Lacunas médias por cargo × competência (nota_lider < nível esperado)."""
    if ciclo is None:
        return []

    rows = (
        _competency_lines_qs(
            visible,
            ciclo,
            area_id=area_id,
            cargo_id=cargo_id,
        )
        .values(
            'avaliacao__usuario__cargo_id',
            'avaliacao__usuario__cargo__nome',
            'competencia_id',
            'competencia__nome',
        )
        .annotate(
            media_nota=Avg('nota_lider'),
            media_esperado=Avg('nivel_esperado_utilizado'),
            media_lacuna=Avg('lacuna'),
            total=Count('pk'),
            com_lacuna=Count('pk', filter=Q(lacuna__gt=0)),
        )
        .order_by('-media_lacuna', 'avaliacao__usuario__cargo__nome', 'competencia__nome')
    )

    return [
        {
            'cargo_id': row['avaliacao__usuario__cargo_id'],
            'cargo_nome': row['avaliacao__usuario__cargo__nome'] or 'Sem cargo',
            'competencia_id': row['competencia_id'],
            'competencia_nome': row['competencia__nome'],
            'media_nota': _quantize_avg(row['media_nota']),
            'media_esperado': _quantize_avg(row['media_esperado']),
            'media_lacuna': _quantize_avg(row['media_lacuna']),
            'total': row['total'],
            'com_lacuna': row['com_lacuna'],
        }
        for row in rows
    ]
