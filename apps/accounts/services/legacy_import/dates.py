"""Parser de datas do legado Sólides (serial Excel + ISO).

Conforme research R10/R6 e ``contracts/column-mapping-contract.md``
(§is_active / §Normalização de nome). Stdlib + ``display_name`` —
**sem** openpyxl (restrito a ``parse_xlsx.py``).
"""

from __future__ import annotations

import re
from datetime import date, datetime, timedelta
from typing import Any

from apps.competencies.services.catalog_import.normalize import display_name

# Epoch Excel / Lotus 1-2-3 (compat openpyxl.from_excel).
_EXCEL_EPOCH = date(1899, 12, 30)

# Texto que parece serial Excel / número (ex. ``46113``, ``46113.0``).
_SERIAL_LIKE_RE = re.compile(r"^[+-]?\d+(?:[.,]\d+)?$")


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


def normalize_ciclo_nome(raw: Any) -> str:
    """Rótulo estável para ``Ciclo.nome`` (research R6 / column-mapping).

    - ``date`` / ``datetime`` tipados → ISO ``YYYY-MM-DD``.
    - Numérico / serial Excel-like → ``parse_legacy_date`` → ISO; se não
      parseável → ``ValueError('nome_serial_ambiguo')`` (não grava bruto).
    - Demais → ``display_name`` (strip + colapso de whitespace).

    Raises:
        ValueError: serial-like ambíguo (código ``nome_serial_ambiguo``).
    """
    if raw is None:
        return ""

    if isinstance(raw, datetime):
        return raw.date().isoformat()
    if isinstance(raw, date):
        return raw.isoformat()

    if _is_excel_serial_like(raw):
        try:
            parsed = parse_legacy_date(raw)
        except ValueError as exc:
            raise ValueError("nome_serial_ambiguo") from exc
        if parsed is None:
            raise ValueError("nome_serial_ambiguo")
        return parsed.isoformat()

    if isinstance(raw, str):
        return display_name(raw)
    return display_name(str(raw))


def is_dismissal_filled(value: Any) -> bool:
    """``True`` se ``Data demissão`` parseia para uma data (≠ sentinela zero)."""
    return parse_legacy_date(value) is not None


def is_active_from_dismissal(value: Any) -> bool:
    """``is_active(row) = NOT is_dismissal_filled(Data demissão)``."""
    return not is_dismissal_filled(value)


def _is_excel_serial_like(value: Any) -> bool:
    """``True`` se o valor parece serial Excel / número (não bool)."""
    if isinstance(value, bool):
        return False
    if isinstance(value, (int, float)):
        return True
    if isinstance(value, str):
        text = value.strip()
        return bool(text) and _SERIAL_LIKE_RE.fullmatch(text) is not None
    if hasattr(value, "__float__") and not isinstance(value, (bytes, bytearray)):
        return True
    return False


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
