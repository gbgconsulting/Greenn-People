"""Persistência e orquestração da importação do catálogo legado.

T007: resolução da escala padrão 1–5 (research R9).
T008: upsert de ``organization.Cargo`` por chave canônica.
T009: upsert de ``competencies.Competencia`` (somente avaliáveis).
T010: ``import_catalog`` — parse → persist (Escala → Cargos → Competências).
T014: upsert de ``competencies.CargoCompetencia`` (peso=1, nivel_esperado).
T015: reconcile + vínculos no pipeline após cargos/competências.
T018: seções Excluídos KPI / Não mapeados (classificação parse → relatório).
T019: lookup ``canonical_key`` — ativo (update/noop) vs inativo
      (``inativo_existente``, skip create) para Cargo e Competencia (§9 / R10).
T020: ``dry_run`` — parse + totais projetados com ``set_rollback``
      (zero commit); códigos de saída no command (0/1).
T021: falhas fatais pré-persistência — ``CatalogParseError`` (parse) e
      ``EscalaInativaError`` (escala inativa) → exit 1 + rollback atomic.
T022: ``merged`` — grafias distintas com mesma ``canonical_key``
      (``CanonicalNameIndex`` / seção Merged no relatório).
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from decimal import Decimal
from pathlib import Path
from typing import Literal, TypeVar

from django.db import transaction
from django.db.models import Model

from apps.competencies.models import CargoCompetencia, Competencia, Escala
from apps.organization.models import Cargo

from .mapping import infer_cargo_nivel, nivel_esperado_for
from .normalize import CanonicalNameIndex, canonical_key, display_name
from .parse import (
    CompetenciaRow,
    classify_competencia_rows,
    parse_catalog,
)
from .reconcile import (
    CatalogPair,
    avaliavel_competencia_keys,
    extract_pairs_vista_a,
    extract_pairs_vista_b,
    reconcile_matrix,
)
from .report import (
    ImportReport,
    ReportEntry,
    extend_excluidos_kpi,
    extend_merged,
    extend_nao_mapeados,
    record_merged,
)

_T = TypeVar("_T", bound=Model)
_MatchKind = Literal["active", "inactive", "missing"]

DEFAULT_ESCALA_NOME = "Escala padrão 1-5"
DEFAULT_ESCALA_MIN = 1
DEFAULT_ESCALA_MAX = 5
DEFAULT_VINCULO_PESO = Decimal("1")


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


def _lookup_by_canonical_key(
    index: Mapping[str, _T],
    key: str,
) -> tuple[_T | None, _MatchKind]:
    """Resolve match por ``canonical_key`` nos três ramos do contrato §9.

    Returns:
        ``(entity, "active")`` — update/noop no registro ativo.
        ``(entity, "inactive")`` — soft-delete: conflito, não reativar,
        não criar duplicata ativa.
        ``(None, "missing")`` — create ``is_active=True``.
    """
    existing = index.get(key)
    if existing is None:
        return None, "missing"
    if existing.is_active:
        return existing, "active"
    return existing, "inactive"


def _record_inativo_existente(
    report: ImportReport,
    *,
    tipo: Literal["cargo", "competencia"],
    nome: str,
) -> None:
    """Registra conflito de soft-delete (motivo ``inativo_existente``)."""
    report.conflitos.append(
        ReportEntry(
            label=tipo,
            extra=nome,
            motivo="inativo_existente",
        )
    )


def upsert_cargo(
    nome: str,
    report: ImportReport,
    *,
    index: dict[str, Cargo] | None = None,
) -> Cargo | None:
    """Cria ou atualiza ``Cargo`` ativo por chave canônica (§9 / research R10).

    Ramos (T019):
    - Ativo com mesma chave → atualiza ``nome``/``nivel`` se diferirem.
    - Inativo com mesma chave → conflito ``inativo_existente``; não reativa;
      não cria ativo duplicado.
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
    resolved_index = index if index is not None else _build_cargo_index()
    existing, kind = _lookup_by_canonical_key(resolved_index, key)

    if kind == "inactive":
        _record_inativo_existente(report, tipo="cargo", nome=display)
        return None

    if kind == "active":
        assert existing is not None
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

    Grafias distintas com a mesma chave são registradas em ``merged``.

    Returns:
        Mapa ``canonical_key`` → ``Cargo`` ativo resolvido (criado/atualizado/
        inalterado). Chaves com conflito de inativo não entram no mapa.
    """
    index = _build_cargo_index()
    resolved: dict[str, Cargo] = {}
    name_index = CanonicalNameIndex()

    for nome in nomes:
        observed = name_index.observe(nome)
        if observed is None:
            continue
        if observed.merge is not None:
            record_merged(
                report,
                observed.merge.nome_a,
                observed.merge.nome_b,
                observed.merge.chave,
            )
        if not observed.is_first:
            continue

        cargo = upsert_cargo(observed.display, report, index=index)
        if cargo is not None:
            resolved[observed.key] = cargo

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
    (``tipo`` mapeado).

    Ramos (T019):
    - Ativo → update campos divergentes / noop (inalterada).
    - Inativo → conflito ``inativo_existente``; não reativa; não cria.
    - Sem match → create ``is_active=True``.

    Returns:
        Instância ativa criada/atualizada/inalterada, ou ``None`` se skip
        (nome vazio ou conflito com inativo).
    """
    display = display_name(nome)
    if not display:
        return None

    key = canonical_key(display)
    desc = display_name(descricao)
    resolved_index = (
        index if index is not None else _build_competencia_index()
    )
    existing, kind = _lookup_by_canonical_key(resolved_index, key)

    if kind == "inactive":
        _record_inativo_existente(report, tipo="competencia", nome=display)
        return None

    if kind == "active":
        assert existing is not None
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
    """Classifica (parse §6) e faz upsert só das avaliáveis.

    Preenche seções ``Excluídos KPI``, ``Não mapeados`` e ``Merged`` via
    ``classify_competencia_rows`` (contadores = ``len`` das listas).
    Primeira grafia por ``canonical_key`` vence (lista-competencias).

    Returns:
        Mapa ``canonical_key`` → ``Competencia`` ativa resolvida.
        Chaves KPI/não mapeadas/conflito inativo não entram no mapa.
    """
    classified = classify_competencia_rows(rows)
    extend_excluidos_kpi(report, classified.excluidos_kpi)
    extend_nao_mapeados(report, classified.nao_mapeados)
    extend_merged(report, classified.merged)

    index = _build_competencia_index()
    resolved: dict[str, Competencia] = {}

    for item in classified.avaliaveis:
        key = canonical_key(item.row.nome)
        competencia = upsert_competencia(
            item.row.nome,
            item.tipo,
            item.row.descricao,
            escala,
            report,
            index=index,
        )
        if competencia is not None:
            resolved[key] = competencia

    return resolved


def upsert_cargo_competencia(
    cargo: Cargo,
    competencia: Competencia,
    report: ImportReport,
) -> CargoCompetencia:
    """Cria ou atualiza ``CargoCompetencia`` pelo par único (§4 / research R5).

    - ``peso`` sempre ``Decimal('1')``.
    - ``nivel_esperado`` via ``nivel_esperado_for(cargo.nivel)``.
    - Existente com mesmos valores → ``vinculos_inalterados``.
    - Existente divergente → atualiza e ``vinculos_atualizados``.
    - Ausente → create e ``vinculos_criados``.

    Equivale semanticamente a ``update_or_create(cargo=..., competencia=...)``
    com contagem explícita de inalterados (sem save desnecessário).
    """
    peso = DEFAULT_VINCULO_PESO
    nivel_esperado = Decimal(nivel_esperado_for(cargo.nivel))

    existing = CargoCompetencia.objects.filter(
        cargo=cargo,
        competencia=competencia,
    ).first()

    if existing is not None:
        changed = False
        if existing.nivel_esperado != nivel_esperado:
            existing.nivel_esperado = nivel_esperado
            changed = True
        if existing.peso != peso:
            existing.peso = peso
            changed = True
        if changed:
            existing.save(
                update_fields=["nivel_esperado", "peso", "updated_at"]
            )
            report.vinculos_atualizados += 1
        else:
            report.vinculos_inalterados += 1
        return existing

    vinculo = CargoCompetencia.objects.create(
        cargo=cargo,
        competencia=competencia,
        peso=peso,
        nivel_esperado=nivel_esperado,
    )
    report.vinculos_criados += 1
    return vinculo


def upsert_cargo_competencias(
    pairs: Iterable[CatalogPair],
    cargos: Mapping[str, Cargo],
    competencias: Mapping[str, Competencia],
    report: ImportReport,
) -> list[CargoCompetencia]:
    """Upsert em lote a partir da matriz reconciliada (chaves canônicas).

    Pares cuja ponta não está nos mapas resolvidos são ignorados (caller
    deve filtrar via ``reconcile_matrix``; este skip é defesa em profundidade).
    """
    result: list[CargoCompetencia] = []
    seen: set[tuple[int, int]] = set()

    for pair in pairs:
        cargo = cargos.get(pair.cargo_key)
        competencia = competencias.get(pair.competencia_key)
        if cargo is None or competencia is None:
            continue
        identity = (cargo.pk, competencia.pk)
        if identity in seen:
            continue
        seen.add(identity)
        result.append(upsert_cargo_competencia(cargo, competencia, report))

    return result


def import_catalog(
    cargos_path: str | Path,
    competencias_path: str | Path,
    *,
    dry_run: bool = False,
) -> ImportReport:
    """Orquestra parse → persistência do catálogo legado (US1–US4 / research R11).

    1. **Parse** (sem DB / T021): valida paths, encoding UTF-8 e colunas;
       monta estruturas em memória. ``CatalogParseError`` propaga
       (exit 1 no command; **zero writes** — fase pré-persistência).
    2. **Persist** em ``transaction.atomic()``:
       Escala → Cargos → Competências (classificação §6 preenche
       ``Excluídos KPI`` / ``Não mapeados``) → Reconcile → Vínculos.
       ``EscalaInativaError`` (T021) → conflito ``escala_inativa`` +
       re-raise; a saída do ``atomic`` faz **rollback** completo
       (nenhuma escrita parcial). Qualquer outra exceção idem.
    3. **``dry_run`` (T020)**: executa a mesma lógica de persistência para
       projetar totais no relatório (``modo=dry-run``), mas marca a
       transação com ``set_rollback(True)`` em ``finally`` — **zero commit**.
       Sucesso de dry-run → exit ``0`` no command (conflitos/divergências
       não-fatais não abortam).

    Cargos: nomes de ``lista-cargos`` primeiro (preferência de display), depois
    cargos referenciados em ``lista-competencias``. Competências: só da fonte
    ``lista-competencias`` (avaliáveis). Vínculos: união A'∪B' (§8).
    """
    # Fase 1 (T021): parse+validate fora do atomic — falha → zero writes.
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
            # Escala primeiro: escala_inativa aborta antes de cargos/comps.
            escala = resolve_default_escala()
            cargos_resolvidos = upsert_cargos(cargo_names, report)
            competencias_resolvidas = upsert_competencias(
                parsed.competencias, escala, report
            )

            pairs_a = extract_pairs_vista_a(parsed.cargos)
            pairs_b = extract_pairs_vista_b(parsed.competencias)
            avaliavel_keys = avaliavel_competencia_keys(parsed.competencias)
            reconciled = reconcile_matrix(
                pairs_a,
                pairs_b,
                avaliavel_keys=avaliavel_keys,
                resolved_cargo_keys=set(cargos_resolvidos),
                resolved_competencia_keys=set(competencias_resolvidas),
            )
            report.divergencias.extend(reconciled.divergencias)
            upsert_cargo_competencias(
                reconciled.matriz,
                cargos_resolvidos,
                competencias_resolvidas,
                report,
            )
        except EscalaInativaError as exc:
            # T021: fatal — registra conflito e re-raise para rollback + exit 1.
            report.conflitos.append(
                ReportEntry(
                    label="escala",
                    extra=exc.nome,
                    motivo="escala_inativa",
                )
            )
            raise EscalaInativaError(exc.nome, report=report) from exc
        finally:
            # T020: dry-run sempre descarta writes, inclusive se exceção
            # fatal (ex.: escala_inativa) — evita commit parcial.
            if dry_run:
                transaction.set_rollback(True)

    return report
