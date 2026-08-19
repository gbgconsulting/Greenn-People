"""Orquestração da importação de PDIs e ações legado Sólides.

Superfície pública: ``import_pdi`` (reexportada por ``__init__``).
T008: persistência 1 PDI + 1 ação por linha resolvível (R-idempotência).
T012: resolução de pessoa no lote — órfãos / ``id_vs_nome`` não-fatais.
T019: dry-run / rollback; T020: consolidar idempotência.

Denylist intacta — **nunca** chama ``open_cycle`` / ``close_cycle`` /
``advance_stage`` / approval / ``get_visible_users`` / ``user_in_scope`` /
``ScopedObjectMixin`` / ``mark_overdue_pdi_actions`` /
``calculate_pdi_progress``; **nunca** edita ``overdue.py`` / ``models.py`` /
views; **nunca** importa openpyxl (parse só em ``accounts``). Hook de atraso
**somente** via ``AcaoPDI.save()``. **PROIBIDO** ``bulk_create``; **PROIBIDO**
FK Ciclo/Avaliação. Inatividade **não** bloqueia e **não** cria atalho de
visibilidade.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

from django.apps import apps
from django.db import connection, transaction
from django.db.utils import DatabaseError
from django.utils import timezone

from apps.accounts.models import CustomUser
from apps.accounts.services.legacy_import.dates import parse_legacy_date
from apps.accounts.services.legacy_import.parse_xlsx import PdiRow, parse_pdi_xlsx
from apps.accounts.services.legacy_import.report import (
    ImportReport,
    record_acao_criada,
    record_acao_inalterada,
    record_conflito,
    record_orfao_solicitacao,
    record_pdi_criado,
    record_pdi_inalterado,
    record_pdi_orfao_usuario,
)
from apps.pdi.models import AcaoPDI, PDI
from apps.pdi.services.legacy_import.resolve import (
    ResolveConflict,
    acao_natural_key,
    build_pdi_digest,
    concat_acao_descricao,
    map_acao_status,
    map_pdi_status,
    normalize_pdi_titulo,
    orfao_usuario_motivo,
    resolve_usuario,
)

_PDI_SOLIDES_ID_MODEL = ("pdi", "PDI")


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

    1. Parse ``--pdi`` (openpyxl via ``parse_pdi_xlsx`` em accounts).
    2. Schema: coluna ``PDI.solides_id`` presente (pré-requisito 010).
    3. ``data_carga = timezone.localdate()`` congelada para FR-011.
    4. Persist: uma ``transaction.atomic()`` cobre o lote; por linha
       resolvível, PDI **e** ação ou nenhum. Órfãos (``orfaos_usuario``) e
       ``id_vs_nome`` são não-fatais: skip da linha, lote continua.
    5. ``dry_run``: stub até T019.
    """
    parsed = parse_pdi_xlsx(pdi_path)
    report = ImportReport(
        modo="dry-run" if dry_run else "persist",
        pdi_file=parsed.path,
    )
    _assert_pdi_solides_id_schema()
    data_carga = timezone.localdate()

    if dry_run:
        raise NotImplementedError("T019: --dry-run (zero writes)")

    with transaction.atomic():
        try:
            _persist_rows(parsed.rows, report, data_carga)
        except LegacyPersistError:
            raise
        except Exception as exc:
            raise LegacyPersistError(str(exc)) from exc

    return report


def _assert_pdi_solides_id_schema() -> None:
    """Garante ``PDI.solides_id`` (010) antes do atomic — zero writes se ausente."""
    app_label, model_name = _PDI_SOLIDES_ID_MODEL
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
        raise LegacySchemaError(
            "Migration pré-requisito PDI.solides_id não aplicada. "
            "Execute `python manage.py migrate` antes de importar."
        )


def _persist_rows(
    rows: tuple[PdiRow, ...],
    report: ImportReport,
    data_carga: date,
) -> None:
    """Processa o lote: 1 PDI + 1 ação por linha resolvível (T008)."""
    for row in rows:
        _persist_row(row, report, data_carga)


def _persist_row(
    row: PdiRow,
    report: ImportReport,
    data_carga: date,
) -> None:
    """Unidade atômica da linha: PDI e ação, ou nenhum.

    ``Identificador Solicitação`` não bloqueia e não persiste FK — só
    amostra informativa em ``orfaos_solicitacao``.
    """
    if row.identificador_solicitacao:
        record_orfao_solicitacao(
            report,
            id_legado=row.identificador_solicitacao,
        )

    try:
        usuario = resolve_usuario(
            nome=_cell_text(row.nome),
            solides_id=row.identificador_pessoa or None,
        )
        if usuario is None:
            record_pdi_orfao_usuario(
                report,
                linha=row.linha,
                motivo=orfao_usuario_motivo(_cell_text(row.nome)),
            )
            return

        titulo = normalize_pdi_titulo(row.titulo)
        pdi_status = map_pdi_status(row.status)
        descricao = concat_acao_descricao(
            row.objetivo,
            row.situacao_atual,
            row.situacao_desejada,
        )
        prazo = _parse_prazo(row.data_entrega)
        acao_status = map_acao_status(
            pdi_status=pdi_status,
            prazo=prazo,
            data_carga=data_carga,
        )
        digest = build_pdi_digest(row.nome, row.titulo, row.criado_em)
    except ResolveConflict as exc:
        _record_line_conflict(report, tipo=exc.tipo, linha=row.linha)
        return

    _upsert_pdi_e_acao(
        report,
        usuario=usuario,
        titulo=titulo,
        pdi_status=pdi_status,
        digest=digest,
        descricao=descricao,
        prazo=prazo,
        acao_status=acao_status,
    )


def _upsert_pdi_e_acao(
    report: ImportReport,
    *,
    usuario: CustomUser,
    titulo: str,
    pdi_status: str,
    digest: str,
    descricao: str,
    prazo: date,
    acao_status: str,
) -> None:
    """Upsert conservador por digest; ação pela chave natural.

    Digest novo → create 1+1. Mesma chave de ação → inalterado (não
    reescreve título/status/descrição). Chave divergente no mesmo PDI →
    ``acao_chave_divergente`` sem 2ª ação e sem delete.
    """
    existing = (
        PDI.objects.filter(solides_id=digest)
        .prefetch_related("acoes")
        .first()
    )
    if existing is None:
        _create_pdi_e_acao(
            report,
            usuario=usuario,
            titulo=titulo,
            pdi_status=pdi_status,
            digest=digest,
            descricao=descricao,
            prazo=prazo,
            acao_status=acao_status,
        )
        return

    wanted = acao_natural_key(descricao, prazo)
    matched: AcaoPDI | None = None
    has_any_acao = False
    for acao in existing.acoes.all():
        has_any_acao = True
        if acao_natural_key(acao.descricao, acao.prazo) == wanted:
            matched = acao
            break

    if matched is not None:
        record_pdi_inalterado(report, solides_id=digest)
        record_acao_inalterada(
            report,
            pdi_solides_id=digest,
            status_acao=matched.status,
        )
        return

    if has_any_acao:
        record_conflito(
            report,
            tipo="acao_chave_divergente",
            extra=f"pdi={digest}",
        )
        return

    _create_acao(
        report,
        pdi=existing,
        digest=digest,
        descricao=descricao,
        prazo=prazo,
        acao_status=acao_status,
    )
    record_pdi_inalterado(report, solides_id=digest)


def _create_pdi_e_acao(
    report: ImportReport,
    *,
    usuario: CustomUser,
    titulo: str,
    pdi_status: str,
    digest: str,
    descricao: str,
    prazo: date,
    acao_status: str,
) -> None:
    """Create 1 PDI + 1 ação via ``full_clean``+``save`` (sem ``bulk_create``)."""
    pdi = PDI(
        usuario=usuario,
        titulo=titulo,
        status=pdi_status,
        solides_id=digest,
    )
    pdi.full_clean()
    pdi.save()
    _create_acao(
        report,
        pdi=pdi,
        digest=digest,
        descricao=descricao,
        prazo=prazo,
        acao_status=acao_status,
    )
    record_pdi_criado(report, solides_id=digest)


def _create_acao(
    report: ImportReport,
    *,
    pdi: PDI,
    digest: str,
    descricao: str,
    prazo: date,
    acao_status: str,
) -> None:
    """Persiste a ação; ``responsavel`` = dono do PDI; hook só via ``save()``.

    **MUST NOT** chamar ``recalculate_overdue_status`` /
    ``mark_overdue_pdi_actions``. Sem ``update_fields`` que pule ``prazo``.
    """
    acao = AcaoPDI(
        pdi=pdi,
        descricao=descricao,
        responsavel=pdi.usuario,
        prazo=prazo,
        status=acao_status,
    )
    acao.full_clean()
    acao.save()
    record_acao_criada(
        report,
        pdi_solides_id=digest,
        status_acao=acao.status,
    )


def _parse_prazo(value: object) -> date:
    """``Data de Entrega`` → date; ausente/ilegível → ``prazo_invalido``."""
    try:
        prazo = parse_legacy_date(value)
    except (TypeError, ValueError) as exc:
        raise ResolveConflict("prazo_invalido") from exc
    if prazo is None:
        raise ResolveConflict("prazo_invalido")
    return prazo


def _record_line_conflict(report: ImportReport, *, tipo: str, linha: int) -> None:
    record_conflito(report, tipo=tipo, extra=f"linha={linha}")


def _cell_text(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return str(value)
