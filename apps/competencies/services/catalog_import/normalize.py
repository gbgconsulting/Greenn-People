"""Normalização de nomes e listas pipe-separated do catálogo legado.

Contrato: `contracts/legado-domain-mapping-contract.md` §1–2.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

_WHITESPACE_RE = re.compile(r"\s+")


def display_name(s: str) -> str:
    """Forma de exibição: strip + colapso de whitespace interno."""
    return _WHITESPACE_RE.sub(" ", s.strip())


def _strip_accents(s: str) -> str:
    """NFKD + remoção de combining marks (acentos)."""
    nfkd = unicodedata.normalize("NFKD", s)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def canonical_key(s: str) -> str:
    """Chave canônica para matching/idempotência (sem acentos, casefold)."""
    return _strip_accents(display_name(s)).casefold()


def split_pipe(s: str) -> list[str]:
    """Expande célula pipe-separated em nomes display não vazios."""
    return [name for part in s.split("|") if (name := display_name(part))]


@dataclass(frozen=True)
class MergePair:
    """Duas grafias distintas com a mesma chave canônica (§1 — reportar merged)."""

    nome_a: str
    nome_b: str
    chave: str


@dataclass(frozen=True)
class ObserveResult:
    """Resultado de observar um nome no índice canônico."""

    display: str
    key: str
    is_first: bool
    merge: MergePair | None = None


class CanonicalNameIndex:
    """Primeira grafia por chave canônica; detecta merges de grafias distintas.

    Contrato §1: dois nomes com a mesma chave → um registro; reportar ``merged``
    quando as formas de display diferem. Duplicata idêntica é só skip.
    """

    def __init__(self) -> None:
        self._first: dict[str, str] = {}

    def observe(self, name: str) -> ObserveResult | None:
        """Registra ``name`` e indica se é a primeira ocorrência da chave.

        Returns:
            ``None`` se display/chave vazios; caso contrário ``ObserveResult``
            com ``is_first`` e eventual ``MergePair`` (grafia distinta).
        """
        display = display_name(name)
        if not display:
            return None
        key = canonical_key(display)
        if not key:
            return None

        first = self._first.get(key)
        if first is None:
            self._first[key] = display
            return ObserveResult(display=display, key=key, is_first=True)

        merge: MergePair | None = None
        if first != display:
            merge = MergePair(nome_a=first, nome_b=display, chave=key)
        return ObserveResult(
            display=display,
            key=key,
            is_first=False,
            merge=merge,
        )
