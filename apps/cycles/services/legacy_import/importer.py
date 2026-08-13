"""Orquestração da importação de ciclos/avaliações legado Sólides.

Superfície pública: ``import_ciclos_avaliacoes`` (reexportada por ``__init__``).
T011: fase 1 — parse solicitações → upsert ``Ciclo`` (sempre ``encerrado``)
via ``resolve.upsert_ciclo_from_solicitacao`` + contadores; ``atomic`` no
modo persist; dry-run com ``set_rollback`` (padrão 010 / R12).
T016: fase 2 — agregar cabeçalhos → resolve FK → upsert ``Avaliacao``
(``etapa=feedback``, ``concluida=True``, ``solides_id`` canônico).
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
from apps.accounts.services.legacy_import.report import (
    ImportReport,
    note_grupo_agregado,
    record_ids_colapsados,
    record_orfao_ciclo,
    record_orfao_usuario,
)
from apps.cycles.services.legacy_import.aggregate import aggregate_avaliacao_headers
from apps.cycles.services.legacy_import.resolve import (
    resolve_ciclo,
    resolve_usuario,
    upsert_avaliacao_header,
    upsert_ciclo_from_solicitacao,
)

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
    """Orquestra parse → fase ciclos → fase cabeçalhos (ou dry-run).

    Assinatura alinhada a ``contracts/import-command-contract.md``.

    1. **Parse+validate** (fora do atomic): paths, OOXML, colunas
       obrigatórias. ``LegacyParseError`` propaga (exit 1; zero writes).
    2. **Schema**: ``Ciclo.solides_id`` presente. Ausência →
       ``LegacySchemaError`` (exit 1, zero writes).
    3. **Persist** em ``transaction.atomic()``:
       a. Fase Ciclos — ``upsert_ciclo_from_solicitacao`` (``full_clean`` +
          ``save``; status sempre ``encerrado``; **sem** open/close).
       b. Fase Avaliações — agregar → resolve FK → upsert ``Avaliacao``
          terminal (T016; **sem** ``advance_stage`` / notas).
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
    """Fase 2 (T016): agregar → resolve FK → upsert ``Avaliacao`` terminal.

    Fluxo normativo (``aggregation-contract.md`` / R8–R11):

    1. ``aggregate_avaliacao_headers`` → grupos ``(solicitacao, avaliado)``
    2. ``resolve_ciclo`` / ``resolve_usuario`` — órfão → report + skip
    3. ``upsert_avaliacao_header`` — ``feedback`` + ``concluida`` + canônico;
       conflitos ``solides_id_divergente`` / ``solides_id_avaliacao_em_uso``
    4. Contadores ``grupos_agregados`` + amostra ``ids_colapsados``

    **Proibido**: ``advance_stage`` / open/close / approval; preencher
    ``nota_final_*`` / ``AvaliacaoCompetencia``.
    """
    groups = aggregate_avaliacao_headers(rows)
    for group in groups:
        ciclo = resolve_ciclo(group.solicitacao_id)
        if ciclo is None:
            record_orfao_ciclo(
                report,
                solicitacao_id=group.solicitacao_id,
                avaliado_id=group.avaliado_id,
            )
            continue

        usuario = resolve_usuario(group.avaliado_id, group.nome_avaliado)
        if usuario is None:
            record_orfao_usuario(
                report,
                solicitacao_id=group.solicitacao_id,
                avaliado_id=group.avaliado_id,
            )
            continue

        upsert_avaliacao_header(
            ciclo=ciclo,
            usuario=usuario,
            solides_id=group.canonical_id,
            report=report,
        )

        note_grupo_agregado(report)
        if group.collapsed_ids:
            record_ids_colapsados(
                report,
                solicitacao_id=group.solicitacao_id,
                avaliado_id=group.avaliado_id,
                canonical_id=group.canonical_id,
                collapsed_ids=group.collapsed_ids,
                n_linhas=group.n_linhas,
            )
