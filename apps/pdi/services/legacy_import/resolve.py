"""Resolução de colaborador, digest, concatenação e de-para de status.

T007: concatenação FR-005, digest R-digest, de-para FR-010/FR-011,
chave natural da ação e match único por ``canonical_key(Nome)``.
T011 completa a matriz ID / ``id_vs_nome`` / órfão.

Denylist intacta — **não** chama ``get_visible_users`` / ``user_in_scope`` /
``ScopedObjectMixin``; **não** inventa ``CustomUser``; **não** usa
``line_manager`` como responsável; **não** importa openpyxl.
"""

from __future__ import annotations

import hashlib
from datetime import date, timezone as dt_timezone
from typing import Any

from django.utils import timezone

from apps.accounts.models import CustomUser
from apps.accounts.services.legacy_import.dates import parse_legacy_datetime
from apps.competencies.services.catalog_import.normalize import (
    canonical_key,
    display_name,
)
from apps.pdi.models import AcaoPDI, PDI

_PDI_STATUS_DE_PARA = {
    "finalizado": PDI.Status.CONCLUIDO,
    "em_andamento": PDI.Status.ATIVO,
}

_TITULO_MAX_LENGTH = PDI._meta.get_field("titulo").max_length


class ResolveConflict(Exception):
    """Conflito não-fatal de linha (caller registra no relatório e faz skip)."""

    def __init__(self, tipo: str) -> None:
        self.tipo = tipo
        super().__init__(tipo)


def _cell_text(value: Any) -> str:
    """Texto cru de célula para ``display_name`` / ``canonical_key``."""
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return str(value)


def concat_acao_descricao(
    objetivo: str,
    situacao_atual: str,
    situacao_desejada: str,
) -> str:
    """Concatena trechos não vazios com ``\\n\\n`` (FR-005).

    Ordem fixa: Objetivo → Situação Atual → Situação Desejada.
    Três trechos vazios (após ``display_name``) → ``descricao_vazia``.
    """
    trechos = [
        display_name(_cell_text(objetivo)),
        display_name(_cell_text(situacao_atual)),
        display_name(_cell_text(situacao_desejada)),
    ]
    descricao = "\n\n".join(t for t in trechos if t)
    if not descricao:
        raise ResolveConflict("descricao_vazia")
    return descricao


def normalize_pdi_titulo(titulo: Any) -> str:
    """``display_name`` do título; vazio → ``titulo_ausente``; ``len>200`` → conflito.

    **Não** trunca. Limite alinhado a ``PDI.titulo`` (schema vigente).
    """
    normalized = display_name(_cell_text(titulo))
    if not normalized:
        raise ResolveConflict("titulo_ausente")
    if len(normalized) > _TITULO_MAX_LENGTH:
        raise ResolveConflict("titulo_excede_limite")
    return normalized


def _criado_em_utc_iso(criado_em: Any) -> str | None:
    """ISO UTC de ``Criado em`` se parseável; ausente/ilegível → ``None``."""
    try:
        parsed = parse_legacy_datetime(criado_em)
    except (TypeError, ValueError):
        return None
    if parsed is None:
        return None
    if timezone.is_naive(parsed):
        parsed = parsed.replace(tzinfo=dt_timezone.utc)
    else:
        parsed = parsed.astimezone(dt_timezone.utc)
    return parsed.isoformat()


def build_pdi_digest(
    nome: str,
    titulo: str,
    criado_em: Any | None = None,
) -> str:
    """Digest curto ``pdi_`` + sha256 hex[:40] para ``PDI.solides_id`` (R-digest).

    Material: ``canonical_key(Nome)`` + ``\\n`` + ``display_name(título)``
    [+ ``\\n`` + ISO UTC de ``Criado em`` se parseável]. Nunca persiste
    nome/título em claro no ID.
    """
    material = (
        canonical_key(_cell_text(nome))
        + "\n"
        + display_name(_cell_text(titulo))
    )
    criado_iso = _criado_em_utc_iso(criado_em)
    if criado_iso:
        material += "\n" + criado_iso
    digest40 = hashlib.sha256(material.encode("utf-8")).hexdigest()[:40]
    return f"pdi_{digest40}"


def map_pdi_status(status_legado: str) -> str:
    """De-para FR-010: ``finalizado``→``concluido``, ``em_andamento``→``ativo``.

    Status desconhecido (incl. vazio / arquivado legado) → ``status_desconhecido``.
    **Nunca** ``arquivado``.
    """
    key = display_name(_cell_text(status_legado)).casefold()
    mapped = _PDI_STATUS_DE_PARA.get(key)
    if mapped is None:
        raise ResolveConflict("status_desconhecido")
    return mapped


def map_acao_status(
    *,
    pdi_status: str,
    prazo: date,
    data_carga: date,
) -> str:
    """Status da ação FR-011 **antes** do ``save``.

    ``concluida`` / ``atrasada`` / ``pendente``. Nunca ``em_andamento`` de ação.
    ``data_carga`` = ``timezone.localdate()`` congelada no início da carga.
    """
    if pdi_status == PDI.Status.CONCLUIDO:
        return AcaoPDI.Status.CONCLUIDA
    if pdi_status == PDI.Status.ATIVO:
        if prazo < data_carga:
            return AcaoPDI.Status.ATRASADA
        return AcaoPDI.Status.PENDENTE
    raise ResolveConflict("status_desconhecido")


def acao_natural_key(descricao: str, prazo: date) -> tuple[str, date]:
    """Chave natural da ação: ``(display_name(descricao), prazo)`` (+ ``pdi_id`` no persist)."""
    return display_name(_cell_text(descricao)), prazo


def resolve_usuario(
    *,
    nome: str,
    solides_id: str | None = None,
) -> CustomUser | None:
    """Match único de colaborador (incl. inativos). T011 completa a matriz ID/órfão.

    **NUNCA** ``get_or_create`` User. **NUNCA** escolher o primeiro em 2+.
    ``solides_id`` é aceito na assinatura e ignorado até T011.
    """
    _ = solides_id  # T011: unique hit em CustomUser.solides_id + id_vs_nome
    return _lookup_user_by_canonical_key_unique(nome)


def _lookup_user_by_canonical_key_unique(nome: str) -> CustomUser | None:
    """Match único por ``canonical_key(nome)``; 0 ou >1 → ``None``.

    Inclui inativos. Não filtra ``is_active``. Não usa ``line_manager``.
    """
    key = canonical_key(_cell_text(nome)) if nome else ""
    if not key:
        return None

    match: CustomUser | None = None
    for user in CustomUser.objects.only("id", "nome", "solides_id", "is_active").iterator():
        if not user.nome:
            continue
        if canonical_key(user.nome) != key:
            continue
        if match is not None:
            return None
        match = user
    return match
