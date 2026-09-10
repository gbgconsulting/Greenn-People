"""Abertura idempotente da coorte automática do mês (lote).

Contrato: ``contracts/auto-cohort-open-contract.md`` (FR-001, FR-006, FR-009).
A task Beat (``run_auto_cycle_admission_daily``) decide noop de dia não-útil
e cria o ``AutoCycleRun``; este módulo materializa ciclo + matrículas.

Bootstrap (FR-005 / R5): defesa em profundidade — se chamado fora do 1º dia
útil, **não** abre o mês “atrasado” nem matricula; zero backfill de k passados
(candidatos só via ``next_future_marco`` / ``list_auto_marco_candidates``).
"""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.audit.services import log_entity_created
from apps.core.calendar_br import first_business_day_of_month
from apps.cycles.models import AutoCycleEvent, AutoCycleRun, Ciclo
from apps.cycles.services.marco import (
    is_auto_opening_day,
    list_auto_marco_candidates,
    user_blocked_by_open_cycle,
)
from apps.cycles.services.prazo import data_fim_from_inicio
from apps.reviews.models import Avaliacao
from apps.reviews.services.enrollment import ensure_avaliacao_for_user

if TYPE_CHECKING:
    from apps.accounts.models import CustomUser

_MESES_PT_ABREV = (
    'Jan',
    'Fev',
    'Mar',
    'Abr',
    'Mai',
    'Jun',
    'Jul',
    'Ago',
    'Set',
    'Out',
    'Nov',
    'Dez',
)


def _nome_coorte(year: int, month: int) -> str:
    return f'Avaliação automática — {_MESES_PT_ABREV[month - 1]}/{year}'


def _append_event(
    run: AutoCycleRun,
    *,
    tipo: str,
    usuario: CustomUser | None = None,
    ciclo: Ciclo | None = None,
    payload: dict | None = None,
) -> AutoCycleEvent:
    """Persiste event append-only com metadados mínimos de reconstrução (FR-016)."""
    body = dict(payload or {})
    # quem/quando/por quê: ator de sistema quando não há usuário de negócio.
    body.setdefault('ator', 'sistema_beat' if usuario is None else 'usuario')
    body.setdefault('run_id', run.pk)
    body.setdefault('data_referencia', run.data_referencia.isoformat())
    return AutoCycleEvent.objects.create(
        run=run,
        tipo=tipo,
        usuario=usuario,
        ciclo=ciclo,
        payload=body,
    )


def _audit_coorte_criada(ciclo: Ciclo) -> None:
    """Trilha técnica append-only na criação do ciclo automático (FR-016 / R12)."""
    log_entity_created(
        instance=ciclo,
        fields={
            'origem': ciclo.origem,
            'marco_competencia': ciclo.marco_competencia,
            'data_inicio': ciclo.data_inicio,
            'data_fim': ciclo.data_fim,
            'status': ciclo.status,
            'nome': ciclo.nome,
        },
    )


def _get_or_create_coorte(
    *,
    marco_competencia: date,
    data_inicio: date,
) -> tuple[Ciclo, bool]:
    """Retorna ``(ciclo, created)`` idempotente por marco automático."""
    defaults = {
        'nome': _nome_coorte(marco_competencia.year, marco_competencia.month),
        'data_inicio': data_inicio,
        # FR-006 / R4: 20 dias corridos; atraso sinalizável, sem auto-close.
        'data_fim': data_fim_from_inicio(data_inicio),
        'status': Ciclo.Status.ABERTO,
    }
    try:
        with transaction.atomic():
            return Ciclo.objects.get_or_create(
                origem=Ciclo.Origem.AUTOMATICO,
                marco_competencia=marco_competencia,
                defaults=defaults,
            )
    except IntegrityError:
        ciclo = Ciclo.objects.get(
            origem=Ciclo.Origem.AUTOMATICO,
            marco_competencia=marco_competencia,
        )
        return ciclo, False


def _partition_candidates(
    candidates: list[CustomUser],
) -> tuple[list[CustomUser], list[CustomUser]]:
    """Separa alertados (ciclo aberto) de matriculáveis (FR-008)."""
    alertados: list[CustomUser] = []
    matriculaveis: list[CustomUser] = []
    for user in candidates:
        if user_blocked_by_open_cycle(user):
            alertados.append(user)
        else:
            matriculaveis.append(user)
    return alertados, matriculaveis


def _open_cycles_blocking(user: CustomUser) -> list[Ciclo]:
    """Ciclos ``aberto`` em que o usuário já tem Avaliação (FR-008)."""
    return list(
        Ciclo.objects.filter(
            status=Ciclo.Status.ABERTO,
            avaliacoes__usuario_id=user.pk,
        )
        .distinct()
        .order_by('-data_inicio', '-pk'),
    )


def _register_alertas_ciclo_aberto(
    run: AutoCycleRun,
    alertados: list[CustomUser],
) -> int:
    """Persiste events ``alerta_ciclo_aberto``; não matricula; não aborta o lote.

    FR-008 / contrato passo 5: alerta é observabilidade — o lote segue com
    criação da coorte e matrícula dos demais independentemente destes events.
    E-mail aos ``is_admin`` ativos com dedupe diário (falha de envio não
    interrompe o lote).
    """
    from apps.notifications.tasks import enviar_alerta_ciclo_ainda_aberto

    count = 0
    for user in alertados:
        abertos = _open_cycles_blocking(user)
        primario = abertos[0] if abertos else None
        _append_event(
            run,
            tipo=AutoCycleEvent.Tipo.ALERTA_CICLO_ABERTO,
            usuario=user,
            ciclo=primario,
            payload={
                'motivo': 'ciclo_ainda_aberto',
                'ciclos_abertos_ids': [c.pk for c in abertos],
            },
        )
        try:
            enviar_alerta_ciclo_ainda_aberto(user.pk)
        except Exception:  # noqa: BLE001 — e-mail nunca aborta/adia o lote
            pass
        count += 1
    return count


def _register_pendencias_sem_admissao(run: AutoCycleRun) -> int:
    """Conta ativos sem ``data_entrada`` e registra events (sem matricular).

    FR-003 / contrato auto-cohort passo 8: fora do automático até o cadastro;
    snapshot em ``run.excluidos_sem_admissao`` + events ``pendencia_sem_admissao``.
    """
    User = get_user_model()
    qs = User.objects.filter(is_active=True, data_entrada__isnull=True).order_by(
        'pk',
    )
    count = 0
    for user in qs.iterator():
        _append_event(
            run,
            tipo=AutoCycleEvent.Tipo.PENDENCIA_SEM_ADMISSAO,
            usuario=user,
            payload={'motivo': 'data_entrada_ausente'},
        )
        count += 1
    return count


def _enroll_matriculaveis(
    run: AutoCycleRun,
    *,
    ciclo: Ciclo,
    matriculaveis: list[CustomUser],
    data_referencia: date,
) -> tuple[int, int]:
    """Matricula elegíveis; retorna ``(matriculados_novos, falhas)``."""
    matriculados = 0
    falhas = 0
    for user in matriculaveis:
        try:
            existed = Avaliacao.objects.filter(
                ciclo=ciclo,
                usuario=user,
            ).exists()
            avaliacao = ensure_avaliacao_for_user(
                user,
                ciclo=ciclo,
                ref_date=data_referencia,
            )
            if avaliacao is None:
                falhas += 1
                _append_event(
                    run,
                    tipo=AutoCycleEvent.Tipo.FALHA,
                    usuario=user,
                    ciclo=ciclo,
                    payload={'motivo': 'ensure_retornou_none'},
                )
                continue
            if not existed:
                matriculados += 1
                _append_event(
                    run,
                    tipo=AutoCycleEvent.Tipo.MATRICULA,
                    usuario=user,
                    ciclo=ciclo,
                    payload={
                        'motivo': 'elegivel_marco_admissao',
                        'avaliacao_id': avaliacao.pk,
                    },
                )
        except Exception as exc:  # noqa: BLE001 — falha parcial do lote
            falhas += 1
            _append_event(
                run,
                tipo=AutoCycleEvent.Tipo.FALHA,
                usuario=user,
                ciclo=ciclo,
                payload={
                    'motivo': 'excecao_matricula',
                    'erro': str(exc)[:500],
                },
            )
    return matriculados, falhas


def _refuse_late_month_open(
    run: AutoCycleRun,
    *,
    ref: date,
) -> None:
    """Go-live / chamada fora do 1º dia útil: noop sem materializar o mês."""
    primeiro = first_business_day_of_month(ref.year, ref.month)
    run.era_primeiro_dia_util = False
    run.marco_competencia = None
    run.ciclo = None
    run.matriculados = 0
    run.alertas_ciclo_aberto = 0
    run.excluidos_sem_admissao = 0
    run.status = AutoCycleRun.Status.NOOP
    run.mensagem = (
        f'{ref.isoformat()} não é o 1º dia útil do mês '
        f'({primeiro.isoformat()}); coorte não materializada '
        '(FR-005 / R5 — sem abertura atrasada).'
    )
    run.save(
        update_fields=[
            'era_primeiro_dia_util',
            'marco_competencia',
            'ciclo',
            'matriculados',
            'alertas_ciclo_aberto',
            'excluidos_sem_admissao',
            'status',
            'mensagem',
            'updated_at',
        ],
    )
    _append_event(
        run,
        tipo=AutoCycleEvent.Tipo.NOOP_DIA,
        payload={
            'data_referencia': ref.isoformat(),
            'primeiro_dia_util': primeiro.isoformat(),
            'motivo': 'abertura_atrasada_recusada',
        },
    )


def open_auto_cohort(
    run: AutoCycleRun,
    *,
    data_referencia: date | None = None,
) -> Ciclo | None:
    """Abre (ou reutiliza) a coorte automática do mês e matricula elegíveis.

    Pré-condição típica: caller já confirmou 1º dia útil e criou ``run``.
    Defesa R5: se ``data_referencia`` ≠ 1º dia útil → noop sem criar ciclo
    nem matrículas (go-live no meio do mês não abre aquele mês atrasado).
    Sem candidatos ao marco → não cria ciclo; fecha run em ``sucesso``.
    Falha ao criar ciclo → run ``falha`` (sem Avaliações órfãs).
    Falha ao matricular um user → event ``falha``; continua; run ``parcial``.
    """
    ref = data_referencia if data_referencia is not None else run.data_referencia
    if ref is None:
        ref = timezone.localdate()

    # FR-005 / R5: nunca materializa mês “atrasado” após o 1º dia útil.
    if not is_auto_opening_day(ref):
        _refuse_late_month_open(run, ref=ref)
        return None

    year, month = ref.year, ref.month
    marco_competencia = date(year, month, 1)

    run.marco_competencia = marco_competencia
    run.era_primeiro_dia_util = True
    run.save(
        update_fields=[
            'marco_competencia',
            'era_primeiro_dia_util',
            'updated_at',
        ],
    )

    # Pendências de cadastro (FR-003): contagem + events; nunca matricula.
    excluidos_sem_admissao = _register_pendencias_sem_admissao(run)

    candidates = list_auto_marco_candidates(
        year=year,
        month=month,
        ref_date=ref,
    )
    if not candidates:
        run.status = AutoCycleRun.Status.SUCESSO
        run.ciclo = None
        run.matriculados = 0
        run.alertas_ciclo_aberto = 0
        run.excluidos_sem_admissao = excluidos_sem_admissao
        run.mensagem = (
            f'Sem candidatos ao marco {year:04d}-{month:02d}; '
            'ciclo automático não criado. '
            f'{excluidos_sem_admissao} ativo(s) sem data de entrada.'
        )
        run.save(
            update_fields=[
                'status',
                'ciclo',
                'matriculados',
                'alertas_ciclo_aberto',
                'excluidos_sem_admissao',
                'mensagem',
                'updated_at',
            ],
        )
        return None

    alertados, matriculaveis = _partition_candidates(candidates)
    # FR-008: events antes da coorte; alerta nunca adia/aborta o lote.
    n_alertas = _register_alertas_ciclo_aberto(run, alertados)

    try:
        ciclo, created = _get_or_create_coorte(
            marco_competencia=marco_competencia,
            data_inicio=ref,
        )
    except Exception as exc:  # noqa: BLE001 — falha estrutural do lote
        run.status = AutoCycleRun.Status.FALHA
        run.ciclo = None
        run.matriculados = 0
        run.alertas_ciclo_aberto = n_alertas
        run.excluidos_sem_admissao = excluidos_sem_admissao
        run.mensagem = f'Falha ao criar/obter ciclo da coorte: {exc}'[:1000]
        run.save(
            update_fields=[
                'status',
                'ciclo',
                'matriculados',
                'alertas_ciclo_aberto',
                'excluidos_sem_admissao',
                'mensagem',
                'updated_at',
            ],
        )
        _append_event(
            run,
            tipo=AutoCycleEvent.Tipo.FALHA,
            payload={'motivo': 'falha_coorte', 'erro': str(exc)[:500]},
        )
        return None

    if created:
        _audit_coorte_criada(ciclo)
        _append_event(
            run,
            tipo=AutoCycleEvent.Tipo.COORTE_CRIADA,
            ciclo=ciclo,
            payload={
                'motivo': 'abertura_automatica_marco',
                'origem': Ciclo.Origem.AUTOMATICO,
                'marco_competencia': marco_competencia.isoformat(),
                'data_inicio': ciclo.data_inicio.isoformat(),
                'data_fim': ciclo.data_fim.isoformat(),
                'ciclo_id': ciclo.pk,
            },
        )
    else:
        _append_event(
            run,
            tipo=AutoCycleEvent.Tipo.COORTE_REUSADA,
            ciclo=ciclo,
            payload={
                'motivo': 'idempotencia_mesmo_marco',
                'origem': Ciclo.Origem.AUTOMATICO,
                'marco_competencia': marco_competencia.isoformat(),
                'ciclo_id': ciclo.pk,
            },
        )

    matriculados, falhas = _enroll_matriculaveis(
        run,
        ciclo=ciclo,
        matriculaveis=matriculaveis,
        data_referencia=ref,
    )

    status = (
        AutoCycleRun.Status.PARCIAL
        if falhas
        else AutoCycleRun.Status.SUCESSO
    )

    run.status = status
    run.ciclo = ciclo
    run.matriculados = matriculados
    run.alertas_ciclo_aberto = n_alertas
    run.excluidos_sem_admissao = excluidos_sem_admissao
    run.mensagem = (
        f'Coorte {"criada" if created else "reutilizada"}; '
        f'{matriculados} matriculado(s); '
        f'{n_alertas} alerta(s) ciclo aberto (sem matrícula); '
        f'{excluidos_sem_admissao} sem data de entrada; '
        f'{falhas} falha(s).'
    )
    run.save(
        update_fields=[
            'status',
            'ciclo',
            'matriculados',
            'alertas_ciclo_aberto',
            'excluidos_sem_admissao',
            'mensagem',
            'updated_at',
        ],
    )
    return ciclo
