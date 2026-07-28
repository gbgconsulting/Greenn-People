"""Leitura CSV UTF-8, validação de colunas e expansão pipe-separated.

Research R2 / R11; `contracts/import-command-contract.md` §Pré-condições;
`contracts/legado-domain-mapping-contract.md` §2 e §6 (classificação).

T021: falhas fatais pré-persistência (arquivo ausente/ilegível, encoding
inválido, colunas obrigatórias ausentes) → ``CatalogParseError`` (exit 1
no command; zero writes).
"""

from __future__ import annotations

import csv
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from .mapping import classify_competencia
from .normalize import CanonicalNameIndex, display_name, split_pipe
from .report import ReportEntry

CARGOS_REQUIRED_COLUMNS: tuple[str, ...] = ("Cargo", "Competência")
COMPETENCIAS_REQUIRED_COLUMNS: tuple[str, ...] = (
    "Competência",
    "Grupo de competência",
    "Descrição",
    "Peso",
    "Tipo de Avaliação",
    "Cargo",
)


class CatalogParseError(Exception):
    """Erro fatal de pré-condição de parse (arquivo, encoding, colunas).

    Propagado para o management command → exit ``1``, sem escrita no DB.
    """


@dataclass(frozen=True)
class CargoRow:
    """Linha normalizada de lista-cargos (competências já expandidas)."""

    nome: str
    competencias: tuple[str, ...]


@dataclass(frozen=True)
class CompetenciaRow:
    """Linha normalizada de lista-competencias (cargos já expandidos).

    Colunas legadas `Peso` e `Tipo de Avaliação` são lidas mas não
    influenciam a persistência (contrato §5).
    """

    nome: str
    grupo: str
    descricao: str
    cargos: tuple[str, ...]


@dataclass(frozen=True)
class ParsedSources:
    """Estruturas em memória das duas fontes legadas após parse."""

    cargos: tuple[CargoRow, ...]
    competencias: tuple[CompetenciaRow, ...]
    cargos_path: str
    competencias_path: str


@dataclass(frozen=True)
class AvaliavelCompetenciaRow:
    """Linha de lista-competencias classificada como avaliável (§6)."""

    row: CompetenciaRow
    tipo: str


@dataclass(frozen=True)
class ClassifiedCompetencias:
    """Resultado da classificação §6 sobre linhas parseadas (sem DB).

    ``excluidos_kpi`` / ``nao_mapeados`` / ``merged`` já no formato de
    relatório; contadores no resumo = ``len`` dessas tuplas após merge no
    ``ImportReport``.
    """

    avaliaveis: tuple[AvaliavelCompetenciaRow, ...]
    excluidos_kpi: tuple[ReportEntry, ...]
    nao_mapeados: tuple[ReportEntry, ...]
    merged: tuple[ReportEntry, ...] = ()


def classify_competencia_rows(
    rows: Iterable[CompetenciaRow],
) -> ClassifiedCompetencias:
    """Classifica linhas de lista-competencias (§6) sem persistir.

    Deduplica por ``canonical_key`` (primeira grafia vence). Grafias
    distintas com a mesma chave entram em ``merged``. Somente
    ``avaliaveis`` são elegíveis a upsert; KPI e não mapeados seguem
    para as seções do relatório.
    """
    avaliaveis: list[AvaliavelCompetenciaRow] = []
    excluidos_kpi: list[ReportEntry] = []
    nao_mapeados: list[ReportEntry] = []
    merged: list[ReportEntry] = []
    index = CanonicalNameIndex()

    for row in rows:
        observed = index.observe(row.nome)
        if observed is None:
            continue
        if observed.merge is not None:
            merged.append(
                ReportEntry(
                    label=observed.merge.nome_a,
                    extra=observed.merge.nome_b,
                    motivo=observed.merge.chave,
                )
            )
        if not observed.is_first:
            continue

        display = observed.display
        classification = classify_competencia(display, row.grupo)
        if classification.kind == "excluidos_kpi":
            excluidos_kpi.append(
                ReportEntry(
                    label=display,
                    motivo=classification.motivo or "kpi_operacional",
                )
            )
            continue
        if classification.kind == "nao_mapeados":
            nao_mapeados.append(
                ReportEntry(
                    label=display,
                    motivo=classification.motivo or "grupo_desconhecido",
                )
            )
            continue
        if classification.tipo is None:
            nao_mapeados.append(
                ReportEntry(label=display, motivo="grupo_desconhecido")
            )
            continue

        avaliaveis.append(
            AvaliavelCompetenciaRow(
                row=CompetenciaRow(
                    nome=display,
                    grupo=row.grupo,
                    descricao=row.descricao,
                    cargos=row.cargos,
                ),
                tipo=classification.tipo,
            )
        )

    return ClassifiedCompetencias(
        avaliaveis=tuple(avaliaveis),
        excluidos_kpi=tuple(excluidos_kpi),
        nao_mapeados=tuple(nao_mapeados),
        merged=tuple(merged),
    )


def _cell(row: dict[str, str | None], column: str) -> str:
    """Valor de célula como string (None → vazio)."""
    value = row.get(column)
    return "" if value is None else value


def _assert_readable_file(path: Path) -> None:
    """Garante que ``path`` existe e é um arquivo legível.

    Raises:
        CatalogParseError: ausente ou não é arquivo.
    """
    if not path.exists():
        raise CatalogParseError(f"Arquivo não encontrado: {path}")
    if not path.is_file():
        raise CatalogParseError(f"Path não é um arquivo legível: {path}")


def validate_source_paths(
    cargos_path: str | Path,
    competencias_path: str | Path,
) -> tuple[Path, Path]:
    """Pré-condição §1: ambos os paths existem e são arquivos (T021).

    Valida os dois paths **antes** de ler qualquer conteúdo, para falhar
    cedo sem escrita parcial. Se ambos falharem, a mensagem agrega os dois.

    Returns:
        ``(cargos_path, competencias_path)`` resolvidos como ``Path``.

    Raises:
        CatalogParseError: um ou ambos os paths inválidos.
    """
    cargos = Path(cargos_path)
    competencias = Path(competencias_path)
    errors: list[str] = []
    for path in (cargos, competencias):
        try:
            _assert_readable_file(path)
        except CatalogParseError as exc:
            errors.append(str(exc))
    if errors:
        raise CatalogParseError("; ".join(errors))
    return cargos, competencias


def _read_csv_rows(
    path: Path,
    required: tuple[str, ...],
) -> list[dict[str, str | None]]:
    """Abre path como CSV UTF-8, valida colunas e retorna linhas.

    Raises:
        CatalogParseError: arquivo ausente/ilegível, encoding inválido
            ou colunas obrigatórias ausentes (T021 — fatal, zero writes).
    """
    _assert_readable_file(path)

    try:
        # utf-8-sig tolera BOM opcional sem alterar conteúdo sem BOM.
        with path.open(newline="", encoding="utf-8-sig") as fh:
            reader = csv.DictReader(fh)
            if reader.fieldnames is None:
                raise CatalogParseError(f"CSV sem header legível: {path}")
            present = set(reader.fieldnames)
            missing = [col for col in required if col not in present]
            if missing:
                raise CatalogParseError(
                    f"Colunas obrigatórias ausentes em {path}: "
                    f"{', '.join(missing)}"
                )
            try:
                return list(reader)
            except csv.Error as exc:
                raise CatalogParseError(
                    f"Falha ao parsear CSV {path}: {exc}"
                ) from exc
    except UnicodeDecodeError as exc:
        raise CatalogParseError(
            f"Encoding inválido (esperado UTF-8): {path}"
        ) from exc
    except CatalogParseError:
        raise
    except OSError as exc:
        raise CatalogParseError(f"Arquivo ilegível: {path} ({exc})") from exc


def parse_cargos_file(path: str | Path) -> tuple[CargoRow, ...]:
    """Lê lista-cargos: valida colunas e expande `Competência` pipe-separated."""
    path = Path(path)
    rows = _read_csv_rows(path, CARGOS_REQUIRED_COLUMNS)
    result: list[CargoRow] = []
    for row in rows:
        nome = display_name(_cell(row, "Cargo"))
        if not nome:
            continue
        competencias = tuple(split_pipe(_cell(row, "Competência")))
        result.append(CargoRow(nome=nome, competencias=competencias))
    return tuple(result)


def parse_competencias_file(path: str | Path) -> tuple[CompetenciaRow, ...]:
    """Lê lista-competencias: valida colunas e expande `Cargo` pipe-separated."""
    path = Path(path)
    rows = _read_csv_rows(path, COMPETENCIAS_REQUIRED_COLUMNS)
    result: list[CompetenciaRow] = []
    for row in rows:
        nome = display_name(_cell(row, "Competência"))
        if not nome:
            continue
        grupo = display_name(_cell(row, "Grupo de competência"))
        descricao = display_name(_cell(row, "Descrição"))
        cargos = tuple(split_pipe(_cell(row, "Cargo")))
        result.append(
            CompetenciaRow(
                nome=nome,
                grupo=grupo,
                descricao=descricao,
                cargos=cargos,
            )
        )
    return tuple(result)


def parse_catalog(
    cargos_path: str | Path,
    competencias_path: str | Path,
) -> ParsedSources:
    """Parse completo das duas fontes (sem persistência).

    Ordem (T021 / research R11 fase 1):
    1. Valida existência/legibilidade de **ambos** os paths.
    2. Lê CSV UTF-8 e valida colunas obrigatórias.
    3. Monta estruturas em memória.

    Falha em qualquer pré-condição → ``CatalogParseError`` (exit 1 no
    management command; **nenhuma** escrita no banco).
    """
    cargos_path, competencias_path = validate_source_paths(
        cargos_path, competencias_path
    )
    return ParsedSources(
        cargos=parse_cargos_file(cargos_path),
        competencias=parse_competencias_file(competencias_path),
        cargos_path=str(cargos_path),
        competencias_path=str(competencias_path),
    )
