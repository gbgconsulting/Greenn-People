"""Leadership adherence index (RF-26 / calculation-contract).

Actions are attributed to the real author (AuditLog.usuario / Feedback.autor /
AcaoPDI.responsavel), never to the collaborator's current ``line_manager``.
"""

from __future__ import annotations

from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from django.utils import timezone

from apps.audit.models import AuditLog
from apps.cycles.models import Ciclo
from apps.pdi.models import AcaoPDI
from apps.reviews.models import Avaliacao, Feedback

_QUANT = Decimal('0.01')

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


def _ratio(no_prazo: int, total: int) -> Decimal:
    if total == 0:
        return Decimal('100.00')
    return (Decimal(no_prazo) * Decimal('100') / Decimal(total)).quantize(
        _QUANT,
        rounding=ROUND_HALF_UP,
    )


def _component(no_prazo: int, total: int) -> dict:
    percentual = _ratio(no_prazo, total)
    return {
        'total': total,
        'no_prazo': no_prazo,
        'percentual': str(percentual),
    }


def _on_or_before(when: date, deadline: date) -> bool:
    return when <= deadline


def _aprovacoes_component(lider_id: int, ciclo: Ciclo) -> dict:
    avaliacao_ids = list(
        Avaliacao.objects.filter(ciclo_id=ciclo.pk).values_list('pk', flat=True),
    )
    if not avaliacao_ids:
        return _component(0, 0)

    logs = AuditLog.objects.filter(
        usuario_id=lider_id,
        acao=AuditLog.Acao.UPDATE,
        entity_type=_AVALIACAO_ENTITY,
        entity_id__in=avaliacao_ids,
        campo='etapa',
        valor_novo__in=_LEADER_ETAPA_TARGETS,
    ).only('created_at')

    total = 0
    no_prazo = 0
    for log in logs.iterator():
        total += 1
        action_date = timezone.localtime(log.created_at).date()
        if _on_or_before(action_date, ciclo.data_fim):
            no_prazo += 1
    return _component(no_prazo, total)


def _feedbacks_component(lider_id: int, ciclo: Ciclo) -> dict:
    feedbacks = Feedback.objects.filter(
        autor_id=lider_id,
        tipo=Feedback.Tipo.LIDER,
        avaliacao__ciclo_id=ciclo.pk,
    ).only('created_at')

    total = 0
    no_prazo = 0
    for fb in feedbacks.iterator():
        total += 1
        action_date = timezone.localtime(fb.created_at).date()
        if _on_or_before(action_date, ciclo.data_fim):
            no_prazo += 1
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


def _acoes_pdi_component(lider_id: int, ciclo: Ciclo, today: date) -> dict:
    """PDI actions owned by the leader whose prazo falls in the cycle window."""
    acoes = AcaoPDI.objects.filter(
        responsavel_id=lider_id,
        prazo__gte=ciclo.data_inicio,
        prazo__lte=ciclo.data_fim,
    ).only('status', 'prazo', 'updated_at')

    total = 0
    no_prazo = 0
    for acao in acoes.iterator():
        # Only score due or completed actions (pending future deadlines excluded).
        if acao.status != AcaoPDI.Status.CONCLUIDA and acao.prazo > today:
            continue

        total += 1
        if acao.status == AcaoPDI.Status.CONCLUIDA:
            completed = _acao_pdi_completion_date(acao)
            if completed is not None and _on_or_before(completed, acao.prazo):
                no_prazo += 1
        # atrasada / overdue pending → not on time
    return _component(no_prazo, total)


def compute_adherence(
    lider_id: int,
    ciclo_id: int,
    *,
    today: date | None = None,
) -> tuple[Decimal, dict]:
    """Return ``(percentual 0–100, componentes JSON-serializable)``.

    Index = equal-weight mean of approvals, feedbacks and on-time PDI actions.
    """
    ciclo = Ciclo.objects.only('pk', 'data_inicio', 'data_fim').get(pk=ciclo_id)
    ref_day = today if today is not None else timezone.localdate()

    aprovacoes = _aprovacoes_component(lider_id, ciclo)
    feedbacks = _feedbacks_component(lider_id, ciclo)
    acoes_pdi = _acoes_pdi_component(lider_id, ciclo, ref_day)

    componentes = {
        'aprovacoes': aprovacoes,
        'feedbacks': feedbacks,
        'acoes_pdi': acoes_pdi,
    }
    percentual = (
        Decimal(aprovacoes['percentual'])
        + Decimal(feedbacks['percentual'])
        + Decimal(acoes_pdi['percentual'])
    ) / Decimal('3')
    percentual = percentual.quantize(_QUANT, rounding=ROUND_HALF_UP)
    return percentual, componentes
