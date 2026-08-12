"""API pública do serviço de importação de colaboradores legado Sólides.

Reexporta a superfície usada pelo management command e por testes.
"""

from __future__ import annotations

from apps.accounts.services.legacy_import.importer import import_colaboradores
from apps.accounts.services.legacy_import.report import (
    ImportReport,
    ReportEntry,
    format_report,
    mask_email,
    mask_pii,
)

__all__ = [
    "ImportReport",
    "ReportEntry",
    "format_report",
    "import_colaboradores",
    "mask_email",
    "mask_pii",
]
