"""Enrollment de Avaliacao mid-cycle (contracts/mid-cycle-enrollment-contract.md).

Multi-open (018): criação nova sem ``ciclo=`` ambíguo é fail-closed;
predicado de elegibilidade segue ``Ciclo.origem`` (manual 015 vs auto marco).
"""

from __future__ import annotations

from datetime import date

from django.utils import timezone

from apps.accounts.models import CustomUser
from apps.cycles.models import Ciclo
from apps.cycles.services.eligibility import user_eligible_for_ciclo
from apps.cycles.services.marco import user_eligible_for_auto_enrollment
from apps.reviews.models import Avaliacao


def resolve_mid_cycle_ciclo() -> Ciclo | None:
    """Ciclo alvo para mid-cycle (forms) sem escolha silenciosa errada.

    Preferência documentada (research R7): manual aberto mais recente com
    ``admitidos_ate``. Se houver exatamente um aberto (qualquer origem),
    usa esse. Com N abertos sem manual com corte → ``None`` (caller passa
    ``ciclo=`` ou o ensure não cria).
    """
    open_ciclos = list(
        Ciclo.objects.filter(status=Ciclo.Status.ABERTO).order_by(
            '-data_inicio',
            'nome',
        ),
    )
    if not open_ciclos:
        return None
    if len(open_ciclos) == 1:
        return open_ciclos[0]
    for ciclo in open_ciclos:
        if (
            ciclo.origem == Ciclo.Origem.MANUAL
            and ciclo.admitidos_ate is not None
        ):
            return ciclo
    return None


def _open_ciclos_ordered() -> list[Ciclo]:
    return list(
        Ciclo.objects.filter(status=Ciclo.Status.ABERTO).order_by(
            '-data_inicio',
            'nome',
        ),
    )


def _user_eligible_for_origem(
    user: CustomUser,
    ciclo: Ciclo,
    *,
    ref_date: date | None = None,
) -> bool:
    """Predicado de criação conforme ``ciclo.origem``."""
    if ciclo.origem == Ciclo.Origem.AUTOMATICO:
        marco = ciclo.marco_competencia
        if marco is None:
            return False
        today = ref_date if ref_date is not None else timezone.localdate()
        return user_eligible_for_auto_enrollment(
            user,
            year=marco.year,
            month=marco.month,
            ref_date=today,
        )
    return user_eligible_for_ciclo(user, ciclo)


def ensure_avaliacao_for_user(
    user: CustomUser,
    ciclo: Ciclo | None = None,
    *,
    ref_date: date | None = None,
) -> Avaliacao | None:
    """Garante Avaliacao idempotente para colaborador elegível em ciclo aberto.

    Se ``user.is_active`` e existir ciclo aberto (ou ``ciclo`` passado e aberto):
    retorna Avaliacao existente (snapshot; nunca remove); se inelegível pelo
    predicado da origem do ciclo, no-op ``None``; senão
    ``get_or_create`` com ``etapa=input_metas``.

    Sem ``ciclo=`` e com **mais de um** aberto: não cria Avaliação nova
    (ambiguidade multi-open). Pode devolver a existente se houver exatamente
    uma nos ciclos abertos. Ramo automático de lote deve sempre passar
    ``ciclo=`` da coorte.
    """
    if not getattr(user, 'is_active', False) or not getattr(user, 'pk', None):
        return None

    if ciclo is None:
        open_ciclos = _open_ciclos_ordered()
        if not open_ciclos:
            return None
        if len(open_ciclos) == 1:
            ciclo = open_ciclos[0]
        else:
            existing_open = Avaliacao.objects.filter(
                usuario=user,
                ciclo__in=open_ciclos,
            )
            if existing_open.count() == 1:
                return existing_open.first()
            # 0 → exige ciclo= para criar; >1 → ambíguo demais
            return None
    elif ciclo.status != Ciclo.Status.ABERTO:
        return None

    if ciclo is None:
        return None

    existing = Avaliacao.objects.filter(ciclo=ciclo, usuario=user).first()
    if existing is not None:
        return existing

    if not _user_eligible_for_origem(user, ciclo, ref_date=ref_date):
        return None

    avaliacao, _created = Avaliacao.objects.get_or_create(
        ciclo=ciclo,
        usuario=user,
        defaults={'etapa': Avaliacao.Etapa.INPUT_METAS},
    )
    return avaliacao
