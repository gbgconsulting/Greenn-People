"""Orquestração da importação de ciclos/avaliações legado Sólides.

Superfície pública: ``import_ciclos_avaliacoes`` (reexportada por ``__init__``).
T011: fase 1 — parse solicitações → upsert ``Ciclo`` (sempre ``encerrado``)
via ``resolve.upsert_ciclo_from_solicitacao`` + contadores; ``atomic`` no
modo persist; dry-run com ``set_rollback`` (padrão 010 / R12).
T016: fase 2 cabeçalhos (stub até US2).
T025/T026: consolidar dry-run / idempotência.

Denylist intacta — **nunca** chama ``open_cycle`` / ``close_cycle`` /
``advance_stage`` / approval / evaluation / adherence.
"""

from __future__ import annotations

from pathlib import Path

from django.apps import apps
from django.db import connection, transaction
from django.db.utils import DatabaseError

from apps.accounts.services.legacy_import.parse_xlsx import (
    AvaliacaoHeaderRow,
    LegacyParseError,
    SolicitacaoRow,
    parse_avaliacoes_headers_xlsx,
    parse_solicitacoes_xlsx,
    validate_source_paths,
)
from apps.accounts.services.legacy_import.report import ImportReport
from apps.cycles.services.legacy_import.resolve import upsert_ciclo_from_solicitacao

# Schema desta feature — checagem pré-persistência (contrato §Pré-condições).
_SOLIDES_ID_MODELS: tuple[tuple[str, str], ...] = (
    ("cycles", "Ciclo"),
)


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
    """Orquestra parse → fase ciclos (+ stub cabeçalhos) ou dry-run.

    Assinatura alinhada a ``contracts/import-command-contract.md``.

    1. **Parse+validate** (fora do atomic): paths, OOXML, colunas
       obrigatórias. ``LegacyParseError`` propaga (exit 1; zero writes).
    2. **Schema**: ``Ciclo.solides_id`` presente. Ausência →
       ``LegacySchemaError`` (exit 1, zero writes).
    3. **Persist** em ``transaction.atomic()``:
       a. Fase Ciclos — ``upsert_ciclo_from_solicitacao`` (``full_clean`` +
          ``save``; status sempre ``encerrado``; **sem** open/close).
       b. Fase Avaliações — stub até T016.
    4. **``dry_run``**: mesma lógica para projetar totais, com
       ``set_rollback(True)`` — zero commit.
    """
    solicitacoes_file, avaliacoes_file = _validate_required_paths(
        solicitacoes_path,
        avaliacoes_path,
    )
    parsed_solicitacoes = parse_solicitacoes_xlsx(solicitacoes_file)
    parsed_avaliacoes = parse_avaliacoes_headers_xlsx(avaliacoes_file)

    report = ImportReport(
        modo="dry-run" if dry_run else "persist",
        solicitacoes_file=parsed_solicitacoes.path,
        avaliacoes_file=parsed_avaliacoes.path,
    )

    _assert_ciclo_solides_id_schema()

    with transaction.atomic():
        try:
            _persist_fase_ciclos(parsed_solicitacoes.rows, report)
            _persist_fase_avaliacoes(parsed_avaliacoes.rows, report)
        except LegacyPersistError:
            raise
        except Exception as exc:
            raise LegacyPersistError(str(exc)) from exc
        finally:
            if dry_run:
                transaction.set_rollback(True)

    return report


def _validate_required_paths(
    solicitacoes_path: str | Path,
    avaliacoes_path: str | Path,
) -> tuple[Path, Path]:
    """Ambos os paths são obrigatórios (contrato / research R3)."""
    if not str(avaliacoes_path).strip():
        raise LegacyParseError("Arquivo de avaliações é obrigatório")
    solicitacoes, avaliacoes = validate_source_paths(
        solicitacoes_path,
        avaliacoes_path,
    )
    if avaliacoes is None:
        raise LegacyParseError("Arquivo de avaliações é obrigatório")
    return solicitacoes, avaliacoes


def _assert_ciclo_solides_id_schema() -> None:
    """Garante coluna ``Ciclo.solides_id`` antes do atomic (T011 / R13)."""
    missing: list[str] = []
    for app_label, model_name in _SOLIDES_ID_MODELS:
        model = apps.get_model(app_label, model_name)
        table = model._meta.db_table
        try:
            with connection.cursor() as cursor:
                description = connection.introspection.get_table_description(
                    cursor, table
                )
        except DatabaseError as exc:
            raise LegacySchemaError(
                "Não foi possível verificar o schema de solides_id em "
                f"{table}: {exc}. Execute `python manage.py migrate`."
            ) from exc
        columns = {col.name for col in description}
        if "solides_id" not in columns:
            missing.append(f"{table}.solides_id")

    if missing:
        raise LegacySchemaError(
            "Migration Ciclo.solides_id não aplicada: "
            + ", ".join(missing)
            + ". Execute `python manage.py migrate` antes de importar."
        )


def _persist_fase_ciclos(
    rows: tuple[SolicitacaoRow, ...],
    report: ImportReport,
) -> None:
    """Fase 1 (T011): upsert ``Ciclo`` por ``solides_id`` (sempre encerrado).

    Conflitos por linha são não-fatais (R7) — registrados no relatório;
    as demais linhas seguem. **Proibido** ``open_cycle`` / ``close_cycle``.
    """
    for row in rows:
        upsert_ciclo_from_solicitacao(row, report)


def _persist_fase_avaliacoes(
    rows: tuple[AvaliacaoHeaderRow, ...],
    report: ImportReport,
) -> None:
    """Fase 2 (T016): stub — cabeçalhos agregados ainda não persistidos.

    Parse já validou o arquivo; a agregação/upsert entra em US2.
    ``rows`` / ``report`` reservados para a implementação futura.
    """
    _ = (rows, report)
