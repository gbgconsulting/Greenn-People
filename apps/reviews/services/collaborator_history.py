"""Montagem da listagem «Minhas Avaliações» (colaborador sem escopo de time)."""

from __future__ import annotations

from typing import Any, TypedDict

from apps.cycles.models import Ciclo
from apps.reviews.models import Avaliacao


class CollaboratorHistoryRow(TypedDict):
    avaliacao: Avaliacao
    is_highlight: bool
    status_label: str
    status_variant: str
    ciclo_subtitulo: str


def is_collaborator_history_view(user) -> bool:
    """True para colaborador puro (sem liderados / gestão / admin)."""
    from apps.accounts.services.scope import get_scope_level

    return get_scope_level(user) == 'collaborator'


def _ciclo_subtitulo(ciclo: Ciclo) -> str:
    if ciclo.status == Ciclo.Status.ABERTO:
        return 'Ciclo em andamento'
    return 'Avaliação de desempenho'


def resolve_cycle_status(avaliacao: Avaliacao) -> tuple[str, str]:
    """Rótulo e variante de badge para uma avaliação no histórico pessoal."""
    if avaliacao.concluida:
        return 'Concluído', 'concluido'

    if avaliacao.ciclo.status == Ciclo.Status.ENCERRADO:
        return 'Encerrado', 'arquivado'

    if avaliacao.etapa == Avaliacao.Etapa.AVALIACAO:
        return 'Em andamento', 'em_andamento'

    if avaliacao.etapa in {
        Avaliacao.Etapa.APROVACAO_METAS,
        Avaliacao.Etapa.APROVACAO_RESULTADOS,
    }:
        return 'Pendente', 'pendente'

    if avaliacao.etapa == Avaliacao.Etapa.FEEDBACK:
        return 'Feedback', 'em_andamento'

    return avaliacao.get_etapa_display(), 'em_andamento'


def build_collaborator_history_rows(
    avaliacoes: list[Avaliacao] | Any,
) -> list[CollaboratorHistoryRow]:
    """Linhas ordenadas (ciclo mais recente primeiro) para o template colaborador."""
    rows: list[CollaboratorHistoryRow] = []
    for index, avaliacao in enumerate(avaliacoes):
        status_label, status_variant = resolve_cycle_status(avaliacao)
        rows.append(
            {
                'avaliacao': avaliacao,
                'is_highlight': index == 0,
                'status_label': status_label,
                'status_variant': status_variant,
                'ciclo_subtitulo': _ciclo_subtitulo(avaliacao.ciclo),
            },
        )
    return rows
