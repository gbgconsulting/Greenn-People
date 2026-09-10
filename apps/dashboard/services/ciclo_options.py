"""Resolução de ciclo operacional e opções agrupadas do seletor.

Default das homes gerenciais = ciclo aberto via ``get_open_ciclo()``
(primeiro de ``get_open_ciclos()``). Grupo ``operacional`` lista **todos**
os abertos. Query ``?ciclo=<pk>`` só como intenção explícita (arquivo pontual).

Este módulo **MUST NOT**:
- fazer fallback silencioso para ciclo encerrado;
- truncar ``operacional`` em um único aberto;
- chamar ``get_visible_users`` (builders/views recebem ``visible`` já resolvido).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, TypedDict

from apps.cycles.models import Ciclo
from apps.goals.forms import get_open_ciclo, get_open_ciclos
from apps.reviews.models import Avaliacao

if TYPE_CHECKING:
    from django.contrib.auth.models import AbstractBaseUser
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


def _user_participates(user: AbstractBaseUser, ciclo: Ciclo) -> bool:
    """True se existe ``Avaliacao`` do usuário naquele ciclo (escopo pessoal)."""
    user_pk = getattr(user, 'pk', None)
    if user_pk is None:
        return False
    return Avaliacao.objects.filter(ciclo=ciclo, usuario_id=user_pk).exists()


def _default_personal_ciclo(user: AbstractBaseUser) -> Ciclo | None:
    """Primeiro aberto (ordem canônica) em que o usuário participa.

    **Nunca** faz fallback para encerrado. Com multi-open, percorre
    ``get_open_ciclos()`` e devolve o primeiro com ``Avaliacao`` do usuário.
    """
    for aberto in get_open_ciclos():
        if _user_participates(user, aberto):
            return aberto
    return None


def resolve_personal_ciclo(
    request: HttpRequest,
    user: AbstractBaseUser,
) -> Ciclo | None:
    """Ciclo do Meu painel: participação obrigatória (só ciclos do usuário).

    - Sem ``ciclo`` na query → aberto se o usuário tem avaliação; senão ``None``
      (**nunca** o último encerrado).
    - ``?ciclo=<pk>`` só resolve se existir ``Avaliacao(usuario=user)`` naquele
      ciclo (join — não aceita pk alheio).
    - pk inválido / sem participação → mesmo default (aberto se participa).
    """
    user_pk = getattr(user, 'pk', None)
    if user_pk is None:
        return None

    raw = request.GET.get('ciclo')
    if not raw:
        return _default_personal_ciclo(user)
    try:
        pk = int(raw)
    except (TypeError, ValueError):
        return _default_personal_ciclo(user)

    # Escopo no queryset: ciclo só entra se o próprio usuário participa.
    found = (
        Ciclo.objects.filter(pk=pk, avaliacoes__usuario_id=user_pk)
        .distinct()
        .first()
    )
    if found is None:
        return _default_personal_ciclo(user)
    return found


def grouped_ciclo_options(*, q: str | None = None) -> GroupedCicloOptions:
    """Opções para ``<optgroup>`` Operacional / Arquivo.

    - Operacional: **todos** os ciclos ``aberto`` (via ``get_open_ciclos()``).
    - Arquivo: ``encerrado``, ordenado por ``-data_inicio`` (depois ``-pk``).
    - Se o arquivo tiver mais de ``ARCHIVE_FILTER_THRESHOLD`` ciclos e ``q``
      não-vazio, filtra ``nome__icontains``; caso contrário lista o arquivo
      completo (o template só exibe o campo de busca quando ``show_q_filter``).
    """
    operacional: list[Ciclo] = list(get_open_ciclos())

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


def grouped_ciclo_options_for_user(
    user: AbstractBaseUser,
    *,
    q: str | None = None,
) -> GroupedCicloOptions:
    """Seletor do Meu painel: só ciclos em que o usuário tem ``Avaliacao``.

    Mesmo shape de ``grouped_ciclo_options`` para reusar ``_ciclo_selector.html``.
    Operacional = todos os abertos com participação; arquivo só encerrados
    com avaliação do usuário.
    """
    user_pk = getattr(user, 'pk', None)
    participated_ids = (
        Avaliacao.objects.filter(usuario_id=user_pk).values_list(
            'ciclo_id',
            flat=True,
        )
        if user_pk is not None
        else []
    )
    participated = set(participated_ids)

    operacional: list[Ciclo] = [
        c for c in get_open_ciclos() if c.pk in participated
    ]

    arquivo_qs = Ciclo.objects.filter(
        status=Ciclo.Status.ENCERRADO,
        pk__in=participated,
    ).order_by(
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
