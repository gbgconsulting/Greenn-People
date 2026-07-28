"""De-paras legado → domínio: senioridade, tipo, KPI e classificação.

Contrato: `contracts/legado-domain-mapping-contract.md` §3–6.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

from .normalize import canonical_key

# --- §3 Senioridade → Cargo.nivel -------------------------------------------------

# Ordem = prioridade; primeira regra que casar vence.
# Frases multi-palavra antes de tokens curtos na mesma faixa (ex.: "tech lead" antes de "lead").
_NIVEL_RULES: tuple[tuple[tuple[str, ...], int], ...] = (
    (("estagiario", "estag", "trainee"), 1),
    (("jr", "junior"), 2),
    (("pl", "pleno"), 3),
    (("sr", "senior"), 4),
    (("tech lead", "ux lead", "qa lead", "lead"), 5),
    (
        (
            "gerente",
            "diretor",
            "coordenador",
            "coordenadora",
            "ceo",
            "presidente",
            "head",
        ),
        6,
    ),
)

_DEFAULT_CARGO_NIVEL = 6

# --- §4 Cargo.nivel → CargoCompetencia.nivel_esperado -----------------------------

_NIVEL_ESPERADO: dict[int, int] = {
    1: 2,
    2: 2,
    3: 3,
    4: 4,
    5: 4,
    6: 4,
}

# --- §5 Grupo legado → Competencia.tipo ------------------------------------------

_GRUPO_TIPO: dict[str, str] = {
    canonical_key("Liderança"): "lideranca",
    canonical_key("Comportamento"): "comportamental",
    canonical_key("Desempenho"): "tecnica",
}

# --- §6.1 KPI — chaves canônicas (família por igualdade ou prefixo+separador) ----

KPI_KEYS: frozenset[str] = frozenset(
    {
        canonical_key("SLA"),
        canonical_key("Lead time discovery"),
        canonical_key("Custo de nuvem por transação"),
        canonical_key("Throughput por Colaborador"),
        canonical_key("Índice de incidentes"),
        canonical_key("Tempo médio de espera na esteira"),
    }
)

# --- §6.2 Ambíguos — não importar nesta versão -----------------------------------

AMBIGUOUS_KEYS: frozenset[str] = frozenset(
    {
        canonical_key("Erros de usabilidade"),
        canonical_key(
            "Oportunidade de usabilidades entregues e cm problemas resolvidos"
        ),
        canonical_key("Oportunidades entregues de modernização"),
        canonical_key("Oportunidades tracionadas"),
        canonical_key("Monitoramento contínuo"),
    }
)

ClassificationKind = Literal["avaliavel", "excluidos_kpi", "nao_mapeados"]


@dataclass(frozen=True)
class CompetenciaClassification:
    """Resultado de `classify_competencia` (§6)."""

    kind: ClassificationKind
    motivo: str = ""
    tipo: str | None = None


def _has_delimited_pattern(text: str, pattern: str) -> bool:
    """Match de token/frase com boundary (não substring de outra palavra).

    Tokens de 1–2 caracteres (`jr`, `pl`, `sr`) e frases (`tech lead`) usam
    boundaries nas extremidades; whitespace interno da frase é flexível.
    """
    parts = pattern.split()
    body = r"\s+".join(re.escape(p) for p in parts)
    return re.search(rf"(?<!\w){body}(?!\w)", text) is not None


def infer_cargo_nivel(nome: str) -> int:
    """Infere `Cargo.nivel` (1–6) a partir de tokens no nome canônico (§3)."""
    key = canonical_key(nome)
    for patterns, nivel in _NIVEL_RULES:
        for pattern in patterns:
            if _has_delimited_pattern(key, pattern):
                return nivel
    return _DEFAULT_CARGO_NIVEL


def nivel_esperado_for(nivel: int) -> int:
    """Mapeia `Cargo.nivel` → `CargoCompetencia.nivel_esperado` (§4)."""
    try:
        return _NIVEL_ESPERADO[nivel]
    except KeyError as exc:
        raise ValueError(f"Cargo.nivel inválido: {nivel!r} (esperado 1–6)") from exc


def map_grupo_tipo(grupo: str) -> str | None:
    """Mapeia grupo legado → `Competencia.tipo`, ou None se desconhecido (§5)."""
    return _GRUPO_TIPO.get(canonical_key(grupo))


def _is_kpi_key(key: str) -> bool:
    """Igualdade ou família: base + separador (` - `, ` -`, espaço) (§6.1)."""
    for base in KPI_KEYS:
        if key == base:
            return True
        if key.startswith(base + " -") or key.startswith(base + " "):
            return True
    return False


def is_kpi(nome: str) -> bool:
    """True se o nome canônico casa com KPI de exclusão (§6.1)."""
    return _is_kpi_key(canonical_key(nome))


def is_ambiguous(nome: str) -> bool:
    """True se o nome está na lista documentada de ambíguos (§6.2)."""
    return canonical_key(nome) in AMBIGUOUS_KEYS


def classify_competencia(nome: str, grupo: str) -> CompetenciaClassification:
    """Classifica item de lista-competencias na ordem normativa §6.

    1. KPI → excluidos_kpi (motivo=kpi_operacional)
    2. Ambíguo → nao_mapeados (motivo=ambiguo)
    3. Grupo mapeável → avaliavel (+ tipo)
    4. Senão → nao_mapeados (motivo=grupo_desconhecido)
    """
    if is_kpi(nome):
        return CompetenciaClassification(
            kind="excluidos_kpi",
            motivo="kpi_operacional",
        )
    if is_ambiguous(nome):
        return CompetenciaClassification(
            kind="nao_mapeados",
            motivo="ambiguo",
        )
    tipo = map_grupo_tipo(grupo)
    if tipo is not None:
        return CompetenciaClassification(kind="avaliavel", tipo=tipo)
    return CompetenciaClassification(
        kind="nao_mapeados",
        motivo="grupo_desconhecido",
    )
