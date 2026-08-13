"""Fase B: resolver ``line_manager`` via ``Superior direto id`` → ``solides_id``.

Contrato: ``contracts/column-mapping-contract.md`` §line_manager;
research R5 (2ª passada após persistir todos os usuários) e R11
(gestor demitido permitido). Aciclicidade via ``CustomUser.clean()``
(RF-04.1) — ``full_clean()`` + ``save()``; vínculo inválido não é
aplicado. Denylist de domínio intacta.
"""

from __future__ import annotations

from collections.abc import Iterable

from django.core.exceptions import ValidationError

from apps.accounts.models import CustomUser
from apps.accounts.services.legacy_import.parse_xlsx import ColaboradorRow
from apps.accounts.services.legacy_import.report import (
    ImportReport,
    note_gestor_vinculado,
    note_sem_gestor,
    record_ciclo_hierarquia,
    record_conflito,
)
from apps.accounts.services.legacy_import.resolve import resolve_email


def apply_hierarchy(
    rows: Iterable[ColaboradorRow],
    report: ImportReport,
) -> None:
    """Aplica vínculos de gestor em 2ª passada (R5 / FR-009 / FR-010).

    Para cada linha importável (e-mail único, usuário já persistido):

    - ``Superior direto id`` vazio → ``sem_gestor`` (não altera vínculo).
    - ID sem ``CustomUser.solides_id`` → conflito ``gestor_nao_resolvido``.
    - Gestor encontrado → ``user.line_manager = manager``; ``full_clean()``
      + ``save()``. Ciclo / auto-gestor → reverte, registra
      ``ciclos_hierarquia``, não persiste o vínculo.
    - Gestor demitido (inativo) é permitido (R11).
    """
    seen_emails: set[str] = set()

    for row in rows:
        email = resolve_email(row)
        if not email or email in seen_emails:
            continue
        seen_emails.add(email)

        user = (
            CustomUser.objects.select_related("line_manager")
            .filter(email=email)
            .first()
        )
        if user is None:
            continue

        superior_id = (row.superior_direto_id or "").strip()
        if not superior_id:
            note_sem_gestor(report)
            continue

        manager = lookup_manager_by_solides_id(superior_id)
        if manager is None:
            record_conflito(
                report,
                tipo="gestor_nao_resolvido",
                extra=f"superior_id={superior_id}",
                motivo=f"usuario={email}",
            )
            continue

        if user.line_manager_id == manager.pk:
            note_gestor_vinculado(report)
            continue

        _assign_line_manager(user, manager, report)


def lookup_manager_by_solides_id(superior_id: str) -> CustomUser | None:
    """``CustomUser`` cujo ``solides_id`` bate com ``Superior direto id``.

    Match canônico: ``str(id)`` já normalizado no parse (contrato §Gestor).
    """
    sid = (superior_id or "").strip()
    if not sid:
        return None
    return (
        CustomUser.objects.select_related("line_manager")
        .filter(solides_id=sid)
        .first()
    )


def _assign_line_manager(
    user: CustomUser,
    manager: CustomUser,
    report: ImportReport,
) -> None:
    """Persiste ``line_manager`` via ``full_clean`` + ``save`` (R4).

    Em ``ValidationError`` de ``line_manager`` (ciclo / auto-gestor):
    restaura o vínculo anterior **sem** ``save`` e registra o ciclo.
    Em bloqueio de desativação (usuário já inativo com liderados ativos
    — edge case R11 / reexecução): reativa temporariamente para gravar o
    vínculo; a fase C do importer tenta demitir de novo ou reporta conflito.
    Demais erros de validação propagam (não silenciar).
    """
    previous = user.line_manager
    user.line_manager = manager
    try:
        user.full_clean()
        user.save()
    except ValidationError as exc:
        if _is_line_manager_error(exc):
            label = _cycle_user_label(user, manager)
            user.line_manager = previous
            record_ciclo_hierarquia(report, usuarios=label)
            return
        if _is_deactivation_blocked(exc) and not user.is_active:
            # Precisa gravar o vínculo sem abortar a carga (R11).
            user.is_active = True
            user.full_clean()
            user.save()
            note_gestor_vinculado(report)
            return
        user.line_manager = previous
        raise

    note_gestor_vinculado(report)


def _is_line_manager_error(exc: ValidationError) -> bool:
    """True se ``clean()`` rejeitou ``line_manager`` (ciclo ou auto-gestor)."""
    error_dict = getattr(exc, "error_dict", None) or {}
    return "line_manager" in error_dict


def _is_deactivation_blocked(exc: ValidationError) -> bool:
    """True se ``clean()`` bloqueou ``is_active`` (liderados ativos)."""
    error_dict = getattr(exc, "error_dict", None) or {}
    return "is_active" in error_dict


def _cycle_user_label(user: CustomUser, attempted_manager: CustomUser) -> str:
    """Cadeia de e-mails do ciclo para a amostra do relatório.

    Formato contrato: ``usuarios=a@..., b@..., c@...``. E-mails são
    mascarados em ``format_report``.
    """
    emails = [user.email]
    seen = {user.pk}
    current: CustomUser | None = attempted_manager
    while current is not None:
        emails.append(current.email)
        if current.pk in seen:
            break
        seen.add(current.pk)
        current = current.line_manager
    return ", ".join(emails)
