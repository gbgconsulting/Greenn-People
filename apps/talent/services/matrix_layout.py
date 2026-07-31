"""Layout da matriz 9-box (grade 3×3) compartilhado entre full page e partials HTMX."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from typing import Any

from apps.talent.models import ClassificacaoTalento

# Ordem visual: desempenho alto no topo, potencial crescente à direita.
DESEMPENHO_ROWS = (3, 2, 1)
POTENCIAL_COLS = (1, 2, 3)
NIVEL_LABEL = {1: 'Baixo', 2: 'Médio', 3: 'Alto'}
QUADRANTE_MEMBER = {
    (3, 1): 'ALTO_BAIXO',
    (3, 2): 'ALTO_MEDIO',
    (3, 3): 'ALTO_ALTO',
    (2, 1): 'MEDIO_BAIXO',
    (2, 2): 'MEDIO_MEDIO',
    (2, 3): 'MEDIO_ALTO',
    (1, 1): 'BAIXO_BAIXO',
    (1, 2): 'BAIXO_MEDIO',
    (1, 3): 'BAIXO_ALTO',
}


def potencial_labels() -> list[str]:
    """Rótulos de coluna de potencial na ordem visual da grade."""
    return [NIVEL_LABEL[p] for p in POTENCIAL_COLS]


def build_matriz_rows(
    classificacoes: Iterable[ClassificacaoTalento],
) -> list[dict[str, Any]]:
    """Monta ``matriz_rows`` (3 linhas × 3 células) a partir das classificações.

    Cada célula contém ``desempenho``, ``potencial``, ``quadrante``, ``label``
    e ``itens`` (lista de ``ClassificacaoTalento`` naquela célula).
    """
    by_quadrante: dict[str, list[ClassificacaoTalento]] = defaultdict(list)
    for item in classificacoes:
        by_quadrante[item.quadrante].append(item)

    rows: list[dict[str, Any]] = []
    for desempenho in DESEMPENHO_ROWS:
        cells: list[dict[str, Any]] = []
        for potencial in POTENCIAL_COLS:
            member_name = QUADRANTE_MEMBER[(desempenho, potencial)]
            quadrante = ClassificacaoTalento.Quadrante[member_name]
            cells.append(
                {
                    'desempenho': desempenho,
                    'potencial': potencial,
                    'quadrante': quadrante.value,
                    'label': quadrante.label,
                    'itens': by_quadrante.get(quadrante.value, []),
                },
            )
        rows.append(
            {
                'desempenho': desempenho,
                'desempenho_label': NIVEL_LABEL[desempenho],
                'cells': cells,
            },
        )
    return rows
