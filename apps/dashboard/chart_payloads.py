"""Helpers de formatação de payloads Chart.js (sem fórmulas de negócio).

Contagem/agrupamento e shape `has_data` / `labels` / `values` / `series` /
`legend_items` / `total` / `empty_message`.

Cores Status Triad alinhadas ao Freeze (`docs/design-system.md` + contratos 005).
Types canônicos: `contracts/chart-catalog.md` (Freeze A / FR-001).
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from typing import Any

# ---------------------------------------------------------------------------
# Status Triad — alta / média / baixa (emerald-600 / amber-600 / rose-600)
# ---------------------------------------------------------------------------
STATUS_TRIAD_ALTA = '#059669'
STATUS_TRIAD_MEDIA = '#d97706'
STATUS_TRIAD_BAIXA = '#e11d48'

STATUS_TRIAD_COLORS: tuple[str, str, str] = (
    STATUS_TRIAD_ALTA,
    STATUS_TRIAD_MEDIA,
    STATUS_TRIAD_BAIXA,
)

ADERENCIA_KEYS: tuple[str, str, str] = ('alta', 'media', 'baixa')
ADERENCIA_LABELS: dict[str, str] = {
    'alta': 'Alta',
    'media': 'Média',
    'baixa': 'Baixa',
}
ADERENCIA_COLORS: dict[str, str] = {
    'alta': STATUS_TRIAD_ALTA,
    'media': STATUS_TRIAD_MEDIA,
    'baixa': STATUS_TRIAD_BAIXA,
}

SEM_AVALIACAO_KEY = 'sem_avaliacao'
SEM_AVALIACAO_LABEL = 'Sem avaliação'

# ---------------------------------------------------------------------------
# Types canônicos (chart-catalog.md) — emitidos como first-class no Python
# ---------------------------------------------------------------------------
CHART_TYPE_BAR = 'bar'
CHART_TYPE_DOUGHNUT = 'doughnut'
CHART_TYPE_DOUGHNUT_OR_BAR = 'doughnut_or_bar'
CHART_TYPE_BAR_GROUPED = 'bar_grouped'
CHART_TYPE_BAR_HORIZONTAL = 'bar_horizontal'
CHART_TYPE_AREA = 'area'

CHART_TYPES: frozenset[str] = frozenset({
    CHART_TYPE_BAR,
    CHART_TYPE_DOUGHNUT,
    CHART_TYPE_DOUGHNUT_OR_BAR,
    CHART_TYPE_BAR_GROUPED,
    CHART_TYPE_BAR_HORIZONTAL,
    CHART_TYPE_AREA,
})

# Série única: bar / doughnut / doughnut_or_bar / bar_horizontal / area
SINGLE_SERIES_TYPES: frozenset[str] = frozenset({
    CHART_TYPE_BAR,
    CHART_TYPE_DOUGHNUT,
    CHART_TYPE_DOUGHNUT_OR_BAR,
    CHART_TYPE_BAR_HORIZONTAL,
    CHART_TYPE_AREA,
})

# Multi-série: bar_grouped (esperado×nota) ou area (tendência multi)
MULTI_SERIES_TYPES: frozenset[str] = frozenset({
    CHART_TYPE_BAR_GROUPED,
    CHART_TYPE_AREA,
})

# ---------------------------------------------------------------------------
# Paleta de acabamento (não-semântica) — espelha COLOR_FINISH_* no JS
# Contagens / rankings / cobertura: mono teal; amber só no gargalo (DS).
# ---------------------------------------------------------------------------
FINISH_TEAL = '#0d9488'
FINISH_SLATE = '#64748b'
FINISH_AMBER_HIGHLIGHT = STATUS_TRIAD_MEDIA  # gargalo / below-meta (não reinventar Triad)


def count_by_ordered_keys(
    items: Iterable[str | None],
    keys: Sequence[str],
) -> list[int]:
    """Conta ocorrências de cada chave na ordem de `keys` (ignorando demais)."""
    counts = Counter(item for item in items if item is not None)
    return [int(counts.get(key, 0)) for key in keys]


def colors_for_keys(
    keys: Sequence[str],
    *,
    color_map: Mapping[str, str] | None = None,
    fallback: Sequence[str] = STATUS_TRIAD_COLORS,
) -> list[str]:
    """Resolve cores por chave; fallback cicla na Status Triad."""
    mapping = color_map or ADERENCIA_COLORS
    result: list[str] = []
    for index, key in enumerate(keys):
        if key in mapping:
            result.append(mapping[key])
        else:
            result.append(fallback[index % len(fallback)])
    return result


def mono_finish_colors(
    length: int,
    *,
    base: str = FINISH_TEAL,
    highlight_index: int | None = None,
    highlight: str = FINISH_AMBER_HIGHLIGHT,
) -> list[str]:
    """Lista monocromática de acabamento; amber opcional no índice do gargalo.

    Só apresentação — o caller escolhe `highlight_index` a partir de contagens
    já calculadas (ex.: maior volume). Não inventa métrica.
    """
    if length <= 0:
        return []
    colors = [base] * int(length)
    if (
        highlight_index is not None
        and 0 <= highlight_index < length
    ):
        colors[highlight_index] = highlight
    return colors


def _legend_items_single(
    labels: Sequence[str],
    values: Sequence[int | float | None],
    colors: Sequence[str] | None = None,
) -> list[dict[str, Any]]:
    """Pares label/valor(/cor) para figcaption — texto além da cor (FR-007)."""
    items: list[dict[str, Any]] = []
    color_list = list(colors) if colors is not None else []
    for index, label in enumerate(labels):
        value = values[index] if index < len(values) else None
        item: dict[str, Any] = {
            'label': label,
            'value': value,
        }
        if index < len(color_list):
            item['color'] = color_list[index]
        items.append(item)
    return items


def _legend_items_grouped(
    labels: Sequence[str],
    series: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Linhas por categoria com partes nomeadas (esperado × nota) — FR-007."""
    items: list[dict[str, Any]] = []
    for index, label in enumerate(labels):
        parts: list[dict[str, Any]] = []
        for serie in series:
            raw_values = serie.get('values') or []
            part: dict[str, Any] = {
                'label': serie.get('label') or serie.get('key') or '',
                'value': raw_values[index] if index < len(raw_values) else None,
            }
            if serie.get('color'):
                part['color'] = serie['color']
            elif serie.get('key') in ('nivel_esperado', 'nota_atual'):
                # Alinha ao init JS (GROUPED_DEFAULTS) para swatch no figcaption.
                part['color'] = (
                    FINISH_SLATE
                    if serie.get('key') == 'nivel_esperado'
                    else STATUS_TRIAD_ALTA
                )
            parts.append(part)
        items.append({'label': label, 'parts': parts})
    return items


def series_payload(
    *,
    chart_id: str,
    chart_type: str,
    title: str,
    labels: Sequence[str],
    values: Sequence[int | float | None],
    empty_message: str,
    keys: Sequence[str] | None = None,
    colors: Sequence[str] | None = None,
    has_data: bool | None = None,
    total: int | None = None,
    center_text: str | None = None,
) -> dict[str, Any]:
    """Monta payload de série única no shape dos contratos.

    Types suportados (catálogo): ``bar``, ``doughnut``, ``doughnut_or_bar``,
    ``bar_horizontal``, ``area``. ``total`` alimenta o valor central do doughnut
    no init JS quando ``center_text`` não é informado.
    """
    numeric_values = [0 if v is None else v for v in values]
    computed_total = int(sum(numeric_values)) if total is None else int(total)
    resolved_has_data = (
        bool(has_data) if has_data is not None else computed_total > 0
    )

    payload: dict[str, Any] = {
        'id': chart_id,
        'type': chart_type,
        'has_data': resolved_has_data,
        'title': title,
        # Sem série fictícia: labels/values vazios quando has_data é falso (FR-006).
        'labels': list(labels) if resolved_has_data else [],
        'values': list(values) if resolved_has_data else [],
        'total': computed_total if resolved_has_data else 0,
        'empty_message': empty_message,
        # Resumo textual espelhando faixas/séries (FR-007 / R4).
        'legend_items': (
            _legend_items_single(labels, values, colors)
            if resolved_has_data
            else []
        ),
    }
    if keys is not None:
        payload['keys'] = list(keys) if resolved_has_data else []
    if colors is not None:
        payload['colors'] = list(colors) if resolved_has_data else []
    # Texto opcional do centro (doughnut) — JS: center_text || total.
    if center_text is not None and resolved_has_data:
        payload['center_text'] = center_text
    return payload


def empty_series_payload(
    *,
    chart_id: str,
    chart_type: str,
    title: str,
    empty_message: str,
    keys: Sequence[str] | None = None,
    labels: Sequence[str] | None = None,
) -> dict[str, Any]:
    """Payload honesto sem série fictícia (`has_data: false`)."""
    return series_payload(
        chart_id=chart_id,
        chart_type=chart_type,
        title=title,
        labels=list(labels or []),
        values=[],
        empty_message=empty_message,
        keys=keys,
        colors=None,
        has_data=False,
        total=0,
    )


def _nullable_number(value: Any) -> float | int | None:
    """Preserva ``None`` como null JSON; não converte ausência em zero."""
    if value is None:
        return None
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (int, float)):
        return value
    return float(value)


def grouped_series_payload(
    *,
    chart_id: str,
    title: str,
    labels: Sequence[str],
    series: Sequence[Mapping[str, Any]],
    empty_message: str,
    has_data: bool | None = None,
    chart_type: str = CHART_TYPE_BAR_GROUPED,
    total: int | None = None,
) -> dict[str, Any]:
    """Monta payload multi-série no shape do contrato.

    Types típicos: ``bar_grouped`` (esperado × nota) ou ``area`` (tendência
    multi). Valores ``None`` em ``series[].values`` permanecem null (não viram 0).
    ``total`` é opcional (compatível com o shape canônico); não inventa soma.
    """
    resolved_has_data = bool(has_data) if has_data is not None else bool(labels)
    normalized_series: list[dict[str, Any]] = []
    if resolved_has_data:
        for serie in series:
            entry = dict(serie)
            raw_values = entry.get('values') or []
            entry['values'] = [_nullable_number(v) for v in raw_values]
            normalized_series.append(entry)

    payload: dict[str, Any] = {
        'id': chart_id,
        'type': chart_type,
        'has_data': resolved_has_data,
        'title': title,
        'labels': list(labels) if resolved_has_data else [],
        'series': normalized_series,
        'empty_message': empty_message,
        # Resumo textual por competência/categoria (FR-007 / R4).
        'legend_items': (
            _legend_items_grouped(labels, normalized_series)
            if resolved_has_data
            else []
        ),
    }
    # Compatível com shape canônico; só emite quando o caller passa total.
    if total is not None:
        payload['total'] = int(total) if resolved_has_data else 0
    return payload


def aderencia_distribution_payload(
    status_keys: Iterable[str],
    *,
    chart_id: str = 'chart-aderencia-distribuicao',
    title: str = 'Distribuição de aderência',
    empty_message: str = 'Ainda não há dados de aderência para este ciclo.',
    chart_type: str = CHART_TYPE_DOUGHNUT_OR_BAR,
    center_text: str | None = None,
) -> dict[str, Any]:
    """Formata contagens alta/média/baixa já classificadas (só agrupamento).

    ``total`` (soma das faixas) alimenta o valor central do doughnut no JS.
    ``center_text`` sobrescreve o centro quando informado (sem inventar %).
    """
    values = count_by_ordered_keys(status_keys, ADERENCIA_KEYS)
    labels = [ADERENCIA_LABELS[key] for key in ADERENCIA_KEYS]
    colors = [ADERENCIA_COLORS[key] for key in ADERENCIA_KEYS]
    return series_payload(
        chart_id=chart_id,
        chart_type=chart_type,
        title=title,
        labels=labels,
        values=values,
        empty_message=empty_message,
        keys=ADERENCIA_KEYS,
        colors=colors,
        center_text=center_text,
    )


def categorical_counts_payload(
    key_counts: Mapping[str, int],
    *,
    ordered_keys: Sequence[str],
    labels_by_key: Mapping[str, str],
    chart_id: str,
    chart_type: str,
    title: str,
    empty_message: str,
    colors: Sequence[str] | None = None,
    highlight_max: bool = False,
) -> dict[str, Any]:
    """Formata um mapa chave→contagem na ordem contratual (progresso / escopo).

    Com ``highlight_max=True`` e sem ``colors``, aplica mono teal + amber no
    índice de maior volume (gargalo) — só acabamento, mesmos counts.
    """
    values = [int(key_counts.get(key, 0)) for key in ordered_keys]
    labels = [labels_by_key.get(key, key) for key in ordered_keys]
    resolved_colors: Sequence[str] | None = colors
    if resolved_colors is None and highlight_max and values:
        # Amber só se houver pico real (máx estritamente > mín); empate total → mono.
        max_index = max(range(len(values)), key=lambda i: values[i])
        peak = values[max_index]
        has_peak = peak > 0 and peak > min(values)
        resolved_colors = mono_finish_colors(
            len(values),
            highlight_index=max_index if has_peak else None,
        )
    return series_payload(
        chart_id=chart_id,
        chart_type=chart_type,
        title=title,
        labels=labels,
        values=values,
        empty_message=empty_message,
        keys=ordered_keys,
        colors=list(resolved_colors) if resolved_colors is not None else None,
    )


def coverage_bar_payload(
    rows: Sequence[Mapping[str, Any]],
    *,
    chart_id: str,
    title: str,
    label_key: str,
    empty_message: str,
    chart_type: str = CHART_TYPE_BAR_HORIZONTAL,
    value_key: str = 'percentual',
    highlight_lowest: bool = True,
) -> dict[str, Any]:
    """Payload ``bar_horizontal`` de cobertura (% ou totais) — FR-006 / Freeze B.

    ``rows`` vêm de ``coverage_by_area`` / ``coverage_by_cargo`` (composição).
    Amber no índice de **menor** cobertura só quando há gargalo real
    (mínimo estritamente menor que o máximo) — sem inventar métrica.
    """
    usable = [
        row for row in rows
        if int(row.get('total') or 0) > 0 and row.get(value_key) is not None
    ]
    if not usable:
        return empty_series_payload(
            chart_id=chart_id,
            chart_type=chart_type,
            title=title,
            empty_message=empty_message,
        )

    labels = [str(row.get(label_key) or '') for row in usable]
    values: list[float] = [float(row[value_key]) for row in usable]

    highlight_index: int | None = None
    if highlight_lowest and values:
        # Empate total (ex.: todas 100%) → sem amber; primeiro mín se houver gap.
        min_index = min(range(len(values)), key=lambda i: values[i])
        if values[min_index] < max(values):
            highlight_index = min_index

    colors = mono_finish_colors(
        len(values),
        highlight_index=highlight_index,
    )
    return series_payload(
        chart_id=chart_id,
        chart_type=chart_type,
        title=title,
        labels=labels,
        values=values,
        empty_message=empty_message,
        colors=colors,
        total=len(usable),
    )
