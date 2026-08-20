"""API pública do backfill de ``data_entrada`` a partir do backup Sólides.

Reexporta a superfície usada pelo management command e por testes.
"""

from __future__ import annotations

from apps.accounts.services.admission_backfill.importer import (
    AdmissionBackfillReport,
    backfill_data_entrada,
)
from apps.accounts.services.admission_backfill.resolve import (
    match_user_for_admission,
    parse_data_admissao,
)

__all__ = [
    "AdmissionBackfillReport",
    "backfill_data_entrada",
    "match_user_for_admission",
    "parse_data_admissao",
]
