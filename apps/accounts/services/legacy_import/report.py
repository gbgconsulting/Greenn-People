"""Tipos de relatório da importação de colaboradores legado Sólides.

Superfície pública reexportada por ``legacy_import.__init__``.
Formatação com amostra mascarada e helpers ``mask_*``: T007+.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ReportEntry:
    """Entrada de lista detalhada / amostra do relatório de carga.

    Convenções por seção (contrato §Formato do relatório):
    - criados / atualizados: ``label`` = nome; ``extra`` = e-mail mascarado
      (+ área/cargo em ``motivo`` quando útil).
    - nao_importaveis: ``label`` = linha; ``motivo`` = código.
    - conflitos: ``label`` = tipo; ``extra`` / ``motivo`` = detalhe mascarado.
    - ciclos_hierarquia: ``label`` = usuários (mascarados); ``motivo`` = código.
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


def format_report(report: ImportReport) -> str:
    """Serializa o relatório em texto UTF-8 (contrato §Formato).

    Implementação completa (amostra mascarada, ``mask_email``/``mask_pii``): T007.
    """
    raise NotImplementedError("format_report — pending T007")
