"""Helpers compartilhados para ModelForms."""

from __future__ import annotations

from django.db.models import Q, QuerySet


def active_choices_queryset(
    base_qs: QuerySet,
    *,
    current_pk=None,
) -> QuerySet:
    """Ativos + valor atual (edição), para seletores com soft-delete.

    Em criação (`current_pk` ausente): só `is_active=True`.
    Em edição: inclui o pk atualmente vinculado mesmo se inativo.
    """
    q = Q(is_active=True)
    if current_pk is not None:
        q |= Q(pk=current_pk)
    return base_qs.filter(q)
