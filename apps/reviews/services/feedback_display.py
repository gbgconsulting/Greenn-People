"""Contexto de apresentação da tela de leitura/assinatura de feedbacks."""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

from django.db.models import Avg

from apps.goals.models import Meta
from apps.reviews.models import Avaliacao, AvaliacaoCompetencia
from apps.reviews.services.display import escala_rotulo, format_nota_percentual


def _escala_referencia(avaliacao: Avaliacao):
    linha = (
        AvaliacaoCompetencia.objects.filter(avaliacao_id=avaliacao.pk)
        .select_related('competencia__escala')
        .first()
    )
    if linha is None:
        return None
    return linha.competencia.escala


def _denormalize_nota(nota_normalizada, escala) -> Decimal | None:
    if nota_normalizada is None or escala is None:
        return None
    minimo = Decimal(escala.valor_minimo)
    maximo = Decimal(escala.valor_maximo)
    amplitude = maximo - minimo
    if amplitude == 0:
        return None
    valor = minimo + Decimal(str(nota_normalizada)) * amplitude
    return valor.quantize(Decimal('0.1'), rounding=ROUND_HALF_UP)


def build_feedback_resumo(avaliacao: Avaliacao) -> dict:
    """Monta cartão de resultado calibrado (somente leitura; dados já persistidos)."""
    escala = _escala_referencia(avaliacao)
    nota = avaliacao.nota_final_lider

    competencia_valor = None
    competencia_escala_max = None
    valor_escala = _denormalize_nota(nota, escala)
    if valor_escala is not None and escala is not None:
        competencia_valor = valor_escala
        competencia_escala_max = escala.valor_maximo

    media_progresso = (
        Meta.objects.filter(
            usuario_id=avaliacao.usuario_id,
            objetivo_estrategico__ciclo_id=avaliacao.ciclo_id,
            status=Meta.Status.APROVADA,
            progresso__isnull=False,
        ).aggregate(media=Avg('progresso'))['media']
    )
    metas_atingimento = None
    if media_progresso is not None:
        metas_atingimento = int(
            Decimal(media_progresso).quantize(Decimal('1'), rounding=ROUND_HALF_UP),
        )

    classificacao = None
    if nota is not None and escala is not None and valor_escala is not None:
        nivel = int(valor_escala.quantize(Decimal('1'), rounding=ROUND_HALF_UP))
        nivel = max(int(escala.valor_minimo), min(int(escala.valor_maximo), nivel))
        rotulo = escala_rotulo(escala, nivel)
        if rotulo:
            classificacao = rotulo

    return {
        'competencia_valor': competencia_valor,
        'competencia_escala_max': competencia_escala_max,
        'competencia_percentual': format_nota_percentual(nota)
        if nota is not None
        else None,
        'metas_atingimento': metas_atingimento,
        'classificacao': classificacao,
        'tem_dados': (
            nota is not None
            or metas_atingimento is not None
            or classificacao is not None
        ),
    }
