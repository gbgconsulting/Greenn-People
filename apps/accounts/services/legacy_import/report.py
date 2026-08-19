"""Tipos de relatório da importação legado Sólides.

Superfície pública reexportada por ``legacy_import.__init__``.
Totais + amostra mascarada (max 5 por seção) conforme
``contracts/import-command-contract.md`` §Formato do relatório
(010 colaboradores + 011 ciclos/avaliações + 013 notas/comentários)
e research R12/R14 (010/011) / R13 (013).

US2 (T017/010): contadores ``areas_*`` / ``cargos_*`` / ``usuarios_*`` /
``solides_id_preenchidos`` / ``demitidos_inativos`` + seções
``criados`` / ``atualizados`` / ``nao_importaveis`` / ``conflitos``
com helpers ``record_*`` e formatação mascarada.

US3 (T022/010): contadores ``gestores_vinculados`` / ``sem_gestor`` e seção
``ciclos_hierarquia`` (amostra mascarada; contador = ``len``).

011 (T007): contadores ``ciclos_*`` / ``avaliacoes_*`` / ``grupos_agregados``
+ seções ``orfaos_ciclo`` / ``orfaos_usuario`` / ``ids_colapsados`` via
``format_ciclos_avaliacoes_report``.

013 (T006): contadores ``notas_*`` / ``comentarios_*`` / ``orfaos_*`` /
``conflitos_lider_divergente`` / ``conflitos_ciclo_aberto`` /
``habilidades_extras_criadas`` / ``ids_colapsados_resolvidos`` via
``format_notas_comentarios_report``. NEVER emite comentário completo,
nome ou e-mail; IDs via ``mask_solides_id``.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field

# Contrato §Formato: amostra truncada a 5 itens por seção.
_SAMPLE_MAX = 5

# Tokens curtos permitidos na amostra 013 — texto livre (comentário/nome)
# NÃO pode vazar via ``lado`` / ``tipo`` (T025 / SC-010).
_SAMPLE_LADO_TOKENS = frozenset({"auto", "lider", "líder", "ambos"})
_SAMPLE_TIPO_TOKENS = frozenset({"colaborador", "lider", "líder", "auto"})
_PII_FIELD_RE = re.compile(
    r"\b(nome|comentario|comentário|conteudo|conteúdo|email|e-mail)=([^|\n]+)",
    flags=re.IGNORECASE,
)

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
    - 011 ciclos_criados: ``label`` = solides_id; ``extra`` = nome;
      ``motivo`` = status.
    - 011 orfaos_*: ``label`` / ``extra`` = ids; ``motivo`` = código.
    - 011 ids_colapsados: ``label`` = group_key; ``extra`` = canonical;
      ``motivo`` = colapsados / n_linhas.
    - 013 notas_*: ``label`` = avaliacao_id; ``extra`` = competencia_id;
      ``motivo`` = lado (``auto`` / ``lider``).
    - 013 comentarios_*: ``label`` = avaliacao_id; ``extra`` = autor_id;
      ``motivo`` = tipo (``colaborador`` / ``lider``). NEVER ``conteudo``.
    - 013 orfaos_avaliacao: ``label`` = id_legado; ``motivo`` = código.
    - 013 orfaos_competencia: ``label`` = habilidade_id; ``motivo`` = código.
    - 013 orfaos_autor: ``label`` = avaliador_id; ``motivo`` = código.
    - 013 conflitos_lider_divergente: ``label`` / ``extra`` = ids.
    - 013 conflitos_ciclo_aberto: ``label`` = avaliacao_id; ``extra`` = ciclo.
    - 013 habilidades_extras: ``label`` = solides_id; ``extra`` = tipo.
    - 013 ids_colapsados_resolvidos: ``label`` = colapsado; ``extra`` = canônico.
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
    Amostra em ``format_report`` / ``format_ciclos_avaliacoes_report`` /
    ``format_notas_comentarios_report`` trunca a 5 por seção (documentado
    no header). NEVER dump de comentário completo / nome / e-mail.
    """

    modo: str = "persist"
    colaboradores_file: str = ""
    avaliacoes_file: str = ""
    solicitacoes_file: str = ""

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

    # --- 011: ciclos históricos + cabeçalhos de avaliação ---
    ciclos_criados: int = 0
    ciclos_atualizados: int = 0
    ciclos_inalterados: int = 0
    ciclos_conflitos: int = 0
    avaliacoes_criadas: int = 0
    avaliacoes_atualizadas: int = 0
    avaliacoes_inalteradas: int = 0
    grupos_agregados: int = 0

    # --- 013: notas por competência + comentários qualitativos ---
    notas_file: str = ""
    comentarios_file: str = ""
    habilidades_file: str = ""
    notas_criadas: int = 0
    notas_atualizadas: int = 0
    notas_inalteradas: int = 0
    comentarios_criados: int = 0
    comentarios_inalterados: int = 0
    habilidades_extras_criadas: int = 0

    criados: list[ReportEntry] = field(default_factory=list)
    atualizados: list[ReportEntry] = field(default_factory=list)
    nao_importaveis: list[ReportEntry] = field(default_factory=list)
    conflitos: list[ReportEntry] = field(default_factory=list)
    ciclos_hierarquia: list[ReportEntry] = field(default_factory=list)

    amostra_ciclos_criados: list[ReportEntry] = field(default_factory=list)
    orfaos_ciclo: list[ReportEntry] = field(default_factory=list)
    orfaos_usuario: list[ReportEntry] = field(default_factory=list)
    ids_colapsados: list[ReportEntry] = field(default_factory=list)

    amostra_notas_criadas: list[ReportEntry] = field(default_factory=list)
    amostra_notas_atualizadas: list[ReportEntry] = field(default_factory=list)
    amostra_notas_inalteradas: list[ReportEntry] = field(default_factory=list)
    amostra_comentarios_criados: list[ReportEntry] = field(default_factory=list)
    amostra_comentarios_inalterados: list[ReportEntry] = field(default_factory=list)
    orfaos_avaliacao: list[ReportEntry] = field(default_factory=list)
    orfaos_competencia: list[ReportEntry] = field(default_factory=list)
    orfaos_autor: list[ReportEntry] = field(default_factory=list)
    conflitos_lider_divergente: list[ReportEntry] = field(default_factory=list)
    conflitos_ciclo_aberto: list[ReportEntry] = field(default_factory=list)
    amostra_habilidades_extras: list[ReportEntry] = field(default_factory=list)
    ids_colapsados_resolvidos: list[ReportEntry] = field(default_factory=list)

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

    @property
    def n_orfaos_ciclo(self) -> int:
        """Contador alinhado à seção órfãos de ciclo (011)."""
        return len(self.orfaos_ciclo)

    @property
    def n_orfaos_usuario(self) -> int:
        """Contador alinhado à seção órfãos de usuário (011)."""
        return len(self.orfaos_usuario)

    @property
    def n_orfaos_avaliacao(self) -> int:
        """Contador alinhado à seção órfãos de avaliação (013)."""
        return len(self.orfaos_avaliacao)

    @property
    def n_orfaos_competencia(self) -> int:
        """Contador alinhado à seção órfãos de competência (013)."""
        return len(self.orfaos_competencia)

    @property
    def n_orfaos_autor(self) -> int:
        """Contador alinhado à seção órfãos de autor (013)."""
        return len(self.orfaos_autor)

    @property
    def n_conflitos_lider_divergente(self) -> int:
        """Contador alinhado à seção dois líderes divergentes (013)."""
        return len(self.conflitos_lider_divergente)

    @property
    def n_conflitos_ciclo_aberto(self) -> int:
        """Contador alinhado à seção ciclo aberto (013)."""
        return len(self.conflitos_ciclo_aberto)

    @property
    def n_ids_colapsados_resolvidos(self) -> int:
        """Contador alinhado à seção IDs colapsados resolvidos (013)."""
        return len(self.ids_colapsados_resolvidos)


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
    - 011 ``datas_ausentes_ou_invalidas``: ``extra=solicitacao=…``,
      ``motivo=linha=…``
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


# ---------------------------------------------------------------------------
# Helpers 011 — ciclos / avaliações cabeçalho
# ---------------------------------------------------------------------------


def note_ciclo_criado(report: ImportReport, n: int = 1) -> None:
    """Incrementa ``ciclos_criados``."""
    report.ciclos_criados += n


def note_ciclo_atualizado(report: ImportReport, n: int = 1) -> None:
    """Incrementa ``ciclos_atualizados``."""
    report.ciclos_atualizados += n


def note_ciclo_inalterado(report: ImportReport, n: int = 1) -> None:
    """Incrementa ``ciclos_inalterados``."""
    report.ciclos_inalterados += n


def note_ciclo_conflito(report: ImportReport, n: int = 1) -> None:
    """Incrementa ``ciclos_conflitos`` (fase 1; não-fatal por linha)."""
    report.ciclos_conflitos += n


def note_avaliacao_criada(report: ImportReport, n: int = 1) -> None:
    """Incrementa ``avaliacoes_criadas``."""
    report.avaliacoes_criadas += n


def note_avaliacao_atualizada(report: ImportReport, n: int = 1) -> None:
    """Incrementa ``avaliacoes_atualizadas``."""
    report.avaliacoes_atualizadas += n


def note_avaliacao_inalterada(report: ImportReport, n: int = 1) -> None:
    """Incrementa ``avaliacoes_inalteradas``."""
    report.avaliacoes_inalteradas += n


def note_grupo_agregado(report: ImportReport, n: int = 1) -> None:
    """Incrementa ``grupos_agregados`` (cardinalidade de group_key)."""
    report.grupos_agregados += n


def record_ciclo_criado_amostra(
    report: ImportReport,
    *,
    solides_id: str,
    nome: str,
    status: str = "encerrado",
    increment_counter: bool = True,
) -> None:
    """Amostra de ciclo criado (IDs mascarados na formatação)."""
    report.amostra_ciclos_criados.append(
        ReportEntry(label=solides_id, extra=nome, motivo=status)
    )
    if increment_counter:
        report.ciclos_criados += 1


def record_orfao_ciclo(
    report: ImportReport,
    *,
    solicitacao_id: str,
    avaliado_id: str = "",
    motivo: str = "ciclo_nao_resolvido",
) -> None:
    """Órfão: solicitação sem ``Ciclo.solides_id`` (contador = ``len``)."""
    report.orfaos_ciclo.append(
        ReportEntry(
            label=solicitacao_id,
            extra=avaliado_id,
            motivo=motivo,
        )
    )


def record_orfao_usuario(
    report: ImportReport,
    *,
    solicitacao_id: str,
    avaliado_id: str,
    motivo: str = "usuario_nao_resolvido",
) -> None:
    """Órfão: avaliado sem ``CustomUser`` (contador = ``len``)."""
    report.orfaos_usuario.append(
        ReportEntry(
            label=solicitacao_id,
            extra=avaliado_id,
            motivo=motivo,
        )
    )


def record_ids_colapsados(
    report: ImportReport,
    *,
    solicitacao_id: str,
    avaliado_id: str,
    canonical_id: str,
    collapsed_ids: Iterable[str],
    n_linhas: int,
) -> None:
    """Amostra mascarada de IDs colapsados (handoff 6.5.5).

    Não incrementa ``grupos_agregados`` — use ``note_grupo_agregado``.
    """
    colapsados = ",".join(str(item) for item in collapsed_ids)
    report.ids_colapsados.append(
        ReportEntry(
            label=f"sol={solicitacao_id}, av={avaliado_id}",
            extra=canonical_id,
            motivo=f"colapsados={colapsados} | n_linhas={n_linhas}",
        )
    )


# ---------------------------------------------------------------------------
# Helpers 013 — notas / comentários / órfãos / conflitos
# ---------------------------------------------------------------------------


def _nota_entry(avaliacao_id: str, competencia_id: str, lado: str) -> ReportEntry:
    return ReportEntry(
        label=str(avaliacao_id),
        extra=str(competencia_id),
        motivo=str(lado).strip(),
    )


def _comentario_entry(avaliacao_id: str, autor_id: str, tipo: str) -> ReportEntry:
    """Amostra de comentário — só IDs e tipo; NEVER ``conteudo``/nome/e-mail."""
    return ReportEntry(
        label=str(avaliacao_id),
        extra=str(autor_id),
        motivo=str(tipo).strip(),
    )


def note_nota_criada(report: ImportReport, n: int = 1) -> None:
    """Incrementa ``notas_criadas``."""
    report.notas_criadas += n


def note_nota_atualizada(report: ImportReport, n: int = 1) -> None:
    """Incrementa ``notas_atualizadas``."""
    report.notas_atualizadas += n


def note_nota_inalterada(report: ImportReport, n: int = 1) -> None:
    """Incrementa ``notas_inalteradas``."""
    report.notas_inalteradas += n


def note_comentario_criado(report: ImportReport, n: int = 1) -> None:
    """Incrementa ``comentarios_criados``."""
    report.comentarios_criados += n


def note_comentario_inalterado(report: ImportReport, n: int = 1) -> None:
    """Incrementa ``comentarios_inalterados``."""
    report.comentarios_inalterados += n


def note_habilidade_extra_criada(report: ImportReport, n: int = 1) -> None:
    """Incrementa ``habilidades_extras_criadas``."""
    report.habilidades_extras_criadas += n


def record_nota_criada(
    report: ImportReport,
    *,
    avaliacao_id: str,
    competencia_id: str,
    lado: str,
    increment_counter: bool = True,
) -> None:
    """Amostra de nota criada (IDs mascarados na formatação)."""
    report.amostra_notas_criadas.append(
        _nota_entry(avaliacao_id, competencia_id, lado)
    )
    if increment_counter:
        report.notas_criadas += 1


def record_nota_atualizada(
    report: ImportReport,
    *,
    avaliacao_id: str,
    competencia_id: str,
    lado: str,
    increment_counter: bool = True,
) -> None:
    """Amostra de nota atualizada (só ``nota_*``; snapshots write-once)."""
    report.amostra_notas_atualizadas.append(
        _nota_entry(avaliacao_id, competencia_id, lado)
    )
    if increment_counter:
        report.notas_atualizadas += 1


def record_nota_inalterada(
    report: ImportReport,
    *,
    avaliacao_id: str,
    competencia_id: str,
    lado: str,
    increment_counter: bool = True,
) -> None:
    """Amostra de nota já equivalente na 2ª run."""
    report.amostra_notas_inalteradas.append(
        _nota_entry(avaliacao_id, competencia_id, lado)
    )
    if increment_counter:
        report.notas_inalteradas += 1


def record_comentario_criado(
    report: ImportReport,
    *,
    avaliacao_id: str,
    autor_id: str,
    tipo: str,
    increment_counter: bool = True,
) -> None:
    """Amostra de feedback criado — sem ``conteudo``, nome ou e-mail."""
    report.amostra_comentarios_criados.append(
        _comentario_entry(avaliacao_id, autor_id, tipo)
    )
    if increment_counter:
        report.comentarios_criados += 1


def record_comentario_inalterado(
    report: ImportReport,
    *,
    avaliacao_id: str,
    autor_id: str,
    tipo: str,
    increment_counter: bool = True,
) -> None:
    """Amostra de feedback já existente pela chave natural (não reescrito)."""
    report.amostra_comentarios_inalterados.append(
        _comentario_entry(avaliacao_id, autor_id, tipo)
    )
    if increment_counter:
        report.comentarios_inalterados += 1


def record_orfao_avaliacao(
    report: ImportReport,
    *,
    id_legado: str,
    motivo: str = "avaliacao_nao_resolvida",
) -> None:
    """Órfão: ID de avaliação irresolvível (contador = ``len``)."""
    report.orfaos_avaliacao.append(
        ReportEntry(label=str(id_legado), motivo=motivo)
    )


def record_orfao_competencia(
    report: ImportReport,
    *,
    habilidade_id: str,
    motivo: str = "kpi_ou_sem_nota",
) -> None:
    """Órfão: habilidade KPI/ambígua ou sem FK de nota (contador = ``len``)."""
    report.orfaos_competencia.append(
        ReportEntry(label=str(habilidade_id), motivo=motivo)
    )


def record_orfao_autor(
    report: ImportReport,
    *,
    avaliador_id: str,
    motivo: str = "usuario_nao_resolvido",
) -> None:
    """Órfão: autor irresolvível — nunca inventa User (contador = ``len``)."""
    report.orfaos_autor.append(
        ReportEntry(label=str(avaliador_id), motivo=motivo)
    )


def record_conflito_lider_divergente(
    report: ImportReport,
    *,
    avaliacao_id: str,
    competencia_id: str,
) -> None:
    """Dois líderes, sem média e sem persistir líder (contador = ``len``)."""
    report.conflitos_lider_divergente.append(
        ReportEntry(label=str(avaliacao_id), extra=str(competencia_id))
    )


def record_conflito_ciclo_aberto(
    report: ImportReport,
    *,
    avaliacao_id: str,
    ciclo: str = "aberto",
) -> None:
    """Skip: ciclo ``status=aberto`` (contador = ``len``)."""
    report.conflitos_ciclo_aberto.append(
        ReportEntry(label=str(avaliacao_id), extra=str(ciclo))
    )


def record_habilidade_extra_criada(
    report: ImportReport,
    *,
    solides_id: str,
    tipo: str = "tecnica",
    increment_counter: bool = True,
) -> None:
    """Amostra de ``Competencia`` extra mínima (FK de nota; R11)."""
    report.amostra_habilidades_extras.append(
        ReportEntry(label=str(solides_id), extra=str(tipo).strip())
    )
    if increment_counter:
        report.habilidades_extras_criadas += 1


def record_id_colapsado_resolvido(
    report: ImportReport,
    *,
    colapsado: str,
    canonico: str,
) -> None:
    """Amostra mascarada ``colapsado → canônico`` (contador = ``len``)."""
    report.ids_colapsados_resolvidos.append(
        ReportEntry(label=str(colapsado), extra=str(canonico))
    )


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


def mask_solides_id(value: str | None) -> str:
    """Mascara ID Sólides na amostra (``***`` + últimos 3 chars)."""
    if value is None:
        return "***"
    text = str(value).strip()
    if not text:
        return "***"
    if len(text) <= 3:
        return f"***{text}"
    return f"***{text[-3:]}"


def format_report(report: ImportReport) -> str:
    """Serializa o relatório de colaboradores (010) em texto UTF-8.

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


def format_ciclos_avaliacoes_report(report: ImportReport) -> str:
    """Serializa o relatório 011 (ciclos/avaliações) — contrato §Formato.

    Contadores + amostra mascarada (max 5 por seção, T029 / SC-010).
    NEVER dump de nomes/e-mails em massa; IDs Sólides via
    ``mask_solides_id``. Superfície exclusiva de stdout/``--report-file``.
    """
    lines: list[str] = [
        "=== Importação ciclos/avaliações legado Sólides ===",
        f"modo: {report.modo}",
        f"solicitacoes_file: {report.solicitacoes_file}",
        f"avaliacoes_file: {report.avaliacoes_file}",
        "",
        "--- Resumo ---",
        f"ciclos_criados: {report.ciclos_criados}",
        f"ciclos_atualizados: {report.ciclos_atualizados}",
        f"ciclos_inalterados: {report.ciclos_inalterados}",
        f"ciclos_conflitos: {report.ciclos_conflitos}",
        f"avaliacoes_criadas: {report.avaliacoes_criadas}",
        f"avaliacoes_atualizadas: {report.avaliacoes_atualizadas}",
        f"avaliacoes_inalteradas: {report.avaliacoes_inalteradas}",
        f"grupos_agregados: {report.grupos_agregados}",
        f"orfaos_ciclo: {report.n_orfaos_ciclo}",
        f"orfaos_usuario: {report.n_orfaos_usuario}",
        f"conflitos: {report.n_conflitos}",
        "",
        "--- Amostra (mascarada, max 5 por seção) ---",
        "ciclos_criados:",
    ]
    lines.extend(
        _sample_lines(report.amostra_ciclos_criados, _format_ciclo_criado_amostra)
    )
    lines.append("orfaos_usuario:")
    lines.extend(_sample_lines(report.orfaos_usuario, _format_orfao_usuario))
    lines.append("orfaos_ciclo:")
    lines.extend(_sample_lines(report.orfaos_ciclo, _format_orfao_ciclo))
    lines.append("conflitos:")
    lines.extend(_sample_lines(report.conflitos, _format_conflito))
    lines.append("grupos_agregados / ids_colapsados:")
    lines.extend(_sample_lines(report.ids_colapsados, _format_ids_colapsados))
    lines.append("")
    lines.append("=== Fim ===")
    return "\n".join(lines) + "\n"


def format_notas_comentarios_report(report: ImportReport) -> str:
    """Serializa o relatório 013 (notas/comentários) — contrato §Formato.

    Contadores + amostra mascarada (max 5 por seção, T006 / T025 / SC-010).
    NEVER emite comentário completo, nome ou e-mail; IDs via
    ``mask_solides_id``. Superfície exclusiva de stdout/``--report-file``
    (mesmo texto UTF-8 nas duas saídas). Logs NÃO imprimem linha XLSX crua.
    """
    habilidades = report.habilidades_file.strip() or "(omitido)"
    lines: list[str] = [
        "=== Importação notas/comentários legado Sólides ===",
        f"modo: {report.modo}",
        f"notas_file: {report.notas_file}",
        f"comentarios_file: {report.comentarios_file}",
        f"avaliacoes_file: {report.avaliacoes_file}",
        f"habilidades_file: {habilidades}",
        "",
        "--- Resumo ---",
        f"notas_criadas: {report.notas_criadas}",
        f"notas_atualizadas: {report.notas_atualizadas}",
        f"notas_inalteradas: {report.notas_inalteradas}",
        f"comentarios_criados: {report.comentarios_criados}",
        f"comentarios_inalterados: {report.comentarios_inalterados}",
        f"orfaos_avaliacao: {report.n_orfaos_avaliacao}",
        f"orfaos_competencia: {report.n_orfaos_competencia}",
        f"orfaos_autor: {report.n_orfaos_autor}",
        f"conflitos_lider_divergente: {report.n_conflitos_lider_divergente}",
        f"conflitos_ciclo_aberto: {report.n_conflitos_ciclo_aberto}",
        f"habilidades_extras_criadas: {report.habilidades_extras_criadas}",
        f"ids_colapsados_resolvidos: {report.n_ids_colapsados_resolvidos}",
        f"conflitos: {report.n_conflitos}",
        "",
        "--- Amostra (mascarada, max 5 por seção) ---",
        "notas_criadas:",
    ]
    lines.extend(_sample_lines(report.amostra_notas_criadas, _format_nota_amostra))
    lines.append("notas_atualizadas:")
    lines.extend(
        _sample_lines(report.amostra_notas_atualizadas, _format_nota_amostra)
    )
    lines.append("notas_inalteradas:")
    lines.extend(
        _sample_lines(report.amostra_notas_inalteradas, _format_nota_amostra)
    )
    lines.append("comentarios_criados:")
    lines.extend(
        _sample_lines(
            report.amostra_comentarios_criados, _format_comentario_amostra
        )
    )
    lines.append("comentarios_inalterados:")
    lines.extend(
        _sample_lines(
            report.amostra_comentarios_inalterados, _format_comentario_amostra
        )
    )
    lines.append("orfaos_avaliacao:")
    lines.extend(
        _sample_lines(report.orfaos_avaliacao, _format_orfao_avaliacao)
    )
    lines.append("orfaos_competencia:")
    lines.extend(
        _sample_lines(report.orfaos_competencia, _format_orfao_competencia)
    )
    lines.append("orfaos_autor:")
    lines.extend(_sample_lines(report.orfaos_autor, _format_orfao_autor))
    lines.append("conflitos_lider_divergente:")
    lines.extend(
        _sample_lines(
            report.conflitos_lider_divergente, _format_lider_divergente
        )
    )
    lines.append("conflitos_ciclo_aberto:")
    lines.extend(
        _sample_lines(report.conflitos_ciclo_aberto, _format_ciclo_aberto)
    )
    lines.append("habilidades_extras_criadas:")
    lines.extend(
        _sample_lines(
            report.amostra_habilidades_extras, _format_habilidade_extra
        )
    )
    lines.append("ids_colapsados_resolvidos:")
    lines.extend(
        _sample_lines(
            report.ids_colapsados_resolvidos, _format_id_colapsado_resolvido
        )
    )
    lines.append("conflitos:")
    lines.extend(_sample_lines(report.conflitos, _format_conflito_notas))
    lines.append("")
    lines.append("=== Fim ===")
    return _scrub_notas_comentarios_text("\n".join(lines) + "\n")


def _sample_lines(
    entries: list[ReportEntry],
    formatter: Callable[[ReportEntry], str],
) -> list[str]:
    return [formatter(entry) for entry in entries[:_SAMPLE_MAX]]


def _repl_pii_field(match: re.Match[str]) -> str:
    return f"{match.group(1)}={mask_pii(match.group(2).strip())}"


def _token_ou_mascara(value: str, allowed: frozenset[str]) -> str:
    """Mantém token curto conhecido; texto livre → ``mask_pii`` (T025)."""
    text = str(value).strip()
    if not text:
        return ""
    if text.casefold() in allowed:
        return text
    return mask_pii(_mask_emails_in_text(text))


def _scrub_notas_comentarios_text(text: str) -> str:
    """T025 / SC-010: segunda passagem — sem e-mail/nome/comentário completos.

    Aplica-se linha a linha na amostra para não colapsar IDs mascarados
    de várias linhas num falso positivo de CPF (11+ dígitos concatenados).
    """
    scrubbed = _PII_FIELD_RE.sub(_repl_pii_field, text)
    marker = "--- Amostra (mascarada, max 5 por seção) ---"
    if marker not in scrubbed:
        return scrubbed
    head, _, rest = scrubbed.partition(marker)
    fim = "=== Fim ==="
    sample, sep, tail = rest.partition(fim)
    lines = [
        _mask_emails_in_text(line) if line.strip() else line
        for line in sample.split("\n")
    ]
    return head + marker + "\n".join(lines) + sep + tail


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
        parts.append(_mask_solides_ids_in_text(entry.extra.strip()))
    if entry.motivo.strip():
        parts.append(_mask_solides_ids_in_text(entry.motivo.strip()))
    return " | ".join(parts)


def _format_conflito_notas(entry: ReportEntry) -> str:
    """Conflito 013: além de IDs/e-mail/CPF, redige nome e texto livre."""
    return _PII_FIELD_RE.sub(_repl_pii_field, _format_conflito(entry))


def _format_ciclo(entry: ReportEntry) -> str:
    usuarios = _mask_emails_in_text(entry.label.strip()) if entry.label.strip() else ""
    motivo = _mask_emails_in_text(entry.motivo.strip()) if entry.motivo.strip() else ""
    return f"  - usuarios={usuarios} | motivo={motivo}"


def _format_ciclo_criado_amostra(entry: ReportEntry) -> str:
    return (
        f"  - solides_id={mask_solides_id(entry.label)}"
        f" | nome={_mask_emails_in_text(entry.extra)}"
        f" | status={entry.motivo.strip() or 'encerrado'}"
    )


def _format_orfao_usuario(entry: ReportEntry) -> str:
    return (
        f"  - solicitacao={mask_solides_id(entry.label)}"
        f" | avaliado_id={mask_solides_id(entry.extra)}"
        f" | motivo={entry.motivo.strip() or 'usuario_nao_resolvido'}"
    )


def _format_orfao_ciclo(entry: ReportEntry) -> str:
    parts = [f"  - solicitacao={mask_solides_id(entry.label)}"]
    if entry.extra.strip():
        parts.append(f"avaliado_id={mask_solides_id(entry.extra)}")
    parts.append(f"motivo={entry.motivo.strip() or 'ciclo_nao_resolvido'}")
    return " | ".join(parts)


def _format_ids_colapsados(entry: ReportEntry) -> str:
    # label = "sol=X, av=Y"
    group = _mask_group_key(entry.label)
    canonical = mask_solides_id(entry.extra)
    motivo = _mask_colapsados_motivo(entry.motivo)
    return f"  - grupo=({group}) | canonical={canonical} | {motivo}"


def _format_nota_amostra(entry: ReportEntry) -> str:
    lado = _token_ou_mascara(entry.motivo, _SAMPLE_LADO_TOKENS)
    parts = [
        f"  - avaliacao={mask_solides_id(entry.label)}",
        f"competencia={mask_solides_id(entry.extra)}",
    ]
    if lado:
        parts.append(f"lado={lado}")
    return " | ".join(parts)


def _format_comentario_amostra(entry: ReportEntry) -> str:
    """Só IDs mascarados + tipo; NEVER ``conteudo`` / nome / e-mail."""
    tipo = _token_ou_mascara(entry.motivo, _SAMPLE_TIPO_TOKENS)
    parts = [
        f"  - avaliacao={mask_solides_id(entry.label)}",
        f"autor={mask_solides_id(entry.extra)}",
    ]
    if tipo:
        parts.append(f"tipo={tipo}")
    return " | ".join(parts)


def _format_orfao_avaliacao(entry: ReportEntry) -> str:
    return (
        f"  - id_legado={mask_solides_id(entry.label)}"
        f" | motivo={entry.motivo.strip() or 'avaliacao_nao_resolvida'}"
    )


def _format_orfao_competencia(entry: ReportEntry) -> str:
    return (
        f"  - habilidade_id={mask_solides_id(entry.label)}"
        f" | motivo={entry.motivo.strip() or 'kpi_ou_sem_nota'}"
    )


def _format_orfao_autor(entry: ReportEntry) -> str:
    return (
        f"  - avaliador_id={mask_solides_id(entry.label)}"
        f" | motivo={entry.motivo.strip() or 'usuario_nao_resolvido'}"
    )


def _format_lider_divergente(entry: ReportEntry) -> str:
    return (
        f"  - avaliacao={mask_solides_id(entry.label)}"
        f" | competencia={mask_solides_id(entry.extra)}"
    )


def _format_ciclo_aberto(entry: ReportEntry) -> str:
    return (
        f"  - avaliacao={mask_solides_id(entry.label)}"
        f" | ciclo={mask_solides_id(entry.extra)}"
    )


def _format_habilidade_extra(entry: ReportEntry) -> str:
    tipo = entry.extra.strip() or "tecnica"
    return (
        f"  - solides_id={mask_solides_id(entry.label)}"
        f" | tipo={_mask_emails_in_text(tipo)}"
    )


def _format_id_colapsado_resolvido(entry: ReportEntry) -> str:
    return (
        f"  - colapsado={mask_solides_id(entry.label)}"
        f" → canônico={mask_solides_id(entry.extra)}"
    )


def _mask_group_key(label: str) -> str:
    """``sol=123, av=456`` → ``sol=***123, av=***456``."""
    parts: list[str] = []
    for chunk in label.split(","):
        chunk = chunk.strip()
        if "=" not in chunk:
            parts.append(mask_solides_id(chunk))
            continue
        key, _, value = chunk.partition("=")
        parts.append(f"{key.strip()}={mask_solides_id(value)}")
    return ", ".join(parts)


def _mask_colapsados_motivo(motivo: str) -> str:
    """Mascara lista ``colapsados=a,b,c`` preservando ``n_linhas``."""
    text = motivo.strip()
    if not text:
        return "colapsados= | n_linhas=0"
    if "colapsados=" not in text:
        return _mask_solides_ids_in_text(text)
    prefix, _, rest = text.partition("colapsados=")
    ids_part, sep, tail = rest.partition(" | ")
    masked_ids = ",".join(
        mask_solides_id(item) for item in ids_part.split(",") if item.strip()
    )
    if sep:
        return f"{prefix}colapsados={masked_ids} | {tail}"
    return f"{prefix}colapsados={masked_ids}"


def _mask_solides_ids_in_text(text: str) -> str:
    """Mascara valores após ``=`` que parecem IDs (além de e-mails/PII)."""
    masked = _mask_emails_in_text(text)

    def _repl_kv(match: re.Match[str]) -> str:
        return f"{match.group(1)}={mask_solides_id(match.group(2))}"

    return re.sub(
        r"\b(solicitacao|sol|av|avaliado_id|avaliador_id|avaliacao|"
        r"competencia|id_legado|habilidade_id|autor|colapsado|"
        r"can[oô]nico|canonical|solides_id|usuario|ciclo|"
        r"superior_id|ids)=([^\s|,]+)",
        _repl_kv,
        masked,
        flags=re.IGNORECASE,
    )


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
