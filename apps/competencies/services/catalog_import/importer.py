"""Persistência e orquestração da importação do catálogo legado.

T007: resolução da escala padrão 1–5 (research R9).
T008: upsert de ``organization.Cargo`` por chave canônica.
T009: upsert de ``competencies.Competencia`` (somente avaliáveis).
T010: ``import_catalog`` — parse → persist (Escala → Cargos → Competências).
Vínculos CargoCompetencia: T014/T015.
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from django.db import transaction

from apps.competencies.models import Competencia, Escala
from apps.organization.models import Cargo

from .mapping import classify_competencia, infer_cargo_nivel
from .normalize import canonical_key, display_name
from .parse import CompetenciaRow, parse_catalog
from .report import ImportReport, ReportEntry

DEFAULT_ESCALA_NOME = "Escala padrão 1-5"
DEFAULT_ESCALA_MIN = 1
DEFAULT_ESCALA_MAX = 5


class EscalaInativaError(Exception):
    """Escala padrão existe apenas inativa — conflito fatal (R9).

    Não reativar nem criar duplicata semântica; o caller deve registrar
    ``conflitos`` com ``motivo=escala_inativa`` e abortar (exit 1).
    ``report`` é preenchido por ``import_catalog`` quando o conflito
    ocorre no pipeline (para o command emitir o relatório antes do exit 1).
    """

    def __init__(
        self,
        nome: str = DEFAULT_ESCALA_NOME,
        *,
        report: ImportReport | None = None,
    ) -> None:
        self.nome = nome
        self.report = report
        super().__init__(
            f"Escala '{nome}' existe apenas inativa; "
            "não será reativada nem duplicada (escala_inativa)."
        )


def resolve_default_escala() -> Escala:
    """Reutiliza ou cria a escala ativa ``Escala padrão 1-5``.

    Ordem (research R9 / contrato §7):
    1. Ativa com esse nome → reutilizar.
    2. Só inativa com esse nome → ``EscalaInativaError`` (não reativar,
       não criar duplicata).
    3. Ausente → criar ``valor_minimo=1``, ``valor_maximo=5``, ativa.
    """
    ativa = Escala.objects.filter(
        nome=DEFAULT_ESCALA_NOME,
        is_active=True,
    ).first()
    if ativa is not None:
        return ativa

    if Escala.objects.filter(
        nome=DEFAULT_ESCALA_NOME,
        is_active=False,
    ).exists():
        raise EscalaInativaError(DEFAULT_ESCALA_NOME)

    return Escala.objects.create(
        nome=DEFAULT_ESCALA_NOME,
        valor_minimo=DEFAULT_ESCALA_MIN,
        valor_maximo=DEFAULT_ESCALA_MAX,
        is_active=True,
    )


def _build_cargo_index() -> dict[str, Cargo]:
    """Indexa cargos por ``canonical_key``; ativo sobrescreve inativo."""
    index: dict[str, Cargo] = {}
    for cargo in Cargo.objects.filter(is_active=False).iterator():
        index[canonical_key(cargo.nome)] = cargo
    for cargo in Cargo.objects.filter(is_active=True).iterator():
        index[canonical_key(cargo.nome)] = cargo
    return index


def upsert_cargo(
    nome: str,
    report: ImportReport,
    *,
    index: dict[str, Cargo] | None = None,
) -> Cargo | None:
    """Cria ou atualiza ``Cargo`` ativo por chave canônica (§9 / research R10).

    - Ativo com mesma chave → atualiza ``nome``/``nivel`` se diferirem.
    - Inativo com mesma chave → conflito ``inativo_existente``; não reativa.
    - Sem match → create ``is_active=True`` com ``nivel`` via ``infer_cargo_nivel``.

    Returns:
        Instância ativa criada/atualizada/inalterada, ou ``None`` se skip
        (nome vazio ou conflito com inativo).
    """
    display = display_name(nome)
    if not display:
        return None

    key = canonical_key(display)
    nivel = infer_cargo_nivel(display)

    if index is not None:
        existing = index.get(key)
    else:
        existing = _build_cargo_index().get(key)

    if existing is not None:
        if not existing.is_active:
            report.conflitos.append(
                ReportEntry(
                    label="cargo",
                    extra=display,
                    motivo="inativo_existente",
                )
            )
            return None

        changed = False
        if existing.nivel != nivel:
            existing.nivel = nivel
            changed = True
        if existing.nome != display:
            existing.nome = display
            changed = True
        if changed:
            existing.save(update_fields=["nome", "nivel", "updated_at"])
            report.cargos_atualizados += 1
        else:
            report.cargos_inalterados += 1
        return existing

    cargo = Cargo.objects.create(nome=display, nivel=nivel, is_active=True)
    report.cargos_criados += 1
    if index is not None:
        index[key] = cargo
    return cargo


def upsert_cargos(
    nomes: Iterable[str],
    report: ImportReport,
) -> dict[str, Cargo]:
    """Upsert em lote; deduplica por chave canônica (primeira grafia vence).

    Returns:
        Mapa ``canonical_key`` → ``Cargo`` ativo resolvido (criado/atualizado/
        inalterado). Chaves com conflito de inativo não entram no mapa.
    """
    index = _build_cargo_index()
    resolved: dict[str, Cargo] = {}
    seen_keys: set[str] = set()

    for nome in nomes:
        display = display_name(nome)
        if not display:
            continue
        key = canonical_key(display)
        if key in seen_keys:
            continue
        seen_keys.add(key)

        cargo = upsert_cargo(display, report, index=index)
        if cargo is not None:
            resolved[key] = cargo

    return resolved


def _build_competencia_index() -> dict[str, Competencia]:
    """Indexa competências por ``canonical_key``; ativo sobrescreve inativo."""
    index: dict[str, Competencia] = {}
    for competencia in Competencia.objects.filter(is_active=False).iterator():
        index[canonical_key(competencia.nome)] = competencia
    for competencia in Competencia.objects.filter(is_active=True).iterator():
        index[canonical_key(competencia.nome)] = competencia
    return index


def upsert_competencia(
    nome: str,
    tipo: str,
    descricao: str,
    escala: Escala,
    report: ImportReport,
    *,
    index: dict[str, Competencia] | None = None,
) -> Competencia | None:
    """Cria ou atualiza ``Competencia`` ativa por chave canônica (§9 / R10).

    Caller MUST passar apenas itens já classificados como avaliáveis
    (``tipo`` mapeado). Soft-delete: inativo com mesma chave → conflito
    ``inativo_existente``; não reativa.

    Returns:
        Instância ativa criada/atualizada/inalterada, ou ``None`` se skip
        (nome vazio ou conflito com inativo).
    """
    display = display_name(nome)
    if not display:
        return None

    key = canonical_key(display)
    desc = display_name(descricao)

    if index is not None:
        existing = index.get(key)
    else:
        existing = _build_competencia_index().get(key)

    if existing is not None:
        if not existing.is_active:
            report.conflitos.append(
                ReportEntry(
                    label="competencia",
                    extra=display,
                    motivo="inativo_existente",
                )
            )
            return None

        changed = False
        if existing.nome != display:
            existing.nome = display
            changed = True
        if existing.descricao != desc:
            existing.descricao = desc
            changed = True
        if existing.tipo != tipo:
            existing.tipo = tipo
            changed = True
        if existing.escala_id != escala.pk:
            existing.escala = escala
            changed = True
        if changed:
            existing.save(
                update_fields=["nome", "descricao", "tipo", "escala", "updated_at"]
            )
            report.competencias_atualizadas += 1
        else:
            report.competencias_inalteradas += 1
        return existing

    competencia = Competencia.objects.create(
        nome=display,
        descricao=desc,
        tipo=tipo,
        escala=escala,
        is_active=True,
    )
    report.competencias_criadas += 1
    if index is not None:
        index[key] = competencia
    return competencia


def upsert_competencias(
    rows: Iterable[CompetenciaRow],
    escala: Escala,
    report: ImportReport,
) -> dict[str, Competencia]:
    """Classifica linhas e faz upsert só das avaliáveis; dedupe por chave.

    KPI → ``excluidos_kpi``; ambíguos/grupo desconhecido → ``nao_mapeados``.
    Primeira grafia por ``canonical_key`` vence (fonte: lista-competencias).

    Returns:
        Mapa ``canonical_key`` → ``Competencia`` ativa resolvida.
        Chaves KPI/não mapeadas/conflito inativo não entram no mapa.
    """
    index = _build_competencia_index()
    resolved: dict[str, Competencia] = {}
    seen_keys: set[str] = set()

    for row in rows:
        display = display_name(row.nome)
        if not display:
            continue
        key = canonical_key(display)
        if key in seen_keys:
            continue
        seen_keys.add(key)

        classification = classify_competencia(display, row.grupo)
        if classification.kind == "excluidos_kpi":
            report.excluidos_kpi.append(
                ReportEntry(label=display, motivo=classification.motivo)
            )
            continue
        if classification.kind == "nao_mapeados":
            report.nao_mapeados.append(
                ReportEntry(label=display, motivo=classification.motivo)
            )
            continue

        if classification.tipo is None:
            report.nao_mapeados.append(
                ReportEntry(label=display, motivo="grupo_desconhecido")
            )
            continue

        competencia = upsert_competencia(
            display,
            classification.tipo,
            row.descricao,
            escala,
            report,
            index=index,
        )
        if competencia is not None:
            resolved[key] = competencia

    return resolved


def import_catalog(
    cargos_path: str | Path,
    competencias_path: str | Path,
    *,
    dry_run: bool = False,
) -> ImportReport:
    """Orquestra parse → persistência do catálogo legado (US1 / research R11).

    1. **Parse** (sem DB): valida arquivos/colunas; monta estruturas em memória.
       ``CatalogParseError`` propaga (exit 1 no command; zero writes).
    2. **Persist** em ``transaction.atomic()``: Escala → Cargos → Competências.
       ``EscalaInativaError`` → conflito ``escala_inativa`` + re-raise (rollback).
    3. ``dry_run``: mesma lógica com ``set_rollback(True)`` (zero commit).

    Cargos: nomes de ``lista-cargos`` primeiro (preferência de display), depois
    cargos referenciados em ``lista-competencias``. Competências: só da fonte
    ``lista-competencias``. Vínculos: T015.
    """
    parsed = parse_catalog(cargos_path, competencias_path)
    report = ImportReport(
        modo="dry-run" if dry_run else "persist",
        cargos_file=parsed.cargos_path,
        competencias_file=parsed.competencias_path,
    )

    cargo_names: list[str] = [row.nome for row in parsed.cargos]
    for row in parsed.competencias:
        cargo_names.extend(row.cargos)

    with transaction.atomic():
        try:
            escala = resolve_default_escala()
        except EscalaInativaError as exc:
            report.conflitos.append(
                ReportEntry(
                    label="escala",
                    extra=exc.nome,
                    motivo="escala_inativa",
                )
            )
            raise EscalaInativaError(exc.nome, report=report) from exc

        upsert_cargos(cargo_names, report)
        upsert_competencias(parsed.competencias, escala, report)

        if dry_run:
            transaction.set_rollback(True)

    return report
