"""Orquestração da importação de colaboradores legado Sólides.

Superfície pública: ``import_colaboradores`` (reexportada por ``__init__``).
Pipeline completo (parse → resolve → persist → hierarquia): T018+.
"""

from __future__ import annotations

from pathlib import Path

from .report import ImportReport


def import_colaboradores(
    colaboradores_path: str | Path,
    *,
    avaliacoes_path: str | Path | None = None,
    dry_run: bool = False,
) -> ImportReport:
    """Orquestra parse → crosswalk → persistência (ou dry-run).

    Assinatura alinhada a ``contracts/import-command-contract.md``.
    Implementação: T018+ (fase A), T022 (hierarquia), T025–T027 (dry-run/exit).
    """
    raise NotImplementedError("import_colaboradores — pending T018+")
