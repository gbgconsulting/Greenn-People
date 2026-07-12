"""Aggregações de estrutura e lacunas de competências (FR-019 / RF-29)."""

from __future__ import annotations

from decimal import Decimal

from django.db.models import Avg, Count, DecimalField, ExpressionWrapper, F, Q, QuerySet

from apps.accounts.models import CustomUser
from apps.cycles.models import Ciclo
from apps.dashboard.models import AderenciaSnapshot
from apps.reviews.models import AvaliacaoCompetencia

_QUANT = Decimal('0.01')


def leaders_in_scope(visible: QuerySet[CustomUser]) -> QuerySet[CustomUser]:
    """Usuários visíveis que são gestores diretos de alguém no mesmo escopo."""
    visible_ids = visible.values('pk')
    lider_ids = (
        CustomUser.objects.filter(
            line_manager_id__isnull=False,
            pk__in=visible_ids,
        )
        .values_list('line_manager_id', flat=True)
        .distinct()
    )
    return (
        visible.filter(pk__in=lider_ids)
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
    """Líderes da estrutura com snapshot de aderência do ciclo (se houver)."""
    lideres = leaders_in_scope(visible)
    if area_id is not None:
        lideres = lideres.filter(area_id=area_id)
    if cargo_id is not None:
        lideres = lideres.filter(cargo_id=cargo_id)

    snapshots: dict[int, AderenciaSnapshot] = {}
    if ciclo is not None:
        snapshots = {
            snap.lider_id: snap
            for snap in AderenciaSnapshot.objects.filter(
                ciclo=ciclo,
                lider_id__in=lideres.values('pk'),
            ).select_related('lider')
        }

    return [
        {
            'lider': lider,
            'snapshot': snapshots.get(lider.pk),
        }
        for lider in lideres
    ]


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
