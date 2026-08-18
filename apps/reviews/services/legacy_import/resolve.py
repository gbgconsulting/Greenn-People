"""Resolução de avaliação canônica, competência, autor e ciclo aberto.

US1 (T007) — mapa em memória via ``parse_avaliacoes_headers_xlsx`` +
IMPORTAR ``aggregate_avaliacao_headers`` (não copiar);
``resolve_avaliacao`` na ordem canônico → mapa → órfão
(``contracts/collapsed-id-resolution.md``); skip se ciclo ``aberto`` (R10);
``is_auto`` via ``canonical_key`` (R5); ``resolve_competencia`` por
``Competencia.solides_id`` e create mínima (R11). **NUNCA**
``get_or_create(ciclo=..., usuario=...)``. **NUNCA** inventar
``Avaliacao`` / ``Ciclo`` / ``User``.

US2 (T012) — ``resolve_autor``: ``CustomUser.solides_id``; fallback match
único ``canonical_key(Nome Avaliador)``; inativo permitido; senão órfão.

Denylist intacta — **não** chama ``open_cycle`` / ``close_cycle`` /
``advance_stage`` / approval / ``create_competency_lines``; **não** importa
``get_open_ciclo`` de ``goals``.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from apps.accounts.services.legacy_import.parse_xlsx import (
    canonicalize_id,
    parse_avaliacoes_headers_xlsx,
)
from apps.competencies.models import Competencia
from apps.competencies.services.catalog_import.importer import resolve_default_escala
from apps.competencies.services.catalog_import.mapping import (
    is_ambiguous,
    is_kpi,
    map_grupo_tipo,
)
from apps.competencies.services.catalog_import.normalize import (
    canonical_key,
    display_name,
)
from apps.cycles.models import Ciclo
from apps.cycles.services.legacy_import.aggregate import aggregate_avaliacao_headers
from apps.reviews.models import Avaliacao


@dataclass(frozen=True)
class AvaliacaoResolveResult:
    """Lookup de ``Avaliacao`` canônica — nunca cria cabeçalho.

    ``via_collapsed`` é True somente quando o passo (2) do contrato
    (mapa colapsado → canônico) foi o que resolveu — handoff para
    ``ids_colapsados_resolvidos``.
    """

    avaliacao: Avaliacao | None
    via_collapsed: bool = False


@dataclass(frozen=True)
class CompetenciaResolveResult:
    """Lookup / create mínima de ``Competencia`` (R11).

    ``created`` alimenta ``habilidades_extras_criadas``. Órfão →
    ``competencia is None`` (KPI, ambíguo, id/nome vazio, unique nome).
    """

    competencia: Competencia | None
    created: bool = False


def build_collapsed_id_map(avaliacoes_path: str | Path) -> dict[str, str]:
    """Rebuild ``legado_id → canonical_id`` em memória (R3 / T007).

    Consome ``parse_avaliacoes_headers_xlsx`` + ``aggregate_avaliacao_headers``.
    **PROIBIDO** persistir tabela de mapa; **PROIBIDO** copiar ``aggregate.py``.
    **PROIBIDO** upsert de ``Avaliacao`` a partir deste arquivo.
    """
    parsed = parse_avaliacoes_headers_xlsx(avaliacoes_path)
    groups = aggregate_avaliacao_headers(parsed.rows)
    mapa: dict[str, str] = {}
    for group in groups:
        mapa[group.canonical_id] = group.canonical_id
        for cid in group.collapsed_ids:
            mapa[cid] = group.canonical_id
    return mapa


def resolve_avaliacao(
    identificador: str,
    mapa: Mapping[str, str],
) -> AvaliacaoResolveResult:
    """Resolve ``Avaliacao`` canônica: solides_id → mapa colapsado → órfão.

    Ordem (collapsed-id-resolution): lookup direto; senão ``mapa``; senão
    ``avaliacao=None`` (órfão). **NUNCA** inventar cabeçalho.
    **NUNCA** ``get_or_create(ciclo=..., usuario=...)``.
    """
    sid = canonicalize_id(identificador)
    if not sid:
        return AvaliacaoResolveResult(avaliacao=None)

    found = (
        Avaliacao.objects.select_related("ciclo")
        .filter(solides_id=sid)
        .first()
    )
    if found is not None:
        return AvaliacaoResolveResult(avaliacao=found, via_collapsed=False)

    canonical = canonicalize_id(mapa.get(sid, ""))
    if not canonical:
        return AvaliacaoResolveResult(avaliacao=None)

    found = (
        Avaliacao.objects.select_related("ciclo")
        .filter(solides_id=canonical)
        .first()
    )
    if found is None:
        return AvaliacaoResolveResult(avaliacao=None)
    return AvaliacaoResolveResult(avaliacao=found, via_collapsed=True)


def is_ciclo_aberto(avaliacao: Avaliacao) -> bool:
    """True se ``avaliacao.ciclo.status == aberto`` (R10).

    Skip da linha; **não** importar ``get_open_ciclo``.
    """
    return avaliacao.ciclo.status == Ciclo.Status.ABERTO


def is_auto(nome_avaliador: str, nome_avaliado: str) -> bool:
    """True se nomes canônicos coincidem e ambos não-vazios (R5).

    Reusa ``canonical_key`` da 003 — **não copiar**.
    """
    key_avaliado = canonical_key(nome_avaliado) if nome_avaliado else ""
    if not key_avaliado:
        return False
    key_avaliador = canonical_key(nome_avaliador) if nome_avaliador else ""
    return bool(key_avaliador) and key_avaliador == key_avaliado


def resolve_competencia(
    habilidade_id: str,
    habilidade_nome: str = "",
    *,
    grupo: str = "",
) -> CompetenciaResolveResult:
    """Resolve ``Competencia`` por ``solides_id``; create mínima (R11) se ok.

    Extras: ``display_name``, ``not is_kpi``, ``not is_ambiguous``,
    ``resolve_default_escala``, tipo ``map_grupo_tipo`` se ``grupo``
    (``--habilidades``) senão ``tecnica``. Zero ``CargoCompetencia``.
    """
    sid = canonicalize_id(habilidade_id)
    if not sid:
        return CompetenciaResolveResult(competencia=None)

    existing = Competencia.objects.filter(solides_id=sid).first()
    if existing is not None:
        return CompetenciaResolveResult(competencia=existing, created=False)

    nome = display_name(habilidade_nome) if habilidade_nome else ""
    if not nome:
        return CompetenciaResolveResult(competencia=None)
    if is_kpi(nome) or is_ambiguous(nome):
        return CompetenciaResolveResult(competencia=None)

    if Competencia.objects.filter(nome=nome, is_active=True).exists():
        return CompetenciaResolveResult(competencia=None)

    mapped = map_grupo_tipo(grupo) if grupo else None
    tipo = mapped if mapped else Competencia.Tipo.TECNICA
    escala = resolve_default_escala()

    competencia = Competencia(
        nome=nome,
        descricao="",
        tipo=tipo,
        escala=escala,
        is_active=True,
        solides_id=sid,
    )
    try:
        with transaction.atomic():
            competencia.full_clean()
            competencia.save()
    except (ValidationError, IntegrityError):
        return CompetenciaResolveResult(competencia=None)

    return CompetenciaResolveResult(competencia=competencia, created=True)


def resolve_autor(avaliador_id: str, nome_avaliador: str = "") -> Any:
    """Resolve autor do comentário: ``solides_id`` → nome canônico único.

    Inativo (010) permitido. Irresolvível → ``None`` (órfão). **Nunca**
    inventar ``User``. Corpo em T012.
    """
    raise NotImplementedError("T002 stub — implementar em T012")
