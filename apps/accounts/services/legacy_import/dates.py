"""Parser de datas do legado Sólides (serial Excel + ISO).

Conforme research R10 e ``contracts/column-mapping-contract.md`` §is_active.
Stdlib apenas — **sem** openpyxl (restrito a ``parse_xlsx.py``).
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

# Epoch Excel / Lotus 1-2-3 (compat openpyxl.from_excel).
_EXCEL_EPOCH = date(1899, 12, 30)


def parse_legacy_date(value: Any) -> date | None:
    """Converte valor cru de célula (ex. ``Data demissão``) em ``date``.

    Aceita:
    - ``None`` / vazio / ``0`` / ``0.0`` → ``None`` (sem demissão).
    - ``date`` / ``datetime`` já tipados (openpyxl).
    - ``int`` / ``float`` serial Excel (ex. ``45446.0``) via epoch 1899-12-30.
    - ``str`` ISO ``YYYY-MM-DD`` (e variantes ``fromisoformat``); ou string
      numérica serial / ``\"0\"``.

    Raises:
        ValueError: valor não vazio e não interpretável como data.
    """
    if value is None:
        return None

    if isinstance(value, bool):
        raise ValueError(f"data legado inválida (bool): {value!r}")

    if isinstance(value, datetime):
        return value.date()

    if isinstance(value, date):
        return value

    if isinstance(value, (int, float)):
        return _from_excel_serial(value)

    if isinstance(value, str):
        return _from_string(value)

    # Decimal e similares numéricos
    if hasattr(value, "__float__") and not isinstance(value, (bytes, bytearray)):
        try:
            return _from_excel_serial(float(value))
        except (TypeError, ValueError, OverflowError):
            pass

    raise ValueError(f"data legado não suportada: {type(value).__name__}={value!r}")


def is_dismissal_filled(value: Any) -> bool:
    """``True`` se ``Data demissão`` parseia para uma data (≠ sentinela zero)."""
    return parse_legacy_date(value) is not None


def is_active_from_dismissal(value: Any) -> bool:
    """``is_active(row) = NOT is_dismissal_filled(Data demissão)``."""
    return not is_dismissal_filled(value)


def _from_excel_serial(serial: float | int) -> date | None:
    if serial == 0 or serial == 0.0:
        return None
    # Parte fracionária = hora; import só precisa do dia civil.
    days = int(serial)
    if days == 0:
        return None
    return _EXCEL_EPOCH + timedelta(days=days)


def _from_string(raw: str) -> date | None:
    text = raw.strip()
    if not text:
        return None

    # Sentinela zero como string (export / CSV intermediário).
    if text in {"0", "0.0", "0.00"}:
        return None

    # ISO primeiro (contrato §Testes: ``2024-06-01``).
    try:
        parsed = date.fromisoformat(text[:10] if len(text) >= 10 and text[4] == "-" else text)
        return parsed
    except ValueError:
        pass

    # Serial Excel em string (ex. ``\"45446.0\"``).
    try:
        return _from_excel_serial(float(text.replace(",", ".")))
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"data legado inválida: {raw!r}") from exc
