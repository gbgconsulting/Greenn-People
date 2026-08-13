"""Resolução / upsert de Ciclo histórico a partir de solicitações Sólides.

Conforme research R5/R6/R7/R11 e ``contracts/column-mapping-contract.md``
§solicitações: lookup por ``solides_id``; create/update ``nome`` /
``data_inicio`` / ``data_fim`` / ``status=encerrado``; datas ambas
obrigatórias; conflito se inválidas; **nunca** ``aberto``.

Denylist intacta — **não** chama ``open_cycle`` / ``close_cycle`` /
``stage`` / approval. Persistência ORM direta + ``full_clean()``/``save()``.

US2 (T015) estende este módulo com ``resolve_ciclo`` / ``resolve_usuario``.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any, Literal

from django.core.exceptions import ValidationError

from apps.accounts.services.legacy_import.dates import (
    normalize_ciclo_nome,
    parse_legacy_date,
)
from apps.accounts.services.legacy_import.parse_xlsx import SolicitacaoRow
from apps.accounts.services.legacy_import.report import (
    ImportReport,
    note_ciclo_atualizado,
    note_ciclo_conflito,
    note_ciclo_inalterado,
    record_ciclo_criado_amostra,
    record_conflito,
)
from apps.cycles.models import Ciclo

# Status Sólides conhecidos (clarification / R5) — qualquer outro ainda
# vira ``encerrado``, com conflito informativo ``status_legado_desconhecido``.
_KNOWN_SOLICITACAO_STATUS = frozenset(
    {"finished", "canceled", "draft", "active"}
)

CicloUpsertKind = Literal["created", "updated", "unchanged", "conflict"]


@dataclass(frozen=True)
class CicloUpsertResult:
    """Resultado do upsert de uma solicitação → ``Ciclo``."""

    kind: CicloUpsertKind
    ciclo: Ciclo | None = None
    conflict_tipo: str = ""


def upsert_ciclo_from_solicitacao(
    row: SolicitacaoRow,
    report: ImportReport | None = None,
) -> CicloUpsertResult:
    """Lookup/create/update ``Ciclo`` por ``solides_id`` (sempre encerrado).

    Contadores / amostra / conflitos atualizados em ``report`` quando
    fornecido. Conflitos por linha são **não-fatais** (R7): a linha é
    pulada e as demais seguem.

    Returns:
        ``CicloUpsertResult`` com ``kind`` e eventual ``ciclo`` persistido.
    """
    prepared = _prepare_ciclo_fields(row, report)
    if prepared is None:
        return CicloUpsertResult(kind="conflict", conflict_tipo="prepare_failed")

    solides_id, nome, data_inicio, data_fim = prepared
    _maybe_note_status_desconhecido(row, report)

    existing = Ciclo.objects.filter(solides_id=solides_id).first()
    if existing is None:
        return _create_ciclo(
            solides_id=solides_id,
            nome=nome,
            data_inicio=data_inicio,
            data_fim=data_fim,
            report=report,
        )

    return _update_ciclo(
        existing,
        nome=nome,
        data_inicio=data_inicio,
        data_fim=data_fim,
        report=report,
    )


def _prepare_ciclo_fields(
    row: SolicitacaoRow,
    report: ImportReport | None,
) -> tuple[str, str, date, date] | None:
    """Valida identificador, datas e nome; ``None`` = conflito (não cria)."""
    solides_id = (row.identificador or "").strip()
    if not solides_id:
        _record_ciclo_conflito(
            report,
            tipo="identificador_ausente",
            solicitacao="",
            linha=row.linha,
        )
        return None

    data_inicio = _safe_parse_date(row.iniciada_em)
    data_fim = _safe_parse_date(row.terminada_em)
    if data_inicio is None or data_fim is None:
        _record_ciclo_conflito(
            report,
            tipo="datas_ausentes_ou_invalidas",
            solicitacao=solides_id,
            linha=row.linha,
        )
        return None

    try:
        nome = normalize_ciclo_nome(row.nome)
    except ValueError as exc:
        tipo = str(exc) if str(exc) == "nome_serial_ambiguo" else "nome_invalido"
        _record_ciclo_conflito(
            report,
            tipo=tipo,
            solicitacao=solides_id,
            linha=row.linha,
        )
        return None

    if not nome:
        _record_ciclo_conflito(
            report,
            tipo="nome_ausente",
            solicitacao=solides_id,
            linha=row.linha,
        )
        return None

    return solides_id, nome, data_inicio, data_fim


def _safe_parse_date(raw: Any) -> date | None:
    """``parse_legacy_date`` sem propagar ``ValueError`` (→ conflito R7)."""
    try:
        return parse_legacy_date(raw)
    except (TypeError, ValueError):
        return None


def _create_ciclo(
    *,
    solides_id: str,
    nome: str,
    data_inicio: date,
    data_fim: date,
    report: ImportReport | None,
) -> CicloUpsertResult:
    ciclo = Ciclo(
        solides_id=solides_id,
        nome=nome,
        data_inicio=data_inicio,
        data_fim=data_fim,
        status=Ciclo.Status.ENCERRADO,
    )
    try:
        ciclo.full_clean()
        ciclo.save()
    except ValidationError:
        _record_ciclo_conflito(
            report,
            tipo="validacao_ciclo",
            solicitacao=solides_id,
            linha="-",
        )
        return CicloUpsertResult(
            kind="conflict",
            conflict_tipo="validacao_ciclo",
        )

    if report is not None:
        record_ciclo_criado_amostra(
            report,
            solides_id=solides_id,
            nome=nome,
            status=Ciclo.Status.ENCERRADO,
        )
    return CicloUpsertResult(kind="created", ciclo=ciclo)


def _update_ciclo(
    ciclo: Ciclo,
    *,
    nome: str,
    data_inicio: date,
    data_fim: date,
    report: ImportReport | None,
) -> CicloUpsertResult:
    """Atualiza campos permitidos; força ``status=encerrado`` (R5/R11)."""
    desired_status = Ciclo.Status.ENCERRADO
    unchanged = (
        ciclo.nome == nome
        and ciclo.data_inicio == data_inicio
        and ciclo.data_fim == data_fim
        and ciclo.status == desired_status
    )
    if unchanged:
        if report is not None:
            note_ciclo_inalterado(report)
        return CicloUpsertResult(kind="unchanged", ciclo=ciclo)

    ciclo.nome = nome
    ciclo.data_inicio = data_inicio
    ciclo.data_fim = data_fim
    ciclo.status = desired_status
    try:
        ciclo.full_clean()
        ciclo.save()
    except ValidationError:
        _record_ciclo_conflito(
            report,
            tipo="validacao_ciclo",
            solicitacao=ciclo.solides_id or "",
            linha="-",
        )
        return CicloUpsertResult(
            kind="conflict",
            conflict_tipo="validacao_ciclo",
            ciclo=ciclo,
        )

    if report is not None:
        note_ciclo_atualizado(report)
    return CicloUpsertResult(kind="updated", ciclo=ciclo)


def _maybe_note_status_desconhecido(
    row: SolicitacaoRow,
    report: ImportReport | None,
) -> None:
    """R5: status presente e fora do conjunto conhecido → conflito informativo.

    Não incrementa ``ciclos_conflitos`` — o ciclo ainda é importado encerrado.
    """
    if report is None:
        return
    status = (row.status or "").strip().lower()
    if not status or status in _KNOWN_SOLICITACAO_STATUS:
        return
    record_conflito(
        report,
        tipo="status_legado_desconhecido",
        extra=f"solicitacao={row.identificador}",
        motivo=f"status={row.status.strip()} | linha={row.linha}",
    )


def _record_ciclo_conflito(
    report: ImportReport | None,
    *,
    tipo: str,
    solicitacao: str,
    linha: int | str,
) -> None:
    """Conflito não-fatal de linha: amostra + contador ``ciclos_conflitos``."""
    if report is None:
        return
    record_conflito(
        report,
        tipo=tipo,
        extra=f"solicitacao={solicitacao}" if solicitacao else "",
        motivo=f"linha={linha}",
    )
    note_ciclo_conflito(report)
