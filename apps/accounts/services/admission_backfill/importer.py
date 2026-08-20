"""Orquestração dry-run / persist / report do backfill de ``data_entrada``.

Contrato: ``contracts/admission-backfill-command-contract.md``.
Só preenche ``data_entrada`` quando NULL/vazio; ``transaction.atomic`` no
persist; MUST NOT chamar open/close/ensure/advance; MUST NOT mutar
nome/email/área/cargo/gestor/``is_active``.
"""

from __future__ import annotations

from pathlib import Path
from typing import TypedDict

from django.db import transaction

from apps.accounts.models import CustomUser
from apps.accounts.services.admission_backfill.resolve import (
    match_user_for_admission,
    parse_data_admissao,
)
from apps.accounts.services.legacy_import.parse_xlsx import (
    ColaboradorAdmissionRow,
    parse_colaboradores_admission_xlsx,
)

# Contrato §Relatório: amostra truncada (~5), padrão 010.
_SAMPLE_MAX = 5


class AdmissionBackfillReport(TypedDict):
    """Totais do relatório operacional (+ amostras para formatação T028)."""

    lidos: int
    matched: int
    preenchidos: int
    ja_preenchidos: int
    orfaos: int
    conflitos: int
    datas_ilegiveis: int
    dry_run: bool
    amostra_preenchidos: list[str]
    amostra_ja_preenchidos: list[str]
    amostra_orfaos: list[str]
    amostra_conflitos: list[str]
    amostra_datas_ilegiveis: list[str]


def backfill_data_entrada(
    colaboradores_path: str | Path,
    *,
    dry_run: bool = False,
) -> AdmissionBackfillReport:
    """Lê ``backup_colaboradores_*.xlsx`` e preenche só ``data_entrada`` vazia.

    ``dry_run=True``: zero writes; totais projetados.
    Persist: ``transaction.atomic``; idempotente (2ª run → delta = 0).
    """
    parsed = parse_colaboradores_admission_xlsx(colaboradores_path)

    if dry_run:
        return _process_rows(parsed.rows, dry_run=True)

    with transaction.atomic():
        return _process_rows(parsed.rows, dry_run=False)


def _process_rows(
    rows: tuple[ColaboradorAdmissionRow, ...],
    *,
    dry_run: bool,
) -> AdmissionBackfillReport:
    """Match + parse + fill (ou projeção) sem tocar campos fora de ``data_entrada``."""
    report = _empty_report(dry_run=dry_run)
    filled_pks: set[int] = set()

    for row in rows:
        report["lidos"] += 1
        email = _row_email(row)
        sample_key = email or row.identificador or f"linha={row.linha}"

        user, outcome = match_user_for_admission(
            email=email,
            solides_id=row.identificador or None,
        )

        if outcome == "orphan":
            report["orfaos"] += 1
            _append_sample(report["amostra_orfaos"], sample_key)
            continue
        if outcome == "conflict":
            report["conflitos"] += 1
            _append_sample(report["amostra_conflitos"], sample_key)
            continue

        report["matched"] += 1
        assert user is not None

        if _is_empty_admission_cell(row.data_admissao):
            continue

        parsed_date = parse_data_admissao(row.data_admissao)
        if parsed_date is None:
            report["datas_ilegiveis"] += 1
            _append_sample(report["amostra_datas_ilegiveis"], sample_key)
            continue

        display_email = user.email or sample_key
        if user.pk in filled_pks or user.data_entrada is not None:
            report["ja_preenchidos"] += 1
            _append_sample(report["amostra_ja_preenchidos"], display_email)
            continue

        if dry_run:
            report["preenchidos"] += 1
            filled_pks.add(user.pk)
            _append_sample(report["amostra_preenchidos"], display_email)
            continue

        updated = CustomUser.objects.filter(
            pk=user.pk,
            data_entrada__isnull=True,
        ).update(data_entrada=parsed_date)
        if updated:
            report["preenchidos"] += 1
            filled_pks.add(user.pk)
            _append_sample(report["amostra_preenchidos"], display_email)
        else:
            report["ja_preenchidos"] += 1
            _append_sample(report["amostra_ja_preenchidos"], display_email)

    return report


def _empty_report(*, dry_run: bool) -> AdmissionBackfillReport:
    return {
        "lidos": 0,
        "matched": 0,
        "preenchidos": 0,
        "ja_preenchidos": 0,
        "orfaos": 0,
        "conflitos": 0,
        "datas_ilegiveis": 0,
        "dry_run": dry_run,
        "amostra_preenchidos": [],
        "amostra_ja_preenchidos": [],
        "amostra_orfaos": [],
        "amostra_conflitos": [],
        "amostra_datas_ilegiveis": [],
    }


def _row_email(row: ColaboradorAdmissionRow) -> str | None:
    """Primeiro e-mail não vazio: empresarial → corporativo → pessoal (padrão 010)."""
    for raw in (row.email_empresarial, row.email, row.email_pessoal):
        text = str(raw).strip() if raw is not None else ""
        if text:
            return text
    return None


def _is_empty_admission_cell(raw: object) -> bool:
    """Célula sem data (None / branco / sentinela 0) — não conta como ilegível."""
    if raw is None:
        return True
    if isinstance(raw, bool):
        return False
    if isinstance(raw, str) and not raw.strip():
        return True
    if isinstance(raw, (int, float)) and raw == 0:
        return True
    return False


def _append_sample(sample: list[str], value: str) -> None:
    if len(sample) < _SAMPLE_MAX and value:
        sample.append(value)
