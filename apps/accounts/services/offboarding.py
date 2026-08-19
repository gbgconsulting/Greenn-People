"""Reatribuição em lote no offboarding (contracts/catalog-offboarding-contract.md)."""

from __future__ import annotations

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction

from apps.accounts.models import CustomUser
from apps.audit.context import audit_actor


def reassign_direct_reports(
    *,
    from_manager: CustomUser,
    to_manager: CustomUser,
    actor: CustomUser,
) -> int:
    """Atualiza ``line_manager`` de todos os liderados ativos de ``from_manager``.

    Valida: ``to_manager`` ativo; ``to_manager`` ≠ ``from_manager``; ``actor``
    autorizado (admin/RH). Retorna a quantidade atualizada. Cada alteração
    gera AuditLog de ``line_manager_id`` com o ``actor``.
    """
    if not getattr(actor, 'is_admin', False):
        raise PermissionDenied(
            'Apenas administradores podem reatribuir liderados em lote.',
        )

    if not getattr(to_manager, 'is_active', False):
        raise ValidationError('O novo gestor precisa estar ativo.')

    if getattr(to_manager, 'pk', None) == getattr(from_manager, 'pk', None):
        raise ValidationError(
            'O novo gestor deve ser diferente do gestor de origem.',
        )

    with transaction.atomic():
        # Lock order: from → to → reports (pk) to serialize offboarding and
        # avoid lost updates / deadlocks under concurrent edits.
        locked_from = CustomUser.objects.select_for_update().get(
            pk=from_manager.pk,
        )
        locked_to = CustomUser.objects.select_for_update().get(pk=to_manager.pk)
        if not locked_to.is_active:
            raise ValidationError('O novo gestor precisa estar ativo.')
        if locked_to.pk == locked_from.pk:
            raise ValidationError(
                'O novo gestor deve ser diferente do gestor de origem.',
            )

        reports = list(
            CustomUser.objects.select_for_update()
            .filter(
                line_manager_id=locked_from.pk,
                is_active=True,
            )
            .order_by('pk'),
        )
        # One save per report so audit signals emit line_manager_id AuditLog
        # with ``actor``; bulk_update would skip that trail (FR-011 / T022).
        with audit_actor(actor):
            for report in reports:
                report.line_manager = locked_to
                report.save(update_fields=['line_manager'])

        if locked_from.has_active_direct_reports():
            raise ValidationError(
                'Ainda restam liderados ativos; a desativação continua bloqueada.',
            )

    return len(reports)
