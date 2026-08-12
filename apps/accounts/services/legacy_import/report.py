"""Tipos de relatório da importação de colaboradores legado Sólides.

Superfície pública reexportada por ``legacy_import.__init__``.
Totais + amostra mascarada (max 5 por seção) conforme
``contracts/import-command-contract.md`` §Formato do relatório e research R14.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass, field

# Contrato §Formato: amostra truncada a 5 itens por seção.
_SAMPLE_MAX = 5

# E-mails no meio de texto (ex. campos livres de conflito / ciclo).
_EMAIL_IN_TEXT = re.compile(
    r"(?<![A-Za-z0-9._%+\-])([A-Za-z0-9._%+\-]+)@([A-Za-z0-9.\-]+\.[A-Za-z]{2,})"
)

# CPF (11) / CNPJ (14) só dígitos, com ou sem máscara tipográfica.
_DIGITS_ONLY = re.compile(r"\D+")


@dataclass
class ReportEntry:
    """Entrada de lista detalhada / amostra do relatório de carga.

    Convenções por seção (contrato §Formato do relatório):
    - criados / atualizados: ``label`` = nome; ``extra`` = e-mail
      (+ área/cargo em ``motivo`` quando útil, ex. ``area=Tech | cargo=Dev PL``).
    - nao_importaveis: ``label`` = linha; ``motivo`` = código.
    - conflitos: ``label`` = tipo; ``extra`` / ``motivo`` = detalhe
      (e-mails serão mascarados na formatação).
    - ciclos_hierarquia: ``label`` = usuários; ``motivo`` = código.
    """

    label: str
    motivo: str = ""
    extra: str = ""


@dataclass
class ImportReport:
    """Relatório estruturado (contadores + listas) — contrato §Formato.

    Contadores de persistência são preenchidos pelo importer (T018+).
    Contadores alinhados a ``len`` das listas detalhadas quando aplicável.
    """

    modo: str = "persist"
    colaboradores_file: str = ""
    avaliacoes_file: str = ""

    areas_criadas: int = 0
    areas_reutilizadas: int = 0
    cargos_criados: int = 0
    cargos_atualizados: int = 0
    cargos_inalterados: int = 0
    usuarios_criados: int = 0
    usuarios_atualizados: int = 0
    usuarios_inalterados: int = 0
    solides_id_preenchidos: int = 0
    demitidos_inativos: int = 0
    gestores_vinculados: int = 0
    sem_gestor: int = 0

    criados: list[ReportEntry] = field(default_factory=list)
    nao_importaveis: list[ReportEntry] = field(default_factory=list)
    conflitos: list[ReportEntry] = field(default_factory=list)
    ciclos_hierarquia: list[ReportEntry] = field(default_factory=list)

    @property
    def n_nao_importaveis(self) -> int:
        """Contador alinhado à seção Não importáveis."""
        return len(self.nao_importaveis)

    @property
    def n_conflitos(self) -> int:
        """Contador alinhado à seção Conflitos."""
        return len(self.conflitos)

    @property
    def n_ciclos_hierarquia(self) -> int:
        """Contador alinhado à seção Ciclos de hierarquia."""
        return len(self.ciclos_hierarquia)


def mask_email(value: str | None) -> str:
    """Mascara e-mail no estilo ``j***@example.com`` (R14 / FR-015).

    NEVER retorna o endereço completo. Valores sem ``@`` delegam a
    ``mask_pii``.
    """
    if value is None:
        return ""
    text = str(value).strip()
    if not text:
        return ""
    if "@" not in text:
        return mask_pii(text)

    local, _, domain = text.partition("@")
    domain = domain.strip()
    if not domain:
        return "***"
    if not local:
        return f"***@{domain}"
    return f"{local[0]}***@{domain}"


def mask_pii(value: str | None) -> str:
    """Mascara PII genérica — CPF/RG/telefone nunca em claro (R14).

    - CPF (11 dígitos) / CNPJ (14): ``***``
    - Texto com ``@``: ``mask_email``
    - Demais: primeiro caractere + ``***`` (curtos → ``***``)
    """
    if value is None:
        return ""
    text = str(value).strip()
    if not text:
        return ""
    if "***" in text and "@" in text:
        return text
    if "@" in text:
        return mask_email(text)

    digits = _DIGITS_ONLY.sub("", text)
    if len(digits) in (11, 14) and sum(c.isdigit() for c in text) >= 11:
        return "***"

    if len(text) <= 2:
        return "***"
    return f"{text[0]}***"


def format_report(report: ImportReport) -> str:
    """Serializa o relatório em texto UTF-8 (contrato §Formato).

    Resumo com contadores (listas via ``len`` / properties) + amostra
    mascarada (max 5 por seção). NEVER emite CPF/RG/telefone/e-mail completo.
    """
    avaliacoes = report.avaliacoes_file.strip() or "ausente"
    lines: list[str] = [
        "=== Importação colaboradores legado Sólides ===",
        f"modo: {report.modo}",
        f"colaboradores_file: {report.colaboradores_file}",
        f"avaliacoes_file: {avaliacoes}",
        "",
        "--- Resumo ---",
        f"areas_criadas: {report.areas_criadas}",
        f"areas_reutilizadas: {report.areas_reutilizadas}",
        f"cargos_criados: {report.cargos_criados}",
        f"cargos_atualizados: {report.cargos_atualizados}",
        f"cargos_inalterados: {report.cargos_inalterados}",
        f"usuarios_criados: {report.usuarios_criados}",
        f"usuarios_atualizados: {report.usuarios_atualizados}",
        f"usuarios_inalterados: {report.usuarios_inalterados}",
        f"solides_id_preenchidos: {report.solides_id_preenchidos}",
        f"demitidos_inativos: {report.demitidos_inativos}",
        f"gestores_vinculados: {report.gestores_vinculados}",
        f"sem_gestor: {report.sem_gestor}",
        f"nao_importaveis: {report.n_nao_importaveis}",
        f"conflitos: {report.n_conflitos}",
        f"ciclos_hierarquia: {report.n_ciclos_hierarquia}",
        "",
        "--- Amostra (mascarada, max 5 por seção) ---",
        "criados:",
    ]
    lines.extend(_sample_lines(report.criados, _format_criado))
    lines.append("nao_importaveis:")
    lines.extend(_sample_lines(report.nao_importaveis, _format_nao_importavel))
    lines.append("conflitos:")
    lines.extend(_sample_lines(report.conflitos, _format_conflito))
    lines.append("ciclos_hierarquia:")
    lines.extend(_sample_lines(report.ciclos_hierarquia, _format_ciclo))
    lines.append("")
    lines.append("=== Fim ===")
    return "\n".join(lines) + "\n"


def _sample_lines(
    entries: list[ReportEntry],
    formatter: Callable[[ReportEntry], str],
) -> list[str]:
    return [formatter(entry) for entry in entries[:_SAMPLE_MAX]]


def _format_criado(entry: ReportEntry) -> str:
    parts = [f"  - nome={entry.label}", f"email={mask_email(entry.extra)}"]
    if entry.motivo.strip():
        parts.append(_mask_emails_in_text(entry.motivo.strip()))
    return " | ".join(parts)


def _format_nao_importavel(entry: ReportEntry) -> str:
    return f"  - linha={entry.label} | motivo={entry.motivo}"


def _format_conflito(entry: ReportEntry) -> str:
    parts = [f"  - tipo={entry.label}"]
    if entry.extra.strip():
        parts.append(_mask_emails_in_text(entry.extra.strip()))
    if entry.motivo.strip():
        parts.append(_mask_emails_in_text(entry.motivo.strip()))
    return " | ".join(parts)


def _format_ciclo(entry: ReportEntry) -> str:
    usuarios = _mask_emails_in_text(entry.label.strip()) if entry.label.strip() else ""
    return f"  - usuarios={usuarios} | motivo={entry.motivo}"


def _mask_emails_in_text(text: str) -> str:
    """Substitui endereços embutidos por ``mask_email``; demais PII via heurística CPF."""

    def _repl(match: re.Match[str]) -> str:
        return mask_email(match.group(0))

    masked = _EMAIL_IN_TEXT.sub(_repl, text)
    # Se o campo inteiro parece CPF/CNPJ sem e-mail, redige.
    if "@" not in masked:
        digits = _DIGITS_ONLY.sub("", masked)
        if len(digits) in (11, 14) and sum(c.isdigit() for c in masked) >= 11:
            return mask_pii(masked)
    return masked
