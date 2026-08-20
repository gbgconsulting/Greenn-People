"""Enrollment de Avaliacao mid-cycle (contracts/mid-cycle-enrollment-contract.md)."""

from __future__ import annotations

from apps.accounts.models import CustomUser
from apps.cycles.models import Ciclo
from apps.cycles.services.eligibility import user_eligible_for_ciclo
from apps.reviews.models import Avaliacao


def ensure_avaliacao_for_user(
    user: CustomUser,
    ciclo: Ciclo | None = None,
) -> Avaliacao | None:
    """Garante Avaliacao idempotente para colaborador elegível em ciclo aberto.

    Se ``user.is_active`` e existir ciclo aberto (ou ``ciclo`` passado e aberto):
    retorna Avaliacao existente (snapshot; nunca remove); se inelegível pelo
    predicado ``user_eligible_for_ciclo``, no-op ``None``; senão
    ``get_or_create`` com ``etapa=input_metas``.
    Se sem ciclo aberto / user inativo / ciclo encerrado: ``None``.
    """
    if not getattr(user, 'is_active', False) or not getattr(user, 'pk', None):
        return None

    if ciclo is None:
        ciclo = (
            Ciclo.objects.filter(status=Ciclo.Status.ABERTO)
            .order_by('-data_inicio')
            .first()
        )
    elif ciclo.status != Ciclo.Status.ABERTO:
        return None

    if ciclo is None:
        return None

    existing = Avaliacao.objects.filter(ciclo=ciclo, usuario=user).first()
    if existing is not None:
        return existing

    if not user_eligible_for_ciclo(user, ciclo):
        return None

    avaliacao, _created = Avaliacao.objects.get_or_create(
        ciclo=ciclo,
        usuario=user,
        defaults={'etapa': Avaliacao.Etapa.INPUT_METAS},
    )
    return avaliacao
