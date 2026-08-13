"""Orquestração da importação de ciclos/avaliações legado Sólides.

Superfície pública: ``import_ciclos_avaliacoes`` (reexportada por ``__init__``).
Implementação completa nas tasks T011 (fase ciclos), T016 (cabeçalhos) e
T025/T026 (dry-run / idempotência). Este módulo existe como esqueleto da
API pública (T002) — denylist intacta (sem stage/open/close/approval).
"""

from __future__ import annotations

from pathlib import Path

from apps.accounts.services.legacy_import.report import ImportReport


class LegacySchemaError(Exception):
    """Migration ``Ciclo.solides_id`` (ou pré-reqs 010) ausente — exit 1, zero writes."""


class LegacyPersistError(Exception):
    """Erro fatal durante persistência — ``atomic`` faz rollback; exit 1."""


def import_ciclos_avaliacoes(
    solicitacoes_path: str | Path,
    avaliacoes_path: str | Path,
    *,
    dry_run: bool = False,
) -> ImportReport:
    """Orquestra parse → fases ciclos/cabeçalhos (ou dry-run).

    Assinatura alinhada a ``contracts/import-command-contract.md``.
    Implementação nas tasks T011+.
    """
    raise NotImplementedError(
        "import_ciclos_avaliacoes será implementado em T011+ "
        f"(solicitacoes={solicitacoes_path!s}, avaliacoes={avaliacoes_path!s}, "
        f"dry_run={dry_run})"
    )
