"""Leadership adherence index (RF-26 / calculation-contract).

Compliance: mede obrigações cumpridas no prazo vs. total devido.
Ações atribuídas ao autor real (AuditLog / Feedback.autor / AcaoPDI.responsavel),
nunca ao ``line_manager`` atual.

Sem obrigações no escopo → estado ``neutro`` (``percentual`` NULL).
Pendências acionáveis só entram no denominador após ``ciclo.data_fim``.
"""

from __future__ import annotations

from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from django.db.models import Exists, OuterRef
from django.utils import timezone

from apps.accounts.models import CustomUser
from apps.audit.models import AuditLog
from apps.cycles.models import Ciclo
from apps.goals.forms import is_meta_approver
from apps.goals.models import Meta
from apps.pdi.models import AcaoPDI
from apps.reviews.forms import can_leader_assess
from apps.reviews.models import Avaliacao, Feedback
from apps.reviews.services.evaluation import self_assessment_submitted

_QUANT = Decimal('0.01')
_ESTADO_NEUTRO = 'neutro'
_ESTADO_CALCULAVEL = 'calculavel'

# Stage targets reached by leaving leader-owned stages (aprovacao_*/avaliacao).
_LEADER_ETAPA_TARGETS = frozenset(
    {
        Avaliacao.Etapa.RESULTADOS,  # left aprovacao_metas
        Avaliacao.Etapa.AVALIACAO,  # left aprovacao_resultados
        Avaliacao.Etapa.FEEDBACK,  # left avaliacao
    }
)

_AVALIACAO_ENTITY = 'reviews.Avaliacao'
_ACAO_PDI_ENTITY = 'pdi.AcaoPDI'


def _ratio(no_prazo: int, total: int) -> Decimal | None:
    if total == 0:
        return None
    return (Decimal(no_prazo) * Decimal('100') / Decimal(total)).quantize(
        _QUANT,
        rounding=ROUND_HALF_UP,
    )


def _component(no_prazo: int, total: int) -> dict:
    atrasado = max(total - no_prazo, 0)
    percentual = _ratio(no_prazo, total)
    return {
        'total': total,
        'no_prazo': no_prazo,
        'atrasado': atrasado,
        'percentual': str(percentual) if percentual is not None else None,
    }


def _on_or_before(when: date, deadline: date) -> bool:
    return when <= deadline


def _past_cycle_deadline(ciclo: Ciclo, ref_day: date) -> bool:
    return ref_day > ciclo.data_fim


def _direct_report_ids_in_ciclo(lider_id: int, ciclo_id: int) -> list[int]:
    return list(
        CustomUser.objects.filter(
            line_manager_id=lider_id,
            is_active=True,
            avaliacoes__ciclo_id=ciclo_id,
        )
        .values_list('pk', flat=True)
        .distinct(),
    )


def _meta_needs_leader_approval(
    avaliacao: Avaliacao,
    meta: Meta,
    leader_id: int,
) -> bool:
    leader = CustomUser.objects.filter(pk=leader_id).first()
    if leader is None or not is_meta_approver(leader, meta):
        return False
    if avaliacao.etapa == Avaliacao.Etapa.APROVACAO_METAS:
        return meta.status == Meta.Status.PENDENTE
    if avaliacao.etapa == Avaliacao.Etapa.APROVACAO_RESULTADOS:
        return (
            meta.status == Meta.Status.APROVADA
            and meta.status_resultado == Meta.StatusResultado.PENDENTE
        )
    return False


def _count_unfulfilled_aprovacoes(
    leader_id: int,
    ciclo: Ciclo,
    report_ids: list[int],
) -> int:
    if not report_ids:
        return 0
    avaliacoes = {
        av.usuario_id: av
        for av in Avaliacao.objects.filter(
            ciclo_id=ciclo.pk,
            usuario_id__in=report_ids,
            etapa__in=(
                Avaliacao.Etapa.APROVACAO_METAS,
                Avaliacao.Etapa.APROVACAO_RESULTADOS,
            ),
        ).select_related('ciclo', 'usuario')
    }
    if not avaliacoes:
        return 0

    metas = Meta.objects.filter(
        usuario_id__in=avaliacoes.keys(),
        objetivo_estrategico__ciclo_id=ciclo.pk,
    ).select_related('usuario')

    count = 0
    for meta in metas:
        avaliacao = avaliacoes.get(meta.usuario_id)
        if avaliacao is not None and _meta_needs_leader_approval(
            avaliacao,
            meta,
            leader_id,
        ):
            count += 1
    return count


def _count_unfulfilled_avaliacoes(
    leader,
    ciclo: Ciclo,
    report_ids: list[int],
) -> int:
    if not report_ids:
        return 0
    count = 0
    qs = Avaliacao.objects.filter(
        ciclo_id=ciclo.pk,
        usuario_id__in=report_ids,
        etapa=Avaliacao.Etapa.AVALIACAO,
    ).select_related('ciclo', 'usuario')
    for avaliacao in qs:
        if can_leader_assess(leader, avaliacao) and self_assessment_submitted(
            avaliacao,
        ):
            count += 1
    return count


def _count_unfulfilled_feedbacks(
    leader,
    ciclo: Ciclo,
    report_ids: list[int],
) -> int:
    if not report_ids:
        return 0
    leader_pk = getattr(leader, 'pk', None)
    has_lider_feedback = Feedback.objects.filter(
        avaliacao_id=OuterRef('pk'),
        tipo=Feedback.Tipo.LIDER,
    )
    qs = (
        Avaliacao.objects.filter(
            ciclo_id=ciclo.pk,
            usuario_id__in=report_ids,
            etapa=Avaliacao.Etapa.FEEDBACK,
        )
        .annotate(_has_lider_fb=Exists(has_lider_feedback))
        .filter(_has_lider_fb=False)
        .select_related('ciclo', 'usuario')
    )
    count = 0
    for avaliacao in qs:
        if avaliacao.usuario_id == leader_pk:
            continue
        if can_leader_assess(leader, avaliacao):
            count += 1
    return count


def _aprovacoes_component(
    lider_id: int,
    ciclo: Ciclo,
    report_ids: list[int],
    *,
    ref_day: date,
) -> dict:
    avaliacao_ids = list(
        Avaliacao.objects.filter(
            ciclo_id=ciclo.pk,
            usuario_id__in=report_ids,
        ).values_list('pk', flat=True),
    )
    no_prazo = 0
    total = 0
    if avaliacao_ids:
        logs = AuditLog.objects.filter(
            usuario_id=lider_id,
            acao=AuditLog.Acao.UPDATE,
            entity_type=_AVALIACAO_ENTITY,
            entity_id__in=avaliacao_ids,
            campo='etapa',
            valor_novo__in=_LEADER_ETAPA_TARGETS,
        ).only('created_at')
        for log in logs.iterator():
            total += 1
            action_date = timezone.localtime(log.created_at).date()
            if _on_or_before(action_date, ciclo.data_fim):
                no_prazo += 1

    if _past_cycle_deadline(ciclo, ref_day):
        leader = CustomUser.objects.filter(pk=lider_id).first()
        if leader is not None:
            total += _count_unfulfilled_aprovacoes(lider_id, ciclo, report_ids)
            total += _count_unfulfilled_avaliacoes(leader, ciclo, report_ids)

    return _component(no_prazo, total)


def _feedbacks_component(
    lider_id: int,
    ciclo: Ciclo,
    report_ids: list[int],
    leader,
    *,
    ref_day: date,
) -> dict:
    no_prazo = 0
    total = 0
    feedbacks = Feedback.objects.filter(
        autor_id=lider_id,
        tipo=Feedback.Tipo.LIDER,
        avaliacao__ciclo_id=ciclo.pk,
        avaliacao__usuario_id__in=report_ids,
    ).only('created_at')
    for fb in feedbacks.iterator():
        total += 1
        action_date = timezone.localtime(fb.created_at).date()
        if _on_or_before(action_date, ciclo.data_fim):
            no_prazo += 1

    if _past_cycle_deadline(ciclo, ref_day):
        total += _count_unfulfilled_feedbacks(leader, ciclo, report_ids)

    return _component(no_prazo, total)


def _acao_pdi_completion_date(acao: AcaoPDI) -> date | None:
    """Date when status became ``concluida`` (AuditLog), else ``updated_at``."""
    log = (
        AuditLog.objects.filter(
            entity_type=_ACAO_PDI_ENTITY,
            entity_id=acao.pk,
            campo='status',
            valor_novo=AcaoPDI.Status.CONCLUIDA,
        )
        .order_by('created_at')
        .only('created_at')
        .first()
    )
    if log is not None:
        return timezone.localtime(log.created_at).date()
    if acao.status == AcaoPDI.Status.CONCLUIDA:
        return timezone.localtime(acao.updated_at).date()
    return None


def _acoes_pdi_component(lider_id: int, ciclo: Ciclo, ref_day: date) -> dict:
    """PDI actions owned by the leader whose prazo falls in the cycle window."""
    acoes = AcaoPDI.objects.filter(
        responsavel_id=lider_id,
        prazo__gte=ciclo.data_inicio,
        prazo__lte=ciclo.data_fim,
    ).only('status', 'prazo', 'updated_at')

    total = 0
    no_prazo = 0
    for acao in acoes.iterator():
        # Pending future deadlines stay out of scope (neutral).
        if acao.status != AcaoPDI.Status.CONCLUIDA and acao.prazo > ref_day:
            continue

        total += 1
        if acao.status == AcaoPDI.Status.CONCLUIDA:
            completed = _acao_pdi_completion_date(acao)
            if completed is not None and _on_or_before(completed, acao.prazo):
                no_prazo += 1
        # atrasada / overdue pending → not on time
    return _component(no_prazo, total)


def _mean_percentual(*componentes: dict) -> Decimal | None:
    values = [
        Decimal(c['percentual'])
        for c in componentes
        if c.get('percentual') is not None
    ]
    if not values:
        return None
    total = sum(values, Decimal('0')) / Decimal(len(values))
    return total.quantize(_QUANT, rounding=ROUND_HALF_UP)


def compute_adherence(
    lider_id: int,
    ciclo_id: int,
    *,
    today: date | None = None,
) -> tuple[Decimal | None, dict]:
    """Return ``(percentual | None, componentes JSON-serializable)``.

    ``percentual`` NULL → estado ``neutro`` (sem obrigações).
    Índice = média dos componentes com ``total > 0``.
    """
    ciclo = Ciclo.objects.only('pk', 'data_inicio', 'data_fim').get(pk=ciclo_id)
    ref_day = today if today is not None else timezone.localdate()
    leader = CustomUser.objects.filter(pk=lider_id).first()
    report_ids = _direct_report_ids_in_ciclo(lider_id, ciclo_id)

    aprovacoes = _aprovacoes_component(
        lider_id,
        ciclo,
        report_ids,
        ref_day=ref_day,
    )
    feedbacks = _feedbacks_component(
        lider_id,
        ciclo,
        report_ids,
        leader,
        ref_day=ref_day,
    )
    acoes_pdi = _acoes_pdi_component(lider_id, ciclo, ref_day)

    percentual = _mean_percentual(aprovacoes, feedbacks, acoes_pdi)
    estado = _ESTADO_CALCULAVEL if percentual is not None else _ESTADO_NEUTRO

    componentes = {
        'estado': estado,
        'aprovacoes': aprovacoes,
        'feedbacks': feedbacks,
        'acoes_pdi': acoes_pdi,
    }
    return percentual, componentes
