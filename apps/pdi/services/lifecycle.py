"""Regras de domínio do PDI (status / arquivamento)."""

from __future__ import annotations

from apps.pdi.models import PDI


class PDINotArchivableError(Exception):
    """PDI não pode ser arquivado no estado atual."""


def archive_pdi(pdi: PDI) -> PDI:
    """Arquiva o PDI (soft). Idempotente se já estiver arquivado.

    Regras (backend):
    - ``ativo`` → ``arquivado``
    - já ``arquivado`` → no-op
    - ``concluido`` → rejeitado (histórico concluído permanece)
    """
    if pdi.status == PDI.Status.ARQUIVADO:
        return pdi
    if pdi.status != PDI.Status.ATIVO:
        raise PDINotArchivableError(
            'Somente planos ativos podem ser arquivados.',
        )
    pdi.status = PDI.Status.ARQUIVADO
    pdi.save(update_fields=['status', 'updated_at'])
    return pdi


def pdi_allows_action_mutations(pdi: PDI) -> bool:
    """Ações só podem ser criadas/editadas/excluídas em PDI não arquivado."""
    return pdi.status != PDI.Status.ARQUIVADO
