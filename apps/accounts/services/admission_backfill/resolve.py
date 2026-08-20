"""Match de pessoa + parse de “Data admissão” (backfill ``data_entrada``).

Contrato: ``contracts/admission-backfill-command-contract.md``.
Chave natural alinhada à 010: e-mail ``iexact`` → ``solides_id`` /
``canonicalize_id``. Sem match / ambíguo → não inventa ``User``.
"""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from apps.accounts.models import CustomUser

MatchOutcome = Literal["matched", "orphan", "conflict"]


def parse_data_admissao(raw: object) -> date | None:
    """Parse célula “Data admissão” (serial Excel + ISO via ``parse_legacy_date``).

    Retorna ``None`` se vazio ou ilegível.
    """
    raise NotImplementedError


def match_user_for_admission(
    *,
    email: str | None,
    solides_id: str | None,
) -> tuple[CustomUser | None, MatchOutcome]:
    """Resolve ``CustomUser`` por e-mail empresarial/``email__iexact``, depois id.

    - Match único → ``(user, "matched")``.
    - Sem match → ``(None, "orphan")`` — órfão no relatório; NÃO cria User.
    - Ambíguo → ``(None, "conflict")`` — conflito no relatório; NÃO grava.
    """
    raise NotImplementedError
