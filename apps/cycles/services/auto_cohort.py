"""Abertura idempotente da coorte automática do mês (lote).

Contrato: ``contracts/auto-cohort-open-contract.md`` (FR-001, FR-006, FR-009).
A task Beat (``run_auto_cycle_admission_daily``) decide noop de dia não-útil
e cria o ``AutoCycleRun``; este módulo materializa ciclo + matrículas.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import TYPE_CHECKING

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.audit.models import AuditLog
from apps.audit.services import entity_type_for, write_audit_log
from apps.cycles.models import AutoCycleEvent, AutoCycleRun, Ciclo
from apps.cycles.services.marco import (
    list_auto_marco_candidates,
    user_blocked_by_open_cycle,
)
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

_PRAZO_DIAS_CORRIDOS = 20


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
    return AutoCycleEvent.objects.create(
        run=run,
        tipo=tipo,
        usuario=usuario,
        ciclo=ciclo,
        payload=payload or {},
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
        'data_fim': data_inicio + timedelta(days=_PRAZO_DIAS_CORRIDOS),
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
                    payload={'avaliacao_id': avaliacao.pk},
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


def open_auto_cohort(
    run: AutoCycleRun,
    *,
    data_referencia: date | None = None,
) -> Ciclo | None:
    """Abre (ou reutiliza) a coorte automática do mês e matricula elegíveis.

    Pré-condição típica: caller já confirmou 1º dia útil e criou ``run``.
    Sem candidatos ao marco → não cria ciclo; fecha run em ``sucesso``.
    Falha ao criar ciclo → run ``falha`` (sem Avaliações órfãs).
    Falha ao matricular um user → event ``falha``; continua; run ``parcial``.
    """
    ref = data_referencia if data_referencia is not None else run.data_referencia
    if ref is None:
        ref = timezone.localdate()

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

    _alertados, matriculaveis = _partition_candidates(candidates)
    # Alertas/e-mail (T018) ficam fora desta fatia.

    try:
        ciclo, created = _get_or_create_coorte(
            marco_competencia=marco_competencia,
            data_inicio=ref,
        )
    except Exception as exc:  # noqa: BLE001 — falha estrutural do lote
        run.status = AutoCycleRun.Status.FALHA
        run.ciclo = None
        run.matriculados = 0
        run.excluidos_sem_admissao = excluidos_sem_admissao
        run.mensagem = f'Falha ao criar/obter ciclo da coorte: {exc}'[:1000]
        run.save(
            update_fields=[
                'status',
                'ciclo',
                'matriculados',
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
        write_audit_log(
            acao=AuditLog.Acao.CREATE,
            entity_type=entity_type_for(ciclo),
            entity_id=ciclo.pk,
            campo='status',
            valor_anterior='',
            valor_novo=ciclo.status,
        )
        _append_event(
            run,
            tipo=AutoCycleEvent.Tipo.COORTE_CRIADA,
            ciclo=ciclo,
            payload={
                'marco_competencia': marco_competencia.isoformat(),
                'data_inicio': ciclo.data_inicio.isoformat(),
                'data_fim': ciclo.data_fim.isoformat(),
            },
        )
    else:
        _append_event(
            run,
            tipo=AutoCycleEvent.Tipo.COORTE_REUSADA,
            ciclo=ciclo,
            payload={'marco_competencia': marco_competencia.isoformat()},
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
    run.alertas_ciclo_aberto = len(_alertados)
    run.excluidos_sem_admissao = excluidos_sem_admissao
    run.mensagem = (
        f'Coorte {"criada" if created else "reutilizada"}; '
        f'{matriculados} matriculado(s); '
        f'{len(_alertados)} com ciclo aberto (sem matrícula nesta fatia); '
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
