"""Regras de domínio do PDI (status / arquivamento / conclusão)."""

from __future__ import annotations

from apps.pdi.models import AcaoPDI, PDI


class PDINotArchivableError(Exception):
    """PDI não pode ser arquivado no estado atual."""


class PDINotCompletableError(Exception):
    """PDI não pode ser concluído no estado atual."""


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


def pdi_can_complete(pdi: PDI, *, acoes: list[AcaoPDI] | None = None) -> bool:
    """True quando as pré-condições de ``complete_pdi`` estão satisfeitas.

    Aceita ``acoes`` já carregadas no detalhe para evitar query extra; se omitido,
    consulta ``pdi.acoes``.
    """
    if pdi.status != PDI.Status.ATIVO:
        return False
    if acoes is None:
        qs = pdi.acoes.all()
        return qs.exists() and not qs.exclude(status=AcaoPDI.Status.CONCLUIDA).exists()
    return bool(acoes) and all(a.status == AcaoPDI.Status.CONCLUIDA for a in acoes)


def complete_pdi(pdi: PDI) -> PDI:
    """Conclui o PDI quando 100% das ações estão concluídas.

    Pré-condições (backend — UI não decide):
    - ``status == ativo``
    - existe ≥1 ação
    - todas as ações com ``status == concluida``

    Rejeita arquivado, já concluído, plano vazio e ações pendentes/atrasadas.
    """
    if pdi.status == PDI.Status.ARQUIVADO:
        raise PDINotCompletableError(
            'Planos arquivados não podem ser concluídos.',
        )
    if pdi.status == PDI.Status.CONCLUIDO:
        raise PDINotCompletableError(
            'Este plano já está concluído.',
        )
    if pdi.status != PDI.Status.ATIVO:
        raise PDINotCompletableError(
            'Somente planos ativos podem ser concluídos.',
        )

    acoes = pdi.acoes.all()
    total = acoes.count()
    if total == 0:
        raise PDINotCompletableError(
            'Não é possível concluir um plano sem ações.',
        )
    incompletas = acoes.exclude(status=AcaoPDI.Status.CONCLUIDA).exists()
    if incompletas:
        raise PDINotCompletableError(
            'Todas as ações precisam estar concluídas para concluir o plano.',
        )

    pdi.status = PDI.Status.CONCLUIDO
    pdi.save(update_fields=['status', 'updated_at'])
    return pdi


def pdi_allows_action_mutations(pdi: PDI) -> bool:
    """Ações só podem ser criadas/editadas/excluídas em PDI não arquivado."""
    return pdi.status != PDI.Status.ARQUIVADO
