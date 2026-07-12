"""Classificação 9-box (contracts/calculation-contract.md)."""

from __future__ import annotations

from decimal import Decimal

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction

from apps.accounts.models import CustomUser
from apps.audit.context import audit_actor
from apps.reviews.models import Avaliacao
from apps.talent.models import ClassificacaoTalento

_LIMITE_BAIXO = Decimal('0.33')
_LIMITE_ALTO = Decimal('0.66')

_NIVEL_LABEL = {
    1: 'baixo',
    2: 'medio',
    3: 'alto',
}


def derive_desempenho(nota_final_lider: Decimal) -> int:
    """Deriva nível de desempenho 1–3 a partir da nota normalizada 0–1.

    ``nota_final_lider`` já está em [0, 1] (média ponderada normalizada).

    - ``< 0.33`` → 1 (baixo)
    - ``0.33–0.66`` → 2 (médio)
    - ``> 0.66`` → 3 (alto)
    """
    nota = Decimal(nota_final_lider)
    if nota < _LIMITE_BAIXO:
        return 1
    if nota <= _LIMITE_ALTO:
        return 2
    return 3


def calculate_quadrante(desempenho: int, potencial: int) -> str:
    """Retorna o rótulo do quadrante (ex.: ``medio_alto``).

    Raises:
        ValidationError: se desempenho ou potencial estiverem fora de 1–3.
    """
    if desempenho not in _NIVEL_LABEL or potencial not in _NIVEL_LABEL:
        raise ValidationError(
            'Desempenho e potencial devem ser inteiros entre 1 e 3.',
        )
    return f'{_NIVEL_LABEL[desempenho]}_{_NIVEL_LABEL[potencial]}'


def upsert_classification(
    usuario: CustomUser,
    ciclo,
    potencial: int,
    admin: CustomUser,
) -> ClassificacaoTalento:
    """Cria ou atualiza classificação: potencial manual; desempenho/quadrante derivados.

    Obtém ``nota_final_lider`` da ``Avaliacao`` do par usuario+ciclo, deriva
    desempenho e calcula o quadrante 9-box. O ator admin é atribuído via
    ``audit_actor`` para o histórico append-only.

    Raises:
        PermissionDenied: se ``admin`` não for administrador.
        ValidationError: potencial inválido, avaliação ausente ou sem nota do líder.
    """
    if not getattr(admin, 'is_admin', False):
        raise PermissionDenied(
            'Apenas administradores podem definir a classificação de talento.',
        )

    if potencial not in (1, 2, 3):
        raise ValidationError('Potencial deve ser um inteiro entre 1 e 3.')

    try:
        avaliacao = Avaliacao.objects.get(usuario_id=usuario.pk, ciclo_id=ciclo.pk)
    except Avaliacao.DoesNotExist as exc:
        raise ValidationError(
            'Não há avaliação para este colaborador neste ciclo.',
        ) from exc

    if avaliacao.nota_final_lider is None:
        raise ValidationError(
            'Avaliação sem nota_final_lider; não é possível derivar desempenho.',
        )

    desempenho = derive_desempenho(avaliacao.nota_final_lider)
    quadrante = calculate_quadrante(desempenho, potencial)

    with transaction.atomic():
        with audit_actor(admin):
            classificacao, _created = ClassificacaoTalento.objects.update_or_create(
                usuario=usuario,
                ciclo=ciclo,
                defaults={
                    'desempenho': desempenho,
                    'potencial': potencial,
                    'quadrante': quadrante,
                },
            )
    return classificacao


def get_visible_classification_for_collaborator(
    usuario: CustomUser,
    ciclo=None,
) -> ClassificacaoTalento | None:
    """Retorna a classificação do colaborador somente se liberada (RF-25).

    Colaboradores só veem o próprio registro quando ``visivel_ao_colaborador``
    é True. Sem ciclo aberto (e sem ``ciclo`` explícito) retorna ``None``.
    """
    if ciclo is None:
        from apps.goals.forms import get_open_ciclo

        ciclo = get_open_ciclo()
    if ciclo is None:
        return None
    return (
        ClassificacaoTalento.objects.filter(
            usuario=usuario,
            ciclo=ciclo,
            visivel_ao_colaborador=True,
        )
        .select_related('ciclo')
        .first()
    )
