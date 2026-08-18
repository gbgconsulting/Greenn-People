"""Helpers de snapshot write-once para ``AvaliacaoCompetencia``.

T008: ``peso_utilizado`` ← ``Decimal(Fator no Momento)`` (ausente /
não-numérico / ≤0 → ``fator_invalido``; **não** assumir 1);
``nivel_esperado_utilizado`` ← ``nivel_esperado_for(avaliado.cargo.nivel)``
da 003 (cargo irresolvível → ``nivel_irresolvivel``).

**NUNCA** ler ``CargoCompetencia``. Na 2ª run **não** reatribuir snapshots;
divergência → ``snapshot_divergente`` (capturar ``ValidationError`` write-once).

T002: stubs — corpos em T008.

Denylist intacta — **não** chama ``create_competency_lines``; **não** edita
``evaluation.py``.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any


def parse_peso_utilizado(fator: Any) -> Decimal:
    """Converte ``Fator no Momento`` em ``Decimal`` > 0.

    Ausente / não-numérico / ≤0 → conflito ``fator_invalido`` (T008).
    **Não** assume peso 1. **Não** lê ``CargoCompetencia.peso``.
    """
    raise NotImplementedError("T002 stub — implementar em T008")


def resolve_nivel_esperado(avaliado: Any) -> int:
    """Nível esperado via tabela 003 ``nivel_esperado_for(cargo.nivel)``.

    Cargo ``None`` / nível ausente / ``ValueError`` → ``nivel_irresolvivel``.
    **NUNCA** ler ``CargoCompetencia.nivel_esperado``.
    """
    raise NotImplementedError("T002 stub — implementar em T008")
