"""Resolução de avaliação canônica, competência, autor e ciclo aberto.

US1 (T007) — mapa em memória via ``parse_avaliacoes_headers_xlsx`` +
IMPORTAR ``aggregate_avaliacao_headers`` (não copiar);
``resolve_avaliacao`` na ordem canônico → mapa → órfão
(``contracts/collapsed-id-resolution.md``); skip se ciclo ``aberto`` (R10);
``is_auto`` via ``canonical_key`` (R5); ``resolve_competencia`` por
``Competencia.solides_id`` e create mínima (R11). **NUNCA**
``get_or_create(ciclo=..., usuario=...)``. **NUNCA** inventar
``Avaliacao`` / ``Ciclo`` / ``User``.

US2 (T012) — ``resolve_autor``: ``CustomUser.solides_id``; fallback match
único ``canonical_key(Nome Avaliador)``; inativo permitido; senão órfão.

T002: stubs — corpos em T007 / T012.

Denylist intacta — **não** chama ``open_cycle`` / ``close_cycle`` /
``advance_stage`` / approval / ``create_competency_lines``; **não** importa
``get_open_ciclo`` de ``goals``.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any


def build_collapsed_id_map(avaliacoes_path: str | Path) -> dict[str, str]:
    """Rebuild ``legado_id → canonical_id`` em memória (R3 / T007).

    Consome ``parse_avaliacoes_headers_xlsx`` + ``aggregate_avaliacao_headers``.
    **PROIBIDO** persistir tabela de mapa; **PROIBIDO** copiar ``aggregate.py``.
    """
    raise NotImplementedError("T002 stub — implementar em T007")


def resolve_avaliacao(
    identificador: str,
    mapa: Mapping[str, str],
) -> Any:
    """Resolve ``Avaliacao`` canônica: solides_id → mapa colapsado → órfão.

    Ordem (collapsed-id-resolution): lookup direto; senão ``mapa``; senão
    ``None`` (órfão). **NUNCA** inventar cabeçalho.
    """
    raise NotImplementedError("T002 stub — implementar em T007")


def is_ciclo_aberto(avaliacao: Any) -> bool:
    """True se ``avaliacao.ciclo.status == aberto`` (R10).

    Skip da linha; **não** importar ``get_open_ciclo``.
    """
    raise NotImplementedError("T002 stub — implementar em T007")


def is_auto(nome_avaliador: str, nome_avaliado: str) -> bool:
    """True se nomes canônicos coincidem e ambos não-vazios (R5).

    Reusa ``canonical_key`` da 003 — **não copiar**.
    """
    raise NotImplementedError("T002 stub — implementar em T007")


def resolve_competencia(
    habilidade_id: str,
    habilidade_nome: str = "",
    *,
    grupo: str = "",
) -> Any:
    """Resolve ``Competencia`` por ``solides_id``; create mínima (R11) se ok.

    Extras: ``display_name``, ``not is_kpi``, ``not is_ambiguous``,
    ``resolve_default_escala``, tipo ``map_grupo_tipo`` se houver
    ``--habilidades`` senão ``tecnica``. Zero ``CargoCompetencia``.
    """
    raise NotImplementedError("T002 stub — implementar em T007")


def resolve_autor(avaliador_id: str, nome_avaliador: str = "") -> Any:
    """Resolve autor do comentário: ``solides_id`` → nome canônico único.

    Inativo (010) permitido. Irresolvível → ``None`` (órfão). **Nunca**
    inventar ``User``. Corpo em T012.
    """
    raise NotImplementedError("T002 stub — implementar em T012")
