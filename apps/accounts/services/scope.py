"""Resolução de escopo hierárquico por ``line_manager`` (contracts/scope-contract.md)."""

from __future__ import annotations

from typing import Literal

from django.db.models import QuerySet

from apps.accounts.models import CustomUser

ScopeLevel = Literal['collaborator', 'leader', 'manager', 'admin']


def get_scope_level(user: CustomUser) -> ScopeLevel:
    """Nível máximo de visão cumulativa do usuário."""
    if getattr(user, 'is_admin', False):
        return 'admin'
    if user.is_manager:
        return 'manager'
    if user.is_leader:
        return 'leader'
    return 'collaborator'


def get_visible_users(requesting_user: CustomUser) -> QuerySet[CustomUser]:
    """Retorna queryset de usuários visíveis ao ``requesting_user``.

    Papéis são cumulativos e derivados da hierarquia ``line_manager``:
    - admin: todos
    - manager: self + toda a subárvore (BFS por camadas ORM)
    - leader: self + liderados diretos
    - collaborator: apenas self
    """
    if not getattr(requesting_user, 'pk', None):
        return CustomUser.objects.none()

    level = get_scope_level(requesting_user)

    if level == 'admin':
        return CustomUser.objects.all()

    if level == 'manager':
        return CustomUser.objects.filter(pk__in=_subtree_ids(requesting_user))

    if level == 'leader':
        return CustomUser.objects.filter(pk__in=_self_and_direct_report_ids(requesting_user))

    return CustomUser.objects.filter(pk=requesting_user.pk)


def user_in_scope(requesting_user: CustomUser, target_user_id: int) -> bool:
    """True se ``target_user_id`` está no escopo de ``requesting_user``."""
    if not getattr(requesting_user, 'pk', None):
        return False
    return get_visible_users(requesting_user).filter(pk=target_user_id).exists()


def _self_and_direct_report_ids(user: CustomUser) -> set[int]:
    ids = {user.pk}
    ids.update(
        CustomUser.objects.filter(line_manager_id=user.pk).values_list('pk', flat=True),
    )
    return ids


def _subtree_ids(user: CustomUser) -> set[int]:
    """Coleta self + todos os descendentes via BFS em camadas ORM (sem CTE)."""
    visible: set[int] = {user.pk}
    frontier: list[int] = [user.pk]

    while frontier:
        next_layer = list(
            CustomUser.objects.filter(line_manager_id__in=frontier)
            .exclude(pk__in=visible)
            .values_list('pk', flat=True),
        )
        if not next_layer:
            break
        visible.update(next_layer)
        frontier = next_layer

    return visible
