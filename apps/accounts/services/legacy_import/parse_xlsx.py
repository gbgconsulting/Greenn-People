"""Leitura OOXML (openpyxl) de backups Sólides — colaboradores e crosswalk.

Único módulo da feature autorizado a importar ``openpyxl`` (research R1).
Colunas: ``contracts/column-mapping-contract.md`` §Obrigatórias;
pré-condições: ``contracts/import-command-contract.md``.

T025: falhas fatais pré-persistência (arquivo ausente/ilegível, OOXML
inválido, colunas obrigatórias ausentes) → ``LegacyParseError`` (exit 1
no command; zero writes).
"""

from __future__ import annotations

import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from openpyxl import load_workbook
from openpyxl.utils.exceptions import InvalidFileException

from apps.competencies.services.catalog_import.normalize import display_name

# --- Colunas (contrato) -------------------------------------------------------

COLABORADORES_REQUIRED_COLUMNS: tuple[str, ...] = ("Nome",)

COLABORADORES_COLUMNS: tuple[str, ...] = (
    "Nome",
    "E-mail empresarial",
    "E-mail",
    "E-mail pessoal",
    "Data demissão",
    "Cargo",
    "Cargo ID",
    "Departamento",
    "Superior direto id",
)

AVALIACOES_REQUIRED_COLUMNS: tuple[str, ...] = (
    "Nome Avaliado",
    "Identificador Avaliado",
)


class LegacyParseError(Exception):
    """Erro fatal de pré-condição de parse (arquivo, OOXML, colunas).

    Propagado para o management command → exit ``1``, sem escrita no DB.
    """


@dataclass(frozen=True)
class ColaboradorRow:
    """Linha normalizada de ``backup_colaboradores`` (sem PII extra).

    ``data_demissao`` permanece cru (datetime / serial / ISO / None) para
    ``dates.py`` (T006). IDs já como string canônica (sem ``.0`` de float).
    """

    linha: int
    nome: str
    email_empresarial: str
    email: str
    email_pessoal: str
    data_demissao: Any
    cargo: str
    cargo_id: str
    departamento: str
    superior_direto_id: str


@dataclass(frozen=True)
class AvaliacaoCrosswalkRow:
    """Par Nome Avaliado → Identificador Avaliado para crosswalk (R8)."""

    linha: int
    nome_avaliado: str
    identificador_avaliado: str


@dataclass(frozen=True)
class ParsedColaboradores:
    """Resultado do parse de colaboradores (sem persistência)."""

    rows: tuple[ColaboradorRow, ...]
    path: str


@dataclass(frozen=True)
class ParsedAvaliacoesCrosswalk:
    """Resultado do parse mínimo de avaliações (crosswalk only)."""

    rows: tuple[AvaliacaoCrosswalkRow, ...]
    path: str


def _assert_readable_file(path: Path) -> None:
    """Garante que ``path`` existe e é um arquivo legível.

    Raises:
        LegacyParseError: ausente, não é arquivo, ou ilegível (T025).
    """
    if not path.exists():
        raise LegacyParseError(f"Arquivo não encontrado: {path}")
    if not path.is_file():
        raise LegacyParseError(f"Path não é um arquivo legível: {path}")
    try:
        with path.open("rb") as fh:
            fh.read(1)
    except OSError as exc:
        raise LegacyParseError(f"Arquivo ilegível: {path} ({exc})") from exc


def validate_source_paths(
    colaboradores_path: str | Path,
    avaliacoes_path: str | Path | None = None,
) -> tuple[Path, Path | None]:
    """Pré-condição: path colaboradores (e avaliações, se informado) existem.

    Valida os paths **antes** de ler conteúdo OOXML, para falhar cedo
    sem escrita. Se ambos falharem, a mensagem agrega os dois.

    Returns:
        ``(colaboradores_path, avaliacoes_path)`` resolvidos como ``Path``.
        ``avaliacoes_path`` é ``None`` quando não informado / vazio.

    Raises:
        LegacyParseError: um ou ambos os paths inválidos (T025 — fatal).
    """
    colaboradores = Path(colaboradores_path)
    avaliacoes: Path | None = None
    if avaliacoes_path is not None and str(avaliacoes_path).strip():
        avaliacoes = Path(avaliacoes_path)

    errors: list[str] = []
    for path in (colaboradores, avaliacoes):
        if path is None:
            continue
        try:
            _assert_readable_file(path)
        except LegacyParseError as exc:
            errors.append(str(exc))
    if errors:
        raise LegacyParseError("; ".join(errors))
    return colaboradores, avaliacoes


def _header_index(header_row: tuple[Any, ...]) -> dict[str, int]:
    """Mapeia nome de coluna (strip) → índice; primeira ocorrência vence."""
    index: dict[str, int] = {}
    for idx, cell in enumerate(header_row):
        if cell is None:
            continue
        name = str(cell).strip()
        if name and name not in index:
            index[name] = idx
    return index


def _require_columns(
    path: Path,
    header_index: dict[str, int],
    required: tuple[str, ...],
) -> None:
    missing = [col for col in required if col not in header_index]
    if missing:
        raise LegacyParseError(
            f"Colunas obrigatórias ausentes em {path}: {', '.join(missing)}"
        )


def _cell(row: tuple[Any, ...], header_index: dict[str, int], column: str) -> Any:
    idx = header_index.get(column)
    if idx is None or idx >= len(row):
        return None
    return row[idx]


def _as_text(value: Any) -> str:
    """Texto display: None→''; floats inteiros sem '.0'; demais via display_name."""
    if value is None:
        return ""
    if isinstance(value, bool):
        return display_name(str(value))
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        if value.is_integer():
            return str(int(value))
        return display_name(str(value))
    return display_name(str(value))


def _as_id(value: Any) -> str:
    """Identificador Sólides como string estável (float 1428115.0 → '1428115')."""
    if value is None:
        return ""
    if isinstance(value, bool):
        return str(value).strip()
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        if value.is_integer():
            return str(int(value))
        return str(value).strip()
    return str(value).strip()


def _load_workbook(path: Path):
    """Abre OOXML; falha de formato → ``LegacyParseError`` (T025)."""
    try:
        return load_workbook(path, read_only=True, data_only=True)
    except InvalidFileException as exc:
        raise LegacyParseError(
            f"Arquivo OOXML ilegível (não é Excel 2007+ válido): {path}"
        ) from exc
    except (zipfile.BadZipFile, zipfile.LargeZipFile) as exc:
        raise LegacyParseError(
            f"Arquivo OOXML ilegível (não é Excel 2007+ válido): {path}"
        ) from exc
    except OSError as exc:
        raise LegacyParseError(f"Arquivo ilegível: {path} ({exc})") from exc


def _load_sheet_rows(path: Path) -> list[tuple[Any, ...]]:
    """Carrega a primeira planilha como lista de tuplas (header + dados).

    Raises:
        LegacyParseError: arquivo ausente/ilegível, OOXML inválido ou
            planilha ausente (T025 — fatal, zero writes).
    """
    _assert_readable_file(path)
    workbook = _load_workbook(path)
    try:
        try:
            sheet = workbook.active
            if sheet is None:
                raise LegacyParseError(f"Planilha ausente em {path}")
            rows: list[tuple[Any, ...]] = []
            for row in sheet.iter_rows(values_only=True):
                rows.append(tuple(row))
            return rows
        except LegacyParseError:
            raise
        except (
            OSError,
            ValueError,
            KeyError,
            zipfile.BadZipFile,
            zipfile.LargeZipFile,
        ) as exc:
            raise LegacyParseError(
                f"Arquivo OOXML ilegível: {path} ({exc})"
            ) from exc
    finally:
        workbook.close()


def parse_colaboradores_xlsx(path: str | Path) -> ParsedColaboradores:
    """Lê ``backup_colaboradores_*.xlsx`` e valida coluna obrigatória ``Nome``.

    Colunas PII (CPF, RG, banco, etc.) são ignoradas — não entram na estrutura.
    Linhas sem ``Nome`` são descartadas. ``Data demissão`` permanece crua.

    Raises:
        LegacyParseError: arquivo / OOXML / colunas (T025 — fatal).
    """
    path = Path(path)
    raw_rows = _load_sheet_rows(path)
    if not raw_rows:
        raise LegacyParseError(f"Planilha vazia (sem header): {path}")

    header_index = _header_index(raw_rows[0])
    _require_columns(path, header_index, COLABORADORES_REQUIRED_COLUMNS)

    result: list[ColaboradorRow] = []
    for excel_row, row in enumerate(raw_rows[1:], start=2):
        nome = _as_text(_cell(row, header_index, "Nome"))
        if not nome:
            continue
        result.append(
            ColaboradorRow(
                linha=excel_row,
                nome=nome,
                email_empresarial=_as_text(
                    _cell(row, header_index, "E-mail empresarial")
                ),
                email=_as_text(_cell(row, header_index, "E-mail")),
                email_pessoal=_as_text(_cell(row, header_index, "E-mail pessoal")),
                data_demissao=_cell(row, header_index, "Data demissão"),
                cargo=_as_text(_cell(row, header_index, "Cargo")),
                cargo_id=_as_id(_cell(row, header_index, "Cargo ID")),
                departamento=_as_text(_cell(row, header_index, "Departamento")),
                superior_direto_id=_as_id(
                    _cell(row, header_index, "Superior direto id")
                ),
            )
        )

    return ParsedColaboradores(rows=tuple(result), path=str(path))


def parse_avaliacoes_crosswalk_xlsx(path: str | Path) -> ParsedAvaliacoesCrosswalk:
    """Lê apenas colunas de crosswalk de ``backup_avaliacoes_*.xlsx``.

    Demais colunas são ignoradas nesta fatia (column-mapping §avaliações).
    Linhas sem nome ou identificador são descartadas (crosswalk R8).

    Raises:
        LegacyParseError: arquivo / OOXML / colunas (T025 — fatal).
    """
    path = Path(path)
    raw_rows = _load_sheet_rows(path)
    if not raw_rows:
        raise LegacyParseError(f"Planilha vazia (sem header): {path}")

    header_index = _header_index(raw_rows[0])
    _require_columns(path, header_index, AVALIACOES_REQUIRED_COLUMNS)

    result: list[AvaliacaoCrosswalkRow] = []
    for excel_row, row in enumerate(raw_rows[1:], start=2):
        nome = _as_text(_cell(row, header_index, "Nome Avaliado"))
        identificador = _as_id(_cell(row, header_index, "Identificador Avaliado"))
        if not nome or not identificador:
            continue
        result.append(
            AvaliacaoCrosswalkRow(
                linha=excel_row,
                nome_avaliado=nome,
                identificador_avaliado=identificador,
            )
        )

    return ParsedAvaliacoesCrosswalk(rows=tuple(result), path=str(path))
