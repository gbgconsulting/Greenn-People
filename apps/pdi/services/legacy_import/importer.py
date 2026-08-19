"""Orquestração da importação de PDIs e ações legado Sólides.

Superfície pública: ``import_pdi`` (reexportada por ``__init__``).
T002: stub. Persistência 1 PDI + 1 ação em T008; dry-run/idempotência em T019/T020.

Denylist intacta — **nunca** chama ``open_cycle`` / ``close_cycle`` /
``advance_stage`` / approval / ``get_visible_users`` / ``user_in_scope`` /
``mark_overdue_pdi_actions`` / ``calculate_pdi_progress``; **nunca** edita
``overdue.py`` / ``models.py`` / views; **nunca** importa openpyxl
(parse só em ``accounts``). Hook de atraso **somente** via ``AcaoPDI.save()``.
"""

from __future__ import annotations

from pathlib import Path

from apps.accounts.services.legacy_import.report import ImportReport


class LegacySchemaError(Exception):
    """Pré-condição de schema ausente (003/010) — exit 1, zero writes.

    Esta fatia **não** gera migration. Falha de schema (ex. ``PDI.solides_id``
    ausente) não entra no ``atomic`` e não deixa escrita parcial.
    """


class LegacyPersistError(Exception):
    """Erro fatal durante persistência — ``atomic`` faz rollback; exit 1.

    Conflitos/órfãos não-fatais NÃO usam esta classe: vão para o relatório
    e exit ``0``.
    """


def import_pdi(
    pdi_path: str | Path,
    *,
    dry_run: bool = False,
) -> ImportReport:
    """Orquestra parse → resolve → persist 1+1 (ou dry-run).

    Assinatura alinhada a ``contracts/import-command-contract.md``.
    Implementação em T008 (persist) / T019 (dry-run).
    """
    raise NotImplementedError("T008: persistência 1 PDI + 1 ação")
