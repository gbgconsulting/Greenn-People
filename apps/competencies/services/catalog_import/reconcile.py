"""Extração e reconciliação de pares cargo↔competência das duas vistas.

Vista A = lista-cargos; Vista B = lista-competencias.
Contrato: `contracts/legado-domain-mapping-contract.md` §8; research R8.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Set
from dataclasses import dataclass

from .mapping import classify_competencia
from .normalize import canonical_key
from .parse import CargoRow, CompetenciaRow
from .report import ReportEntry

PairKey = tuple[str, str]  # (cargo_key, competencia_key)

FONTE_LISTA_CARGOS = "lista-cargos"
FONTE_LISTA_COMPETENCIAS = "lista-competencias"


@dataclass(frozen=True)
class CatalogPair:
    """Par cargo↔competência com chaves canônicas e nomes de exibição."""

    cargo_key: str
    competencia_key: str
    cargo_display: str
    competencia_display: str

    @property
    def key(self) -> PairKey:
        return (self.cargo_key, self.competencia_key)


@dataclass(frozen=True)
class ReconcileResult:
    """Saída da reconciliação §8: matriz elegível + divergências para relatório."""

    matriz: tuple[CatalogPair, ...]
    divergencias: tuple[ReportEntry, ...]


def extract_pairs_vista_a(
    cargos: Iterable[CargoRow],
) -> dict[PairKey, CatalogPair]:
    """Vista A (`lista-cargos`): expande competências pipe e forma pares.

    Chaves canônicas para matching; display do cargo/competência da própria
    fonte. Duplicatas pela mesma chave mantêm a primeira ocorrência.
    """
    pairs: dict[PairKey, CatalogPair] = {}
    for row in cargos:
        cargo_display = row.nome
        cargo_k = canonical_key(cargo_display)
        if not cargo_k:
            continue
        for competencia_display in row.competencias:
            competencia_k = canonical_key(competencia_display)
            if not competencia_k:
                continue
            pair_key: PairKey = (cargo_k, competencia_k)
            if pair_key in pairs:
                continue
            pairs[pair_key] = CatalogPair(
                cargo_key=cargo_k,
                competencia_key=competencia_k,
                cargo_display=cargo_display,
                competencia_display=competencia_display,
            )
    return pairs


def extract_pairs_vista_b(
    competencias: Iterable[CompetenciaRow],
) -> dict[PairKey, CatalogPair]:
    """Vista B (`lista-competencias`): expande cargos pipe e forma pares.

    Chaves canônicas para matching; display do cargo/competência da própria
    fonte. Duplicatas pela mesma chave mantêm a primeira ocorrência.
    """
    pairs: dict[PairKey, CatalogPair] = {}
    for row in competencias:
        competencia_display = row.nome
        competencia_k = canonical_key(competencia_display)
        if not competencia_k:
            continue
        for cargo_display in row.cargos:
            cargo_k = canonical_key(cargo_display)
            if not cargo_k:
                continue
            pair_key: PairKey = (cargo_k, competencia_k)
            if pair_key in pairs:
                continue
            pairs[pair_key] = CatalogPair(
                cargo_key=cargo_k,
                competencia_key=competencia_k,
                cargo_display=cargo_display,
                competencia_display=competencia_display,
            )
    return pairs


def avaliavel_competencia_keys(
    competencias: Iterable[CompetenciaRow],
) -> frozenset[str]:
    """Chaves canônicas de competências classificadas como avaliáveis (§6/§8)."""
    keys: set[str] = set()
    for row in competencias:
        classification = classify_competencia(row.nome, row.grupo)
        if classification.kind != "avaliavel":
            continue
        key = canonical_key(row.nome)
        if key:
            keys.add(key)
    return frozenset(keys)


def filter_avaliavel_pairs(
    pairs: Mapping[PairKey, CatalogPair],
    avaliavel_keys: Set[str],
) -> dict[PairKey, CatalogPair]:
    """Retém apenas pares cuja competência é avaliável resolvível (A'/B')."""
    return {
        key: pair
        for key, pair in pairs.items()
        if pair.competencia_key in avaliavel_keys
    }


def detect_divergencias(
    pairs_a: Mapping[PairKey, CatalogPair],
    pairs_b: Mapping[PairKey, CatalogPair],
) -> list[ReportEntry]:
    """Symmetric difference A' ⊖ B' → entradas de relatório `divergencias`.

    ``motivo`` = fonte em que o par aparece exclusivamente
    (`lista-cargos` | `lista-competencias`).
    """
    keys_a = set(pairs_a)
    keys_b = set(pairs_b)
    entries: list[ReportEntry] = []

    for key in sorted(keys_a - keys_b):
        pair = pairs_a[key]
        entries.append(
            ReportEntry(
                label=pair.cargo_display,
                extra=pair.competencia_display,
                motivo=FONTE_LISTA_CARGOS,
            )
        )

    for key in sorted(keys_b - keys_a):
        pair = pairs_b[key]
        entries.append(
            ReportEntry(
                label=pair.cargo_display,
                extra=pair.competencia_display,
                motivo=FONTE_LISTA_COMPETENCIAS,
            )
        )

    return entries


def build_matriz(
    pairs_a: Mapping[PairKey, CatalogPair],
    pairs_b: Mapping[PairKey, CatalogPair],
    *,
    resolved_cargo_keys: Set[str] | None = None,
    resolved_competencia_keys: Set[str] | None = None,
) -> list[CatalogPair]:
    """União A' ∪ B' com pontas resolvidas (cargo e competência elegíveis).

    Preferência de display: vista A, depois B. Sem sets de resolução,
    todos os pares da união entram (filtragem de pontas fica a cargo do caller).
    """
    union: dict[PairKey, CatalogPair] = dict(pairs_a)
    for key, pair in pairs_b.items():
        if key not in union:
            union[key] = pair

    result: list[CatalogPair] = []
    for key in sorted(union):
        pair = union[key]
        if (
            resolved_cargo_keys is not None
            and pair.cargo_key not in resolved_cargo_keys
        ):
            continue
        if (
            resolved_competencia_keys is not None
            and pair.competencia_key not in resolved_competencia_keys
        ):
            continue
        result.append(pair)
    return result


def reconcile_matrix(
    pairs_a: Mapping[PairKey, CatalogPair],
    pairs_b: Mapping[PairKey, CatalogPair],
    *,
    avaliavel_keys: Set[str],
    resolved_cargo_keys: Set[str] | None = None,
    resolved_competencia_keys: Set[str] | None = None,
) -> ReconcileResult:
    """Reconcilia vistas A/B conforme §8: filtra A'/B', divergências e matriz.

    1. ``pares_A', pares_B'`` = filter competência avaliável.
    2. ``divergencias`` = symmetric difference (sempre no relatório).
    3. ``matriz`` = união onde cargo e competência estão resolvidos.
    """
    a_prime = filter_avaliavel_pairs(pairs_a, avaliavel_keys)
    b_prime = filter_avaliavel_pairs(pairs_b, avaliavel_keys)
    divergencias = detect_divergencias(a_prime, b_prime)
    matriz = build_matriz(
        a_prime,
        b_prime,
        resolved_cargo_keys=resolved_cargo_keys,
        resolved_competencia_keys=resolved_competencia_keys,
    )
    return ReconcileResult(
        matriz=tuple(matriz),
        divergencias=tuple(divergencias),
    )
