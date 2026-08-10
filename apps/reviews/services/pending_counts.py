"""Contagens de apresentação do líder (guidance UX) — somente leitura.

Feature ``008-cycle-guidance-ux`` / FR-006. Soma pendências elegíveis no escopo
já vigente (aprovações + avaliações + feedbacks) sem inventar elegibilidade.

**FR-013 / denylist**: este módulo MUST NÃO alterar nem importar mutators de
máquina de estados (``advance_stage`` / ``can_advance``), aprovação/reprovação
(``approve_*`` / ``reject_*``), fórmulas (``calcular_*``), AuthZ/escopo, models,
migrations ou URLs de domínio. Reusa ``get_visible_users`` e predicados já
existentes; zero escrita.
"""

from __future__ import annotations

from dataclasses import dataclass

from django.db.models import Exists, OuterRef

from apps.accounts.services.scope import get_visible_users
from apps.goals.forms import get_open_ciclo, meta_approval_actionable
from apps.goals.models import Meta
from apps.reviews.forms import (
    can_leader_assess,
    feedback_create_allowed,
    leader_assessment_editable,
)
from apps.reviews.models import Avaliacao, Feedback


@dataclass(frozen=True)
class LeaderPendingBadge:
    """DTO de apresentação do badge único de pendências (data-model.md / FR-006)."""

    total: int
    aprovacoes: int = 0
    avaliacoes: int = 0
    feedbacks: int = 0

    def __post_init__(self) -> None:
        parts = (self.aprovacoes, self.avaliacoes, self.feedbacks)
        if any(n < 0 for n in (self.total, *parts)):
            raise ValueError('contagens do badge devem ser >= 0')
        expected = self.aprovacoes + self.avaliacoes + self.feedbacks
        if self.total != expected:
            raise ValueError(
                f'total deve ser aprovacoes+avaliacoes+feedbacks '
                f'({expected}); recebido {self.total}'
            )


def _badge(aprovacoes: int, avaliacoes: int, feedbacks: int) -> LeaderPendingBadge:
    return LeaderPendingBadge(
        total=aprovacoes + avaliacoes + feedbacks,
        aprovacoes=aprovacoes,
        avaliacoes=avaliacoes,
        feedbacks=feedbacks,
    )


def _count_aprovacoes(leader, ciclo, visible_ids) -> int:
    """Metas onde ``meta_approval_actionable`` seria True no escopo visível."""
    avaliacoes = {
        av.usuario_id: av
        for av in Avaliacao.objects.filter(
            ciclo=ciclo,
            usuario_id__in=visible_ids,
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
        objetivo_estrategico__ciclo=ciclo,
    ).select_related('usuario')

    count = 0
    for meta in metas:
        avaliacao = avaliacoes.get(meta.usuario_id)
        if meta_approval_actionable(avaliacao, meta, leader):
            count += 1
    return count


def _count_avaliacoes(leader, ciclo, visible_ids) -> int:
    """Avaliações elegíveis ao leader assessment (mesmos predicados do hub)."""
    count = 0
    qs = Avaliacao.objects.filter(
        ciclo=ciclo,
        usuario_id__in=visible_ids,
        etapa=Avaliacao.Etapa.AVALIACAO,
    ).select_related('ciclo', 'usuario')
    for avaliacao in qs:
        if can_leader_assess(leader, avaliacao) and leader_assessment_editable(
            avaliacao
        ):
            count += 1
    return count


def _count_feedbacks(leader, ciclo, visible_ids) -> int:
    """Avaliações em feedback sem feedback do líder, onde create é permitido.

    Espelha ``feedback_create_allowed`` + etapa ``feedback`` + ausência de
    feedback tipo líder (pendência de condução, não ciência do colaborador).
    """
    leader_pk = getattr(leader, 'pk', None)
    has_lider_feedback = Feedback.objects.filter(
        avaliacao_id=OuterRef('pk'),
        tipo=Feedback.Tipo.LIDER,
    )
    qs = (
        Avaliacao.objects.filter(
            ciclo=ciclo,
            usuario_id__in=visible_ids,
            etapa=Avaliacao.Etapa.FEEDBACK,
        )
        .annotate(_has_lider_fb=Exists(has_lider_feedback))
        .filter(_has_lider_fb=False)
        .select_related('ciclo', 'usuario')
    )

    count = 0
    for avaliacao in qs:
        # Badge do líder: não conta a própria avaliação (ação de colaborador).
        if avaliacao.usuario_id == leader_pk:
            continue
        if feedback_create_allowed(leader, avaliacao):
            count += 1
    return count


def resolve_leader_pending_badge(leader) -> LeaderPendingBadge:
    """Deriva ``LeaderPendingBadge`` só com leitura + predicados existentes.

    Escopo ⊆ ``get_visible_users(leader)`` (sem alterar AuthZ). Sem ciclo aberto
    ou líder inválido → total zero (sem alarme falso).
    """
    if not getattr(leader, 'pk', None):
        return _badge(0, 0, 0)

    ciclo = get_open_ciclo()
    if ciclo is None:
        return _badge(0, 0, 0)

    visible_ids = list(get_visible_users(leader).values_list('pk', flat=True))
    if not visible_ids:
        return _badge(0, 0, 0)

    return _badge(
        _count_aprovacoes(leader, ciclo, visible_ids),
        _count_avaliacoes(leader, ciclo, visible_ids),
        _count_feedbacks(leader, ciclo, visible_ids),
    )
