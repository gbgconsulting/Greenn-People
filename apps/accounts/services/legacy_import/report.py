"""Tipos de relatório da importação de colaboradores legado Sólides.

Superfície pública reexportada por ``legacy_import.__init__``.
Totais + amostra mascarada (max 5 por seção) conforme
``contracts/import-command-contract.md`` §Formato do relatório e research R14.

US2 (T017): contadores ``areas_*`` / ``cargos_*`` / ``usuarios_*`` /
``solides_id_preenchidos`` / ``demitidos_inativos`` + seções
``criados`` / ``atualizados`` / ``nao_importaveis`` / ``conflitos``
com helpers ``record_*`` e formatação mascarada.

US3 (T022): contadores ``gestores_vinculados`` / ``sem_gestor`` e seção
``ciclos_hierarquia`` (amostra mascarada; contador = ``len``).
"""

from __future__ import annotations

import re
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field

# Contrato §Formato: amostra truncada a 5 itens por seção.
_SAMPLE_MAX = 5

# E-mails no meio de texto (ex. campos livres de conflito / ciclo).
_EMAIL_IN_TEXT = re.compile(
    r"(?<![A-Za-z0-9._%+\-])([A-Za-z0-9._%+\-]+)@([A-Za-z0-9.\-]+\.[A-Za-z]{2,})"
)

# CPF (11) / CNPJ (14) só dígitos, com ou sem máscara tipográfica.
_DIGITS_ONLY = re.compile(r"\D+")

# PII formatada embutida em campos de amostra (SC-009 / T036).
_CPF_FMT = re.compile(r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b")
_CNPJ_FMT = re.compile(r"\b\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}\b")
_RG_FMT = re.compile(r"\b\d{1,2}\.\d{3}\.\d{3}-[\dXx]\b")


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

    Contadores de persistência são preenchidos pelo importer (T018+) /
    resolve (áreas/cargos). Contadores ``nao_importaveis`` / ``conflitos`` /
    ``ciclos_hierarquia`` alinham a ``len`` das listas detalhadas.
    Amostra em ``format_report`` trunca a 5 por seção (documentado no header).
    """

    modo: str = "persist"
    colaboradores_file: str = ""
    avaliacoes_file: str = ""

    # --- US2: estrutura organizacional + usuários ---
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

    # --- US3: hierarquia (fase B / T022) ---
    gestores_vinculados: int = 0
    sem_gestor: int = 0

    criados: list[ReportEntry] = field(default_factory=list)
    atualizados: list[ReportEntry] = field(default_factory=list)
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


# ---------------------------------------------------------------------------
# Helpers US2 — registrar amostra / contadores (importer + resolve + crosswalk)
# ---------------------------------------------------------------------------


def record_criado(
    report: ImportReport,
    *,
    nome: str,
    email: str,
    area: str = "",
    cargo: str = "",
    increment_counter: bool = True,
) -> None:
    """Acrescenta amostra de usuário criado (e-mail mascarado na formatação).

    Quando ``increment_counter`` é True, incrementa ``usuarios_criados``.
    """
    report.criados.append(
        ReportEntry(
            label=nome,
            extra=email,
            motivo=_area_cargo_motivo(area, cargo),
        )
    )
    if increment_counter:
        report.usuarios_criados += 1


def record_atualizado(
    report: ImportReport,
    *,
    nome: str,
    email: str,
    area: str = "",
    cargo: str = "",
    increment_counter: bool = True,
) -> None:
    """Acrescenta amostra de usuário atualizado (e-mail mascarado na formatação).

    Quando ``increment_counter`` é True, incrementa ``usuarios_atualizados``.
    """
    report.atualizados.append(
        ReportEntry(
            label=nome,
            extra=email,
            motivo=_area_cargo_motivo(area, cargo),
        )
    )
    if increment_counter:
        report.usuarios_atualizados += 1


def record_nao_importavel(
    report: ImportReport,
    *,
    linha: str | int,
    motivo: str,
) -> None:
    """Acrescenta item à seção Não importáveis (contador = ``len``)."""
    report.nao_importaveis.append(
        ReportEntry(label=str(linha), motivo=motivo)
    )


def record_conflito(
    report: ImportReport,
    *,
    tipo: str,
    extra: str = "",
    motivo: str = "",
) -> None:
    """Acrescenta conflito (contador = ``len``).

    Convenção de ``extra``/``motivo`` (contrato):
    - ``email_duplicado_backup``: ``extra=email=…``, ``motivo=linhas=a,b``
    - ``crosswalk_ambiguo``: ``extra=nome=…``, ``motivo=ids=a,b``
    - ``gestor_nao_resolvido``: ``extra=superior_id=…``, ``motivo=usuario=…``
    """
    report.conflitos.append(
        ReportEntry(label=tipo, extra=extra, motivo=motivo)
    )


def extend_conflitos(
    report: ImportReport,
    entries: Iterable[ReportEntry],
) -> None:
    """Mescla entradas pré-classificadas em Conflitos (ex. crosswalk)."""
    report.conflitos.extend(entries)


def note_solides_id_preenchido(report: ImportReport, n: int = 1) -> None:
    """Incrementa ``solides_id_preenchidos`` (User/Cargo resolvido via crosswalk)."""
    report.solides_id_preenchidos += n


def note_demitido_inativo(report: ImportReport, n: int = 1) -> None:
    """Incrementa ``demitidos_inativos`` (``is_active=False`` por Data demissão)."""
    report.demitidos_inativos += n


# ---------------------------------------------------------------------------
# Helpers US3 — hierarquia (importer fase B / hierarchy.py)
# ---------------------------------------------------------------------------


def note_gestor_vinculado(report: ImportReport, n: int = 1) -> None:
    """Incrementa ``gestores_vinculados`` (``line_manager`` aplicado ou já correto)."""
    report.gestores_vinculados += n


def note_sem_gestor(report: ImportReport, n: int = 1) -> None:
    """Incrementa ``sem_gestor`` (``Superior direto id`` vazio no backup)."""
    report.sem_gestor += n


def record_ciclo_hierarquia(
    report: ImportReport,
    *,
    usuarios: str,
    motivo: str = "ciclo_detectado",
) -> None:
    """Acrescenta ciclo reportado (contador = ``len``; vínculo NÃO aplicado).

    ``usuarios`` = cadeia de e-mails (mascarados em ``format_report``).
    """
    report.ciclos_hierarquia.append(ReportEntry(label=usuarios, motivo=motivo))


def _area_cargo_motivo(area: str, cargo: str) -> str:
    parts: list[str] = []
    if area.strip():
        parts.append(f"area={area.strip()}")
    if cargo.strip():
        parts.append(f"cargo={cargo.strip()}")
    return " | ".join(parts)


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

    - CPF (11 dígitos) / CNPJ (14) / RG formatado: ``***``
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
    if _CPF_FMT.fullmatch(text) or _CNPJ_FMT.fullmatch(text) or _RG_FMT.fullmatch(text):
        return "***"

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
    lines.extend(_sample_lines(report.criados, _format_usuario_amostra))
    lines.append("atualizados:")
    lines.extend(_sample_lines(report.atualizados, _format_usuario_amostra))
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


def _format_usuario_amostra(entry: ReportEntry) -> str:
    """Formato criados/atualizados: ``nome=… | email=m***@… | area=…``."""
    parts = [
        f"  - nome={_mask_emails_in_text(entry.label)}",
        f"email={mask_email(entry.extra)}",
    ]
    if entry.motivo.strip():
        parts.append(_mask_emails_in_text(entry.motivo.strip()))
    return " | ".join(parts)


def _format_nao_importavel(entry: ReportEntry) -> str:
    parts = [f"  - linha={_mask_emails_in_text(entry.label)}"]
    if entry.motivo.strip():
        parts.append(f"motivo={_mask_emails_in_text(entry.motivo.strip())}")
    if entry.extra.strip():
        parts.append(_mask_emails_in_text(entry.extra.strip()))
    return " | ".join(parts)


def _format_conflito(entry: ReportEntry) -> str:
    parts = [f"  - tipo={_mask_emails_in_text(entry.label)}"]
    if entry.extra.strip():
        parts.append(_mask_emails_in_text(entry.extra.strip()))
    if entry.motivo.strip():
        parts.append(_mask_emails_in_text(entry.motivo.strip()))
    return " | ".join(parts)


def _format_ciclo(entry: ReportEntry) -> str:
    usuarios = _mask_emails_in_text(entry.label.strip()) if entry.label.strip() else ""
    motivo = _mask_emails_in_text(entry.motivo.strip()) if entry.motivo.strip() else ""
    return f"  - usuarios={usuarios} | motivo={motivo}"


def _mask_emails_in_text(text: str) -> str:
    """Substitui endereços por ``mask_email`` e CPF/CNPJ/RG por ``mask_pii``."""

    def _repl_email(match: re.Match[str]) -> str:
        return mask_email(match.group(0))

    def _repl_pii(match: re.Match[str]) -> str:
        return mask_pii(match.group(0))

    masked = _EMAIL_IN_TEXT.sub(_repl_email, text)
    masked = _CPF_FMT.sub(_repl_pii, masked)
    masked = _CNPJ_FMT.sub(_repl_pii, masked)
    masked = _RG_FMT.sub(_repl_pii, masked)
    # Campo inteiro que é CPF/CNPJ sem pontuação (e sem e-mail).
    if "@" not in masked:
        digits = _DIGITS_ONLY.sub("", masked)
        if len(digits) in (11, 14) and sum(c.isdigit() for c in masked) >= 11:
            return mask_pii(masked)
    return masked
