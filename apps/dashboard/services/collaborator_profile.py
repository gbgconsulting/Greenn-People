"""Perfil / timeline do colaborador na Estrutura (visão por colaborador).

Caller resolve ``visible`` via ``get_visible_users``; este módulo **nunca**
chama escopo. Histórico estrutural vem de ``AuditLog`` (campos de usuário);
ciclos/notas de ``Avaliacao``. Avaliador só aparece quando a inferência via
auditoria (ou estado atual do ciclo aberto) é confiável.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time
from decimal import ROUND_HALF_UP, Decimal
from typing import Any, Literal

from django.db.models import Q, QuerySet
from django.utils import timezone

from apps.accounts.models import CustomUser
from apps.audit.models import AuditLog
from apps.cycles.models import Ciclo
from apps.cycles.services.eligibility import filter_coverage_universe
from apps.dashboard.chart_payloads import SEM_AVALIACAO_KEY
from apps.organization.models import Area, Cargo
from apps.reviews.models import Avaliacao
from apps.reviews.services.display import format_nota_percentual
from apps.reviews.services.team_avaliacao_list import user_initials

_USER_ENTITY = (
    f'{CustomUser._meta.app_label}.{CustomUser._meta.object_name}'
)
_STRUCTURAL_FIELDS = frozenset({'area_id', 'cargo_id', 'line_manager_id'})
_PERCENT_QUANT = Decimal('1')
_TIMELINE_PREVIEW = 2

CoverageStatus = Literal['sem_avaliacao', 'com_avaliacao']


@dataclass(frozen=True)
class FieldChange:
    campo: str
    at: datetime
    valor_anterior: str
    valor_novo: str


def _percent_int(value: Any) -> int | None:
    if value is None or value == '':
        return None
    try:
        return int(
            (Decimal(str(value)) * Decimal('100')).quantize(
                _PERCENT_QUANT,
                rounding=ROUND_HALF_UP,
            ),
        )
    except (TypeError, ValueError, ArithmeticError):
        return None


def _parse_optional_pk(raw: str) -> int | None:
    text = (raw or '').strip()
    if not text:
        return None
    try:
        return int(text)
    except (TypeError, ValueError):
        return None


def _ciclo_anchor(ciclo: Ciclo) -> datetime:
    """Âncora temporal do ciclo: fim do dia de ``data_fim`` (fuso local)."""
    local_tz = timezone.get_current_timezone()
    naive = datetime.combine(ciclo.data_fim, time.max.replace(microsecond=0))
    return timezone.make_aware(naive, local_tz)


def _load_structural_changes(user_id: int) -> list[FieldChange]:
    rows = (
        AuditLog.objects.filter(
            entity_type=_USER_ENTITY,
            entity_id=user_id,
            acao=AuditLog.Acao.UPDATE,
            campo__in=_STRUCTURAL_FIELDS,
        )
        .order_by('created_at', 'pk')
        .values_list('campo', 'created_at', 'valor_anterior', 'valor_novo')
    )
    return [
        FieldChange(
            campo=campo,
            at=created_at,
            valor_anterior=valor_anterior or '',
            valor_novo=valor_novo or '',
        )
        for campo, created_at, valor_anterior, valor_novo in rows
    ]


def _value_at(
    changes: list[FieldChange],
    *,
    campo: str,
    at: datetime,
    current: str,
) -> tuple[str, bool]:
    """Resolve valor serializado do campo em ``at``.

    Com trilha de auditoria → reconstrução confiável.
    Sem logs → ``reliable=False`` (caller pode promover ciclo aberto).
    """
    del current  # estado atual só via promoção explícita no caller
    field_logs = [c for c in changes if c.campo == campo]
    if not field_logs:
        return '', False

    applicable = [c for c in field_logs if c.at <= at]
    if not applicable:
        return field_logs[0].valor_anterior, True
    return applicable[-1].valor_novo, True


def _resolve_user_map(
    pks: set[int],
    *,
    allowed_pks: set[int] | None = None,
) -> dict[int, CustomUser]:
    """Resolve usuários por PK; se ``allowed_pks`` for dado, não sai do escopo."""
    if not pks:
        return {}
    query_pks = pks if allowed_pks is None else pks & allowed_pks
    if not query_pks:
        return {}
    return {
        u.pk: u
        for u in CustomUser.objects.filter(pk__in=query_pks).only(
            'id',
            'nome',
            'email',
        )
    }


def _resolve_area_map(pks: set[int]) -> dict[int, str]:
    if not pks:
        return {}
    return dict(Area.objects.filter(pk__in=pks).values_list('pk', 'nome'))


def _resolve_cargo_map(pks: set[int]) -> dict[int, tuple[str, int]]:
    if not pks:
        return {}
    return {
        c.pk: (c.nome, c.nivel)
        for c in Cargo.objects.filter(pk__in=pks).only('id', 'nome', 'nivel')
    }


def _display_user(user: CustomUser | None) -> str:
    if user is None:
        return '—'
    return (user.nome or user.email or '—').strip() or '—'


def _manager_label(pk: int | None, users: dict[int, CustomUser]) -> str:
    """Rótulo de gestor: nome in-scope, genérico fora do escopo, ou sem gestor."""
    if pk is None:
        return 'sem gestor'
    user = users.get(pk)
    if user is not None:
        return _display_user(user)
    return 'Gestor anterior'


def _label_structural_change(
    change: FieldChange,
    *,
    users: dict[int, CustomUser],
    areas: dict[int, str],
    cargos: dict[int, tuple[str, int]],
) -> dict[str, str] | None:
    old_id = _parse_optional_pk(change.valor_anterior)
    new_id = _parse_optional_pk(change.valor_novo)

    if change.campo == 'line_manager_id':
        new_name = _manager_label(new_id, users)
        old_name = _manager_label(old_id, users)
        if old_id is None and new_id is not None:
            text = f'Passou a reportar para {new_name}'
        elif new_id is None and old_id is not None:
            text = f'Deixou de reportar para {old_name}'
        else:
            text = f'Passou a reportar para {new_name}'
        return {'kind': 'line_manager', 'icon': 'person', 'text': text}

    if change.campo == 'area_id':
        old_name = areas.get(old_id, '—') if old_id else '—'
        new_name = areas.get(new_id, '—') if new_id else '—'
        return {
            'kind': 'area',
            'icon': 'swap_horiz',
            'text': f'Mudou de {old_name} para {new_name}',
        }

    if change.campo == 'cargo_id':
        old_cargo = cargos.get(old_id) if old_id else None
        new_cargo = cargos.get(new_id) if new_id else None
        old_name = old_cargo[0] if old_cargo else '—'
        new_name = new_cargo[0] if new_cargo else '—'
        promoted = (
            old_cargo is not None
            and new_cargo is not None
            and new_cargo[1] > old_cargo[1]
        )
        if promoted:
            return {
                'kind': 'promotion',
                'icon': 'trending_up',
                'text': f'Promovido: {old_name} → {new_name}',
            }
        return {
            'kind': 'cargo',
            'icon': 'badge',
            'text': f'Cargo: {old_name} → {new_name}',
        }

    return None


def _avaliacao_status_label(avaliacao: Avaliacao | None) -> tuple[str, str]:
    if avaliacao is None:
        return 'Sem avaliação', 'warning'
    if avaliacao.concluida or avaliacao.etapa == Avaliacao.Etapa.FEEDBACK:
        return 'Concluído', 'success'
    return avaliacao.get_etapa_display(), 'neutral'


def _delta_pp(current: Any, previous: Any) -> dict[str, Any] | None:
    cur = _percent_int(current)
    prev = _percent_int(previous)
    if cur is None or prev is None:
        return None
    delta = cur - prev
    if delta > 0:
        direction: Literal['up', 'down', 'flat'] = 'up'
    elif delta < 0:
        direction = 'down'
    else:
        direction = 'flat'
    return {
        'pp': delta,
        'label': f'{delta:+d}pp' if delta != 0 else '0pp',
        'direction': direction,
    }


def build_structure_collaborator_rows(
    visible: QuerySet[CustomUser],
    ciclo: Ciclo | None,
    *,
    area_id: int | None = None,
    cargo_id: int | None = None,
    busca: str = '',
    status: str = '',
    exclude_user_id: int | None = None,
) -> list[dict[str, Any]]:
    """Lista de colaboradores para a tab Estrutura (AuthZ já no ``visible``).

    Com ciclo: só o recorte de cobertura (elegíveis ∪ matriculados) — quem
    está fora do corte não aparece como ``sem_avaliacao``.
    """
    qs = visible.select_related('area', 'cargo', 'line_manager')
    if exclude_user_id is not None:
        qs = qs.exclude(pk=exclude_user_id)
    if area_id is not None:
        qs = qs.filter(area_id=area_id)
    if cargo_id is not None:
        qs = qs.filter(cargo_id=cargo_id)
    if ciclo is not None:
        qs = filter_coverage_universe(qs, ciclo)
    busca = (busca or '').strip()
    if busca:
        qs = qs.filter(Q(nome__icontains=busca) | Q(email__icontains=busca))
    users = list(qs.order_by('nome', 'email'))

    avaliacoes: dict[int, Avaliacao] = {}
    if ciclo is not None and users:
        avaliacoes = {
            a.usuario_id: a
            for a in Avaliacao.objects.filter(
                ciclo=ciclo,
                usuario_id__in=[u.pk for u in users],
            )
        }

    status_key = (status or '').strip()
    rows: list[dict[str, Any]] = []
    for user in users:
        av = avaliacoes.get(user.pk)
        has_av = av is not None
        if status_key == SEM_AVALIACAO_KEY and has_av:
            continue
        if status_key == 'com_avaliacao' and not has_av:
            continue
        label, tone = _avaliacao_status_label(av)
        coverage: CoverageStatus = (
            'com_avaliacao' if has_av else 'sem_avaliacao'
        )
        rows.append(
            {
                'usuario': user,
                'iniciais': user_initials(user),
                'avaliacao': av,
                'coverage': coverage,
                'status_label': label,
                'status_tone': tone,
                'nota_display': (
                    format_nota_percentual(av.nota_final_lider)
                    if av is not None and av.nota_final_lider is not None
                    else None
                ),
                'lider_nome': _display_user(user.line_manager),
                'area_nome': user.area.nome if user.area_id else '—',
                'cargo_nome': user.cargo.nome if user.cargo_id else '—',
            },
        )
    return rows


def build_collaborator_drawer(
    visible: QuerySet[CustomUser],
    user_id: int,
    ciclo: Ciclo | None,
) -> dict[str, Any] | None:
    """Monta contexto do drawer; ``None`` se o usuário não está em ``visible``."""
    colaborador = (
        visible.filter(pk=user_id)
        .select_related('area', 'cargo', 'line_manager')
        .first()
    )
    if colaborador is None:
        return None

    changes = _load_structural_changes(colaborador.pk)
    avaliacoes = list(
        Avaliacao.objects.filter(usuario_id=colaborador.pk)
        .select_related('ciclo')
        .order_by('-ciclo__data_inicio', '-ciclo__pk'),
    )
    avaliacao_atual = None
    if ciclo is not None:
        for av in avaliacoes:
            if av.ciclo_id == ciclo.pk:
                avaliacao_atual = av
                break

    user_pks: set[int] = set()
    area_pks: set[int] = set()
    cargo_pks: set[int] = set()
    if colaborador.line_manager_id:
        user_pks.add(colaborador.line_manager_id)
    if colaborador.area_id:
        area_pks.add(colaborador.area_id)
    if colaborador.cargo_id:
        cargo_pks.add(colaborador.cargo_id)
    for ch in changes:
        for raw in (ch.valor_anterior, ch.valor_novo):
            pk = _parse_optional_pk(raw)
            if pk is None:
                continue
            if ch.campo == 'line_manager_id':
                user_pks.add(pk)
            elif ch.campo == 'area_id':
                area_pks.add(pk)
            elif ch.campo == 'cargo_id':
                cargo_pks.add(pk)

    # AuthZ: PII de gestores só se estiverem no escopo visível (ou forem o LM atual
    # já exposto pelo FK do colaborador in-scope).
    allowed_user_pks = set(visible.values_list('pk', flat=True))
    if colaborador.line_manager_id:
        allowed_user_pks.add(colaborador.line_manager_id)
    users = _resolve_user_map(user_pks, allowed_pks=allowed_user_pks)
    areas = _resolve_area_map(area_pks)
    cargos = _resolve_cargo_map(cargo_pks)

    current_status_label, current_status_tone = _avaliacao_status_label(
        avaliacao_atual,
    )
    current_cycle_block = {
        'ciclo': ciclo,
        'avaliacao': avaliacao_atual,
        'status_label': current_status_label,
        'status_tone': current_status_tone,
        'detail_url_avaliacao_id': (
            avaliacao_atual.pk if avaliacao_atual is not None else None
        ),
    }

    historico_avs = [
        av
        for av in avaliacoes
        if ciclo is None or av.ciclo_id != ciclo.pk
    ]

    timeline: list[dict[str, Any]] = []
    for idx, av in enumerate(historico_avs):
        next_av = historico_avs[idx + 1] if idx + 1 < len(historico_avs) else None
        anchor = _ciclo_anchor(av.ciclo)
        manager_raw, manager_reliable = _value_at(
            changes,
            campo='line_manager_id',
            at=anchor,
            current=str(colaborador.line_manager_id or ''),
        )
        if not manager_reliable and av.ciclo.status == Ciclo.Status.ABERTO:
            manager_raw = str(colaborador.line_manager_id or '')
            manager_reliable = True

        avaliador_nome = None
        avaliador_reliable = False
        if manager_reliable:
            mid = _parse_optional_pk(manager_raw)
            if mid is not None:
                scoped = users.get(mid)
                avaliador_nome = (
                    _display_user(scoped)
                    if scoped is not None
                    else 'Gestor anterior'
                )
                avaliador_reliable = True

        status_label, status_tone = _avaliacao_status_label(av)
        delta = _delta_pp(
            av.nota_final_lider,
            next_av.nota_final_lider if next_av else None,
        )

        lower = _ciclo_anchor(next_av.ciclo) if next_av else None
        structural_group: list[dict[str, str]] = []
        for ch in changes:
            if ch.at > anchor:
                continue
            if lower is not None and ch.at <= lower:
                continue
            labeled = _label_structural_change(
                ch,
                users=users,
                areas=areas,
                cargos=cargos,
            )
            if labeled:
                structural_group.append(labeled)

        timeline.append(
            {
                'kind': 'cycle',
                'ciclo': av.ciclo,
                'avaliacao': av,
                'status_label': status_label,
                'status_tone': status_tone,
                'nota_display': (
                    format_nota_percentual(av.nota_final_lider)
                    if av.nota_final_lider is not None
                    else None
                ),
                'delta': delta,
                'avaliador_nome': avaliador_nome,
                'avaliador_reliable': avaliador_reliable,
                'structural_changes': structural_group,
            },
        )

    preview = timeline[:_TIMELINE_PREVIEW]
    older = timeline[_TIMELINE_PREVIEW:]

    return {
        'colaborador': colaborador,
        'iniciais': user_initials(colaborador),
        'current_cycle': current_cycle_block,
        'timeline_preview': preview,
        'timeline_older': older,
        'timeline_total_cycles': len(timeline),
        'has_more_history': bool(older),
    }
