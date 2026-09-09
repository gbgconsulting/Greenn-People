"""Helpers de apresentação da organização (somente UI)."""

from __future__ import annotations

from typing import TypedDict

# Labels de senioridade (contrato 003 §3) — só apresentação.
CARGO_NIVEL_LABELS: dict[int, str] = {
    1: 'Estagiário',
    2: 'Júnior',
    3: 'Pleno',
    4: 'Sênior',
    5: 'Especialista',
    6: 'Principal',
}


class NivelFilterOption(TypedDict):
    value: int
    label: str


def format_cargo_nivel_label(nivel: int | None) -> str:
    """Rótulo legível de senioridade a partir de ``Cargo.nivel`` (1–6)."""
    if nivel is None:
        return '—'
    return CARGO_NIVEL_LABELS.get(nivel, str(nivel))


def get_nivel_filter_options(niveis: frozenset[int]) -> list[NivelFilterOption]:
    """Opções de filtro por nível, ordenadas numericamente."""
    if not niveis:
        return []
    return [
        {
            'value': nivel,
            'label': format_cargo_nivel_label(nivel),
        }
        for nivel in sorted(niveis)
    ]
