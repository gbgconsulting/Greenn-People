"""Aprovação de metas e resultados (contracts/stage-machine-contract.md)."""

from __future__ import annotations

from django.core.exceptions import PermissionDenied
from django.db import transaction

from apps.accounts.models import CustomUser
from apps.goals.models import Meta


def _ensure_approver(meta: Meta, approver: CustomUser) -> None:
    """Valida aprovador: line_manager do colaborador, ou is_admin se sem gestor.

    Raises:
        PermissionDenied: se o aprovador não for o responsável válido.
    """
    owner = meta.usuario
    manager_id = owner.line_manager_id

    if manager_id is None:
        if not getattr(approver, 'is_admin', False):
            raise PermissionDenied(
                'Colaborador sem gestor direto: apenas administradores '
                'podem aprovar ou reprovar.',
            )
        return

    if approver.pk != manager_id:
        raise PermissionDenied(
            'Apenas o gestor direto do colaborador pode aprovar ou reprovar.',
        )


def approve_meta(meta: Meta, approver: CustomUser) -> Meta:
    """Define ``Meta.status`` como aprovada."""
    _ensure_approver(meta, approver)
    with transaction.atomic():
        locked = Meta.objects.select_for_update().select_related('usuario').get(
            pk=meta.pk,
        )
        _ensure_approver(locked, approver)
        locked.status = Meta.Status.APROVADA
        locked.save(update_fields=['status', 'updated_at'])
        return locked


def reject_meta(meta: Meta, approver: CustomUser) -> Meta:
    """Define ``Meta.status`` como reprovada (reabertura via FR-026 / reopen)."""
    _ensure_approver(meta, approver)
    with transaction.atomic():
        locked = Meta.objects.select_for_update().select_related('usuario').get(
            pk=meta.pk,
        )
        _ensure_approver(locked, approver)
        locked.mark_reprovada()
        locked.save(update_fields=['status', 'updated_at'])
        return locked


def approve_resultado(meta: Meta, approver: CustomUser) -> Meta:
    """Define ``Meta.status_resultado`` como aprovado."""
    _ensure_approver(meta, approver)
    with transaction.atomic():
        locked = Meta.objects.select_for_update().select_related('usuario').get(
            pk=meta.pk,
        )
        _ensure_approver(locked, approver)
        locked.status_resultado = Meta.StatusResultado.APROVADO
        locked.save(update_fields=['status_resultado', 'updated_at'])
        return locked


def reject_resultado(meta: Meta, approver: CustomUser) -> Meta:
    """Define ``Meta.status_resultado`` como reprovado (reabertura via FR-026)."""
    _ensure_approver(meta, approver)
    with transaction.atomic():
        locked = Meta.objects.select_for_update().select_related('usuario').get(
            pk=meta.pk,
        )
        _ensure_approver(locked, approver)
        locked.mark_resultado_reprovado()
        locked.save(update_fields=['status_resultado', 'updated_at'])
        return locked
