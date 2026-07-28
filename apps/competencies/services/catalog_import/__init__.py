"""API pública do serviço de importação do catálogo legado.

Reexporta a superfície usada pelo management command e por testes.
"""

from __future__ import annotations

from apps.competencies.services.catalog_import.importer import (
    EscalaInativaError,
    import_catalog,
)
from apps.competencies.services.catalog_import.parse import CatalogParseError
from apps.competencies.services.catalog_import.report import (
    ImportReport,
    ReportEntry,
    format_report,
)

__all__ = [
    "CatalogParseError",
    "EscalaInativaError",
    "ImportReport",
    "ReportEntry",
    "format_report",
    "import_catalog",
]
