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

# --- §6.1 KPI — chaves canônicas (igualdade ou família por prefixo+separador) ----

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

# Bases com variantes de sufixo documentadas (data-model *; exemplos §6.1).
KPI_FAMILY_BASES: frozenset[str] = frozenset(
    {
        canonical_key("Throughput por Colaborador"),
        canonical_key("Índice de incidentes"),
    }
)

# Separadores de família na ordem do contrato: ` - `, ` -`, espaço.
_KPI_FAMILY_SEPARATORS: tuple[str, ...] = (" - ", " -", " ")

# --- §6.2 Ambíguos — não importar nesta versão -----------------------------------
# Nomes exatos da tabela do contrato. Match só por igualdade de `canonical_key`
# (sem família/prefixo, ao contrário de §6.1). Mesmo com grupo mapeável
# (ex.: Desempenho → tecnica), classificação → `nao_mapeados` e **não persiste**.

AMBIGUOUS_LEGACY_NAMES: tuple[str, ...] = (
    "Erros de usabilidade",
    "Oportunidade de usabilidades entregues e cm problemas resolvidos",
    "Oportunidades entregues de modernização",
    "Oportunidades tracionadas",
    "Monitoramento contínuo",
)

AMBIGUOUS_KEYS: frozenset[str] = frozenset(
    canonical_key(name) for name in AMBIGUOUS_LEGACY_NAMES
)

MOTIVO_AMBIGUO = "ambiguo"

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


def _matches_kpi_family(key: str, base: str) -> bool:
    """True se `key` é `base` + separador + sufixo não vazio (§6.1)."""
    for sep in _KPI_FAMILY_SEPARATORS:
        prefix = f"{base}{sep}"
        if not key.startswith(prefix):
            continue
        remainder = key[len(prefix) :]
        if remainder.strip():
            return True
    return False


def _is_kpi_key(key: str) -> bool:
    """Igualdade em KPI_KEYS ou família (prefixo + separador) (§6.1).

    `KPI_FAMILY_BASES` documenta throughput / índice de incidentes (sufixos).
    A regra geral do contrato aplica o mesmo padrão a qualquer base em KPI_KEYS;
    bases mais longas são avaliadas primeiro.
    """
    if key in KPI_KEYS:
        return True
    for base in sorted(KPI_KEYS, key=len, reverse=True):
        if _matches_kpi_family(key, base):
            return True
    return False


def is_kpi(nome: str) -> bool:
    """True se o nome canônico casa com KPI de exclusão (§6.1)."""
    return _is_kpi_key(canonical_key(nome))


def is_ambiguous(nome: str) -> bool:
    """True se o nome canônico ∈ lista documentada §6.2 (igualdade exata)."""
    return canonical_key(nome) in AMBIGUOUS_KEYS


def classify_competencia(nome: str, grupo: str) -> CompetenciaClassification:
    """Classifica item de lista-competencias na ordem normativa §6.

    1. KPI → excluidos_kpi (motivo=kpi_operacional)
    2. Ambíguo → nao_mapeados (motivo=ambiguo) — bloqueia persistência
    3. Grupo mapeável → avaliavel (+ tipo)
    4. Senão → nao_mapeados (motivo=grupo_desconhecido)

    Somente ``kind=avaliavel`` é elegível a upsert de ``Competencia``.
    """
    if is_kpi(nome):
        return CompetenciaClassification(
            kind="excluidos_kpi",
            motivo="kpi_operacional",
        )
    if is_ambiguous(nome):
        return CompetenciaClassification(
            kind="nao_mapeados",
            motivo=MOTIVO_AMBIGUO,
        )
    tipo = map_grupo_tipo(grupo)
    if tipo is not None:
        return CompetenciaClassification(kind="avaliavel", tipo=tipo)
    return CompetenciaClassification(
        kind="nao_mapeados",
        motivo="grupo_desconhecido",
    )
