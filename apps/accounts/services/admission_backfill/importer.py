"""Orquestração dry-run / persist / report do backfill de ``data_entrada``.

Contrato: ``contracts/admission-backfill-command-contract.md``.
Só preenche ``data_entrada`` quando NULL/vazio; ``transaction.atomic`` no
persist; MUST NOT chamar open/close/ensure/advance; MUST NOT mutar
nome/email/área/cargo/gestor/``is_active``.
"""

from __future__ import annotations

from pathlib import Path
from typing import TypedDict


class AdmissionBackfillReport(TypedDict):
    """Totais do relatório operacional (amostra mascarada via report 010)."""

    lidos: int
    matched: int
    preenchidos: int
    ja_preenchidos: int
    orfaos: int
    conflitos: int
    datas_ilegiveis: int
    dry_run: bool


def backfill_data_entrada(
    colaboradores_path: str | Path,
    *,
    dry_run: bool = False,
) -> AdmissionBackfillReport:
    """Lê ``backup_colaboradores_*.xlsx`` e preenche só ``data_entrada`` vazia.

    ``dry_run=True``: zero writes; totais projetados.
    Persist: idempotente (2ª run → delta preenchimento = 0).
    """
    raise NotImplementedError
