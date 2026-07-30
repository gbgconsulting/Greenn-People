"""Helpers de formatação de payloads Chart.js (sem fórmulas de negócio).

Contagem/agrupamento e shape `has_data` / `labels` / `values` / `empty_message`.
Cores Status Triad alinhadas ao Freeze (`docs/design-system.md` + contratos 005).
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from typing import Any

# Status Triad — alta / média / baixa (emerald-600 / amber-600 / rose-600)
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
) -> dict[str, Any]:
    """Monta payload de série única (doughnut/bar) no shape dos contratos."""
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
    }
    if keys is not None:
        payload['keys'] = list(keys) if resolved_has_data else []
    if colors is not None:
        payload['colors'] = list(colors) if resolved_has_data else []
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
    chart_type: str = 'bar_grouped',
) -> dict[str, Any]:
    """Monta payload multi-série (ex.: esperado × nota) no shape do contrato pessoal.

    Valores ``None`` em ``series[].values`` permanecem null (não viram 0).
    """
    resolved_has_data = bool(has_data) if has_data is not None else bool(labels)
    normalized_series: list[dict[str, Any]] = []
    if resolved_has_data:
        for serie in series:
            entry = dict(serie)
            raw_values = entry.get('values') or []
            entry['values'] = [_nullable_number(v) for v in raw_values]
            normalized_series.append(entry)
    return {
        'id': chart_id,
        'type': chart_type,
        'has_data': resolved_has_data,
        'title': title,
        'labels': list(labels) if resolved_has_data else [],
        'series': normalized_series,
        'empty_message': empty_message,
    }


def aderencia_distribution_payload(
    status_keys: Iterable[str],
    *,
    chart_id: str = 'chart-aderencia-distribuicao',
    title: str = 'Distribuição de aderência',
    empty_message: str = 'Nenhum snapshot de aderência para este ciclo.',
    chart_type: str = 'doughnut_or_bar',
) -> dict[str, Any]:
    """Formata contagens alta/média/baixa já classificadas (só agrupamento)."""
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
) -> dict[str, Any]:
    """Formata um mapa chave→contagem na ordem contratual (progresso / escopo)."""
    values = [int(key_counts.get(key, 0)) for key in ordered_keys]
    labels = [labels_by_key.get(key, key) for key in ordered_keys]
    return series_payload(
        chart_id=chart_id,
        chart_type=chart_type,
        title=title,
        labels=labels,
        values=values,
        empty_message=empty_message,
        keys=ordered_keys,
        colors=list(colors) if colors is not None else None,
    )
