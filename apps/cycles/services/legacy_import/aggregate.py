"""Agregação 1:1 de cabeçalhos Sólides → grupo canônico por (ciclo, usuário).

Conforme ``contracts/aggregation-contract.md`` e research R8:

- ``group_key = (solicitacao_id, avaliado_id)``
- linha canônica = autoavaliação (``canonical_key``) se existir; senão ``min_id``
- ``collapsed_ids`` = todos − canônico (handoff 6.5.5)

Puro / sem ORM — resolução FK e upsert ficam em ``resolve`` / ``importer``.
Denylist intacta.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from apps.accounts.services.legacy_import.parse_xlsx import AvaliacaoHeaderRow
from apps.competencies.services.catalog_import.normalize import canonical_key


@dataclass(frozen=True)
class AggregatedAvaliacaoGroup:
    """Um grupo colapsado → no máximo uma ``Avaliacao`` futura.

    ``nome_avaliado`` é qualquer nome não-vazio do grupo (fallback de
    resolução de usuário na US2). ``rows`` preserva a ordem de aparição.
    """

    solicitacao_id: str
    avaliado_id: str
    canonical_id: str
    collapsed_ids: tuple[str, ...]
    rows: tuple[AvaliacaoHeaderRow, ...]
    nome_avaliado: str = ""

    @property
    def group_key(self) -> tuple[str, str]:
        return (self.solicitacao_id, self.avaliado_id)

    @property
    def n_linhas(self) -> int:
        return len(self.rows)


def min_id(ids: Iterable[str]) -> str:
    """Menor identificador com ordem total estável (aggregation-contract).

    Se todos parseiam como ``int``, compara numericamente e devolve ``str``.
    Caso contrário, mínimo lexicográfico Unicode.
    """
    values = [str(item) for item in ids]
    if not values:
        raise ValueError("min_id exige ao menos um identificador")
    try:
        return str(min(int(item) for item in values))
    except ValueError:
        return min(values)


def is_autoavaliacao(row: AvaliacaoHeaderRow) -> bool:
    """True se Nome Avaliador ≈ Nome Avaliado via ``canonical_key`` (não-vazio)."""
    key_avaliado = canonical_key(row.nome_avaliado) if row.nome_avaliado else ""
    if not key_avaliado:
        return False
    key_avaliador = canonical_key(row.nome_avaliador) if row.nome_avaliador else ""
    return key_avaliador == key_avaliado


def _sorted_unique_ids(ids: Iterable[str]) -> tuple[str, ...]:
    """IDs únicos ordenados (numérico se todos int; senão lexicográfico)."""
    unique = {str(item) for item in ids}
    if not unique:
        return ()
    try:
        return tuple(str(i) for i in sorted(int(item) for item in unique))
    except ValueError:
        return tuple(sorted(unique))


def _pick_nome_avaliado(rows: Sequence[AvaliacaoHeaderRow]) -> str:
    """Primeiro ``nome_avaliado`` não-vazio do grupo (contrato: any)."""
    for row in rows:
        if row.nome_avaliado:
            return row.nome_avaliado
    return ""


def _canonical_id_for_group(rows: Sequence[AvaliacaoHeaderRow]) -> str:
    """Canônico: ``min_id`` das autoavaliações, senão ``min_id`` de todo o grupo."""
    auto_ids = [row.identificador for row in rows if is_autoavaliacao(row)]
    if auto_ids:
        return min_id(auto_ids)
    return min_id(row.identificador for row in rows)


def aggregate_avaliacao_headers(
    rows: Iterable[AvaliacaoHeaderRow],
) -> tuple[AggregatedAvaliacaoGroup, ...]:
    """Agrupa linhas por ``(solicitacao, avaliado)`` e escolhe linha canônica.

    Linhas sem ``identificador`` / ``identificador_solicitacao`` /
    ``identificador_avaliado`` são descartadas (defesa; o parser já filtra).
    Ordem dos grupos = primeira aparição do ``group_key``.
    """
    buckets: dict[tuple[str, str], list[AvaliacaoHeaderRow]] = {}
    for row in rows:
        solicitacao_id = (row.identificador_solicitacao or "").strip()
        avaliado_id = (row.identificador_avaliado or "").strip()
        identificador = (row.identificador or "").strip()
        if not solicitacao_id or not avaliado_id or not identificador:
            continue
        key = (solicitacao_id, avaliado_id)
        buckets.setdefault(key, []).append(row)

    groups: list[AggregatedAvaliacaoGroup] = []
    for (solicitacao_id, avaliado_id), group_rows in buckets.items():
        canonical = _canonical_id_for_group(group_rows)
        all_ids = {row.identificador for row in group_rows}
        collapsed = _sorted_unique_ids(all_ids - {canonical})
        groups.append(
            AggregatedAvaliacaoGroup(
                solicitacao_id=solicitacao_id,
                avaliado_id=avaliado_id,
                canonical_id=canonical,
                collapsed_ids=collapsed,
                rows=tuple(group_rows),
                nome_avaliado=_pick_nome_avaliado(group_rows),
            )
        )
    return tuple(groups)
