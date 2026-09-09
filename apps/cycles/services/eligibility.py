"""Elegibilidade de matrícula por corte de admissão (admitidos até)."""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING, TypedDict

from django.contrib.auth import get_user_model
from django.db.models import Count, Q, QuerySet

if TYPE_CHECKING:
    from apps.accounts.models import CustomUser
    from apps.cycles.models import Ciclo


class AdmissionPreviewCounts(TypedDict):
    elegiveis: int
    excluidos_admissao_posterior: int
    sem_data_entrada: int


def user_eligible_for_ciclo(user: CustomUser, ciclo: Ciclo) -> bool:
    """True se o usuário pode receber Avaliacao neste ciclo (abertura e mid-cycle).

    Regra (contrato): ativo ∧ data_entrada NOT NULL ∧ admitidos_ate NOT NULL
    ∧ data_entrada <= admitidos_ate (inclusivo). Fail-closed se corte NULL.
    """
    if not getattr(user, 'is_active', False):
        return False
    if ciclo.admitidos_ate is None:
        return False
    entrada = getattr(user, 'data_entrada', None)
    if entrada is None:
        return False
    return entrada <= ciclo.admitidos_ate


def filter_coverage_universe(
    qs: QuerySet[CustomUser],
    ciclo: Ciclo,
) -> QuerySet[CustomUser]:
    """Universo de cobertura / ``sem_avaliacao`` para um ciclo.

    Com ``admitidos_ate`` definido: quem já tem ``Avaliacao`` no ciclo
    (snapshot) **ou** é elegível pelo corte. Quem está fora do recorte e
    não tem avaliação **não** entra — não é pendência, é exclusão do ciclo.

    Sem corte (legado / ``admitidos_ate`` NULL): mantém o QS intacto — não
    há recorte para aplicar.
    """
    if ciclo.admitidos_ate is None:
        return qs

    enrolled = Q(avaliacoes__ciclo=ciclo)
    eligible = Q(
        is_active=True,
        data_entrada__isnull=False,
        data_entrada__lte=ciclo.admitidos_ate,
    )
    return qs.filter(enrolled | eligible).distinct()


def preview_admission_counts(admitidos_ate: date) -> AdmissionPreviewCounts:
    """Contagens agregadas de ativos para o corte ``admitidos_ate``.

    Retorna ``elegiveis``, ``excluidos_admissao_posterior`` e ``sem_data_entrada``.
    Inativos não entram nas contagens. Sem lista nominativa.
    """
    User = get_user_model()
    agg = User.objects.filter(is_active=True).aggregate(
        elegiveis=Count(
            'pk',
            filter=Q(data_entrada__isnull=False, data_entrada__lte=admitidos_ate),
        ),
        excluidos_admissao_posterior=Count(
            'pk',
            filter=Q(data_entrada__isnull=False, data_entrada__gt=admitidos_ate),
        ),
        sem_data_entrada=Count('pk', filter=Q(data_entrada__isnull=True)),
    )
    return AdmissionPreviewCounts(
        elegiveis=agg['elegiveis'],
        excluidos_admissao_posterior=agg['excluidos_admissao_posterior'],
        sem_data_entrada=agg['sem_data_entrada'],
    )
