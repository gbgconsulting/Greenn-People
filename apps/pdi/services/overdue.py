"""Recálculo de status de atraso de ações de PDI."""

from __future__ import annotations

from datetime import date

from django.utils import timezone

from apps.pdi.models import AcaoPDI


def recalculate_overdue_status(
    acao: AcaoPDI,
    today: date | None = None,
) -> None:
    """Ajusta ``status`` após alteração de ``prazo`` (FR-018).

    - ``atrasada`` + ``prazo >= hoje`` → ``pendente``
    - ``atrasada`` + prazo ainda passado → permanece ``atrasada``
    - marcar atraso de pendente/em_andamento com prazo passado fica a cargo
      do job diário ``mark_overdue_pdi_actions``
    """
    if today is None:
        today = timezone.localdate()

    if (
        acao.status == AcaoPDI.Status.ATRASADA
        and acao.prazo >= today
    ):
        acao.status = AcaoPDI.Status.PENDENTE
