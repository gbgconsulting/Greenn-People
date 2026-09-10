"""Elegibilidade automática por marco de admissão (série +6 meses).

Predicado 015 (`user_eligible_for_ciclo`) permanece intacto em
``apps.cycles.services.eligibility`` — este módulo cobre só o caminho
``origem=automatico`` ([contracts/marco-eligibility-contract.md]).

Bootstrap (FR-005 / research R5): só o próximo marco futuro; k passados
nunca entram na elegibilidade nem na materialização da coorte.
"""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING, Iterator

from django.contrib.auth import get_user_model
from django.db.models import QuerySet

from apps.core.calendar_br import first_business_day_of_month

if TYPE_CHECKING:
    from apps.accounts.models import CustomUser


def _ym(d: date) -> tuple[int, int]:
    return (d.year, d.month)


def _add_months(year: int, month: int, delta: int) -> tuple[int, int]:
    """Soma ``delta`` meses a ``(year, month)`` (mês 1–12)."""
    idx = year * 12 + (month - 1) + delta
    return idx // 12, (idx % 12) + 1


def is_auto_opening_day(ref_date: date) -> bool:
    """True iff ``ref_date`` é o 1º dia útil do próprio mês (janela do lote).

    Fora dessa janela a rotina **não** abre o mês “atrasado” (go-live no
    meio do mês → espera o próximo marco futuro + próximo 1º dia útil).
    """
    return ref_date == first_business_day_of_month(
        ref_date.year,
        ref_date.month,
    )


def next_future_marco(data_entrada: date, ref_date: date) -> tuple[int, int]:
    """Menor mês na série admissão+6k que é >= mês(ref_date).

    Comparação por ``(ano, mês)`` — o dia civil da admissão não entra.
    Nunca retorna um marco < mês(ref); k passados não são materializados.

    Correção de ``data_entrada``: o caller passa o valor **atual** no momento
    da avaliação — a série é recalculada a partir da correção; marcos que
    ficaram no passado relativo a ``ref_date`` não são recuperados.
    """
    start = data_entrada.year * 12 + (data_entrada.month - 1)
    ref = ref_date.year * 12 + (ref_date.month - 1)
    if ref <= start:
        k = 0
    else:
        # menor k>=0 com start + 6k >= ref
        k = (ref - start + 5) // 6
    ym = start + 6 * k
    year, month = ym // 12, (ym % 12) + 1
    # Invariante R5: nunca devolver marco anterior ao mês de referência.
    assert (year, month) >= (ref_date.year, ref_date.month), (
        f'next_future_marco violou R5: {(year, month)} < '
        f'{(ref_date.year, ref_date.month)}'
    )
    return year, month


def user_is_auto_candidate(
    user: CustomUser,
    *,
    year: int,
    month: int,
    ref_date: date,
) -> bool:
    """Ativo com admissão cujo próximo marco futuro é ``(year, month)``.

    Lê ``user.data_entrada`` no momento da chamada (pós-correção usa o valor
    novo). Sem data → fora. Nunca considera k passados da série.
    """
    if not getattr(user, 'is_active', False):
        return False
    entrada = getattr(user, 'data_entrada', None)
    if entrada is None:
        return False
    return next_future_marco(entrada, ref_date) == (year, month)


def user_eligible_for_auto_marco(
    user: CustomUser,
    *,
    year: int,
    month: int,
    ref_date: date,
) -> bool:
    """Candidato ao marco do mês (sem aplicar bloqueio FR-008).

    Nome alinhado a research R2 / tasks T006. Equivale a
    ``user_is_auto_candidate``.
    """
    return user_is_auto_candidate(
        user,
        year=year,
        month=month,
        ref_date=ref_date,
    )


def user_blocked_by_open_cycle(user: CustomUser) -> bool:
    """True se o usuário participa de algum ciclo ``aberto`` (FR-008)."""
    from apps.cycles.models import Ciclo
    from apps.reviews.models import Avaliacao

    return Avaliacao.objects.filter(
        usuario_id=user.pk,
        ciclo__status=Ciclo.Status.ABERTO,
    ).exists()


def user_eligible_for_auto_enrollment(
    user: CustomUser,
    *,
    year: int,
    month: int,
    ref_date: date,
) -> bool:
    """Candidato ao marco e não bloqueado por ciclo aberto."""
    return user_is_auto_candidate(
        user,
        year=year,
        month=month,
        ref_date=ref_date,
    ) and not user_blocked_by_open_cycle(user)


def iter_auto_marco_candidates(
    *,
    year: int,
    month: int,
    ref_date: date,
    queryset: QuerySet[CustomUser] | None = None,
) -> Iterator[CustomUser]:
    """Yield ativos com ``data_entrada`` cujo próximo marco é ``(year, month)``.

    Não aplica FR-008 — quem tem ciclo aberto continua candidato (alerta
    sem matrícula fica a cargo do orquestrador da coorte).
    """
    User = get_user_model()
    qs: QuerySet[CustomUser]
    if queryset is None:
        qs = User.objects.filter(is_active=True, data_entrada__isnull=False)
    else:
        qs = queryset.filter(is_active=True, data_entrada__isnull=False)

    for user in qs.iterator():
        if user_is_auto_candidate(
            user,
            year=year,
            month=month,
            ref_date=ref_date,
        ):
            yield user


def list_auto_marco_candidates(
    *,
    year: int,
    month: int,
    ref_date: date,
    queryset: QuerySet[CustomUser] | None = None,
) -> list[CustomUser]:
    """Lista materializada de candidatos ao marco (sem filtro FR-008)."""
    return list(
        iter_auto_marco_candidates(
            year=year,
            month=month,
            ref_date=ref_date,
            queryset=queryset,
        ),
    )
