"""Helpers de snapshot write-once para ``AvaliacaoCompetencia``.

T008: ``peso_utilizado`` ← ``Decimal(Fator no Momento)`` (ausente /
não-numérico / ≤0 → ``fator_invalido``; **não** assumir 1);
``nivel_esperado_utilizado`` ← ``nivel_esperado_for(avaliado.cargo.nivel)``
da 003 (cargo irresolvível → ``nivel_irresolvivel``).

**NUNCA** ler ``CargoCompetencia``. Na 2ª run **não** reatribuir snapshots;
divergência → ``snapshot_divergente`` (capturar ``ValidationError`` write-once).

Denylist intacta — **não** chama ``create_competency_lines``; **não** edita
``evaluation.py``.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any

from django.core.exceptions import ValidationError

from apps.competencies.services.catalog_import.mapping import nivel_esperado_for
from apps.reviews.models import AvaliacaoCompetencia

_PESO_QUANT = Decimal('0.01')
_SNAPSHOT_FIELDS = ('peso_utilizado', 'nivel_esperado_utilizado')
_WRITE_ONCE_FRAGMENT = 'write-once'


class SnapshotConflict(Exception):
    """Conflito de snapshot não-fatal — relatório, sem persistir a linha.

    ``code`` alimenta ``record_conflito(tipo=...)``:
    ``fator_invalido`` | ``nivel_irresolvivel`` | ``snapshot_divergente``.
    """

    def __init__(self, code: str, detail: str = '') -> None:
        self.code = code
        self.detail = detail
        super().__init__(detail or code)


def parse_peso_utilizado(fator: Any) -> Decimal:
    """Converte ``Fator no Momento`` em ``Decimal`` > 0.

    Ausente / não-numérico / ≤0 → ``SnapshotConflict('fator_invalido')``.
    **Não** assume peso 1. **Não** lê ``CargoCompetencia.peso``.
    """
    if fator is None or isinstance(fator, bool):
        raise SnapshotConflict('fator_invalido')

    if isinstance(fator, str):
        text = fator.strip()
        if not text:
            raise SnapshotConflict('fator_invalido')
        if ',' in text and '.' in text:
            raise SnapshotConflict('fator_invalido')
        text = text.replace(',', '.')
        try:
            peso = Decimal(text)
        except InvalidOperation as exc:
            raise SnapshotConflict('fator_invalido') from exc
    elif isinstance(fator, Decimal):
        peso = fator
    elif isinstance(fator, int):
        peso = Decimal(fator)
    elif isinstance(fator, float):
        peso = Decimal(str(fator))
    else:
        raise SnapshotConflict('fator_invalido')

    if not peso.is_finite():
        raise SnapshotConflict('fator_invalido')

    peso = peso.quantize(_PESO_QUANT)
    if peso <= 0:
        raise SnapshotConflict('fator_invalido')
    return peso


def resolve_nivel_esperado(avaliado: Any) -> int:
    """Nível esperado via tabela 003 ``nivel_esperado_for(cargo.nivel)``.

    Cargo ``None`` / nível ausente / ``ValueError`` →
    ``SnapshotConflict('nivel_irresolvivel')``.
    **NUNCA** ler ``CargoCompetencia.nivel_esperado``.
    """
    if avaliado is None:
        raise SnapshotConflict('nivel_irresolvivel')

    cargo = getattr(avaliado, 'cargo', None)
    if cargo is None:
        raise SnapshotConflict('nivel_irresolvivel')

    nivel = getattr(cargo, 'nivel', None)
    if nivel is None or isinstance(nivel, bool):
        raise SnapshotConflict('nivel_irresolvivel')

    try:
        return nivel_esperado_for(int(nivel))
    except (TypeError, ValueError) as exc:
        raise SnapshotConflict('nivel_irresolvivel') from exc


def snapshots_match(
    linha: AvaliacaoCompetencia,
    peso: Decimal,
    nivel: int | Decimal,
) -> bool:
    """True se snapshots persistidos coincidem bit-a-bit com a fonte."""
    return Decimal(linha.peso_utilizado) == Decimal(peso) and Decimal(
        linha.nivel_esperado_utilizado
    ) == Decimal(nivel)


def apply_snapshots(
    linha: AvaliacaoCompetencia,
    peso: Decimal,
    nivel: int | Decimal,
) -> None:
    """1ª run: preenche snapshots. 2ª run: **não** reatribui.

    Fonte divergente do persistido → ``SnapshotConflict('snapshot_divergente')``
    sem mutar os campos snapshot da instância.
    """
    peso_dec = Decimal(peso)
    nivel_dec = Decimal(nivel)
    if linha.pk is None:
        linha.peso_utilizado = peso_dec
        linha.nivel_esperado_utilizado = nivel_dec
        return

    if not snapshots_match(linha, peso_dec, nivel_dec):
        raise SnapshotConflict('snapshot_divergente')


def is_write_once_validation_error(exc: BaseException) -> bool:
    """True se ``ValidationError`` veio do ``save()`` write-once do model."""
    if not isinstance(exc, ValidationError):
        return False
    message_dict = getattr(exc, 'message_dict', None)
    if isinstance(message_dict, dict) and any(
        field in message_dict for field in _SNAPSHOT_FIELDS
    ):
        return True
    messages = getattr(exc, 'messages', None) or []
    return any(_WRITE_ONCE_FRAGMENT in str(msg) for msg in messages)


def conflict_from_write_once(exc: BaseException) -> SnapshotConflict | None:
    """Mapeia ``ValidationError`` write-once → ``snapshot_divergente``.

    Retorna ``None`` se o erro não for o invariante de snapshot — o caller
    (T009) re-levanta os demais ``ValidationError``.
    """
    if is_write_once_validation_error(exc):
        return SnapshotConflict('snapshot_divergente')
    return None
