"""API pública do serviço de importação de PDIs/ações legado Sólides.

Reexporta a superfície usada pelo management command e por testes.
Tipos de relatório vêm do pacote compartilhado em ``accounts``; o entrypoint
e erros de schema/persistência vivem em ``importer``.
``format_pdi_report`` vem de ``accounts.services.legacy_import.report``.
"""

from __future__ import annotations

from apps.accounts.services.legacy_import.parse_xlsx import LegacyParseError
from apps.accounts.services.legacy_import.report import (
    ImportReport,
    ReportEntry,
    format_pdi_report,
    mask_email,
    mask_pii,
    mask_solides_id,
)
from apps.pdi.services.legacy_import.importer import (
    LegacyPersistError,
    LegacySchemaError,
    import_pdi,
)

__all__ = [
    "ImportReport",
    "LegacyParseError",
    "LegacyPersistError",
    "LegacySchemaError",
    "ReportEntry",
    "format_pdi_report",
    "import_pdi",
    "mask_email",
    "mask_pii",
    "mask_solides_id",
]
