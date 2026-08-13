"""Orquestração da importação de colaboradores legado Sólides.

Superfície pública: ``import_colaboradores`` (reexportada por ``__init__``).
Fase A (T018): parse → crosswalk → Area → Cargo → CustomUser upsert.
Fase B (T022): hierarquia ``line_manager`` após persistir todos os usuários.
Dry-run/exit codes (T025–T027).
"""

from __future__ import annotations

from pathlib import Path

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import CustomUser
from apps.accounts.services.legacy_import.crosswalk import (
    CrosswalkIndex,
    build_crosswalk,
)
from apps.accounts.services.legacy_import.hierarchy import apply_hierarchy
from apps.accounts.services.legacy_import.parse_xlsx import (
    ColaboradorRow,
    parse_avaliacoes_crosswalk_xlsx,
    parse_colaboradores_xlsx,
)
from apps.accounts.services.legacy_import.report import (
    ImportReport,
    note_demitido_inativo,
    note_solides_id_preenchido,
    record_atualizado,
    record_conflito,
    record_criado,
    record_nao_importavel,
)
from apps.accounts.services.legacy_import.resolve import (
    ResolveSession,
    ResolvedRow,
    resolve_email,
    resolve_row,
)


def import_colaboradores(
    colaboradores_path: str | Path,
    *,
    avaliacoes_path: str | Path | None = None,
    dry_run: bool = False,
) -> ImportReport:
    """Orquestra parse → crosswalk → fase A → fase B (ou dry-run).

    Assinatura alinhada a ``contracts/import-command-contract.md``.
    Persistência: ``transaction.atomic()`` — Area → Cargo → CustomUser
    (``full_clean`` + ``save`` / ``create_user`` + ``set_unusable_password``)
    e, em 2ª passada, ``line_manager`` via ``apply_hierarchy`` (R5 / FR-009);
    ``email_confirmado_em=timezone.now()``; sem PII extra; denylist intacta.
    Dry-run completo / exit codes: T025–T027.
    """
    parsed = parse_colaboradores_xlsx(colaboradores_path)
    report = ImportReport(
        modo="dry-run" if dry_run else "persist",
        colaboradores_file=parsed.path,
        avaliacoes_file=str(avaliacoes_path) if avaliacoes_path else "",
    )

    crosswalk = CrosswalkIndex()
    if avaliacoes_path is not None:
        aval = parse_avaliacoes_crosswalk_xlsx(avaliacoes_path)
        report.avaliacoes_file = aval.path
        crosswalk = build_crosswalk(aval.rows, report)

    with transaction.atomic():
        try:
            _persist_phase_a(parsed.rows, crosswalk, report)
            apply_hierarchy(parsed.rows, report)
        finally:
            # T025 refinará dry-run; por ora garante zero commit se dry_run.
            if dry_run:
                transaction.set_rollback(True)

    return report


def _persist_phase_a(
    rows: tuple[ColaboradorRow, ...],
    crosswalk: CrosswalkIndex,
    report: ImportReport,
) -> None:
    """Fase A: Area → Cargo → CustomUser upsert por e-mail (R5 / R12)."""
    session = ResolveSession(report=report)
    # e-mail normalizado → primeira linha que o reivindicou (backup).
    claimed_emails: dict[str, int] = {}

    for row in rows:
        email = resolve_email(row)
        if not email:
            record_nao_importavel(
                report,
                linha=row.linha,
                motivo="sem_email",
            )
            continue

        first_linha = claimed_emails.get(email)
        if first_linha is not None:
            record_conflito(
                report,
                tipo="email_duplicado_backup",
                extra=f"email={email}",
                motivo=f"linhas={first_linha},{row.linha}",
            )
            continue
        claimed_emails[email] = row.linha

        resolved = resolve_row(row, session)
        _upsert_user(resolved, row, crosswalk, report)


def _upsert_user(
    resolved: ResolvedRow,
    row: ColaboradorRow,
    crosswalk: CrosswalkIndex,
    report: ImportReport,
) -> CustomUser:
    """Cria ou atualiza ``CustomUser`` pela chave natural e-mail (R12).

    - Create: ``create_user`` + ``set_unusable_password``; confirma e-mail.
    - Update: campos divergentes via ``full_clean`` + ``save``.
    - ``solides_id`` via crosswalk (ambíguo/ausente → null; colisão unique
      reportada sem corromper o dono existente).
    - Demissão bloqueada por liderados ativos → conflito e mantém ativo (R11).
    """
    assert resolved.email is not None
    email = resolved.email
    solides_id = _resolve_solides_id(resolved.nome, crosswalk, email, report)
    area_nome = resolved.area.nome if resolved.area is not None else ""
    cargo_nome = resolved.cargo.nome if resolved.cargo is not None else ""

    existing = CustomUser.objects.filter(email=email).first()
    if existing is None:
        return _create_user(
            resolved,
            solides_id=solides_id,
            area_nome=area_nome,
            cargo_nome=cargo_nome,
            report=report,
        )

    return _update_user(
        existing,
        resolved,
        solides_id=solides_id,
        area_nome=area_nome,
        cargo_nome=cargo_nome,
        report=report,
    )


def _resolve_solides_id(
    nome: str,
    crosswalk: CrosswalkIndex,
    email: str,
    report: ImportReport,
) -> str | None:
    """Lookup crosswalk + guarda unicidade de ``solides_id`` no DB."""
    candidate = crosswalk.lookup(nome)
    if not candidate:
        return None

    other = (
        CustomUser.objects.filter(solides_id=candidate)
        .exclude(email=email)
        .first()
    )
    if other is not None:
        record_conflito(
            report,
            tipo="solides_id_duplicado",
            extra=f"solides_id={candidate}",
            motivo=f"email={email}|existente={other.email}",
        )
        return None
    return candidate


def _create_user(
    resolved: ResolvedRow,
    *,
    solides_id: str | None,
    area_nome: str,
    cargo_nome: str,
    report: ImportReport,
) -> CustomUser:
    """Cria usuário com senha inutilizável e e-mail confirmado (R6 / R7)."""
    assert resolved.email is not None
    user = CustomUser.objects.create_user(
        email=resolved.email,
        password=None,
        nome=resolved.nome,
        area=resolved.area,
        cargo=resolved.cargo,
        is_active=resolved.is_active,
        solides_id=solides_id,
        email_confirmado_em=timezone.now(),
    )
    user.set_unusable_password()
    user.save(update_fields=["password"])

    record_criado(
        report,
        nome=resolved.nome,
        email=resolved.email,
        area=area_nome,
        cargo=cargo_nome,
    )
    if solides_id:
        note_solides_id_preenchido(report)
    if not resolved.is_active:
        note_demitido_inativo(report)
    return user


def _update_user(
    user: CustomUser,
    resolved: ResolvedRow,
    *,
    solides_id: str | None,
    area_nome: str,
    cargo_nome: str,
    report: ImportReport,
) -> CustomUser:
    """Atualiza campos divergentes; conta inalterado se noop (R12)."""
    assert resolved.email is not None

    # Crosswalk resolve → atualiza; ausente/ambíguo não apaga solides_id existente.
    desired_solides = solides_id if solides_id is not None else user.solides_id

    business_changed = (
        user.nome != resolved.nome
        or user.area_id != (resolved.area.pk if resolved.area else None)
        or user.cargo_id != (resolved.cargo.pk if resolved.cargo else None)
        or user.is_active != resolved.is_active
        or user.solides_id != desired_solides
    )

    if not business_changed:
        report.usuarios_inalterados += 1
        return user

    previous_solides = user.solides_id
    previous_active = user.is_active

    user.nome = resolved.nome
    user.area = resolved.area
    user.cargo = resolved.cargo
    user.is_active = resolved.is_active
    user.solides_id = desired_solides
    user.email_confirmado_em = timezone.now()

    try:
        user.full_clean()
        user.save()
    except ValidationError as exc:
        if _is_deactivation_blocked(exc) and not resolved.is_active:
            # R11: reporta e mantém ativo; aplica demais campos.
            user.is_active = True
            record_conflito(
                report,
                tipo="desativacao_bloqueada_liderados",
                extra=f"email={resolved.email}",
                motivo="liderados_ativos",
            )
            user.full_clean()
            user.save()
        else:
            raise

    record_atualizado(
        report,
        nome=resolved.nome,
        email=resolved.email,
        area=area_nome,
        cargo=cargo_nome,
    )
    if desired_solides and previous_solides != desired_solides:
        note_solides_id_preenchido(report)
    if previous_active and not user.is_active:
        note_demitido_inativo(report)
    return user


def _is_deactivation_blocked(exc: ValidationError) -> bool:
    """True se ``ValidationError`` bloqueou ``is_active`` (liderados ativos)."""
    error_dict = getattr(exc, "error_dict", None) or {}
    return "is_active" in error_dict
