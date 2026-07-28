"""Relatório estruturado da importação do catálogo legado.

Contadores + listas detalhadas e formatação textual conforme
`contracts/import-command-contract.md` §Formato do relatório.

Contadores de ``excluidos_kpi`` / ``nao_mapeados`` / ``conflitos`` /
``divergencias`` / ``merged`` no resumo **MUST** igualar ``len`` das
listas correspondentes (FR-009 / SC-007).
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field


@dataclass
class ReportEntry:
    """Entrada de lista detalhada do relatório de carga.

    Convenções por seção:
    - Excluídos KPI / Não mapeados: ``label`` = nome; ``motivo`` = código.
    - Conflitos: ``label`` = tipo; ``extra`` = nome; ``motivo`` = código.
    - Divergências: ``label`` = cargo; ``extra`` = competência;
      ``motivo`` = ``lista-cargos`` | ``lista-competencias``.
    - Merged: ``label`` = nome_a; ``extra`` = nome_b; ``motivo`` = chave canônica.
    """

    label: str
    motivo: str = ""
    extra: str = ""


@dataclass
class ImportReport:
    """Relatório estruturado da importação (contadores + listas detalhadas).

    Contadores de persistência são preenchidos pelo importer.
    Contadores de listas no resumo vêm de ``len(...)`` das listas
    (sempre alinhados — ver ``format_report``).
    """

    modo: str = "persist"
    cargos_file: str = ""
    competencias_file: str = ""

    cargos_criados: int = 0
    cargos_atualizados: int = 0
    cargos_inalterados: int = 0
    competencias_criadas: int = 0
    competencias_atualizadas: int = 0
    competencias_inalteradas: int = 0
    vinculos_criados: int = 0
    vinculos_atualizados: int = 0
    vinculos_inalterados: int = 0

    excluidos_kpi: list[ReportEntry] = field(default_factory=list)
    nao_mapeados: list[ReportEntry] = field(default_factory=list)
    conflitos: list[ReportEntry] = field(default_factory=list)
    divergencias: list[ReportEntry] = field(default_factory=list)
    merged: list[ReportEntry] = field(default_factory=list)

    @property
    def n_excluidos_kpi(self) -> int:
        """Contador alinhado à seção Excluídos KPI."""
        return len(self.excluidos_kpi)

    @property
    def n_nao_mapeados(self) -> int:
        """Contador alinhado à seção Não mapeados."""
        return len(self.nao_mapeados)


def record_excluido_kpi(
    report: ImportReport,
    nome: str,
    motivo: str = "kpi_operacional",
) -> None:
    """Acrescenta item à seção Excluídos KPI (contador = ``len`` da lista)."""
    report.excluidos_kpi.append(ReportEntry(label=nome, motivo=motivo))


def record_nao_mapeado(
    report: ImportReport,
    nome: str,
    motivo: str,
) -> None:
    """Acrescenta item à seção Não mapeados (contador = ``len`` da lista)."""
    report.nao_mapeados.append(ReportEntry(label=nome, motivo=motivo))


def extend_excluidos_kpi(
    report: ImportReport,
    entries: Iterable[ReportEntry],
) -> None:
    """Mescla entradas pré-classificadas em Excluídos KPI."""
    report.excluidos_kpi.extend(entries)


def extend_nao_mapeados(
    report: ImportReport,
    entries: Iterable[ReportEntry],
) -> None:
    """Mescla entradas pré-classificadas em Não mapeados."""
    report.nao_mapeados.extend(entries)


def format_report(report: ImportReport) -> str:
    """Serializa o relatório em texto UTF-8 com seções na ordem do contrato.

    Contadores ``excluidos_kpi`` / ``nao_mapeados`` no resumo usam
    ``n_excluidos_kpi`` / ``n_nao_mapeados`` (= ``len`` das listas).
    """
    lines: list[str] = [
        "=== Importação catálogo legado ===",
        f"modo: {report.modo}",
        f"cargos_file: {report.cargos_file}",
        f"competencias_file: {report.competencias_file}",
        "",
        "--- Resumo ---",
        f"cargos_criados: {report.cargos_criados}",
        f"cargos_atualizados: {report.cargos_atualizados}",
        f"cargos_inalterados: {report.cargos_inalterados}",
        f"competencias_criadas: {report.competencias_criadas}",
        f"competencias_atualizadas: {report.competencias_atualizadas}",
        f"competencias_inalteradas: {report.competencias_inalteradas}",
        f"vinculos_criados: {report.vinculos_criados}",
        f"vinculos_atualizados: {report.vinculos_atualizados}",
        f"vinculos_inalterados: {report.vinculos_inalterados}",
        f"excluidos_kpi: {report.n_excluidos_kpi}",
        f"nao_mapeados: {report.n_nao_mapeados}",
        f"conflitos: {len(report.conflitos)}",
        f"divergencias: {len(report.divergencias)}",
        f"merged: {len(report.merged)}",
        "",
        "--- Excluídos KPI ---",
    ]
    for entry in report.excluidos_kpi:
        lines.append(_format_named_motivo(entry))
    lines.append("")
    lines.append("--- Não mapeados ---")
    for entry in report.nao_mapeados:
        lines.append(_format_named_motivo(entry))
    lines.append("")
    lines.append("--- Conflitos ---")
    for entry in report.conflitos:
        lines.append(_format_conflito(entry))
    lines.append("")
    lines.append("--- Divergências entre fontes ---")
    for entry in report.divergencias:
        lines.append(_format_divergencia(entry))
    lines.append("")
    lines.append("--- Merged (mesma chave canônica) ---")
    for entry in report.merged:
        lines.append(_format_merged(entry))
    lines.append("")
    lines.append("=== Fim ===")
    return "\n".join(lines) + "\n"


def _format_named_motivo(entry: ReportEntry) -> str:
    return f"- {entry.label} | motivo={entry.motivo}"


def _format_conflito(entry: ReportEntry) -> str:
    return f"- {entry.label} | {entry.extra} | motivo={entry.motivo}"


def _format_divergencia(entry: ReportEntry) -> str:
    return (
        f"- cargo={entry.label} competencia={entry.extra} | apenas_em={entry.motivo}"
    )


def _format_merged(entry: ReportEntry) -> str:
    return f"- {entry.label} ~ {entry.extra} | chave={entry.motivo}"
