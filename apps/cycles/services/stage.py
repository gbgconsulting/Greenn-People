"""Máquina de estados agregada por Avaliacao (contracts/stage-machine-contract.md)."""

from __future__ import annotations

from decimal import Decimal

from django.apps import apps
from django.db import transaction
from django.db.models import Sum

from apps.accounts.models import CustomUser
from apps.audit.context import audit_actor
from apps.cycles.exceptions import CycleClosedError, StageTransitionError
from apps.cycles.models import Ciclo
from apps.reviews.models import Avaliacao

ETAPAS = (
    'input_metas',
    'aprovacao_metas',
    'resultados',
    'aprovacao_resultados',
    'avaliacao',
    'feedback',
)

_NEXT_ETAPA = {
    Avaliacao.Etapa.INPUT_METAS: Avaliacao.Etapa.APROVACAO_METAS,
    Avaliacao.Etapa.APROVACAO_METAS: Avaliacao.Etapa.RESULTADOS,
    Avaliacao.Etapa.RESULTADOS: Avaliacao.Etapa.APROVACAO_RESULTADOS,
    Avaliacao.Etapa.APROVACAO_RESULTADOS: Avaliacao.Etapa.AVALIACAO,
    Avaliacao.Etapa.AVALIACAO: Avaliacao.Etapa.FEEDBACK,
}


def is_cycle_closed(avaliacao: Avaliacao) -> bool:
    """True se ciclo.status == 'encerrado'."""
    return avaliacao.ciclo.status == Ciclo.Status.ENCERRADO


def can_advance(avaliacao: Avaliacao) -> tuple[bool, str]:
    """Retorna (ok, motivo) para avançar etapa."""
    if is_cycle_closed(avaliacao):
        return False, 'Ciclo encerrado.'

    etapa = avaliacao.etapa
    if etapa == Avaliacao.Etapa.FEEDBACK:
        return _check_feedback_conclusion(avaliacao)

    checker = {
        Avaliacao.Etapa.INPUT_METAS: _check_input_metas,
        Avaliacao.Etapa.APROVACAO_METAS: _check_aprovacao_metas,
        Avaliacao.Etapa.RESULTADOS: _check_resultados,
        Avaliacao.Etapa.APROVACAO_RESULTADOS: _check_aprovacao_resultados,
        Avaliacao.Etapa.AVALIACAO: _check_avaliacao,
    }.get(etapa)

    if checker is None:
        return False, f'Etapa desconhecida: {etapa}.'

    return checker(avaliacao)


def advance_stage(avaliacao: Avaliacao, actor: CustomUser) -> Avaliacao:
    """Avança etapa se pré-condições satisfeitas; levanta StageTransitionError."""
    if is_cycle_closed(avaliacao):
        raise CycleClosedError('Ciclo encerrado; não é possível avançar etapas.')

    if avaliacao.etapa == Avaliacao.Etapa.FEEDBACK:
        ok, motivo = _check_feedback_conclusion(avaliacao)
        if not ok:
            raise StageTransitionError(motivo)
        # Etapa terminal: conclusão é derivada (feedback líder + ciente_em).
        return avaliacao

    ok, motivo = can_advance(avaliacao)
    if not ok:
        raise StageTransitionError(motivo)

    next_etapa = _NEXT_ETAPA.get(avaliacao.etapa)
    if next_etapa is None:
        raise StageTransitionError('Não há etapa seguinte.')

    with transaction.atomic():
        locked = (
            Avaliacao.objects.select_for_update()
            .select_related('ciclo', 'usuario')
            .get(pk=avaliacao.pk)
        )
        if is_cycle_closed(locked):
            raise CycleClosedError('Ciclo encerrado; não é possível avançar etapas.')

        locked.etapa = next_etapa
        # Actor attributed via audit context; signals write AuditLog for etapa.
        with audit_actor(actor):
            locked.save(update_fields=['etapa', 'updated_at'])

        if next_etapa == Avaliacao.Etapa.AVALIACAO:
            _create_competency_lines(locked)

        return locked


def _metas_queryset(avaliacao: Avaliacao):
    """Metas do colaborador no ciclo da avaliação."""
    Meta = apps.get_model('goals', 'Meta')
    return Meta.objects.filter(
        usuario_id=avaliacao.usuario_id,
        objetivo_estrategico__ciclo_id=avaliacao.ciclo_id,
    )


def _check_input_metas(avaliacao: Avaliacao) -> tuple[bool, str]:
    """input_metas → aprovacao_metas: ≥1 meta criada pelo colaborador."""
    if not _metas_queryset(avaliacao).exists():
        return False, 'É necessário criar ao menos uma meta.'
    return True, ''


def _check_aprovacao_metas(avaliacao: Avaliacao) -> tuple[bool, str]:
    """aprovacao_metas → resultados: ≥1 meta e 100% com status=aprovada."""
    metas = _metas_queryset(avaliacao)
    count = metas.count()
    if count == 0:
        return False, 'É necessário ter ao menos uma meta aprovada.'
    if metas.exclude(status='aprovada').exists():
        return False, 'Todas as metas devem estar aprovadas.'
    return True, ''


def _check_resultados(avaliacao: Avaliacao) -> tuple[bool, str]:
    """resultados → aprovacao_resultados: metas aprovadas têm progresso."""
    aprovadas = _metas_queryset(avaliacao).filter(status='aprovada')
    if not aprovadas.exists():
        return False, 'Não há metas aprovadas com progresso a registrar.'
    if aprovadas.filter(progresso__isnull=True).exists():
        return False, 'Todas as metas aprovadas devem ter progresso registrado.'
    return True, ''


def _check_aprovacao_resultados(avaliacao: Avaliacao) -> tuple[bool, str]:
    """aprovacao_resultados → avaliacao: 100% status_resultado=aprovado + cargo."""
    metas = _metas_queryset(avaliacao)
    count = metas.count()
    if count == 0:
        return False, 'É necessário ter ao menos uma meta.'
    if metas.exclude(status_resultado='aprovado').exists():
        return False, 'Todos os resultados devem estar aprovados.'

    cargo_ok, cargo_motivo = _check_cargo_competencias(avaliacao)
    if not cargo_ok:
        return False, cargo_motivo
    return True, ''


def _check_cargo_competencias(avaliacao: Avaliacao) -> tuple[bool, str]:
    """Bloqueio para avaliacao: ≥1 CargoCompetencia com Σpeso > 0."""
    usuario = avaliacao.usuario
    if usuario.cargo_id is None:
        return False, 'Colaborador sem cargo; vincule um cargo com competências.'

    CargoCompetencia = apps.get_model('competencies', 'CargoCompetencia')
    qs = CargoCompetencia.objects.filter(cargo_id=usuario.cargo_id)
    if not qs.exists():
        return False, 'Cargo sem competências vinculadas.'
    total = qs.aggregate(total=Sum('peso'))['total'] or Decimal('0')
    if total <= 0:
        return False, 'Soma dos pesos das competências do cargo deve ser maior que zero.'
    return True, ''


def _check_avaliacao(avaliacao: Avaliacao) -> tuple[bool, str]:
    """avaliacao → feedback: todas notas_lider + nota_final_lider calculada."""
    AvaliacaoCompetencia = apps.get_model('reviews', 'AvaliacaoCompetencia')
    linhas = AvaliacaoCompetencia.objects.filter(avaliacao_id=avaliacao.pk)
    if not linhas.exists():
        return False, 'Não há linhas de competência na avaliação.'
    if linhas.filter(nota_lider__isnull=True).exists():
        return False, 'Todas as competências devem ter nota do líder.'
    if avaliacao.nota_final_lider is None:
        return False, 'Nota final do líder ainda não foi calculada.'
    return True, ''


def _check_feedback_conclusion(avaliacao: Avaliacao) -> tuple[bool, str]:
    """feedback → (concluída): feedback líder + ciente_em."""
    Feedback = apps.get_model('reviews', 'Feedback')
    lider_fb = Feedback.objects.filter(
        avaliacao_id=avaliacao.pk,
        tipo='lider',
    ).order_by('-pk').first()
    if lider_fb is None:
        return False, 'É necessário registrar o feedback do líder.'
    if lider_fb.ciente_em is None:
        return False, 'O colaborador ainda não deu ciência ao feedback.'
    return True, ''


def _create_competency_lines(avaliacao: Avaliacao) -> None:
    """Side effect ao entrar em avaliacao (implementação plena em T034)."""
    try:
        from apps.reviews.services.evaluation import create_competency_lines
    except ImportError:
        return
    create_competency_lines(avaliacao)

