"""Servicos de avaliacao e snapshots de competencia (contracts/calculation-contract.md)."""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

from django.core.exceptions import ValidationError
from django.db import transaction

from apps.competencies.models import CargoCompetencia, Escala
from apps.reviews.exceptions import CalculationError
from apps.reviews.models import Avaliacao, AvaliacaoCompetencia

# Origem da nota exibida ao colaborador (FR-005).
NOTA_ORIGEM_LIDER = 'lider'
NOTA_ORIGEM_AUTOAVALIACAO = 'autoavaliacao'

_NOTA_FINAL_QUANT = Decimal('0.0001')

MSG_AUTOAVALIACAO_INCOMPLETA = (
    'O colaborador deve concluir a autoavaliação antes da avaliação do líder.'
)


def self_assessment_complete(avaliacao: Avaliacao | None) -> bool:
    """True se todas as linhas de competência têm ``nota_autoavaliacao``."""
    if avaliacao is None:
        return False
    linhas = AvaliacaoCompetencia.objects.filter(avaliacao_id=avaliacao.pk)
    if not linhas.exists():
        return False
    return not linhas.filter(nota_autoavaliacao__isnull=True).exists()


def normalize_score(nota: Decimal, escala: Escala) -> Decimal:
    """Normaliza nota para [0, 1]: (nota - valor_minimo) / (valor_maximo - valor_minimo)."""
    minimo = Decimal(escala.valor_minimo)
    maximo = Decimal(escala.valor_maximo)
    amplitude = maximo - minimo
    if amplitude == 0:
        raise CalculationError(
            'Escala com valor_maximo igual a valor_minimo; nao e possivel normalizar.',
        )
    return (Decimal(nota) - minimo) / amplitude


def _media_ponderada_normalizada(
    linhas: list[AvaliacaoCompetencia],
    *,
    campo_nota: str,
) -> Decimal:
    """Σ(normalize(nota) × peso_utilizado) / Σ(peso_utilizado)."""
    soma_pesos = Decimal('0')
    soma_ponderada = Decimal('0')

    for linha in linhas:
        nota = getattr(linha, campo_nota)
        if nota is None:
            raise CalculationError(
                f'Linha de competencia sem {campo_nota}; nao e possivel calcular.',
            )
        peso = Decimal(linha.peso_utilizado)
        escala = linha.competencia.escala
        normalizada = normalize_score(Decimal(nota), escala)
        soma_pesos += peso
        soma_ponderada += normalizada * peso

    if soma_pesos == 0:
        raise CalculationError(
            'Soma de peso_utilizado igual a zero; nao e possivel calcular a nota final.',
        )

    return (soma_ponderada / soma_pesos).quantize(
        _NOTA_FINAL_QUANT,
        rounding=ROUND_HALF_UP,
    )


def calcular_nota_final_lider(avaliacao: Avaliacao) -> Decimal:
    """Media ponderada das notas do lider normalizadas (apenas peso_utilizado).

    Persiste o resultado em ``Avaliacao.nota_final_lider``.
    Levanta ``CalculationError`` se Σpeso_utilizado == 0 ou faltar nota_lider.
    """
    linhas = list(
        AvaliacaoCompetencia.objects.filter(avaliacao_id=avaliacao.pk).select_related(
            'competencia',
            'competencia__escala',
        ),
    )
    if not linhas:
        raise CalculationError(
            'Avaliacao sem linhas de competencia; nao e possivel calcular a nota final.',
        )

    nota_final = _media_ponderada_normalizada(linhas, campo_nota='nota_lider')
    avaliacao.nota_final_lider = nota_final
    avaliacao.save(update_fields=['nota_final_lider', 'updated_at'])
    return nota_final


def calcular_nota_final_autoavaliacao(avaliacao: Avaliacao) -> Decimal | None:
    """Mesma formula de nota final usando ``nota_autoavaliacao`` (opcional).

    Retorna ``None`` se nenhuma linha tiver autoavaliacao preenchida.
    Quando calculada, persiste em ``Avaliacao.nota_final_autoavaliacao``.
    """
    linhas = list(
        AvaliacaoCompetencia.objects.filter(avaliacao_id=avaliacao.pk).select_related(
            'competencia',
            'competencia__escala',
        ),
    )
    linhas_com_nota = [linha for linha in linhas if linha.nota_autoavaliacao is not None]
    if not linhas_com_nota:
        return None

    nota_final = _media_ponderada_normalizada(
        linhas_com_nota,
        campo_nota='nota_autoavaliacao',
    )
    avaliacao.nota_final_autoavaliacao = nota_final
    avaliacao.save(update_fields=['nota_final_autoavaliacao', 'updated_at'])
    return nota_final


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
