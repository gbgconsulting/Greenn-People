"""Índice crosswalk Nome Avaliado → Identificador Avaliado.

Contrato: ``contracts/solides-id-crosswalk-contract.md`` (US2 / research R8).
Reuso read-only: ``canonical_key`` / ``display_name`` de catalog_import.
Denylist de domínio intacta — sem persistência; sem PII extra.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field

from apps.accounts.services.legacy_import.parse_xlsx import AvaliacaoCrosswalkRow
from apps.accounts.services.legacy_import.report import ImportReport, ReportEntry
from apps.competencies.services.catalog_import.normalize import (
    canonical_key,
    display_name,
)


@dataclass
class CrosswalkIndex:
    """Mapa canônico Nome → ``solides_id`` somente para matches únicos.

    Chaves ambíguas (IDs distintos para a mesma ``canonical_key``) ficam em
    ``conflicts`` e **não** resolvem no ``lookup`` (R8).
    """

    _by_key: dict[str, str] = field(default_factory=dict, repr=False)
    _ambiguous: set[str] = field(default_factory=set, repr=False)
    _display: dict[str, str] = field(default_factory=dict, repr=False)
    conflicts: list[ReportEntry] = field(default_factory=list)

    def lookup(self, nome: str) -> str | None:
        """Retorna Identificador Avaliado se match único; senão ``None``.

        Sem match, chave vazia ou ambiguidade prévia → ``None`` (``solides_id``
        permanece null; dedupe por e-mail).
        """
        key = canonical_key(nome) if nome else ""
        if not key or key in self._ambiguous:
            return None
        return self._by_key.get(key)

    @property
    def size(self) -> int:
        """Quantidade de chaves com ID único resolvível."""
        return len(self._by_key)

    @property
    def n_ambiguous(self) -> int:
        """Quantidade de chaves com ambiguidade (sem atribuição)."""
        return len(self._ambiguous)


def build_crosswalk(
    rows: Iterable[AvaliacaoCrosswalkRow],
    report: ImportReport | None = None,
) -> CrosswalkIndex:
    """Constrói o índice a partir das linhas de ``backup_avaliacoes`` (R8).

    Algoritmo (contrato §Crosswalk usuário):

    1. Para cada ``Nome Avaliado`` + ``Identificador Avaliado``:
       ``key = canonical_key(nome)``; ``id = str(id).strip()``.
       Skip se key/id vazios.
       Se key já mapeada com ID diferente → conflito ``crosswalk_ambiguo``
       e a key deixa de atribuir ID.
       Caso contrário → ``index[key] = id``.

    2. Lookup posterior via ``CrosswalkIndex.lookup(nome)``.

    Conflitos são anexados a ``report.conflitos`` quando ``report`` é passado
    (formato: ``tipo=crosswalk_ambiguo | nome=… | ids=a,b``).
    """
    index = CrosswalkIndex()
    for row in rows:
        _observe(index, row.nome_avaliado, row.identificador_avaliado)

    if report is not None and index.conflicts:
        report.conflitos.extend(index.conflicts)

    return index


def _observe(index: CrosswalkIndex, nome: str, identificador: str) -> None:
    """Incorpora um par nome/id no índice; detecta ambiguidade."""
    key = canonical_key(nome) if nome else ""
    sid = (identificador or "").strip()
    if not key or not sid:
        return

    display = display_name(nome) if nome else ""
    if key not in index._display and display:
        index._display[key] = display

    # Já ambígua — não atribui; não re-registra o mesmo conflito.
    if key in index._ambiguous:
        return

    existing = index._by_key.get(key)
    if existing is None:
        index._by_key[key] = sid
        return

    if existing == sid:
        # Mesmo ID repetido — idempotente, sem conflito.
        return

    # Ambiguidade: remove do índice resolvível e reporta.
    del index._by_key[key]
    index._ambiguous.add(key)
    nome_label = index._display.get(key, display or key)
    index.conflicts.append(
        ReportEntry(
            label="crosswalk_ambiguo",
            extra=f"nome={nome_label}",
            motivo=f"ids={existing},{sid}",
        )
    )
