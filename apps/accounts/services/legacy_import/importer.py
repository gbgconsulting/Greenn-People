"""Orquestração da importação de colaboradores legado Sólides.

Superfície pública: ``import_colaboradores`` (reexportada por ``__init__``).
Fase A (T018): parse → crosswalk → Area → Cargo → CustomUser upsert.
Fase B (T022): hierarquia ``line_manager`` após persistir todos os usuários.
Fase C (R11): demissões diferidas — ``is_active=False`` só depois da
hierarquia; se ``clean()`` bloquear por liderados ativos, conflito
``desativacao_bloqueada_liderados`` e mantém ativo (sem abortar).
T025: ``dry_run`` — parse + totais projetados com ``set_rollback``
(zero commit); falhas fatais pré-persistência via ``LegacyParseError``.
T026: idempotência por e-mail normalizado (R12 / FR-013) —
``criados`` / ``atualizados`` / ``inalterados``; colisão no backup
não sobrescreve a primeira linha; ``solides_id`` complementar.
T027: exit codes 0/1 + rollback em exceção de persistência
(``transaction.atomic``) e pré-checagem de schema ``solides_id``.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from django.apps import apps
from django.core.exceptions import ValidationError
from django.db import connection, transaction
from django.db.utils import DatabaseError
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
    validate_source_paths,
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


@dataclass(frozen=True)
class _PendingDismissal:
    """Demissão a aplicar na fase C (após hierarquia / R11)."""

    email: str
    nome: str
    area: str
    cargo: str

# Models US1 com ``solides_id`` aditivo — checagem pré-persistência (T027).
_SOLIDES_ID_MODELS: tuple[tuple[str, str], ...] = (
    ("accounts", "CustomUser"),
    ("organization", "Cargo"),
    ("competencies", "Competencia"),
    ("reviews", "Avaliacao"),
    ("pdi", "PDI"),
)


class LegacySchemaError(Exception):
    """Migrations 6.5.1 (``solides_id``) ausentes — exit 1, zero writes.

    Pré-condição do contrato (``import-command-contract.md`` §Pré-condições
    e §Códigos de saída): falha de migration pré-requisito não entra no
    ``atomic`` e não deixa escrita parcial.
    """


class LegacyPersistError(Exception):
    """Erro fatal durante persistência — ``atomic`` faz rollback; exit 1.

    Conflitos não-fatais (sem e-mail, crosswalk ambíguo, gestor não
    resolvido) NÃO usam esta classe: vão para o relatório e exit ``0``.
    """


def import_colaboradores(
    colaboradores_path: str | Path,
    *,
    avaliacoes_path: str | Path | None = None,
    dry_run: bool = False,
) -> ImportReport:
    """Orquestra parse → crosswalk → fase A → fase B (ou dry-run).

    Assinatura alinhada a ``contracts/import-command-contract.md``.

    1. **Parse+validate** (sem DB / T025 / R13): valida paths, lê OOXML
       e colunas obrigatórias; monta estruturas em memória. ``LegacyParseError``
       propaga (exit 1 no command; **zero writes** — fase pré-persistência).
    2. **Schema** (T027): ``solides_id`` presente nas cinco tabelas US1.
       Ausência → ``LegacySchemaError`` (exit 1, zero writes).
    3. **Persist** em ``transaction.atomic()``:
       Area → Cargo → CustomUser (``full_clean`` + ``save`` / ``create_user``
       + ``set_unusable_password``); 2ª passada ``line_manager`` via
       ``apply_hierarchy`` (R5 / FR-009); 3ª passada demissões diferidas
       (R11) — nunca ``is_active=False`` antes da hierarquia.
       ``email_confirmado_em=timezone.now()``; sem PII extra; denylist
       intacta. Exceção → ``LegacyPersistError``, rollback do ``atomic``,
       exit 1 no command.
    4. **``dry_run`` (T025)**: executa a mesma lógica de persistência para
       projetar totais no relatório (``modo=dry-run``), mas marca a
       transação com ``set_rollback(True)`` em ``finally`` — **zero commit**.
       Sucesso de dry-run → exit ``0`` no command (conflitos não-fatais
       não abortam).
    5. **Idempotência (T026 / R12)**: chave natural = e-mail normalizado
       (lookup ``email__iexact``); reexecução atualiza só campos
       divergentes e reporta ``criados``/``atualizados``/``inalterados``.
       Duas linhas no backup com o mesmo e-mail → conflito; a posterior
       não sobrescreve. ``solides_id`` complementar (FR-013) evita
       duplicar a mesma pessoa quando o e-mail da fonte mudou.
    """
    # Fase 1 (T025): parse+validate fora do atomic — falha → zero writes.
    colaboradores_file, avaliacoes_file = validate_source_paths(
        colaboradores_path,
        avaliacoes_path,
    )
    parsed = parse_colaboradores_xlsx(colaboradores_file)
    report = ImportReport(
        modo="dry-run" if dry_run else "persist",
        colaboradores_file=parsed.path,
        avaliacoes_file=str(avaliacoes_file) if avaliacoes_file else "",
    )

    crosswalk = CrosswalkIndex()
    if avaliacoes_file is not None:
        aval = parse_avaliacoes_crosswalk_xlsx(avaliacoes_file)
        report.avaliacoes_file = aval.path
        crosswalk = build_crosswalk(aval.rows, report)

    # T027: schema US1 antes do atomic — falha de migration → exit 1, zero writes.
    _assert_solides_id_schema()

    with transaction.atomic():
        try:
            pending = _persist_phase_a(parsed.rows, crosswalk, report)
            apply_hierarchy(parsed.rows, report)
            _apply_dismissals(pending, report)
        except LegacyPersistError:
            raise
        except Exception as exc:
            # T027 / FR-012: qualquer falha de persistência aborta a transação
            # (rollback no __exit__ do atomic) e sinaliza exit 1 no command.
            raise LegacyPersistError(str(exc)) from exc
        finally:
            # T025: dry-run sempre descarta writes, inclusive se exceção
            # durante persistência — evita commit parcial.
            if dry_run:
                transaction.set_rollback(True)

    return report


def _assert_solides_id_schema() -> None:
    """Garante coluna ``solides_id`` nas cinco entidades US1 (T027).

    Introspecção do DB (não só o model) — migrations pendentes falham
    aqui, não no meio do ``atomic``.
    """
    missing: list[str] = []
    for app_label, model_name in _SOLIDES_ID_MODELS:
        model = apps.get_model(app_label, model_name)
        table = model._meta.db_table
        try:
            with connection.cursor() as cursor:
                description = connection.introspection.get_table_description(
                    cursor, table
                )
        except DatabaseError as exc:
            raise LegacySchemaError(
                "Não foi possível verificar o schema de solides_id em "
                f"{table}: {exc}. Execute `python manage.py migrate`."
            ) from exc
        columns = {col.name for col in description}
        if "solides_id" not in columns:
            missing.append(f"{table}.solides_id")

    if missing:
        raise LegacySchemaError(
            "Migrations 6.5.1 (solides_id) não aplicadas: "
            + ", ".join(missing)
            + ". Execute `python manage.py migrate` antes de importar."
        )


def _persist_phase_a(
    rows: tuple[ColaboradorRow, ...],
    crosswalk: CrosswalkIndex,
    report: ImportReport,
) -> list[_PendingDismissal]:
    """Fase A: Area → Cargo → CustomUser upsert por e-mail (R5 / R12 / T026).

    Demissões (``is_active=False``) são **adiadas** para a fase C (R11):
    gestores demitidos precisam permanecer ativos enquanto a hierarquia
    grava ``line_manager`` neles; caso contrário ``CustomUser.save`` /
    ``full_clean`` aborta com liderados ativos.
    """
    session = ResolveSession(report=report)
    # chave casefold → primeira linha que reivindicou o e-mail no backup.
    claimed_emails: dict[str, int] = {}
    pending: list[_PendingDismissal] = []

    for row in rows:
        email = resolve_email(row)
        if not email:
            record_nao_importavel(
                report,
                linha=row.linha,
                motivo="sem_email",
            )
            continue

        claim = _email_claim_key(email)
        first_linha = claimed_emails.get(claim)
        if first_linha is not None:
            # R12: colisão no backup — linha posterior NÃO sobrescreve
            # (nem resolve Area/Cargo, nem muta o usuário da 1ª linha).
            record_conflito(
                report,
                tipo="email_duplicado_backup",
                extra=f"email={email}",
                motivo=f"linhas={first_linha},{row.linha}",
            )
            continue
        claimed_emails[claim] = row.linha

        resolved = resolve_row(row, session)
        _upsert_user(resolved, crosswalk, report, pending)

    return pending


def _email_claim_key(email: str) -> str:
    """Chave de colisão no backup: e-mail normalizado case-insensitive (R12)."""
    return email.casefold()


def _emails_match(left: str, right: str) -> bool:
    """True se os endereços são a mesma chave natural (case-insensitive)."""
    return left.casefold() == right.casefold()


def _lookup_user_by_email(email: str) -> CustomUser | None:
    """Lookup pela chave natural e-mail (R12) — ``iexact`` após normalize."""
    return CustomUser.objects.filter(email__iexact=email).first()


def _upsert_user(
    resolved: ResolvedRow,
    crosswalk: CrosswalkIndex,
    report: ImportReport,
    pending: list[_PendingDismissal],
) -> CustomUser:
    """Cria ou atualiza ``CustomUser`` pela chave natural e-mail (R12 / T026).

    - Lookup: ``email__iexact``; se ausente, ``solides_id`` complementar
      (FR-013 — reexecução não duplica a mesma pessoa).
    - Create: ``create_user`` + ``set_unusable_password``; confirma e-mail;
      demissão diferida (sempre cria ativo se a fonte indicar demissão).
    - Update: campos divergentes via ``full_clean`` + ``save``; noop →
      ``usuarios_inalterados`` sem ``save``; demissão diferida (R11).
    - ``solides_id`` via crosswalk (ambíguo/ausente → null; colisão unique
      reportada sem corromper o dono existente).
    """
    assert resolved.email is not None
    email = resolved.email
    candidate_sid = crosswalk.lookup(resolved.nome)

    existing = _lookup_user_by_email(email)
    if existing is None and candidate_sid:
        existing = CustomUser.objects.filter(solides_id=candidate_sid).first()

    solides_id = _resolve_solides_id(
        candidate=candidate_sid,
        email=email,
        existing=existing,
        report=report,
    )
    area_nome = resolved.area.nome if resolved.area is not None else ""
    cargo_nome = resolved.cargo.nome if resolved.cargo is not None else ""

    if existing is None:
        return _create_user(
            resolved,
            solides_id=solides_id,
            area_nome=area_nome,
            cargo_nome=cargo_nome,
            report=report,
            pending=pending,
        )

    return _update_user(
        existing,
        resolved,
        solides_id=solides_id,
        area_nome=area_nome,
        cargo_nome=cargo_nome,
        report=report,
        pending=pending,
    )


def _resolve_solides_id(
    *,
    candidate: str | None,
    email: str,
    existing: CustomUser | None,
    report: ImportReport,
) -> str | None:
    """Guarda unicidade de ``solides_id`` sem roubar o dono existente.

    Se ``existing`` já é a pessoa (e-mail ou o próprio ``solides_id``),
    o candidato é atribuível. Outro usuário com o mesmo ID → conflito.
    """
    if not candidate:
        return None

    qs = CustomUser.objects.filter(solides_id=candidate)
    if existing is not None:
        qs = qs.exclude(pk=existing.pk)
    else:
        qs = qs.exclude(email__iexact=email)
    other = qs.first()
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
    pending: list[_PendingDismissal],
) -> CustomUser:
    """Cria usuário com senha inutilizável e e-mail confirmado (R6 / R7).

    Sempre cria ``is_active=True``; demissão vai para a fase C (R11).
    """
    assert resolved.email is not None
    user = CustomUser.objects.create_user(
        email=resolved.email,
        password=None,
        nome=resolved.nome,
        area=resolved.area,
        cargo=resolved.cargo,
        is_active=True,
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
        pending.append(
            _PendingDismissal(
                email=resolved.email,
                nome=resolved.nome,
                area=area_nome,
                cargo=cargo_nome,
            )
        )
    return user


def _update_user(
    user: CustomUser,
    resolved: ResolvedRow,
    *,
    solides_id: str | None,
    area_nome: str,
    cargo_nome: str,
    report: ImportReport,
    pending: list[_PendingDismissal],
) -> CustomUser:
    """Atualiza campos divergentes; conta inalterado se noop (R12 / T026).

    Campos considerados (R12): ``nome``, ``cargo``, ``area``, ``is_active``
    (só reativação imediata; demissão diferida R11), ``solides_id``,
    ``email`` (só se a identidade veio por ``solides_id``) e
    ``email_confirmado_em`` quando ainda é null. Reexecução idêntica
    NÃO chama ``save`` nem bumpa o timestamp (SC-007).
    Crosswalk ausente/ambíguo não apaga ``solides_id`` existente.
    """
    assert resolved.email is not None

    desired_solides = solides_id if solides_id is not None else user.solides_id
    # Grafia de e-mail equivalente (só caixa) não é divergência.
    desired_email = (
        resolved.email
        if not _emails_match(user.email, resolved.email)
        else user.email
    )
    desired_area_id = resolved.area.pk if resolved.area else None
    desired_cargo_id = resolved.cargo.pk if resolved.cargo else None
    needs_email_confirm = user.email_confirmado_em is None

    # R11: demissão diferida — na fase A só aplica reativação imediata.
    # Se a fonte pede inativo, mantém ``is_active`` atual até a fase C.
    defer_dismissal = not resolved.is_active
    phase_a_is_active = True if resolved.is_active else user.is_active

    business_changed = (
        user.nome != resolved.nome
        or user.area_id != desired_area_id
        or user.cargo_id != desired_cargo_id
        or user.is_active != phase_a_is_active
        or user.solides_id != desired_solides
        or user.email != desired_email
        or needs_email_confirm
    )

    if defer_dismissal:
        pending.append(
            _PendingDismissal(
                email=resolved.email,
                nome=resolved.nome,
                area=area_nome,
                cargo=cargo_nome,
            )
        )

    if not business_changed:
        # Demissão pendente de quem ainda está ativo: fase C conta atualizado.
        if defer_dismissal and user.is_active:
            return user
        report.usuarios_inalterados += 1
        return user

    previous_solides = user.solides_id

    user.nome = resolved.nome
    user.email = desired_email
    user.area = resolved.area
    user.cargo = resolved.cargo
    user.is_active = phase_a_is_active
    user.solides_id = desired_solides
    user.email_confirmado_em = timezone.now()

    user.full_clean()
    user.save()

    record_atualizado(
        report,
        nome=resolved.nome,
        email=resolved.email,
        area=area_nome,
        cargo=cargo_nome,
    )
    if desired_solides and previous_solides != desired_solides:
        note_solides_id_preenchido(report)
    return user


def _apply_dismissals(
    pending: list[_PendingDismissal],
    report: ImportReport,
) -> None:
    """Fase C (R11): aplica ``is_active=False`` após a hierarquia.

    Se ``clean()``/``save()`` bloquear por liderados ativos → conflito
    ``desativacao_bloqueada_liderados``, mantém ativo, **não** aborta a
    carga (edge case do dump real: gestor demitido com Superior direto id
    e liderados ativos já vinculados na fase B).
    """
    seen: set[str] = set()
    for item in pending:
        key = _email_claim_key(item.email)
        if key in seen:
            continue
        seen.add(key)

        user = _lookup_user_by_email(item.email)
        if user is None or not user.is_active:
            continue

        user.is_active = False
        try:
            user.full_clean()
            user.save()
        except ValidationError as exc:
            if _is_deactivation_blocked(exc):
                user.is_active = True
                record_conflito(
                    report,
                    tipo="desativacao_bloqueada_liderados",
                    extra=f"email={item.email}",
                    motivo="liderados_ativos",
                )
                continue
            raise

        note_demitido_inativo(report)
        # Só demissão (sem outras mudanças na fase A): conta como atualizado.
        already_counted = any(
            _emails_match(e.extra, item.email) for e in report.atualizados
        ) or any(_emails_match(e.extra, item.email) for e in report.criados)
        if not already_counted:
            record_atualizado(
                report,
                nome=item.nome,
                email=item.email,
                area=item.area,
                cargo=item.cargo,
            )


def _is_deactivation_blocked(exc: ValidationError) -> bool:
    """True se ``ValidationError`` bloqueou ``is_active`` (liderados ativos)."""
    error_dict = getattr(exc, "error_dict", None) or {}
    return "is_active" in error_dict
