from __future__ import annotations

from typing import Any

from django.contrib.auth.mixins import UserPassesTestMixin
from django.db.models import Model, QuerySet
from django.http import Http404

from apps.core.htmx import is_htmx


class HtmxPaginatedListMixin:
    """ListView com ``paginate_by=20`` e partial HTMX (htmx-contract.md).

    Em requests ``HX-Request``, retorna ``partial_template_name`` (fragmento
    ``#list-container``) em vez do template completo.
    """

    paginate_by = 20
    partial_template_name: str | None = None

    def get_template_names(self) -> list[str]:
        if is_htmx(self.request) and self.partial_template_name:
            return [self.partial_template_name]
        return super().get_template_names()


class RequiresAdminMixin(UserPassesTestMixin):
    """Restrict the view to users with ``is_admin=True``."""

    def test_func(self) -> bool:
        user = self.request.user
        return bool(user.is_authenticated and getattr(user, 'is_admin', False))


class RequiresLeaderMixin(UserPassesTestMixin):
    """Restrict the view to users with ``is_leader=True`` (direct reports)."""

    def test_func(self) -> bool:
        user = self.request.user
        return bool(user.is_authenticated and getattr(user, 'is_leader', False))


class RequiresManagerMixin(UserPassesTestMixin):
    """Restrict the view to users with ``is_manager=True``."""

    def test_func(self) -> bool:
        user = self.request.user
        return bool(user.is_authenticated and getattr(user, 'is_manager', False))


class RequiresManagerOrAdminMixin(UserPassesTestMixin):
    """Restrict the view to managers or admins (e.g. adherence panel)."""

    def test_func(self) -> bool:
        user = self.request.user
        if not user.is_authenticated:
            return False
        return bool(
            getattr(user, 'is_admin', False) or getattr(user, 'is_manager', False),
        )


class ScopedObjectMixin:
    """Restringe listagem e detalhe ao escopo do usuário autenticado.

    Usa ``scope_user_field`` (lookup Django, ex.: ``usuario`` ou
    ``avaliacao__usuario``) para filtrar o queryset e validar o objeto.
    Acesso a registro existente fora do escopo gera Http404 e auditoria (RF-36).
    """

    scope_user_field: str = 'usuario'

    def get_queryset(self) -> QuerySet:
        from apps.accounts.services.scope import get_visible_users

        qs = super().get_queryset()
        visible = get_visible_users(self.request.user)
        return qs.filter(**{f'{self.scope_user_field}__in': visible})

    def get_object(self, queryset: QuerySet | None = None) -> Model:
        from apps.accounts.services.scope import user_in_scope
        from apps.audit.services import log_scope_denied

        # Queryset sem filtro de escopo: distingue ID inexistente de fora do escopo.
        if queryset is None:
            queryset = super(ScopedObjectMixin, self).get_queryset()

        obj = super().get_object(queryset=queryset)
        scope_user = self._resolve_scope_user(obj)
        if not user_in_scope(self.request.user, scope_user.pk):
            log_scope_denied(self.request.user, obj)
            raise Http404()
        return obj

    def _resolve_scope_user(self, obj: Any) -> Any:
        """Resolve o usuário de escopo, inclusive em lookups aninhados (``a__b``)."""
        value = obj
        for attr in self.scope_user_field.split('__'):
            value = getattr(value, attr)
        return value
