"""Resolução / upsert de Ciclo, User e Avaliacao a partir do legado Sólides.

US1 — upsert de ciclo (research R5/R6/R7/R11,
``contracts/column-mapping-contract.md`` §solicitações): lookup por
``solides_id``; create/update ``nome`` / ``data_inicio`` / ``data_fim`` /
``status=encerrado``; datas ambas obrigatórias; conflito se inválidas;
**nunca** ``aberto``.

US2 — resolução de FKs (research R9, §Resolução de FKs):
``resolve_ciclo`` / ``resolve_usuario`` — lookup apenas; **nunca** inventar
Ciclo/User; usuário inativo permitido; fallback de nome só com match único
via ``canonical_key``.

US2 — upsert de cabeçalho ``Avaliacao`` (research R8/R10/R11,
``contracts/aggregation-contract.md``): ``etapa=feedback``,
``concluida=True``, ``solides_id`` canônico; conflitos
``solides_id_divergente`` / ``solides_id_avaliacao_em_uso``; **não**
toca ``nota_final_*`` / ``AvaliacaoCompetencia``.

Denylist intacta — **não** chama ``open_cycle`` / ``close_cycle`` /
``advance_stage`` / approval / evaluation. Persistência ORM direta +
``full_clean()``/``save()``.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any, Literal

from django.core.exceptions import ValidationError

from apps.accounts.models import CustomUser
from apps.accounts.services.legacy_import.dates import (
    normalize_ciclo_nome,
    parse_legacy_date,
)
from apps.accounts.services.legacy_import.parse_xlsx import SolicitacaoRow
from apps.accounts.services.legacy_import.report import (
    ImportReport,
    note_avaliacao_atualizada,
    note_avaliacao_criada,
    note_avaliacao_inalterada,
    note_ciclo_atualizado,
    note_ciclo_conflito,
    note_ciclo_inalterado,
    record_ciclo_criado_amostra,
    record_conflito,
)
from apps.competencies.services.catalog_import.normalize import canonical_key
from apps.cycles.models import Ciclo
from apps.reviews.models import Avaliacao

# Status Sólides conhecidos (clarification / R5) — qualquer outro ainda
# vira ``encerrado``, com conflito informativo ``status_legado_desconhecido``.
_KNOWN_SOLICITACAO_STATUS = frozenset(
    {"finished", "canceled", "draft", "active"}
)

CicloUpsertKind = Literal["created", "updated", "unchanged", "conflict"]
AvaliacaoUpsertKind = Literal["created", "updated", "unchanged", "conflict"]


@dataclass(frozen=True)
class CicloUpsertResult:
    """Resultado do upsert de uma solicitação → ``Ciclo``."""

    kind: CicloUpsertKind
    ciclo: Ciclo | None = None
    conflict_tipo: str = ""


@dataclass(frozen=True)
class AvaliacaoUpsertResult:
    """Resultado do upsert de um grupo agregado → ``Avaliacao``."""

    kind: AvaliacaoUpsertKind
    avaliacao: Avaliacao | None = None
    conflict_tipo: str = ""


# ---------------------------------------------------------------------------
# US2 — resolução de FKs (lookup puro; órfãos reportados pelo caller)
# ---------------------------------------------------------------------------


def resolve_ciclo(solicitacao_id: str) -> Ciclo | None:
    """Lookup ``Ciclo`` por ``solides_id`` (= Identificador Solicitação).

    Miss → ``None`` (caller registra ``orfao_ciclo``). **Nunca** cria Ciclo.
    """
    sid = str(solicitacao_id or "").strip()
    if not sid:
        return None
    return Ciclo.objects.filter(solides_id=sid).first()


def resolve_usuario(avaliado_id: str, nome: str) -> CustomUser | None:
    """Resolve ``CustomUser`` do avaliado (research R9).

    1. Primário: ``CustomUser.solides_id == avaliado_id``.
    2. Fallback (só se passo 1 falhar): match **único** por
       ``canonical_key(nome) == canonical_key(user.nome)``.
    3. Miss / ambíguo → ``None`` (caller registra ``orfao_usuario``).

    Usuário inativo é permitido. **Nunca** inventa User nem altera
    ``solides_id`` do existente.
    """
    sid = str(avaliado_id or "").strip()
    if sid:
        by_id = CustomUser.objects.filter(solides_id=sid).first()
        if by_id is not None:
            return by_id

    return _lookup_user_by_canonical_key_unique(nome)


def _lookup_user_by_canonical_key_unique(nome: str) -> CustomUser | None:
    """Match único por ``canonical_key(nome)``; 0 ou >1 → ``None`` (R9).

    Inclui inativos (histórico). Não filtra ``is_active``.
    """
    key = canonical_key(nome) if nome else ""
    if not key:
        return None

    match: CustomUser | None = None
    for user in CustomUser.objects.only("id", "nome", "solides_id", "is_active").iterator():
        if not user.nome:
            continue
        if canonical_key(user.nome) != key:
            continue
        if match is not None:
            return None  # ambíguo
        match = user
    return match


def upsert_avaliacao_header(
    *,
    ciclo: Ciclo,
    usuario: CustomUser,
    solides_id: str,
    report: ImportReport | None = None,
) -> AvaliacaoUpsertResult:
    """Cria/atualiza ``Avaliacao`` terminal por ``(ciclo, usuario)`` (R10/R11).

    Persistência direta: ``etapa=feedback``, ``concluida=True``,
    ``solides_id`` canônico. **Não** altera ``nota_final_*`` nem cria
    ``AvaliacaoCompetencia``. **Não** chama ``advance_stage`` / open/close.

    Conflitos não-fatais:
    - ``solides_id_divergente`` — par já tem outro ``solides_id`` non-null
    - ``solides_id_avaliacao_em_uso`` — canônico já pertence a outra Avaliacao
    """
    canonical = str(solides_id or "").strip()
    if not canonical:
        _record_avaliacao_conflito(
            report,
            tipo="identificador_canonico_ausente",
            canonical="",
            ciclo=ciclo,
            usuario=usuario,
        )
        return AvaliacaoUpsertResult(
            kind="conflict",
            conflict_tipo="identificador_canonico_ausente",
        )

    existing_pair = Avaliacao.objects.filter(
        ciclo=ciclo, usuario=usuario
    ).first()
    existing_by_sid = Avaliacao.objects.filter(solides_id=canonical).first()

    if existing_pair is not None:
        return _upsert_existing_avaliacao_pair(
            existing_pair,
            existing_by_sid=existing_by_sid,
            canonical=canonical,
            ciclo=ciclo,
            usuario=usuario,
            report=report,
        )

    if existing_by_sid is not None:
        _record_avaliacao_conflito(
            report,
            tipo="solides_id_avaliacao_em_uso",
            canonical=canonical,
            ciclo=ciclo,
            usuario=usuario,
        )
        return AvaliacaoUpsertResult(
            kind="conflict",
            conflict_tipo="solides_id_avaliacao_em_uso",
            avaliacao=existing_by_sid,
        )

    return _create_avaliacao_header(
        ciclo=ciclo,
        usuario=usuario,
        solides_id=canonical,
        report=report,
    )


def _upsert_existing_avaliacao_pair(
    existing: Avaliacao,
    *,
    existing_by_sid: Avaliacao | None,
    canonical: str,
    ciclo: Ciclo,
    usuario: CustomUser,
    report: ImportReport | None,
) -> AvaliacaoUpsertResult:
    """Update/inalterado/conflito quando já existe Avaliacao no par."""
    current_sid = (existing.solides_id or "").strip()
    if current_sid and current_sid != canonical:
        _record_avaliacao_conflito(
            report,
            tipo="solides_id_divergente",
            canonical=canonical,
            ciclo=ciclo,
            usuario=usuario,
            motivo=f"existente={current_sid}",
        )
        return AvaliacaoUpsertResult(
            kind="conflict",
            conflict_tipo="solides_id_divergente",
            avaliacao=existing,
        )

    if existing_by_sid is not None and existing_by_sid.pk != existing.pk:
        _record_avaliacao_conflito(
            report,
            tipo="solides_id_avaliacao_em_uso",
            canonical=canonical,
            ciclo=ciclo,
            usuario=usuario,
        )
        return AvaliacaoUpsertResult(
            kind="conflict",
            conflict_tipo="solides_id_avaliacao_em_uso",
            avaliacao=existing,
        )

    desired_etapa = Avaliacao.Etapa.FEEDBACK
    desired_concluida = True
    unchanged = (
        existing.etapa == desired_etapa
        and existing.concluida is True
        and current_sid == canonical
    )
    if unchanged:
        if report is not None:
            note_avaliacao_inalterada(report)
        return AvaliacaoUpsertResult(kind="unchanged", avaliacao=existing)

    # Não tocar nota_final_* — só cabeçalho terminal + solides_id.
    existing.etapa = desired_etapa
    existing.concluida = desired_concluida
    existing.solides_id = canonical
    try:
        existing.full_clean()
        existing.save()
    except ValidationError:
        _record_avaliacao_conflito(
            report,
            tipo="validacao_avaliacao",
            canonical=canonical,
            ciclo=ciclo,
            usuario=usuario,
        )
        return AvaliacaoUpsertResult(
            kind="conflict",
            conflict_tipo="validacao_avaliacao",
            avaliacao=existing,
        )

    if report is not None:
        note_avaliacao_atualizada(report)
    return AvaliacaoUpsertResult(kind="updated", avaliacao=existing)


def _create_avaliacao_header(
    *,
    ciclo: Ciclo,
    usuario: CustomUser,
    solides_id: str,
    report: ImportReport | None,
) -> AvaliacaoUpsertResult:
    """Create Avaliacao em estado terminal; nota_final_* permanecem null."""
    avaliacao = Avaliacao(
        ciclo=ciclo,
        usuario=usuario,
        solides_id=solides_id,
        etapa=Avaliacao.Etapa.FEEDBACK,
        concluida=True,
    )
    try:
        avaliacao.full_clean()
        avaliacao.save()
    except ValidationError:
        _record_avaliacao_conflito(
            report,
            tipo="validacao_avaliacao",
            canonical=solides_id,
            ciclo=ciclo,
            usuario=usuario,
        )
        return AvaliacaoUpsertResult(
            kind="conflict",
            conflict_tipo="validacao_avaliacao",
        )

    if report is not None:
        note_avaliacao_criada(report)
    return AvaliacaoUpsertResult(kind="created", avaliacao=avaliacao)


def _record_avaliacao_conflito(
    report: ImportReport | None,
    *,
    tipo: str,
    canonical: str,
    ciclo: Ciclo,
    usuario: CustomUser,
    motivo: str = "",
) -> None:
    """Conflito não-fatal de cabeçalho (R7/R11) — amostra no relatório."""
    if report is None:
        return
    extras = [
        f"canonical={canonical}" if canonical else "",
        f"ciclo={ciclo.solides_id or ciclo.pk}",
        f"usuario={usuario.solides_id or usuario.pk}",
    ]
    record_conflito(
        report,
        tipo=tipo,
        extra=" | ".join(part for part in extras if part),
        motivo=motivo,
    )


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
