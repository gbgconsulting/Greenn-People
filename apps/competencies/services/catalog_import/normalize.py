"""Normalização de nomes e listas pipe-separated do catálogo legado.

Contrato: `contracts/legado-domain-mapping-contract.md` §1–2.
"""

from __future__ import annotations

import re
import unicodedata

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
