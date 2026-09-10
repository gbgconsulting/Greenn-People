"""Internal audit helpers — not exposed via user-facing forms."""

from __future__ import annotations

from typing import Any

from django.db.models import Model

from apps.audit.context import get_audit_actor
from apps.audit.models import AuditLog


def serialize_audit_value(value: Any) -> str:
    """Normalize field values for valor_anterior / valor_novo."""
    if value is None:
        return ''
    return str(value)


def write_audit_log(
    *,
    acao: str,
    entity_type: str,
    entity_id: int,
    campo: str = '',
    valor_anterior: str = '',
    valor_novo: str = '',
    usuario=None,
) -> AuditLog:
    """Create one AuditLog row (append-only entry point for services/signals)."""
    if usuario is None:
        usuario = get_audit_actor()
    return AuditLog.objects.create(
        usuario=usuario,
        acao=acao,
        entity_type=entity_type,
        entity_id=entity_id,
        campo=campo,
        valor_anterior=valor_anterior,
        valor_novo=valor_novo,
    )


def entity_type_for(obj: Model) -> str:
    """Canonical label used in AuditLog.entity_type (e.g. ``reviews.Avaliacao``)."""
    return f'{obj._meta.app_label}.{obj._meta.object_name}'


def log_entity_created(
    *,
    instance: Model,
    fields: dict[str, Any] | None = None,
    usuario=None,
) -> list[AuditLog]:
    """Append CREATE AuditLog rows for a newly persisted entity (FR-016).

    One row per key field when ``fields`` is provided so quem/quando/por quê
    of the creation can be reconstructed from the append-only trail.
    ``usuario`` defaults to the audit actor context (``None`` for Celery/Beat).
    """
    entity_type = entity_type_for(instance)
    entity_id = instance.pk
    if not fields:
        return [
            write_audit_log(
                acao=AuditLog.Acao.CREATE,
                entity_type=entity_type,
                entity_id=entity_id,
                usuario=usuario,
            ),
        ]
    logs: list[AuditLog] = []
    for campo, valor in fields.items():
        logs.append(
            write_audit_log(
                acao=AuditLog.Acao.CREATE,
                entity_type=entity_type,
                entity_id=entity_id,
                campo=campo,
                valor_anterior='',
                valor_novo=serialize_audit_value(valor),
                usuario=usuario,
            ),
        )
    return logs


def log_scope_denied(user, obj: Model) -> AuditLog:
    """RF-36: record access denied when the object exists but is out of scope."""
    return write_audit_log(
        usuario=user if getattr(user, 'is_authenticated', False) else None,
        acao=AuditLog.Acao.ACCESS_DENIED,
        entity_type=entity_type_for(obj),
        entity_id=obj.pk,
        campo='',
        valor_anterior='',
        valor_novo='',
    )


def log_field_changes(
    *,
    instance: Model,
    old_values: dict[str, Any] | None,
    tracked_fields: tuple[str, ...],
) -> None:
    """Emit one AuditLog row per changed tracked field (updates only)."""
    if old_values is None:
        return

    entity_type = entity_type_for(instance)
    entity_id = instance.pk

    for field in tracked_fields:
        old_val = serialize_audit_value(old_values.get(field))
        new_val = serialize_audit_value(getattr(instance, field))
        if old_val == new_val:
            continue
        write_audit_log(
            acao=AuditLog.Acao.UPDATE,
            entity_type=entity_type,
            entity_id=entity_id,
            campo=field,
            valor_anterior=old_val,
            valor_novo=new_val,
        )
