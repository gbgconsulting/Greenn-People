"""Abertura e encerramento de ciclos de desempenho."""

from __future__ import annotations

from datetime import date

from django.apps import apps
from django.db import transaction
from django.db.models import Exists, OuterRef

from apps.accounts.models import CustomUser
from apps.cycles.exceptions import (
    CycleAlreadyOpenError,
    CycleMissingCutoffError,
    CycleNotOpenError,
)
from apps.cycles.models import Ciclo
from apps.reviews.services.enrollment import ensure_avaliacao_for_user


def open_cycle(ciclo: Ciclo, *, admitidos_ate: date | None = None) -> Ciclo:
    """Open ``ciclo`` with admission cutoff (multiple open cycles allowed).

    Resolves ``admitidos_ate`` from the keyword arg or the locked row.
    Raises ``CycleAlreadyOpenError`` if this cycle is already open.
    Raises ``CycleMissingCutoffError`` before opening if still missing.
    Creates evaluations only for users eligible via ``ensure_avaliacao_for_user``.
    """
    with transaction.atomic():
        locked = Ciclo.objects.select_for_update().get(pk=ciclo.pk)

        if locked.status == Ciclo.Status.ABERTO:
            raise CycleAlreadyOpenError('Este ciclo já está aberto.')

        resolved = (
            admitidos_ate if admitidos_ate is not None else locked.admitidos_ate
        )
        if resolved is None:
            raise CycleMissingCutoffError(
                'Defina "Admitidos até" no cadastro do ciclo antes de abrir.',
            )

        locked.admitidos_ate = resolved
        locked.status = Ciclo.Status.ABERTO
        locked.save()

        for user in CustomUser.objects.filter(is_active=True).iterator():
            ensure_avaliacao_for_user(user, ciclo=locked)

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
