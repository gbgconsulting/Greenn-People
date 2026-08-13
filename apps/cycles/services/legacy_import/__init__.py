"""API pública do serviço de importação de ciclos/avaliações legado Sólides.

Reexporta a superfície usada pelo management command e por testes.
Tipos de relatório vêm do pacote compartilhado em ``accounts``; o entrypoint
e erros de schema/persistência vivem em ``importer``.
"""

from __future__ import annotations

from apps.accounts.services.legacy_import.parse_xlsx import LegacyParseError
from apps.accounts.services.legacy_import.report import (
    ImportReport,
    ReportEntry,
    format_ciclos_avaliacoes_report,
    mask_email,
    mask_pii,
)
from apps.cycles.services.legacy_import.importer import (
    LegacyPersistError,
    LegacySchemaError,
    import_ciclos_avaliacoes,
)

__all__ = [
    "ImportReport",
    "LegacyParseError",
    "LegacyPersistError",
    "LegacySchemaError",
    "ReportEntry",
    "format_ciclos_avaliacoes_report",
    "import_ciclos_avaliacoes",
    "mask_email",
    "mask_pii",
]
