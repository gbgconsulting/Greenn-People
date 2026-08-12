"""T013 [US1] — types novos do catálogo + empty honesto (`has_data` falso).

Asserts só de presentation payload (`apps/dashboard/chart_payloads.py`).
Não altera asserts de stage/scope; sem formulas/AuthZ/models.
Contratos: chart-catalog.md, chart-baseline.md (shape + FR-002/003).
"""

from __future__ import annotations

from apps.dashboard.chart_payloads import (
    ADERENCIA_COLORS,
    ADERENCIA_KEYS,
    ADERENCIA_LABELS,
    CHART_TYPE_AREA,
    CHART_TYPE_BAR,
    CHART_TYPE_BAR_GROUPED,
    CHART_TYPE_BAR_HORIZONTAL,
    CHART_TYPE_DOUGHNUT,
    CHART_TYPE_DOUGHNUT_OR_BAR,
    CHART_TYPES,
    FINISH_AMBER_HIGHLIGHT,
    FINISH_TEAL,
    MULTI_SERIES_TYPES,
    SINGLE_SERIES_TYPES,
    STATUS_TRIAD_ALTA,
    STATUS_TRIAD_BAIXA,
    STATUS_TRIAD_COLORS,
    STATUS_TRIAD_MEDIA,
    aderencia_distribution_payload,
    categorical_counts_payload,
    empty_series_payload,
    grouped_series_payload,
    mono_finish_colors,
    series_payload,
)

CANONICAL_SHAPE_KEYS = frozenset({
    'id',
    'type',
    'has_data',
    'title',
    'labels',
    'empty_message',
    'legend_items',
})


def _assert_empty_honest(payload: dict, *, chart_type: str, chart_id: str) -> None:
    """has_data falso ⇒ sem série fictícia (FR-003 / baseline § empty)."""
    assert payload['id'] == chart_id
    assert payload['type'] == chart_type
    assert payload['has_data'] is False
    assert payload['labels'] == []
    assert payload['legend_items'] == []
    assert payload['empty_message']
    # série única
    if 'values' in payload:
        assert payload['values'] == []
        assert payload['total'] == 0
    # multi-série
    if 'series' in payload:
        assert payload['series'] == []
    # campos opcionais limpos quando presentes
    for key in ('colors', 'keys'):
        if key in payload:
            assert payload[key] == []
    assert 'center_text' not in payload


# --- Catálogo de types (T006/T007) ---


def test_catalog_includes_new_types():
    assert CHART_TYPE_BAR_HORIZONTAL in CHART_TYPES
    assert CHART_TYPE_AREA in CHART_TYPES
    assert CHART_TYPE_DOUGHNUT in CHART_TYPES
    assert CHART_TYPE_BAR_HORIZONTAL in SINGLE_SERIES_TYPES
    assert CHART_TYPE_AREA in SINGLE_SERIES_TYPES
    assert CHART_TYPE_AREA in MULTI_SERIES_TYPES
    assert CHART_TYPE_BAR_GROUPED in MULTI_SERIES_TYPES


def test_status_triad_unchanged():
    """Cores semânticas de negócio — freeze (não inventar paleta de status)."""
    assert STATUS_TRIAD_ALTA == '#059669'
    assert STATUS_TRIAD_MEDIA == '#d97706'
    assert STATUS_TRIAD_BAIXA == '#e11d48'
    assert STATUS_TRIAD_COLORS == (
        '#059669',
        '#d97706',
        '#e11d48',
    )
    for key in ADERENCIA_KEYS:
        assert ADERENCIA_COLORS[key] in STATUS_TRIAD_COLORS


# --- Série única: bar_horizontal / area / doughnut ---


def test_series_payload_bar_horizontal_with_data():
    payload = series_payload(
        chart_id='chart-ranking',
        chart_type=CHART_TYPE_BAR_HORIZONTAL,
        title='Ranking',
        labels=['Pendente', 'Em curso'],
        values=[4, 2],
        empty_message='Sem dados.',
        colors=[FINISH_TEAL, FINISH_AMBER_HIGHLIGHT],
    )
    assert CANONICAL_SHAPE_KEYS <= payload.keys()
    assert payload['type'] == CHART_TYPE_BAR_HORIZONTAL
    assert payload['has_data'] is True
    assert payload['labels'] == ['Pendente', 'Em curso']
    assert payload['values'] == [4, 2]
    assert payload['total'] == 6
    assert payload['colors'] == [FINISH_TEAL, FINISH_AMBER_HIGHLIGHT]
    assert payload['legend_items'] == [
        {'label': 'Pendente', 'value': 4, 'color': FINISH_TEAL},
        {'label': 'Em curso', 'value': 2, 'color': FINISH_AMBER_HIGHLIGHT},
    ]


def test_series_payload_area_single_series():
    payload = series_payload(
        chart_id='chart-tendencia',
        chart_type=CHART_TYPE_AREA,
        title='Tendência',
        labels=['Jan', 'Fev'],
        values=[1, 3],
        empty_message='Sem tendência.',
    )
    assert payload['type'] == CHART_TYPE_AREA
    assert payload['has_data'] is True
    assert payload['values'] == [1, 3]
    assert payload['total'] == 4
    assert len(payload['legend_items']) == 2


def test_series_payload_doughnut_center_text_and_total():
    """Doughnut: ``total`` e ``center_text`` opcional (valor central no JS)."""
    payload = series_payload(
        chart_id='chart-aderencia',
        chart_type=CHART_TYPE_DOUGHNUT,
        title='Distribuição',
        labels=['Alta', 'Média', 'Baixa'],
        values=[2, 1, 0],
        empty_message='Sem aderência.',
        keys=ADERENCIA_KEYS,
        colors=[ADERENCIA_COLORS[k] for k in ADERENCIA_KEYS],
        center_text='3',
    )
    assert payload['type'] == CHART_TYPE_DOUGHNUT
    assert payload['has_data'] is True
    assert payload['total'] == 3
    assert payload['center_text'] == '3'
    assert payload['keys'] == list(ADERENCIA_KEYS)
    assert payload['colors'] == [
        STATUS_TRIAD_ALTA,
        STATUS_TRIAD_MEDIA,
        STATUS_TRIAD_BAIXA,
    ]


# --- Empty honesto (has_data falso) ---


def test_empty_series_payload_bar_horizontal():
    payload = empty_series_payload(
        chart_id='chart-escopo-status',
        chart_type=CHART_TYPE_BAR_HORIZONTAL,
        title='Status do escopo',
        empty_message='Não há dados de ciclo no seu escopo para exibir.',
    )
    _assert_empty_honest(
        payload,
        chart_type=CHART_TYPE_BAR_HORIZONTAL,
        chart_id='chart-escopo-status',
    )


def test_empty_series_payload_area():
    payload = empty_series_payload(
        chart_id='chart-area',
        chart_type=CHART_TYPE_AREA,
        title='Área',
        empty_message='Sem série temporal.',
    )
    _assert_empty_honest(
        payload,
        chart_type=CHART_TYPE_AREA,
        chart_id='chart-area',
    )


def test_empty_series_payload_doughnut():
    payload = empty_series_payload(
        chart_id='chart-aderencia-distribuicao',
        chart_type=CHART_TYPE_DOUGHNUT,
        title='Distribuição de aderência',
        empty_message='Não há ciclo disponível.',
    )
    _assert_empty_honest(
        payload,
        chart_type=CHART_TYPE_DOUGHNUT,
        chart_id='chart-aderencia-distribuicao',
    )


def test_series_payload_zero_values_is_empty_honest():
    """Soma 0 ⇒ has_data falso e labels/values limpos (sem barras zeradas)."""
    payload = series_payload(
        chart_id='chart-zeros',
        chart_type=CHART_TYPE_BAR,
        title='Zeros',
        labels=['A', 'B'],
        values=[0, 0],
        empty_message='Sem dados.',
        colors=[FINISH_TEAL, FINISH_TEAL],
    )
    _assert_empty_honest(
        payload,
        chart_type=CHART_TYPE_BAR,
        chart_id='chart-zeros',
    )


def test_grouped_series_payload_empty():
    payload = grouped_series_payload(
        chart_id='chart-gaps',
        title='Gaps',
        labels=['Comp A'],
        series=[
            {'key': 'nivel_esperado', 'label': 'Esperado', 'values': [3]},
            {'key': 'nota_atual', 'label': 'Nota', 'values': [2]},
        ],
        empty_message='Sem gaps.',
        has_data=False,
    )
    _assert_empty_honest(
        payload,
        chart_type=CHART_TYPE_BAR_GROUPED,
        chart_id='chart-gaps',
    )


def test_grouped_series_payload_area_multi():
    """``area`` multi-série reusa grouped shape (catálogo / MULTI_SERIES)."""
    payload = grouped_series_payload(
        chart_id='chart-trend-multi',
        title='Tendência',
        labels=['Jan', 'Fev'],
        series=[
            {'key': 'a', 'label': 'Série A', 'values': [1, 2]},
            {'key': 'b', 'label': 'Série B', 'values': [None, 4]},
        ],
        empty_message='Sem tendência.',
        chart_type=CHART_TYPE_AREA,
    )
    assert payload['type'] == CHART_TYPE_AREA
    assert payload['has_data'] is True
    assert payload['series'][1]['values'] == [None, 4]
    assert payload['legend_items'][0]['parts'][0]['label'] == 'Série A'


def test_grouped_preserves_null_nota():
    payload = grouped_series_payload(
        chart_id='chart-gap',
        title='Gap',
        labels=['Liderança'],
        series=[
            {'key': 'nivel_esperado', 'label': 'Esperado', 'values': [3]},
            {'key': 'nota_atual', 'label': 'Nota', 'values': [None]},
        ],
        empty_message='Sem gap.',
    )
    assert payload['has_data'] is True
    assert payload['series'][1]['values'] == [None]
    parts = payload['legend_items'][0]['parts']
    assert parts[1]['value'] is None
    assert parts[0]['color'] == '#64748b'  # FINISH_SLATE
    assert parts[1]['color'] == STATUS_TRIAD_ALTA


# --- Builders de domínio de apresentação ---


def test_aderencia_distribution_with_data_preserves_triad():
    payload = aderencia_distribution_payload(
        ['alta', 'alta', 'media', 'baixa'],
        chart_type=CHART_TYPE_DOUGHNUT,
    )
    assert payload['type'] == CHART_TYPE_DOUGHNUT
    assert payload['has_data'] is True
    assert payload['keys'] == list(ADERENCIA_KEYS)
    assert payload['labels'] == [ADERENCIA_LABELS[k] for k in ADERENCIA_KEYS]
    assert payload['values'] == [2, 1, 1]
    assert payload['total'] == 4
    assert payload['colors'] == [
        STATUS_TRIAD_ALTA,
        STATUS_TRIAD_MEDIA,
        STATUS_TRIAD_BAIXA,
    ]


def test_aderencia_distribution_empty_list():
    payload = aderencia_distribution_payload([])
    _assert_empty_honest(
        payload,
        chart_type=CHART_TYPE_DOUGHNUT_OR_BAR,
        chart_id='chart-aderencia-distribuicao',
    )


def test_categorical_counts_bar_horizontal_highlight_max():
    payload = categorical_counts_payload(
        {'a': 1, 'b': 5, 'c': 2},
        ordered_keys=['a', 'b', 'c'],
        labels_by_key={'a': 'A', 'b': 'B', 'c': 'C'},
        chart_id='chart-ciclo-progresso',
        chart_type=CHART_TYPE_BAR_HORIZONTAL,
        title='Progresso',
        empty_message='Sem progresso.',
        highlight_max=True,
    )
    assert payload['type'] == CHART_TYPE_BAR_HORIZONTAL
    assert payload['has_data'] is True
    assert payload['values'] == [1, 5, 2]
    assert payload['colors'] == [
        FINISH_TEAL,
        FINISH_AMBER_HIGHLIGHT,
        FINISH_TEAL,
    ]
    assert mono_finish_colors(3, highlight_index=1) == payload['colors']


def test_categorical_counts_highlight_max_skips_flat_tie():
    """Empate total no máximo → mono teal (sem amber fantasma)."""
    payload = categorical_counts_payload(
        {'a': 3, 'b': 3, 'c': 3},
        ordered_keys=['a', 'b', 'c'],
        labels_by_key={'a': 'A', 'b': 'B', 'c': 'C'},
        chart_id='chart-flat',
        chart_type=CHART_TYPE_BAR_HORIZONTAL,
        title='Flat',
        empty_message='Sem progresso.',
        highlight_max=True,
    )
    assert payload['colors'] == [FINISH_TEAL, FINISH_TEAL, FINISH_TEAL]


def test_coverage_bar_highlights_lowest_when_gap():
    from apps.dashboard.chart_payloads import coverage_bar_payload

    payload = coverage_bar_payload(
        [
            {'area_nome': 'A', 'total': 4, 'percentual': 50},
            {'area_nome': 'B', 'total': 2, 'percentual': 100},
        ],
        chart_id='chart-cobertura-area',
        title='Cobertura por área',
        label_key='area_nome',
        empty_message='Sem cobertura.',
    )
    assert payload['has_data'] is True
    assert payload['values'] == [50.0, 100.0]
    assert payload['colors'] == [FINISH_AMBER_HIGHLIGHT, FINISH_TEAL]


def test_coverage_bar_no_highlight_when_all_equal():
    """Todas em 100% → sem amber na primeira barra por empate."""
    from apps.dashboard.chart_payloads import coverage_bar_payload

    payload = coverage_bar_payload(
        [
            {'area_nome': 'Move Smoke', 'total': 2, 'percentual': 100},
            {'area_nome': 'Outra', 'total': 3, 'percentual': 100},
        ],
        chart_id='chart-cobertura-area',
        title='Cobertura por área',
        label_key='area_nome',
        empty_message='Sem cobertura.',
    )
    assert payload['has_data'] is True
    assert payload['values'] == [100.0, 100.0]
    assert payload['colors'] == [FINISH_TEAL, FINISH_TEAL]


def test_categorical_counts_all_zero_is_empty():
    payload = categorical_counts_payload(
        {'a': 0, 'b': 0},
        ordered_keys=['a', 'b'],
        labels_by_key={'a': 'A', 'b': 'B'},
        chart_id='chart-empty-cat',
        chart_type=CHART_TYPE_BAR_HORIZONTAL,
        title='Vazio',
        empty_message='Sem categorias.',
        highlight_max=True,
    )
    _assert_empty_honest(
        payload,
        chart_type=CHART_TYPE_BAR_HORIZONTAL,
        chart_id='chart-empty-cat',
    )
