"""Abertura e encerramento de ciclos de desempenho."""

from __future__ import annotations

from django.apps import apps
from django.db import transaction
from django.db.models import Exists, OuterRef

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
    """Close an open cycle; block stage advances and freeze completion flags.

    Sets ``Ciclo.status=encerrado`` so ``advance_stage`` raises
    ``CycleClosedError``. Marks each ``Avaliacao.concluida`` for the
    completion KPI (feedback líder + ``ciente_em``).
    """
    with transaction.atomic():
        locked = Ciclo.objects.select_for_update().get(pk=ciclo.pk)

        if locked.status != Ciclo.Status.ABERTO:
            raise CycleNotOpenError('Este ciclo não está aberto.')

        locked.status = Ciclo.Status.ENCERRADO
        locked.save()

        _freeze_avaliacao_conclusao(locked)
        return locked


def _freeze_avaliacao_conclusao(ciclo: Ciclo) -> None:
    """Persist ``concluida`` on all evaluations of ``ciclo`` (FR-017 / RF-16.1)."""
    Avaliacao = apps.get_model('reviews', 'Avaliacao')
    Feedback = apps.get_model('reviews', 'Feedback')

    feedback_ciente = Feedback.objects.filter(
        avaliacao_id=OuterRef('pk'),
        tipo='lider',
        ciente_em__isnull=False,
    )
    base = Avaliacao.objects.filter(ciclo_id=ciclo.pk)
    concluidas_ids = list(
        base.annotate(_ok=Exists(feedback_ciente))
        .filter(_ok=True)
        .values_list('pk', flat=True),
    )
    if concluidas_ids:
        base.filter(pk__in=concluidas_ids).update(concluida=True)
        base.exclude(pk__in=concluidas_ids).update(concluida=False)
    else:
        base.update(concluida=False)
