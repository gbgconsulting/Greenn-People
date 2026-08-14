"""Builder de tendência etapa/conclusão (US3).

Recebe o QS ``visible`` já resolvido pela view e a janela de ciclos (≤ N).
Este módulo **MUST NOT** chamar ``get_visible_users`` nem ``compute_adherence``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

    from django.db.models import QuerySet

    from apps.accounts.models import CustomUser
    from apps.cycles.models import Ciclo


def build_stage_history(
    visible: QuerySet[CustomUser],
    ciclos: Sequence[Ciclo],
) -> dict:
    """Monta o payload de tendência ``area`` de etapa/conclusão no escopo.

    API pública (T002 stub; implementação na T030).

    ``visible``
        QuerySet já autorizado pela view. Este builder **nunca** chama
        ``get_visible_users`` — o caller resolve o escopo (admin = visible
        admin; líder = ``get_visible_users`` sem o próprio, como o time).

    ``ciclos``
        Janela já recortada: lista ≤ ``HISTORY_DEFAULT_N`` (default 8),
        ordenada por ``data_inicio`` / ``pk``. O caller aplica o cap de
        ``?ciclos=``; este módulo **não** plota o arquivo completo.

    Retorno (T030)
        Payload canônico 009 via ``grouped_series_payload`` / ``series_payload``
        com ``type: area``. Contagens de ``Avaliacao.etapa`` (+ ``sem_avaliacao``)
        e/ou fração ``concluida`` por ciclo. Lacuna = ``null`` (nunca 0 de
        desempenho). ``has_data=false`` se a janela no escopo não tem
        cabeçalhos úteis. **MUST NOT** chamar ``compute_adherence`` nem
        inventar nota.
    """
    raise NotImplementedError(
        'build_stage_history é stub da T002; implementação na T030.',
    )
