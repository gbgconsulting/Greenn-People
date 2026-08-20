"""Match de pessoa + parse de “Data admissão” (backfill ``data_entrada``).

Contrato: ``contracts/admission-backfill-command-contract.md``.
Chave natural alinhada à 010: e-mail ``iexact`` → ``solides_id`` /
``canonicalize_id``. Sem match / ambíguo → não inventa ``User``.
"""

from __future__ import annotations

from datetime import date
from typing import Literal

from apps.accounts.models import CustomUser
from apps.accounts.services.legacy_import.dates import parse_legacy_date
from apps.accounts.services.legacy_import.parse_xlsx import canonicalize_id

MatchOutcome = Literal["matched", "orphan", "conflict"]


def parse_data_admissao(raw: object) -> date | None:
    """Parse célula “Data admissão” (serial Excel + ISO via ``parse_legacy_date``).

    Retorna ``None`` se vazio ou ilegível.
    """
    try:
        return parse_legacy_date(raw)
    except (TypeError, ValueError):
        return None


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
    normalized = _normalize_email(email)
    if normalized:
        by_email = list(
            CustomUser.objects.filter(email__iexact=normalized)[:2]
        )
        if len(by_email) > 1:
            return None, "conflict"
        if len(by_email) == 1:
            return by_email[0], "matched"

    sid = canonicalize_id(solides_id)
    if sid:
        by_id = list(CustomUser.objects.filter(solides_id=sid)[:2])
        if len(by_id) > 1:
            return None, "conflict"
        if len(by_id) == 1:
            return by_id[0], "matched"

    return None, "orphan"


def _normalize_email(email: str | None) -> str:
    """Normalização vigente (strip + ``CustomUserManager.normalize_email``)."""
    if email is None:
        return ""
    text = str(email).strip()
    if not text:
        return ""
    return CustomUser.objects.normalize_email(text)
