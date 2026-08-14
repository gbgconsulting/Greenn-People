"""Orquestração da importação de ciclos/avaliações legado Sólides.

Superfície pública: ``import_ciclos_avaliacoes`` (reexportada por ``__init__``).
T011: fase 1 — parse solicitações → upsert ``Ciclo`` (sempre ``encerrado``)
via ``resolve.upsert_ciclo_from_solicitacao`` + contadores; ``atomic`` no
modo persist; dry-run com ``set_rollback`` (padrão 010 / R12).
T016: fase 2 — agregar cabeçalhos → resolve FK → upsert ``Avaliacao``
(``etapa=feedback``, ``concluida=True``, ``solides_id`` canônico).
T025: consolidar ``--dry-run`` (parse + agregação + totais projetados,
zero commit via ``set_rollback``), falha fatal pré-persistência
(arquivo/OOXML/colunas/migration) e rollback em exceção (``atomic``).
T026: consolidar idempotência (R11 / FR-015) — Ciclo por ``solides_id``;
Avaliacao por ``(ciclo, usuario)`` + canônico; update só campos
permitidos; conflitos sem sobrescrever silenciosamente.

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

# Schema pré-persistência (contrato §Pré-condições / T025):
# - Ciclo.solides_id — migration desta feature
# - Avaliacao.solides_id — pré-requisito 010
_SOLIDES_ID_MODELS: tuple[tuple[str, str], ...] = (
    ("cycles", "Ciclo"),
    ("reviews", "Avaliacao"),
)


class LegacySchemaError(Exception):
    """Migration pré-requisito ausente — exit 1, zero writes.

    Pré-condição do contrato (``import-command-contract.md`` §Pré-condições
    e §Códigos de saída / T025): falha de schema não entra no ``atomic``
    e não deixa escrita parcial.
    """


class LegacyPersistError(Exception):
    """Erro fatal durante persistência — ``atomic`` faz rollback; exit 1.

    Conflitos/órfãos não-fatais NÃO usam esta classe: vão para o relatório
    e exit ``0`` (R12).
    """


def import_ciclos_avaliacoes(
    solicitacoes_path: str | Path,
    avaliacoes_path: str | Path,
    *,
    dry_run: bool = False,
) -> ImportReport:
    """Orquestra parse → fase ciclos → fase cabeçalhos (ou dry-run).

    Assinatura alinhada a ``contracts/import-command-contract.md`` / R12.

    1. **Parse+validate** (fora do atomic / T025): paths, OOXML, colunas
       obrigatórias. ``LegacyParseError`` propaga (exit 1; **zero writes**).
    2. **Schema** (T025): ``Ciclo.solides_id`` e ``Avaliacao.solides_id``
       presentes. Ausência → ``LegacySchemaError`` (exit 1, zero writes).
    3. **Persist** em ``transaction.atomic()``:
       a. Fase Ciclos — ``upsert_ciclo_from_solicitacao`` (``full_clean`` +
          ``save``; status sempre ``encerrado``; **sem** open/close).
       b. Fase Avaliações — agregar → resolve FK → upsert ``Avaliacao``
          terminal (T016; **sem** ``advance_stage`` / notas).
       Exceção → ``LegacyPersistError``, rollback do ``atomic``, exit 1.
    4. **``dry_run`` (T025 / R12)**: mesma lógica para projetar totais
       (ciclos + grupos agregados) no relatório (``modo=dry-run``), com
       ``set_rollback(True)`` em ``finally`` — **zero commit**. Sucesso
       de dry-run → exit ``0`` no command (conflitos/órfãos não abortam).
    5. **Idempotência (T026 / R11 / FR-015)**:
       - Ciclo: chave ``solides_id``; create ou update
         ``nome``/``data_inicio``/``data_fim``/``status=encerrado``;
         nunca duplica; nunca reabre.
       - Avaliacao: chave ``(ciclo, usuario)`` + validação do canônico;
         update ``etapa``/``concluida``/``solides_id`` (se vazio ou
         igual); ``solides_id_divergente`` /
         ``solides_id_avaliacao_em_uso`` → conflito, **sem** sobrescrita
         silenciosa; **não** toca ``nota_final_*``.
    """
    # Fase 1 (T025): parse+validate fora do atomic — falha → zero writes.
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

    # T025: schema pré-atomic — migration pendente → exit 1, zero writes.
    _assert_solides_id_schema()

    with transaction.atomic():
        try:
            _persist_fase_ciclos(parsed_solicitacoes.rows, report)
            _persist_fase_avaliacoes(parsed_avaliacoes.rows, report)
        except LegacyPersistError:
            raise
        except Exception as exc:
            # T025 / R12: qualquer falha de persistência aborta a transação
            # (rollback no __exit__ do atomic) e sinaliza exit 1 no command.
            raise LegacyPersistError(str(exc)) from exc
        finally:
            # T025: dry-run sempre descarta writes, inclusive se exceção
            # durante persistência — evita commit parcial.
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


def _assert_solides_id_schema() -> None:
    """Garante colunas ``solides_id`` pré-requisito antes do atomic (T025).

    Introspecção do DB (não só o model) — migrations pendentes falham
    aqui, não no meio do ``atomic``.
    """
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
            "Migration pré-requisito solides_id não aplicada: "
            + ", ".join(missing)
            + ". Execute `python manage.py migrate` antes de importar."
        )


def _persist_fase_ciclos(
    rows: tuple[SolicitacaoRow, ...],
    report: ImportReport,
) -> None:
    """Fase 1 (T011/T026): upsert idempotente ``Ciclo`` por ``solides_id``.

    R11: lookup por ``solides_id`` → create ou update dos campos
    permitidos (``nome`` / ``data_inicio`` / ``data_fim`` /
    ``status=encerrado``). Reexecução idêntica → ``inalterado`` (sem
    duplicar). Conflitos por linha são não-fatais (R7). **Proibido**
    ``open_cycle`` / ``close_cycle``.
    """
    for row in rows:
        upsert_ciclo_from_solicitacao(row, report)


def _persist_fase_avaliacoes(
    rows: tuple[AvaliacaoHeaderRow, ...],
    report: ImportReport,
) -> None:
    """Fase 2 (T016/T026): agregar → resolve FK → upsert idempotente.

    Fluxo normativo (``aggregation-contract.md`` / R8–R11):

    1. ``aggregate_avaliacao_headers`` → grupos ``(solicitacao, avaliado)``
    2. ``resolve_ciclo`` / ``resolve_usuario`` — órfão → report + skip
    3. ``upsert_avaliacao_header`` — chave ``(ciclo, usuario)`` + canônico;
       update só ``etapa``/``concluida``/``solides_id`` (vazio ou igual);
       conflitos ``solides_id_divergente`` /
       ``solides_id_avaliacao_em_uso`` **sem** sobrescrita silenciosa
    4. Contadores ``grupos_agregados`` + amostra ``ids_colapsados`` só
       quando o upsert não conflitou (create/update/unchanged)

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

        result = upsert_avaliacao_header(
            ciclo=ciclo,
            usuario=usuario,
            solides_id=group.canonical_id,
            report=report,
        )

        # T026: handoff 6.5.5 e contagem de grupos só para upsert ok —
        # conflito não inventa mapeamento nem infla ``grupos_agregados``.
        if result.kind == "conflict":
            continue

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
