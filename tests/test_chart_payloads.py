"""T003 (densidade) + T006 (empty kinds) + T013 [US1] — catálogo, empty e Top-N.

T003/T006: asserts de presentation payload (`chart_payloads.py`).
T013: gap pessoal via ``PersonalDashboardView._chart_gaps_competencia``
(Top-N por |gap| com nota; resto omitido; ``null`` ≠ 0; sem
``visao=historico``).

Não altera asserts de stage/scope; sem fórmulas/AuthZ/models.
Fixtures sintéticas (12–20 categorias); MUST NOT ``data/legado-solides/raw/``.
Contratos: chart-catalog.md, chart-baseline.md, density-history-empty.md.
"""

from __future__ import annotations

import pytest

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
    CHART_TYPE_RADAR,
    CHART_TYPES,
    EMPTY_KIND_COPY,
    EMPTY_KIND_ESCOPO,
    EMPTY_KIND_OPERACIONAL,
    EMPTY_KIND_SEM_DADO,
    EMPTY_KIND_SEM_NOTA,
    EMPTY_KINDS,
    FINISH_AMBER_HIGHLIGHT,
    FINISH_TEAL,
    MULTI_SERIES_TYPES,
    SEM_AVALIACAO_KEY,
    SEM_AVALIACAO_LABEL,
    SINGLE_SERIES_TYPES,
    STATUS_TRIAD_ALTA,
    STATUS_TRIAD_BAIXA,
    STATUS_TRIAD_COLORS,
    STATUS_TRIAD_MEDIA,
    aderencia_distribution_payload,
    categorical_counts_payload,
    empty_kind_message,
    empty_kind_payload,
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
    assert CHART_TYPE_RADAR in CHART_TYPES
    assert CHART_TYPE_BAR_HORIZONTAL in SINGLE_SERIES_TYPES
    assert CHART_TYPE_AREA in SINGLE_SERIES_TYPES
    assert CHART_TYPE_AREA in MULTI_SERIES_TYPES
    assert CHART_TYPE_BAR_GROUPED in MULTI_SERIES_TYPES
    assert CHART_TYPE_RADAR in MULTI_SERIES_TYPES


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


# --- Empty kinds canônicos (T006 / density-history-empty.md §4) ---


def test_empty_kind_copy_covers_canonical_kinds():
    """Quatro kinds fechados: operacional, escopo, sem_dado, sem_nota."""
    assert EMPTY_KINDS == frozenset({
        EMPTY_KIND_OPERACIONAL,
        EMPTY_KIND_ESCOPO,
        EMPTY_KIND_SEM_DADO,
        EMPTY_KIND_SEM_NOTA,
    })
    assert set(EMPTY_KIND_COPY) == EMPTY_KINDS
    for kind, copy in EMPTY_KIND_COPY.items():
        assert empty_kind_message(kind) == copy
        assert copy.strip()
        assert '100%' not in copy
        assert 'saudável' not in copy.lower()


def test_empty_kind_operacional_points_to_selector_not_archive():
    copy = EMPTY_KIND_COPY[EMPTY_KIND_OPERACIONAL]
    lowered = copy.lower()
    assert 'ciclo aberto' in lowered
    assert 'seletor' in lowered
    assert 'encerrado' not in lowered


def test_empty_kind_sem_nota_is_not_performance_health():
    """FR-009: empty de desempenho ≠ ciclo 100% saudável."""
    copy = EMPTY_KIND_COPY[EMPTY_KIND_SEM_NOTA]
    lowered = copy.lower()
    assert 'desempenho' in lowered or 'nota' in lowered
    assert 'completo' in lowered
    assert 'saudável' not in lowered
    assert '100%' not in copy


def test_empty_kind_message_rejects_unknown_kind():
    with pytest.raises(ValueError, match='empty kind inválido'):
        empty_kind_message('fantasma')


@pytest.mark.parametrize(
    'kind',
    [
        EMPTY_KIND_OPERACIONAL,
        EMPTY_KIND_ESCOPO,
        EMPTY_KIND_SEM_DADO,
        EMPTY_KIND_SEM_NOTA,
    ],
)
def test_empty_kind_payload_is_honest(kind):
    payload = empty_kind_payload(
        kind=kind,
        chart_id='chart-empty-kind',
        chart_type=CHART_TYPE_BAR_HORIZONTAL,
        title='Empty canônico',
    )
    _assert_empty_honest(
        payload,
        chart_type=CHART_TYPE_BAR_HORIZONTAL,
        chart_id='chart-empty-kind',
    )
    assert payload['empty_message'] == EMPTY_KIND_COPY[kind]
    assert payload['labels'] == []
    assert payload['values'] == []


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


def test_coverage_bar_all_zero_percent_is_empty():
    """0% em todas as categorias → sem gráfico (não ocupa tela com barras zeradas)."""
    from apps.dashboard.chart_payloads import coverage_bar_payload

    payload = coverage_bar_payload(
        [
            {'area_nome': 'A', 'total': 4, 'com_avaliacao': 0, 'percentual': 0},
            {'area_nome': 'B', 'total': 2, 'com_avaliacao': 0, 'percentual': 0.0},
        ],
        chart_id='chart-cobertura-area',
        title='Cobertura por área',
        label_key='area_nome',
        empty_message='Sem cobertura.',
    )
    _assert_empty_honest(
        payload,
        chart_type=CHART_TYPE_BAR_HORIZONTAL,
        chart_id='chart-cobertura-area',
    )
    assert payload['labels'] == []
    assert payload['values'] == []


def test_coverage_bar_keeps_zero_when_mixed_with_progress():
    """Mistura 0% + cobertura real → gráfico permanece (0% é o gargalo)."""
    from apps.dashboard.chart_payloads import coverage_bar_payload

    payload = coverage_bar_payload(
        [
            {'area_nome': 'A', 'total': 4, 'com_avaliacao': 0, 'percentual': 0},
            {'area_nome': 'B', 'total': 2, 'com_avaliacao': 1, 'percentual': 50},
        ],
        chart_id='chart-cobertura-area',
        title='Cobertura por área',
        label_key='area_nome',
        empty_message='Sem cobertura.',
    )
    assert payload['has_data'] is True
    assert 0 in payload['values']
    assert 50 in payload['values'] or 50.0 in payload['values']


def _coverage_rows_over_n() -> list[dict]:
    """15 áreas: Top-8 por volume (todas 50%) + 7 residuais (isca de média)."""
    top_rows = [
        {
            'area_nome': f'Area-{i}',
            'com_avaliacao': total // 2,
            'total': total,
            'percentual': 50.0,
        }
        for i, total in enumerate((100, 90, 80, 70, 60, 50, 40, 30), start=1)
    ]
    residual_rows = [
        {'area_nome': 'R-100a', 'com_avaliacao': 20, 'total': 20, 'percentual': 100.0},
        {'area_nome': 'R-100b', 'com_avaliacao': 10, 'total': 10, 'percentual': 100.0},
        {'area_nome': 'R-100c', 'com_avaliacao': 5, 'total': 5, 'percentual': 100.0},
        {'area_nome': 'R-0a', 'com_avaliacao': 0, 'total': 4, 'percentual': 0.0},
        {'area_nome': 'R-0b', 'com_avaliacao': 0, 'total': 3, 'percentual': 0.0},
        {'area_nome': 'R-0c', 'com_avaliacao': 0, 'total': 2, 'percentual': 0.0},
        {'area_nome': 'R-0d', 'com_avaliacao': 0, 'total': 1, 'percentual': 0.0},
    ]
    rows = top_rows + residual_rows
    assert 12 <= len(rows) <= 20
    return rows


def test_coverage_bar_payload_applies_top_n_weighted_others():
    """T005: eixo > N → labels Top-8 + Outros; % residual ponderada, não média."""
    from apps.dashboard.chart_payloads import (
        DENSITY_TOP_N,
        OTHERS_LABEL,
        coverage_bar_payload,
    )

    payload = coverage_bar_payload(
        _coverage_rows_over_n(),
        chart_id='chart-cobertura-area',
        title='Cobertura por área',
        label_key='area_nome',
        empty_message='Sem cobertura.',
    )

    assert payload['has_data'] is True
    assert len(payload['labels']) == DENSITY_TOP_N + 1
    assert payload['labels'][-1] == OTHERS_LABEL
    assert OTHERS_LABEL not in payload['labels'][:-1]
    assert set(payload['labels'][:-1]) == {f'Area-{i}' for i in range(1, 9)}

    # 35/45 → 77.777… → 78 (inteiro half-up no chart).
    weighted_int = 78
    mean_of_pct = (100.0 + 100.0 + 100.0 + 0.0 + 0.0 + 0.0 + 0.0) / 7
    others_pct = payload['values'][-1]
    assert others_pct == weighted_int
    assert isinstance(others_pct, int)
    assert payload.get('value_unit') == '%'
    assert others_pct != pytest.approx(mean_of_pct)
    assert all(isinstance(v, int) for v in payload['values'])
    assert len(payload['values']) == len(payload['labels'])
    assert len(payload['values']) <= DENSITY_TOP_N + 1


def test_coverage_bar_orders_by_percent_asc_others_last():
    """Exceção primeiro (% ASC); barra Outros fora da ordenação, fixa no final."""
    from apps.dashboard.chart_payloads import (
        DENSITY_TOP_N,
        OTHERS_LABEL,
        coverage_bar_payload,
    )

    # Top-N por volume (totais altos e distintos); % propositalmente fora de ordem.
    top_rows = [
        {'area_nome': 'Alta', 'com_avaliacao': 90, 'total': 100, 'percentual': 90.0},
        {'area_nome': 'Baixa', 'com_avaliacao': 8, 'total': 80, 'percentual': 10.0},
        {'area_nome': 'Media', 'com_avaliacao': 30, 'total': 60, 'percentual': 50.0},
        {'area_nome': 'Quarenta', 'com_avaliacao': 20, 'total': 50, 'percentual': 40.0},
        {'area_nome': 'Trinta', 'com_avaliacao': 12, 'total': 40, 'percentual': 30.0},
        {'area_nome': 'Vinte', 'com_avaliacao': 6, 'total': 30, 'percentual': 20.0},
        {'area_nome': 'Setenta', 'com_avaliacao': 14, 'total': 20, 'percentual': 70.0},
        {'area_nome': 'Sessenta', 'com_avaliacao': 6, 'total': 10, 'percentual': 60.0},
    ]
    assert len(top_rows) == DENSITY_TOP_N
    residual_rows = [
        {'area_nome': f'Residual-{i}', 'com_avaliacao': 1, 'total': 1, 'percentual': 100.0}
        for i in range(5)
    ]

    payload = coverage_bar_payload(
        top_rows + residual_rows,
        chart_id='chart-cobertura-area',
        title='Cobertura por área',
        label_key='area_nome',
        empty_message='Sem cobertura.',
    )

    assert payload['has_data'] is True
    assert payload['labels'][-1] == OTHERS_LABEL
    real_labels = payload['labels'][:-1]
    real_values = payload['values'][:-1]
    assert real_labels == [
        'Baixa',
        'Vinte',
        'Trinta',
        'Quarenta',
        'Media',
        'Sessenta',
        'Setenta',
        'Alta',
    ]
    assert real_values == [10, 20, 30, 40, 50, 60, 70, 90]
    assert real_values == sorted(real_values)
    assert OTHERS_LABEL not in real_labels


def test_coverage_bar_payload_passthrough_at_most_n_has_no_others():
    """T005: ≤ N categorias — sem rótulo Outros no payload emitido."""
    from apps.dashboard.chart_payloads import (
        DENSITY_TOP_N,
        OTHERS_LABEL,
        coverage_bar_payload,
    )

    rows = [
        {
            'area_nome': f'Area-{i}',
            'com_avaliacao': i,
            'total': 10,
            'percentual': i * 10.0,
        }
        for i in range(1, DENSITY_TOP_N + 1)
    ]
    payload = coverage_bar_payload(
        rows,
        chart_id='chart-cobertura-area',
        title='Cobertura por área',
        label_key='area_nome',
        empty_message='Sem cobertura.',
    )
    assert payload['has_data'] is True
    assert OTHERS_LABEL not in payload['labels']
    assert len(payload['labels']) == DENSITY_TOP_N


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


# --- T003: teto de densidade Top-N + "Outros" (`top_n_with_others`) ---
#
# Contrato do helper (T004 implementa; estes testes MUST falhar até lá):
#   top_n_with_others(items, *, n=DENSITY_TOP_N, strategy="sum"|"coverage"|"gap",
#                     label_key="label", value_key="value")
#   → lista nova; N default 8; residual "Outros"; não muta a entrada.
# Fixtures: 12–20 categorias sintéticas. Etapas / Status Triad não passam no corte.


def _density_api():
    """Importa a API de densidade — falha até T004 exportar os símbolos."""
    from apps.dashboard.chart_payloads import (
        DENSITY_TOP_N,
        OTHERS_LABEL,
        top_n_with_others,
    )
    return DENSITY_TOP_N, OTHERS_LABEL, top_n_with_others


def _count_items(n: int = 15) -> list[dict]:
    """N categorias com valores únicos N..1 (Top-N por volume é inequívoco)."""
    return [
        {'label': f'Cat-{i}', 'value': n - i + 1}
        for i in range(1, n + 1)
    ]


def test_density_constants_are_canonical():
    density_n, others_label, _ = _density_api()
    assert density_n == 8
    assert others_label == 'Outros'


def test_top_n_counts_residual_is_sum_not_drop():
    """(a) Contagens: Top-N + residual soma em ``Outros``; total conservado."""
    density_n, others_label, top_n_with_others = _density_api()
    items = list(reversed(_count_items(15)))
    original = [dict(row) for row in items]

    result = top_n_with_others(items, strategy='sum')

    assert items == original
    labels = [row['label'] for row in result]
    assert density_n == 8
    assert len(result) == density_n + 1
    assert labels[-1] == others_label
    assert others_label not in labels[:-1]
    assert set(labels[:-1]) == {f'Cat-{i}' for i in range(1, 9)}

    kept_sum = sum(row['value'] for row in result[:-1])
    others_value = result[-1]['value']
    residual_sum = sum(range(1, 15 - density_n + 1))  # 7+6+…+1 = 28
    assert others_value == residual_sum
    assert kept_sum + others_value == sum(row['value'] for row in items)


def test_top_n_passthrough_when_at_most_n_has_no_others():
    density_n, others_label, top_n_with_others = _density_api()
    items = _count_items(density_n)

    result = top_n_with_others(items, strategy='sum')

    labels = [row['label'] for row in result]
    assert others_label not in labels
    assert len(result) == density_n
    assert {row['value'] for row in result} == {row['value'] for row in items}


def test_top_n_coverage_residual_is_weighted_not_mean_of_percentuais():
    """(b) Cobertura: residual = sum(com)/sum(total), **não** média dos %.

    Ranking por ``total`` (volume). ``percentual`` pré-calculado do residual
    é isca — o helper MUST recompor a % pelos counts, nunca média de %.
    """
    density_n, others_label, top_n_with_others = _density_api()
    # 8 áreas de maior volume (total 100..30, todas a 50%) + 7 residuais.
    top_rows = [
        {
            'area_nome': f'Area-{i}',
            'com_avaliacao': total // 2,
            'total': total,
            'percentual': 50.0,
        }
        for i, total in enumerate((100, 90, 80, 70, 60, 50, 40, 30), start=1)
    ]
    # Residual: % médios ≈ 42.86; ponderado = 35/45 → 78 inteiro.
    residual_rows = [
        {'area_nome': 'R-100a', 'com_avaliacao': 20, 'total': 20, 'percentual': 100.0},
        {'area_nome': 'R-100b', 'com_avaliacao': 10, 'total': 10, 'percentual': 100.0},
        {'area_nome': 'R-100c', 'com_avaliacao': 5, 'total': 5, 'percentual': 100.0},
        {'area_nome': 'R-0a', 'com_avaliacao': 0, 'total': 4, 'percentual': 0.0},
        {'area_nome': 'R-0b', 'com_avaliacao': 0, 'total': 3, 'percentual': 0.0},
        {'area_nome': 'R-0c', 'com_avaliacao': 0, 'total': 2, 'percentual': 0.0},
        {'area_nome': 'R-0d', 'com_avaliacao': 0, 'total': 1, 'percentual': 0.0},
    ]
    rows = top_rows + residual_rows
    assert 12 <= len(rows) <= 20

    result = top_n_with_others(
        rows,
        strategy='coverage',
        label_key='area_nome',
    )

    labels = [
        row['area_nome'] if 'area_nome' in row else row['label']
        for row in result
    ]
    assert len(result) == density_n + 1
    others = result[-1]
    others_label_value = others.get('area_nome') or others.get('label')
    assert others_label_value == others_label

    com_residual = 20 + 10 + 5
    total_residual = 20 + 10 + 5 + 4 + 3 + 2 + 1
    # 35/45 → 78 (inteiro half-up no residual de cobertura).
    weighted_int = 78
    mean_of_pct = (100.0 + 100.0 + 100.0 + 0.0 + 0.0 + 0.0 + 0.0) / 7
    others_pct = others['percentual']
    assert others_pct == weighted_int
    assert isinstance(others_pct, int)
    assert others_pct != pytest.approx(mean_of_pct)
    assert int(others['com_avaliacao']) == com_residual
    assert int(others['total']) == total_residual
    named = set(labels[:-1])
    assert named == {f'Area-{i}' for i in range(1, 9)}
    assert named.isdisjoint({row['area_nome'] for row in residual_rows})


def test_top_n_gap_keeps_largest_abs_gap_with_nota_omits_rest():
    """(c) Gap |gap|: Top-N com nota; resto omitido (sem média) — usado por radar pessoal."""
    density_n, others_label, top_n_with_others = _density_api()
    # 12 competências com nota (|gap| 12..1) + 3 sem nota (null ≠ 0).
    with_nota = [
        {
            'label': f'Comp-{gap}',
            'nivel_esperado': 5,
            'nota_atual': 5 - gap,
        }
        for gap in range(12, 0, -1)
    ]
    without_nota = [
        {
            'label': f'SemNota-{i}',
            'nivel_esperado': 4,
            'nota_atual': None,
        }
        for i in range(3)
    ]
    items = without_nota + list(reversed(with_nota))
    assert 12 <= len(items) <= 20

    result = top_n_with_others(items, strategy='gap')

    labels = [row['label'] for row in result]
    assert others_label not in labels
    assert len(result) == density_n
    # Maiores |gap|: Comp-12 .. Comp-5 (12,11,…,5).
    assert labels == [f'Comp-{g}' for g in range(12, 12 - density_n, -1)]
    for row in result:
        assert row['nota_atual'] is not None
        gap = abs(row['nivel_esperado'] - row['nota_atual'])
        assert gap >= 5
    omitted_with_nota = {f'Comp-{g}' for g in range(1, 5)}
    assert omitted_with_nota.isdisjoint(set(labels))
    assert {row['label'] for row in without_nota}.isdisjoint(set(labels))


def test_top_n_gap_does_not_treat_null_nota_as_zero():
    """null ≠ 0: competência sem nota não entra no ranking como gap inventado."""
    _, others_label, top_n_with_others = _density_api()
    items = [
        {'label': 'Com nota', 'nivel_esperado': 3, 'nota_atual': 3},  # |gap|=0
        {'label': 'Sem nota', 'nivel_esperado': 5, 'nota_atual': None},
    ]

    result = top_n_with_others(items, strategy='gap')

    labels = [row['label'] for row in result]
    assert labels == ['Com nota']
    assert others_label not in labels
    assert result[0]['nota_atual'] == 3


def test_pipeline_etapas_closed_set_not_cut_by_top_n():
    """(d) Pipeline de etapas (+ sem avaliação) é conjunto fechado — sem Top-N."""
    _, others_label, _ = _density_api()
    etapa_keys = [
        'input_metas',
        'aprovacao_metas',
        'resultados',
        'aprovacao_resultados',
        'avaliacao',
        'feedback',
        SEM_AVALIACAO_KEY,
    ]
    labels_by_key = {
        'input_metas': 'Metas',
        'aprovacao_metas': 'Aprovação de metas',
        'resultados': 'Resultados',
        'aprovacao_resultados': 'Aprovação de resultados',
        'avaliacao': 'Avaliação',
        'feedback': 'Feedback',
        SEM_AVALIACAO_KEY: SEM_AVALIACAO_LABEL,
    }
    key_counts = {key: index + 1 for index, key in enumerate(etapa_keys)}
    payload = categorical_counts_payload(
        key_counts,
        ordered_keys=etapa_keys,
        labels_by_key=labels_by_key,
        chart_id='chart-ciclo-progresso',
        chart_type=CHART_TYPE_BAR_HORIZONTAL,
        title='Progresso',
        empty_message='Sem progresso.',
    )
    assert payload['has_data'] is True
    assert payload['labels'] == [labels_by_key[key] for key in etapa_keys]
    assert len(payload['labels']) == 7
    assert others_label not in payload['labels']
    assert payload['values'] == [index + 1 for index in range(7)]


def test_categorical_counts_does_not_apply_density_cut():
    """(d) Builder de etapas não aplica o corte mesmo com eixo sintético > N."""
    density_n, others_label, _ = _density_api()
    ordered_keys = [f'etapa_{i}' for i in range(15)]
    labels_by_key = {key: key.replace('_', ' ').title() for key in ordered_keys}
    key_counts = {key: i + 1 for i, key in enumerate(ordered_keys)}
    payload = categorical_counts_payload(
        key_counts,
        ordered_keys=ordered_keys,
        labels_by_key=labels_by_key,
        chart_id='chart-etapas-sinteticas',
        chart_type=CHART_TYPE_BAR_HORIZONTAL,
        title='Etapas',
        empty_message='Sem etapas.',
    )
    assert len(payload['labels']) == 15
    assert len(payload['labels']) > density_n
    assert others_label not in payload['labels']


def test_status_triad_doughnut_does_not_apply_density_cut():
    """(d) Status Triad (3 fatias) nunca passa pelo corte Top-N + Outros."""
    _, others_label, _ = _density_api()
    payload = aderencia_distribution_payload(
        ['alta'] * 8 + ['media'] * 5 + ['baixa'] * 4,
        chart_type=CHART_TYPE_DOUGHNUT,
    )
    assert payload['has_data'] is True
    assert payload['keys'] == list(ADERENCIA_KEYS)
    assert payload['labels'] == [ADERENCIA_LABELS[key] for key in ADERENCIA_KEYS]
    assert payload['values'] == [8, 5, 4]
    assert len(payload['labels']) == 3
    assert others_label not in payload['labels']


# --- T013 [US1]: gap pessoal Top-N + sem ``visao=historico`` ---------------


def _series_values(payload: dict, key: str) -> list:
    for serie in payload.get('series') or []:
        if serie.get('key') == key:
            return list(serie.get('values') or [])
    return []


def _personal_gap_resumo(
    *,
    n_com_nota: int = 12,
    n_sem_nota: int = 3,
    esperado: float = 12.0,
) -> list[dict]:
    """12–20 competências sintéticas; inserção deliberadamente fora da ordem |gap|."""
    from types import SimpleNamespace

    without_nota = [
        {
            'competencia': SimpleNamespace(nome=f'SemNota-{i}'),
            'nivel_esperado': esperado,
            'nota_atual': None,
        }
        for i in range(n_sem_nota)
    ]
    # |gap| = n_com_nota .. 1; nomes Comp-12 .. Comp-01. Ordem de inserção: menor gap primeiro.
    with_nota = [
        {
            'competencia': SimpleNamespace(nome=f'Comp-{gap:02d}'),
            'nivel_esperado': esperado,
            'nota_atual': esperado - gap,
        }
        for gap in range(1, n_com_nota + 1)
    ]
    items = without_nota + with_nota
    assert 12 <= len(items) <= 20
    return items


def _personal_gap_chart(resumo: list[dict]) -> dict:
    from apps.dashboard.views import PersonalDashboardView

    return PersonalDashboardView()._chart_gaps_competencia({
        'vinculo_pendente': False,
        'competencias_resumo': resumo,
    })


def test_personal_gap_top_n_by_abs_gap_omits_rest():
    """T013: Top-N por |gap| entre competências **com nota**; resto omitido.

    Sem rótulo ``Outros`` (estratégia gap). N = ``DENSITY_TOP_N`` (8).
    """
    density_n, others_label, _ = _density_api()
    payload = _personal_gap_chart(_personal_gap_resumo())

    assert payload['has_data'] is True
    assert payload['type'] == CHART_TYPE_RADAR
    labels = list(payload['labels'])
    assert others_label not in labels
    assert len(labels) == density_n
    assert labels == [f'Comp-{gap:02d}' for gap in range(12, 12 - density_n, -1)]
    assert {f'SemNota-{i}' for i in range(3)}.isdisjoint(set(labels))
    omitted = {f'Comp-{gap:02d}' for gap in range(1, 5)}
    assert omitted.isdisjoint(set(labels))

    notas = _series_values(payload, 'nota_atual')
    assert len(notas) == density_n
    assert None not in notas
    esperados = _series_values(payload, 'nivel_esperado')
    gaps = [abs(esp - nota) for esp, nota in zip(esperados, notas)]
    assert gaps == sorted(gaps, reverse=True)
    assert min(gaps) >= 5


def test_personal_gap_null_nota_is_not_zero():
    """T013: ``null`` ≠ 0 — competência sem nota não entra como gap inventado."""
    from types import SimpleNamespace

    _, others_label, _ = _density_api()
    resumo = [
        {
            'competencia': SimpleNamespace(nome='Com nota'),
            'nivel_esperado': 3,
            'nota_atual': 3,
        },
        {
            'competencia': SimpleNamespace(nome='Sem nota'),
            'nivel_esperado': 12,
            'nota_atual': None,
        },
    ]
    payload = _personal_gap_chart(resumo)

    assert payload['has_data'] is True
    labels = list(payload['labels'])
    assert labels == ['Com nota']
    assert others_label not in labels
    assert _series_values(payload, 'nota_atual') == [3]
    assert None not in _series_values(payload, 'nota_atual')
    assert 0 not in _series_values(payload, 'nota_atual')


@pytest.mark.django_db
def test_personal_dashboard_does_not_honor_visao_historico(
    colaborador,
    ciclo_aberto,
):
    """T013 / FR-016: pessoal MUST NOT ganhar série ``visao=historico``."""
    from django.test import Client
    from django.urls import reverse

    from apps.cycles.models import Ciclo

    assert ciclo_aberto.status == Ciclo.Status.ABERTO
    client = Client()
    client.force_login(colaborador)
    url = reverse('dashboard:personal')

    resp_hist = client.get(url, {'visao': 'historico', 'ciclos': '1,2,3'})
    assert resp_hist.status_code == 200
    chart = resp_hist.context['chart_gaps_competencia']
    assert chart['type'] == CHART_TYPE_RADAR
    assert chart['type'] != CHART_TYPE_AREA

    html = resp_hist.content.decode()
    assert 'visao=historico' not in html
    assert '/historico/' not in html
    assert 'data-chart-payload="chart-stage-history"' not in html
    assert resp_hist.context.get('chart_stage_history') is None
    assert resp_hist.context.get('visao') != 'historico'
