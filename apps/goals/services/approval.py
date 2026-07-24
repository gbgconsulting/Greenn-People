"""Aprovação de metas e resultados (contracts/stage-machine-contract.md)."""

from __future__ import annotations

from django.core.exceptions import PermissionDenied
from django.db import transaction

from apps.accounts.models import CustomUser
from apps.audit.context import audit_actor
from apps.goals.models import Meta


def _ensure_approver(meta: Meta, approver: CustomUser) -> None:
    """Valida aprovador: ``is_admin`` sempre, ou ``line_manager`` do colaborador.

    Raises:
        PermissionDenied: se o aprovador não for o responsável válido.
    """
    # Exceção RH (FR-014): admin aprova/reprova com ou sem gestor presente.
    if getattr(approver, 'is_admin', False):
        return

    manager_id = meta.usuario.line_manager_id
    if manager_id is None:
        raise PermissionDenied(
            'Colaborador sem gestor direto: apenas administradores '
            'podem aprovar ou reprovar.',
        )

    if approver.pk != manager_id:
        raise PermissionDenied(
            'Apenas o gestor direto do colaborador pode aprovar ou reprovar.',
        )


def _ensure_meta_pending(meta: Meta) -> None:
    """Só permite ação quando ``Meta.status`` ainda está pendente."""
    if meta.status != Meta.Status.PENDENTE:
        raise PermissionDenied(
            'Só é possível aprovar ou reprovar metas pendentes.',
        )


def _ensure_resultado_pending(meta: Meta) -> None:
    """Só permite ação quando o resultado ainda está pendente."""
    if meta.status != Meta.Status.APROVADA:
        raise PermissionDenied(
            'Só é possível aprovar ou reprovar resultados de metas aprovadas.',
        )
    if meta.status_resultado != Meta.StatusResultado.PENDENTE:
        raise PermissionDenied(
            'Só é possível aprovar ou reprovar resultados pendentes.',
        )


def approve_meta(meta: Meta, approver: CustomUser) -> Meta:
    """Define ``Meta.status`` como aprovada."""
    _ensure_approver(meta, approver)
    with transaction.atomic():
        locked = Meta.objects.select_for_update().select_related('usuario').get(
            pk=meta.pk,
        )
        _ensure_approver(locked, approver)
        _ensure_meta_pending(locked)
        locked.status = Meta.Status.APROVADA
        # FR-015: AuditLog.actor = aprovador real (admin ou gestor).
        with audit_actor(approver):
            locked.save(update_fields=['status', 'updated_at'])
        return locked


def reject_meta(meta: Meta, approver: CustomUser) -> Meta:
    """Persiste ``Meta.status`` como reprovada.

    Não altera ``Avaliacao.etapa``. Não chama ``Meta.reopen()`` — a reabertura
    para ``pendente`` ocorre apenas quando o colaborador salva uma correção elegível
    (FR-026 / ``contracts/post-rejection-contract.md``).
    """
    _ensure_approver(meta, approver)
    with transaction.atomic():
        locked = Meta.objects.select_for_update().select_related('usuario').get(
            pk=meta.pk,
        )
        _ensure_approver(locked, approver)
        _ensure_meta_pending(locked)
        locked.mark_reprovada()
        with audit_actor(approver):
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
        _ensure_resultado_pending(locked)
        locked.status_resultado = Meta.StatusResultado.APROVADO
        with audit_actor(approver):
            locked.save(update_fields=['status_resultado', 'updated_at'])
        return locked


def reject_resultado(meta: Meta, approver: CustomUser) -> Meta:
    """Persiste ``Meta.status_resultado`` como reprovado.

    Não altera ``Avaliacao.etapa``. Não chama ``Meta.reopen_resultado()`` — a
    reabertura para ``pendente`` ocorre apenas na correção elegível do colaborador
    (FR-026 / ``contracts/post-rejection-contract.md``).
    """
    _ensure_approver(meta, approver)
    with transaction.atomic():
        locked = Meta.objects.select_for_update().select_related('usuario').get(
            pk=meta.pk,
        )
        _ensure_approver(locked, approver)
        _ensure_resultado_pending(locked)
        locked.mark_resultado_reprovado()
        with audit_actor(approver):
            locked.save(update_fields=['status_resultado', 'updated_at'])
        return locked
