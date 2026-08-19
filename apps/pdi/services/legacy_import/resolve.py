"""Resolução de colaborador, digest, concatenação e de-para de status.

T002: stubs. Corpos em T007 (concat/digest/de-para US1) e T011 (ID/órfão US2).

Denylist intacta — **não** chama ``get_visible_users`` / ``user_in_scope`` /
``ScopedObjectMixin``; **não** inventa ``CustomUser``; **não** usa
``line_manager`` como responsável; **não** importa openpyxl.
"""

from __future__ import annotations

from datetime import date
from typing import Any


def concat_acao_descricao(
    objetivo: str,
    situacao_atual: str,
    situacao_desejada: str,
) -> str:
    """Concatena trechos não vazios com ``\\n\\n`` (FR-005).

    Três trechos vazios → conflito ``descricao_vazia`` (implementação T007).
    """
    raise NotImplementedError("T007: concatenação FR-005")


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
    raise NotImplementedError("T007: digest R-digest")


def map_pdi_status(status_legado: str) -> str:
    """De-para FR-010: ``finalizado``→``concluido``, ``em_andamento``→``ativo``.

    Status desconhecido → conflito. **Nunca** ``arquivado``.
    """
    raise NotImplementedError("T007: de-para PDI FR-010")


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
    raise NotImplementedError("T007: de-para ação FR-011")


def acao_natural_key(descricao: str, prazo: date) -> tuple[str, date]:
    """Chave natural da ação: ``(display_name(descricao), prazo)`` (+ ``pdi_id`` no persist)."""
    raise NotImplementedError("T007: chave natural da ação")


def resolve_usuario(
    *,
    nome: str,
    solides_id: str | None = None,
) -> Any:
    """Match único de colaborador (incl. inativos). T011 completa a matriz ID/órfão.

    **NUNCA** ``get_or_create`` User. **NUNCA** escolher o primeiro em 2+.
    """
    raise NotImplementedError("T007/T011: resolução de colaborador")
