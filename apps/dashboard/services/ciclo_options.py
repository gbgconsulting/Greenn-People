"""Resolução de ciclo operacional e opções agrupadas do seletor.

Default das homes gerenciais = ciclo aberto via ``get_open_ciclo()``.
Query ``?ciclo=<pk>`` só como intenção explícita (arquivo pontual).

Este módulo **MUST NOT**:
- fazer fallback silencioso para ciclo encerrado;
- chamar ``get_visible_users`` (builders/views recebem ``visible`` já resolvido).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, TypedDict

from apps.cycles.models import Ciclo
from apps.goals.forms import get_open_ciclo

if TYPE_CHECKING:
    from django.http import HttpRequest

#: Arquivo com mais que este total expõe filtro GET ``q`` no nome (R4 / FR-006).
ARCHIVE_FILTER_THRESHOLD = 20


class GroupedCicloOptions(TypedDict):
    """Shape consumido por ``templates/dashboard/_ciclo_selector.html`` (T009)."""

    operacional: list[Ciclo]
    arquivo: list[Ciclo]
    arquivo_total: int
    q: str
    show_q_filter: bool


def resolve_operational_ciclo(request: HttpRequest) -> Ciclo | None:
    """Ciclo da visão operacional (ou arquivo só com ``?ciclo=`` explícito).

    - Sem ``ciclo`` na query → ``get_open_ciclo()`` (pode ser ``None`` → empty
      operacional; **nunca** o último encerrado).
    - ``?ciclo=<pk>`` válido → aquele ``Ciclo`` (aberto ou arquivo).
    - ``?ciclo=`` inválido / pk inexistente → ``get_open_ciclo()`` (não inventa
      encerrado).
    """
    raw = request.GET.get('ciclo')
    if not raw:
        return get_open_ciclo()
    try:
        pk = int(raw)
    except (TypeError, ValueError):
        return get_open_ciclo()
    found = Ciclo.objects.filter(pk=pk).first()
    if found is None:
        return get_open_ciclo()
    return found


def grouped_ciclo_options(*, q: str | None = None) -> GroupedCicloOptions:
    """Opções para ``<optgroup>`` Operacional / Arquivo.

    - Operacional: no máximo o ciclo ``aberto`` (via ``get_open_ciclo()``).
    - Arquivo: ``encerrado``, ordenado por ``-data_inicio`` (depois ``-pk``).
    - Se o arquivo tiver mais de ``ARCHIVE_FILTER_THRESHOLD`` ciclos e ``q``
      não-vazio, filtra ``nome__icontains``; caso contrário lista o arquivo
      completo (o template só exibe o campo de busca quando ``show_q_filter``).
    """
    aberto = get_open_ciclo()
    operacional: list[Ciclo] = [aberto] if aberto is not None else []

    arquivo_qs = Ciclo.objects.filter(status=Ciclo.Status.ENCERRADO).order_by(
        '-data_inicio',
        '-pk',
    )
    arquivo_total = arquivo_qs.count()
    show_q_filter = arquivo_total > ARCHIVE_FILTER_THRESHOLD
    q_clean = (q or '').strip()
    if show_q_filter and q_clean:
        arquivo_qs = arquivo_qs.filter(nome__icontains=q_clean)

    return GroupedCicloOptions(
        operacional=operacional,
        arquivo=list(arquivo_qs),
        arquivo_total=arquivo_total,
        q=q_clean,
        show_q_filter=show_q_filter,
    )
