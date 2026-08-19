"""Enrollment de Avaliacao mid-cycle (contracts/mid-cycle-enrollment-contract.md)."""

from __future__ import annotations

from apps.accounts.models import CustomUser
from apps.cycles.models import Ciclo
from apps.reviews.models import Avaliacao


def ensure_avaliacao_for_user(
    user: CustomUser,
    ciclo: Ciclo | None = None,
) -> Avaliacao | None:
    """Garante Avaliacao idempotente para colaborador ativo em ciclo aberto.

    Se ``user.is_active`` e existir ciclo aberto (ou ``ciclo`` passado e aberto):
    ``get_or_create`` de ``Avaliacao(ciclo, usuario)`` com ``etapa=input_metas``.
    Se já existir: retorna a existente (sem duplicar).
    Se sem ciclo aberto / user inativo: retorna ``None`` (no-op).
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

    avaliacao, _created = Avaliacao.objects.get_or_create(
        ciclo=ciclo,
        usuario=user,
        defaults={'etapa': Avaliacao.Etapa.INPUT_METAS},
    )
    return avaliacao
