"""Resolução de e-mail, Area, Cargo e is_active do legado Sólides.

Contrato: ``contracts/column-mapping-contract.md`` (US2).
Reuso read-only: ``catalog_import.normalize`` + ``infer_cargo_nivel`` (003).
Denylist de domínio intacta — sem PII extra.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from apps.accounts.models import CustomUser
from apps.accounts.services.legacy_import.dates import is_active_from_dismissal
from apps.accounts.services.legacy_import.parse_xlsx import ColaboradorRow
from apps.accounts.services.legacy_import.report import ImportReport, ReportEntry
from apps.competencies.services.catalog_import.mapping import infer_cargo_nivel
from apps.competencies.services.catalog_import.normalize import (
    canonical_key,
    display_name,
)
from apps.organization.models import Area, Cargo


@dataclass
class ResolveSession:
    """Estado por execução de import — contadores únicos de Area/Cargo."""

    report: ImportReport | None = None
    seen_area_pks: set[int] = field(default_factory=set)
    seen_cargo_pks: set[int] = field(default_factory=set)


@dataclass(frozen=True)
class ResolvedRow:
    """Identidade resolvida de uma linha de colaboradores (pré-persist User)."""

    nome: str
    email: str | None
    is_active: bool
    area: Area | None
    cargo: Cargo | None


def resolve_email(row: ColaboradorRow) -> str | None:
    """Primeiro e-mail não vazio: empresarial → corporativo → pessoal.

    ``normalize`` = ``display_name`` (collapse whitespace) +
    ``CustomUserManager.normalize_email``.
    """
    for raw in (row.email_empresarial, row.email, row.email_pessoal):
        normalized = _normalize_email_cell(raw)
        if normalized:
            return normalized
    return None


def resolve_is_active(row: ColaboradorRow) -> bool:
    """``is_active = NOT is_dismissal_filled(Data demissão)``."""
    return is_active_from_dismissal(row.data_demissao)


def resolve_area(
    row: ColaboradorRow,
    session: ResolveSession | None = None,
) -> Area | None:
    """``get_or_create`` Area por ``Departamento`` (display); parent=null.

    Departamento vazio → ``None`` (sem área).
    """
    nome = display_name(row.departamento) if row.departamento else ""
    if not nome:
        return None

    existing = Area.objects.filter(nome=nome, is_active=True).first()
    if existing is not None:
        _note_area_reuse(existing, session)
        return existing

    area = Area(nome=nome, parent=None, is_active=True)
    area.full_clean()
    area.save()
    if session is not None:
        session.seen_area_pks.add(area.pk)
        if session.report is not None:
            session.report.areas_criadas += 1
    return area


def resolve_cargo(
    row: ColaboradorRow,
    session: ResolveSession | None = None,
) -> Cargo | None:
    """Lookup ``Cargo`` por ``solides_id`` → ``canonical_key`` ativo → create.

    - Match por ID: preferido; nome divergente → conflito reportado (não bloqueia).
    - Match por nome ativo: preenche ``solides_id`` se ``Cargo ID`` vier no backup.
    - Miss: create com ``nivel`` via ``infer_cargo_nivel`` (senioridade 003).
    """
    cargo_id = (row.cargo_id or "").strip()
    display = display_name(row.cargo) if row.cargo else ""
    report = session.report if session is not None else None

    if cargo_id:
        by_id = Cargo.objects.filter(solides_id=cargo_id).first()
        if by_id is not None:
            if (
                display
                and report is not None
                and canonical_key(by_id.nome) != canonical_key(display)
            ):
                report.conflitos.append(
                    ReportEntry(
                        label="cargo_nome",
                        extra=f"solides_id={cargo_id}",
                        motivo=f"catalogo={by_id.nome} | backup={display}",
                    )
                )
            _note_cargo_unchanged(by_id, session)
            return by_id

    if display:
        key = canonical_key(display)
        by_name = _lookup_cargo_by_canonical_key(key)
        if by_name is not None:
            return _maybe_attach_solides_id(by_name, cargo_id, session)

    if not display:
        # Sem nome (com ou sem ID sem match) — não inventa cargo.
        return None

    nivel = infer_cargo_nivel(display)
    cargo = Cargo(
        nome=display,
        nivel=nivel,
        is_active=True,
        solides_id=cargo_id or None,
    )
    cargo.full_clean()
    cargo.save()
    if session is not None:
        session.seen_cargo_pks.add(cargo.pk)
        if session.report is not None:
            session.report.cargos_criados += 1
    return cargo


def resolve_row(
    row: ColaboradorRow,
    session: ResolveSession | None = None,
) -> ResolvedRow:
    """Resolve nome, e-mail, is_active, Area e Cargo de uma linha."""
    return ResolvedRow(
        nome=display_name(row.nome),
        email=resolve_email(row),
        is_active=resolve_is_active(row),
        area=resolve_area(row, session),
        cargo=resolve_cargo(row, session),
    )


def _normalize_email_cell(raw: str) -> str:
    collapsed = display_name(raw) if raw else ""
    if not collapsed:
        return ""
    return CustomUser.objects.normalize_email(collapsed)


def _lookup_cargo_by_canonical_key(key: str) -> Cargo | None:
    """Primeiro Cargo ativo cuja ``canonical_key(nome)`` coincide."""
    if not key:
        return None
    for cargo in Cargo.objects.filter(is_active=True).iterator():
        if canonical_key(cargo.nome) == key:
            return cargo
    return None


def _maybe_attach_solides_id(
    cargo: Cargo,
    cargo_id: str,
    session: ResolveSession | None,
) -> Cargo:
    """Atualiza ``solides_id`` quando match por nome e ID presente (R9)."""
    report = session.report if session is not None else None

    if not cargo_id:
        _note_cargo_unchanged(cargo, session)
        return cargo

    if cargo.solides_id == cargo_id:
        _note_cargo_unchanged(cargo, session)
        return cargo

    # Já tem outro solides_id — não sobrescreve; reporta conflito.
    if cargo.solides_id and cargo.solides_id != cargo_id:
        if report is not None:
            report.conflitos.append(
                ReportEntry(
                    label="cargo_solides_id",
                    extra=f"cargo={cargo.nome}",
                    motivo=(
                        f"existente={cargo.solides_id} | backup={cargo_id}"
                    ),
                )
            )
        _note_cargo_unchanged(cargo, session)
        return cargo

    cargo.solides_id = cargo_id
    cargo.full_clean()
    cargo.save(update_fields=["solides_id", "updated_at"])
    if session is not None:
        if cargo.pk not in session.seen_cargo_pks:
            session.seen_cargo_pks.add(cargo.pk)
            if report is not None:
                report.cargos_atualizados += 1
    elif report is not None:
        report.cargos_atualizados += 1
    return cargo


def _note_area_reuse(area: Area, session: ResolveSession | None) -> None:
    if session is None or session.report is None:
        return
    if area.pk in session.seen_area_pks:
        return
    session.seen_area_pks.add(area.pk)
    session.report.areas_reutilizadas += 1


def _note_cargo_unchanged(cargo: Cargo, session: ResolveSession | None) -> None:
    if session is None or session.report is None:
        return
    if cargo.pk in session.seen_cargo_pks:
        return
    session.seen_cargo_pks.add(cargo.pk)
    session.report.cargos_inalterados += 1
