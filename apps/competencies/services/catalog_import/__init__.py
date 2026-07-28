"""API pública do serviço de importação do catálogo legado.

Reexporta a superfície usada pelo management command e por testes.
Implementações detalhadas vivem em `importer.py` e `report.py` (fases seguintes).
"""

from __future__ import annotations

from pathlib import Path

from apps.competencies.services.catalog_import.report import (
    ImportReport,
    ReportEntry,
    format_report,
)


def import_catalog(
    cargos_path: str | Path,
    competencias_path: str | Path,
    *,
    dry_run: bool = False,
) -> ImportReport:
    """Orquestra parse → persistência do catálogo legado.

    Implementação completa nas fases Foundational / US1–US4 (`importer.py`).
    """
    raise NotImplementedError(
        "import_catalog será implementado em apps.competencies.services.catalog_import.importer"
    )


__all__ = [
    "ImportReport",
    "ReportEntry",
    "format_report",
    "import_catalog",
]
