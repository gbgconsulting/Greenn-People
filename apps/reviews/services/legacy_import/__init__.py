"""API pública do serviço de importação de notas/comentários legado Sólides.

Reexporta a superfície usada pelo management command e por testes.
Tipos de relatório vêm do pacote compartilhado em ``accounts``; o entrypoint
e erros de schema/persistência vivem em ``importer``.
"""

from __future__ import annotations

from apps.accounts.services.legacy_import.parse_xlsx import LegacyParseError
from apps.accounts.services.legacy_import.report import (
    ImportReport,
    ReportEntry,
    format_notas_comentarios_report,
    mask_email,
    mask_pii,
    mask_solides_id,
)
from apps.reviews.services.legacy_import.importer import (
    LegacyPersistError,
    LegacySchemaError,
    import_notas_comentarios,
)

__all__ = [
    "ImportReport",
    "LegacyParseError",
    "LegacyPersistError",
    "LegacySchemaError",
    "ReportEntry",
    "format_notas_comentarios_report",
    "import_notas_comentarios",
    "mask_email",
    "mask_pii",
    "mask_solides_id",
]
