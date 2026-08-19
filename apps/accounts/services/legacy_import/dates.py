"""Parser de datas/datetimes do legado Sólides (serial Excel + ISO).

Conforme research R10/R6/R12 (010/011/013) e R8 (014) +
``contracts/column-mapping-contract.md`` (§is_active / §Normalização de
nome / §Datas). Stdlib + Django ``USE_TZ`` + ``display_name`` — **sem**
openpyxl (restrito a ``parse_xlsx.py``).

014 (T005): reusar estes helpers — **não** duplicar em ``pdi/``.

- ``Data de Entrega`` (prazo da ação) → ``parse_legacy_date``
- ``Criado em`` (material do digest, se parseável) → ``parse_legacy_datetime``

Estender **somente** se o dump 6.5.6 trouxer formato fora de serial Excel,
``date``/``datetime`` tipados, ISO/``fromisoformat``, ou sentinela ``0``/vazio.
"""

from __future__ import annotations

import re
from datetime import date, datetime, time, timedelta
from typing import Any

from django.conf import settings
from django.utils import timezone

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


def parse_legacy_datetime(value: Any) -> datetime | None:
    """Converte valor cru de célula (ex. ``Criado em``) em ``datetime``.

    Aceita:
    - ``None`` / vazio / ``0`` / ``0.0`` → ``None`` (ausente).
    - ``datetime`` já tipado (openpyxl) — aware se ``USE_TZ``.
    - ``date`` tipado (sem hora) → meia-noite, aware se ``USE_TZ``.
    - ``int`` / ``float`` serial Excel (epoch 1899-12-30) **com fração de
      dia** convertida em hora.
    - ``str`` ISO (``fromisoformat``, inclusive ``Z``) ou string numérica
      serial / ``\"0\"``.

    Raises:
        ValueError: valor não vazio e não interpretável como datetime.
    """
    if value is None:
        return None

    if isinstance(value, bool):
        raise ValueError(f"datetime legado inválido (bool): {value!r}")

    if isinstance(value, datetime):
        return _ensure_tz(value)

    if isinstance(value, date):
        return _ensure_tz(datetime.combine(value, time.min))

    if isinstance(value, (int, float)):
        parsed = _from_excel_serial_datetime(value)
        return None if parsed is None else _ensure_tz(parsed)

    if isinstance(value, str):
        parsed = _from_string_datetime(value)
        return None if parsed is None else _ensure_tz(parsed)

    if hasattr(value, "__float__") and not isinstance(value, (bytes, bytearray)):
        try:
            parsed = _from_excel_serial_datetime(float(value))
        except (TypeError, ValueError, OverflowError):
            pass
        else:
            return None if parsed is None else _ensure_tz(parsed)

    raise ValueError(
        f"datetime legado não suportado: {type(value).__name__}={value!r}"
    )


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


def _ensure_tz(dt: datetime) -> datetime:
    """Naive → aware no TZ corrente se ``USE_TZ``; aware permanece."""
    if timezone.is_aware(dt):
        return dt
    if settings.USE_TZ:
        return timezone.make_aware(dt, timezone.get_current_timezone())
    return dt


def _from_excel_serial_datetime(serial: float | int) -> datetime | None:
    if serial == 0 or serial == 0.0:
        return None
    # Parte inteira = dia civil; fração = hora (contrato §Datas).
    days = int(serial)
    if days == 0:
        return None
    fraction = float(serial) - days
    microseconds = round(fraction * 86_400 * 1_000_000)
    extra_days, microseconds = divmod(microseconds, 86_400 * 1_000_000)
    try:
        return datetime.combine(_EXCEL_EPOCH, time.min) + timedelta(
            days=days + extra_days,
            microseconds=microseconds,
        )
    except OverflowError as exc:
        raise ValueError(
            f"datetime legado serial fora do intervalo: {serial!r}"
        ) from exc


def _from_string_datetime(raw: str) -> datetime | None:
    text = raw.strip()
    if not text:
        return None

    if text in {"0", "0.0", "0.00"}:
        return None

    iso = text[:-1] + "+00:00" if text.endswith(("Z", "z")) else text
    try:
        return datetime.fromisoformat(iso)
    except ValueError:
        pass

    if len(text) >= 10 and text[4] == "-":
        try:
            return datetime.combine(date.fromisoformat(text[:10]), time.min)
        except ValueError:
            pass

    try:
        return _from_excel_serial_datetime(float(text.replace(",", ".")))
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"datetime legado inválido: {raw!r}") from exc
