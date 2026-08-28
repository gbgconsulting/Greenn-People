"""Capture field-level changes on sensitive models into AuditLog."""

from __future__ import annotations

from typing import Any

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from apps.audit.services import log_field_changes

# RF-33 — sensitive fields per model (attr names as stored on the instance).
USER_TRACKED_FIELDS = (
    'is_admin',
    'is_active',
    'area_id',
    'cargo_id',
    'line_manager_id',
)

AVALIACAO_TRACKED_FIELDS = (
    'etapa',
    'nota_final_lider',
    'nota_final_autoavaliacao',
    'autoavaliacao_enviada',
)

CLASSIFICACAO_TRACKED_FIELDS = (
    'desempenho',
    'potencial',
    'quadrante',
    'visivel_ao_colaborador',
)

ACAO_PDI_TRACKED_FIELDS = (
    'status',
    'prazo',
)

META_TRACKED_FIELDS = (
    'status',
    'status_resultado',
)

_AUDIT_OLD_ATTR = '_audit_old_values'
_connected = False


def _snapshot(instance, fields: tuple[str, ...]) -> dict[str, Any] | None:
    if not instance.pk:
        return None
    try:
        old = instance.__class__.objects.get(pk=instance.pk)
    except instance.__class__.DoesNotExist:
        return None
    return {field: getattr(old, field) for field in fields}


def _attach_pre_save(sender, fields: tuple[str, ...]):
    @receiver(pre_save, sender=sender, weak=False)
    def _cache_old_values(sender, instance, **kwargs):
        setattr(instance, _AUDIT_OLD_ATTR, _snapshot(instance, fields))

    return _cache_old_values


def _attach_post_save(sender, fields: tuple[str, ...]):
    @receiver(post_save, sender=sender, weak=False)
    def _log_changes(sender, instance, created, **kwargs):
        if created:
            return
        old_values = getattr(instance, _AUDIT_OLD_ATTR, None)
        log_field_changes(
            instance=instance,
            old_values=old_values,
            tracked_fields=fields,
        )

    return _log_changes


def connect_audit_signals() -> None:
    """Wire pre_save/post_save for models that exist at ready() time."""
    global _connected
    if _connected:
        return
    _connected = True

    from apps.accounts.models import CustomUser
    from apps.reviews.models import Avaliacao

    _attach_pre_save(CustomUser, USER_TRACKED_FIELDS)
    _attach_post_save(CustomUser, USER_TRACKED_FIELDS)

    _attach_pre_save(Avaliacao, AVALIACAO_TRACKED_FIELDS)
    _attach_post_save(Avaliacao, AVALIACAO_TRACKED_FIELDS)

    from apps.pdi.models import AcaoPDI

    _attach_pre_save(AcaoPDI, ACAO_PDI_TRACKED_FIELDS)
    _attach_post_save(AcaoPDI, ACAO_PDI_TRACKED_FIELDS)

    from apps.goals.models import Meta

    _attach_pre_save(Meta, META_TRACKED_FIELDS)
    _attach_post_save(Meta, META_TRACKED_FIELDS)

    try:
        from django.apps import apps

        ClassificacaoTalento = apps.get_model('talent', 'ClassificacaoTalento')
    except LookupError:
        return

    _attach_pre_save(ClassificacaoTalento, CLASSIFICACAO_TRACKED_FIELDS)
    _attach_post_save(ClassificacaoTalento, CLASSIFICACAO_TRACKED_FIELDS)
