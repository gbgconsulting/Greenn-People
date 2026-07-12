"""Servicos de avaliacao e snapshots de competencia (contracts/calculation-contract.md)."""

from __future__ import annotations

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction

from apps.competencies.models import CargoCompetencia
from apps.reviews.models import Avaliacao, AvaliacaoCompetencia

# Origem da nota exibida ao colaborador (FR-005).
NOTA_ORIGEM_LIDER = 'lider'
NOTA_ORIGEM_AUTOAVALIACAO = 'autoavaliacao'


def resolve_nota_atual(
    avaliacao: Avaliacao | None,
) -> tuple[Decimal | None, str]:
    """Nota vigente para exibicao ao colaborador (FR-005).

    Prefere ``nota_final_lider`` (oficial); senao ``nota_final_autoavaliacao``.
    Retorna ``(valor, origem)`` onde origem e ``lider``, ``autoavaliacao`` ou ``''``.
    """
    if avaliacao is None:
        return None, ''
    if avaliacao.nota_final_lider is not None:
        return avaliacao.nota_final_lider, NOTA_ORIGEM_LIDER
    if avaliacao.nota_final_autoavaliacao is not None:
        return avaliacao.nota_final_autoavaliacao, NOTA_ORIGEM_AUTOAVALIACAO
    return None, ''


def nota_atual_competencia(linha: AvaliacaoCompetencia | None) -> Decimal | None:
    """Nota por competencia: lider se existir, senao autoavaliacao."""
    if linha is None:
        return None
    if linha.nota_lider is not None:
        return linha.nota_lider
    return linha.nota_autoavaliacao


def build_fr005_context(user, *, ciclo=None, avaliacao=None) -> dict:
    """Contexto compartilhado: nivel esperado + nota atual (FR-005)."""
    from apps.goals.forms import get_avaliacao_for_user, get_open_ciclo

    cargo = user.cargo
    if user.cargo_id:
        competencias_cargo = list(
            CargoCompetencia.objects.filter(cargo_id=user.cargo_id)
            .select_related('competencia', 'competencia__escala')
            .order_by('competencia__nome'),
        )
    else:
        competencias_cargo = []

    vinculo_pendente = cargo is None or not competencias_cargo
    ciclo_aberto = ciclo if ciclo is not None else get_open_ciclo()
    if avaliacao is None:
        avaliacao = get_avaliacao_for_user(user, ciclo_aberto)
    nota_atual, nota_atual_origem = resolve_nota_atual(avaliacao)

    linhas_por_competencia: dict[int, AvaliacaoCompetencia] = {}
    if avaliacao is not None:
        linhas_por_competencia = {
            linha.competencia_id: linha
            for linha in AvaliacaoCompetencia.objects.filter(
                avaliacao=avaliacao,
            ).select_related('competencia', 'competencia__escala')
        }

    competencias_resumo = [
        {
            'cargo_competencia': item,
            'competencia': item.competencia,
            'nivel_esperado': item.nivel_esperado,
            'nota_atual': nota_atual_competencia(
                linhas_por_competencia.get(item.competencia_id),
            ),
        }
        for item in competencias_cargo
    ]

    return {
        'cargo': cargo,
        'competencias_cargo': competencias_cargo,
        'competencias_resumo': competencias_resumo,
        'vinculo_pendente': vinculo_pendente,
        'ciclo_aberto': ciclo_aberto,
        'avaliacao': avaliacao,
        'nota_atual': nota_atual,
        'nota_atual_origem': nota_atual_origem,
    }


def create_competency_lines(avaliacao: Avaliacao) -> list[AvaliacaoCompetencia]:
    """Copia peso e nivel esperado de CargoCompetencia para AvaliacaoCompetencia.

    Side effect da transicao para etapa ``avaliacao`` (write-once snapshots).
    Idempotente: linhas ja existentes para a avaliacao nao sao recriadas.
    """
    usuario = avaliacao.usuario
    if usuario.cargo_id is None:
        raise ValidationError(
            'Colaborador sem cargo; nao e possivel criar linhas de competencia.',
        )

    cargo_competencias = list(
        CargoCompetencia.objects.filter(cargo_id=usuario.cargo_id).select_related(
            'competencia',
        ),
    )
    if not cargo_competencias:
        raise ValidationError(
            'Cargo sem competencias vinculadas; nao e possivel criar linhas.',
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
