"""Abertura e encerramento de ciclos de desempenho."""

from __future__ import annotations

from django.apps import apps
from django.db import transaction

from apps.accounts.models import CustomUser
from apps.cycles.exceptions import CycleAlreadyOpenError, CycleNotOpenError
from apps.cycles.models import Ciclo

# Initial stage for new Avaliacao rows (contracts/stage-machine-contract.md).
_ETAPA_INICIAL = 'input_metas'


def open_cycle(ciclo: Ciclo) -> Ciclo:
    """Open ``ciclo``, enforcing a single open cycle, and create evaluations.

    Creates one ``Avaliacao`` per ``CustomUser`` with ``is_active=True``
    (idempotent via get_or_create on ciclo+usuario).
    """
    with transaction.atomic():
        locked = Ciclo.objects.select_for_update().get(pk=ciclo.pk)

        if locked.status == Ciclo.Status.ABERTO:
            raise CycleAlreadyOpenError('Este ciclo já está aberto.')

        other_open = (
            Ciclo.objects.select_for_update()
            .filter(status=Ciclo.Status.ABERTO)
            .exclude(pk=locked.pk)
            .exists()
        )
        if other_open:
            raise CycleAlreadyOpenError(
                'Já existe um ciclo aberto. Encerre-o antes de abrir outro.',
            )

        locked.status = Ciclo.Status.ABERTO
        locked.save()

        Avaliacao = apps.get_model('reviews', 'Avaliacao')
        for user in CustomUser.objects.filter(is_active=True).iterator():
            Avaliacao.objects.get_or_create(
                ciclo=locked,
                usuario=user,
                defaults={'etapa': _ETAPA_INICIAL},
            )

        return locked


def close_cycle(ciclo: Ciclo) -> Ciclo:
    """Close an open cycle; blocks further stage advances (FR / stage machine)."""
    with transaction.atomic():
        locked = Ciclo.objects.select_for_update().get(pk=ciclo.pk)

        if locked.status != Ciclo.Status.ABERTO:
            raise CycleNotOpenError('Este ciclo não está aberto.')

        locked.status = Ciclo.Status.ENCERRADO
        locked.save()
        return locked
