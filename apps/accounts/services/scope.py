"""Resolução de escopo hierárquico por ``line_manager`` (contracts/scope-contract.md)."""

from __future__ import annotations

from typing import Literal

from django.db.models import QuerySet

from apps.accounts.models import CustomUser

ScopeLevel = Literal['collaborator', 'leader', 'manager', 'admin']
OwnershipVisao = Literal['proprias', 'equipe']

VISAO_PROPRIAS: OwnershipVisao = 'proprias'
VISAO_EQUIPE: OwnershipVisao = 'equipe'


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


def can_view_team_ownership_list(user: CustomUser) -> bool:
    """True se o usuário pode alternar para a fatia 'equipe' (escopo − self)."""
    return get_scope_level(user) != 'collaborator'


def resolve_ownership_visao(
    user: CustomUser,
    raw: str | None,
) -> OwnershipVisao:
    """Resolve ``?visao=`` para listas próprias vs equipe.

    - Colaborador puro: sempre ``proprias`` (pedido ``equipe`` é ignorado).
    - Líder/gestor/admin: ``equipe`` só se ``raw == 'equipe'``; default ``proprias``.
    - Valores desconhecidos → ``proprias`` (default seguro).

    Nunca amplia o escopo — só escolhe fatia dentro de ``get_visible_users``.
    """
    if not can_view_team_ownership_list(user):
        return VISAO_PROPRIAS
    if (raw or '').strip() == VISAO_EQUIPE:
        return VISAO_EQUIPE
    return VISAO_PROPRIAS


def apply_ownership_visao(
    qs: QuerySet,
    user: CustomUser,
    visao: OwnershipVisao,
    *,
    user_field: str = 'usuario',
) -> QuerySet:
    """Aplica fatia próprias/equipe sobre um QS já restrito por escopo."""
    if visao == VISAO_EQUIPE:
        return qs.exclude(**{f'{user_field}_id': user.pk})
    return qs.filter(**{f'{user_field}_id': user.pk})


def ownership_visao_equipe_label(user: CustomUser) -> str:
    """Rótulo da fatia equipe (admin = organização; demais = equipe)."""
    if get_scope_level(user) == 'admin':
        return 'Organização'
    return 'Equipe'


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
