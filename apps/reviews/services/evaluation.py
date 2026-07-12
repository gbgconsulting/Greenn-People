"""Serviços de avaliação e snapshots de competência (contracts/calculation-contract.md)."""

from __future__ import annotations

from django.core.exceptions import ValidationError
from django.db import transaction

from apps.competencies.models import CargoCompetencia
from apps.reviews.models import Avaliacao, AvaliacaoCompetencia


def create_competency_lines(avaliacao: Avaliacao) -> list[AvaliacaoCompetencia]:
    """Copia peso e nível esperado de CargoCompetencia para AvaliacaoCompetencia.

    Side effect da transição para etapa ``avaliacao`` (write-once snapshots).
    Idempotente: linhas já existentes para a avaliação não são recriadas.
    """
    usuario = avaliacao.usuario
    if usuario.cargo_id is None:
        raise ValidationError(
            'Colaborador sem cargo; não é possível criar linhas de competência.',
        )

    cargo_competencias = list(
        CargoCompetencia.objects.filter(cargo_id=usuario.cargo_id).select_related(
            'competencia',
        ),
    )
    if not cargo_competencias:
        raise ValidationError(
            'Cargo sem competências vinculadas; não é possível criar linhas.',
        )

    existentes = set(
        AvaliacaoCompetencia.objects.filter(avaliacao_id=avaliacao.pk).values_list(
            'competencia_id',
            flat=True,
        ),
    )

    criadas: list[AvaliacaoCompetencia] = []
    with transaction.atomic():
        for cc in cargo_competencias:
            if cc.competencia_id in existentes:
                continue
            linha = AvaliacaoCompetencia(
                avaliacao=avaliacao,
                competencia=cc.competencia,
                peso_utilizado=cc.peso,
                nivel_esperado_utilizado=cc.nivel_esperado,
            )
            linha.save()
            criadas.append(linha)

    return criadas