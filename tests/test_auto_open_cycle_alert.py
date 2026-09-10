"""T021 [US3]: alerta não-bloqueante + prazo 20d + dedupe de e-mail.

Quickstart V4; SC-003 / SC-004; contrato auto-cohort-open (FR-006/FR-008).
"""

from __future__ import annotations

from datetime import date, timedelta
from unittest.mock import patch

import pytest
from django.utils import timezone

from apps.accounts.models import CustomUser
from apps.cycles.models import AutoCycleEvent, AutoCycleRun, Ciclo
from apps.cycles.services.prazo import data_fim_from_inicio
from apps.cycles.tasks import run_auto_cycle_admission_daily
from apps.notifications.emails import referencia_alerta_ciclo_ainda_aberto
from apps.notifications.models import NotificacaoLog
from apps.notifications.tasks import enviar_alerta_ciclo_ainda_aberto
from apps.reviews.models import Avaliacao
from tests.conftest import DEFAULT_PASSWORD

# jul/2026: 01/07 = quarta → 1º dia útil
REF_FIRST = date(2026, 7, 1)
MARCO_JUL = date(2026, 7, 1)


def _make_user(
    *,
    email: str,
    lider,
    area,
    cargo_colab,
    data_entrada: date | None,
) -> CustomUser:
    return CustomUser.objects.create_user(
        email=email,
        password=DEFAULT_PASSWORD,
        nome=email.split('@')[0],
        cargo=cargo_colab,
        area=area,
        line_manager=lider,
        data_entrada=data_entrada,
        is_active=True,
        email_confirmado_em=timezone.now(),
    )


def _isolate_fixtures_from_july_marco(lider) -> None:
    """Evita que admin/líder (data_entrada jan/2020) entrem no lote de jul."""
    CustomUser.objects.filter(pk=lider.pk).update(data_entrada=date(2026, 2, 1))
    lider.refresh_from_db()
    if lider.line_manager_id:
        CustomUser.objects.filter(pk=lider.line_manager_id).update(
            data_entrada=date(2026, 2, 1),
        )


def _seed_v4(lider, area, cargo_colab) -> dict:
    """1 alertado (ciclo A aberto) + ≥1 elegível livre no marco de julho."""
    _isolate_fixtures_from_july_marco(lider)

    alertado = _make_user(
        email='alertado-jul@test.greenn.com.br',
        lider=lider,
        area=area,
        cargo_colab=cargo_colab,
        data_entrada=date(2026, 1, 12),
    )
    livres = [
        _make_user(
            email=f'livre-jul-{i}@test.greenn.com.br',
            lider=lider,
            area=area,
            cargo_colab=cargo_colab,
            data_entrada=date(2026, 1, 14 + i),
        )
        for i in range(2)
    ]

    # Coorte A (manual) ainda aberta — bloqueia só o alertado (FR-008).
    ciclo_a = Ciclo.objects.create(
        nome='Ciclo A ainda aberto',
        data_inicio=date(2026, 6, 1),
        data_fim=date(2026, 6, 21),
        status=Ciclo.Status.ABERTO,
        origem=Ciclo.Origem.MANUAL,
        admitidos_ate=date(2026, 6, 1),
    )
    Avaliacao.objects.create(
        ciclo=ciclo_a,
        usuario=alertado,
        etapa=Avaliacao.Etapa.INPUT_METAS,
    )

    return {
        'alertado': alertado,
        'livres': livres,
        'ciclo_a': ciclo_a,
    }


def _logs_alerta(*, destinatario: CustomUser | None = None, referencia: str | None = None):
    qs = NotificacaoLog.objects.filter(
        tipo=NotificacaoLog.Tipo.ALERTA_CICLO_AINDA_ABERTO,
        status=NotificacaoLog.Status.ENVIADO,
    )
    if destinatario is not None:
        qs = qs.filter(destinatario=destinatario)
    if referencia is not None:
        qs = qs.filter(referencia=referencia)
    return qs


@pytest.mark.django_db
def test_alerta_nao_bloqueia_lote_prazo_20d_e_email_admin(
    admin,
    lider,
    area,
    cargo_colab,
):
    """V4 / SC-003 / SC-004: alerta + coorte B + demais matriculados; prazo +20d."""
    seed = _seed_v4(lider, area, cargo_colab)

    with patch(
        'apps.notifications.tasks.send_alerta_ciclo_ainda_aberto_email',
    ) as send_mock:
        result = run_auto_cycle_admission_daily(data_referencia=REF_FIRST)

    assert result['status'] == AutoCycleRun.Status.SUCESSO
    assert result['era_primeiro_dia_util'] is True

    # Coorte B criada; lote não adiado pelo alerta.
    assert (
        Ciclo.objects.filter(
            origem=Ciclo.Origem.AUTOMATICO,
            marco_competencia=MARCO_JUL,
        ).count()
        == 1
    )
    ciclo_b = Ciclo.objects.get(
        origem=Ciclo.Origem.AUTOMATICO,
        marco_competencia=MARCO_JUL,
    )
    assert ciclo_b.status == Ciclo.Status.ABERTO
    assert ciclo_b.data_inicio == REF_FIRST
    assert ciclo_b.data_fim == data_fim_from_inicio(REF_FIRST)
    assert ciclo_b.data_fim == REF_FIRST + timedelta(days=20)

    # Alertado sem nova Avaliação; livres matriculados.
    assert not Avaliacao.objects.filter(
        ciclo=ciclo_b,
        usuario=seed['alertado'],
    ).exists()
    for user in seed['livres']:
        assert Avaliacao.objects.filter(ciclo=ciclo_b, usuario=user).exists()
    assert Avaliacao.objects.filter(ciclo=ciclo_b).count() == 2

    # Ciclo A permanece aberto (sem auto-close).
    seed['ciclo_a'].refresh_from_db()
    assert seed['ciclo_a'].status == Ciclo.Status.ABERTO
    assert Ciclo.objects.filter(status=Ciclo.Status.ABERTO).count() == 2

    run = AutoCycleRun.objects.get(pk=result['run_id'])
    assert run.alertas_ciclo_aberto == 1
    assert run.matriculados == 2
    assert run.events.filter(
        tipo=AutoCycleEvent.Tipo.ALERTA_CICLO_ABERTO,
        usuario=seed['alertado'],
    ).count() == 1
    assert run.events.filter(tipo=AutoCycleEvent.Tipo.COORTE_CRIADA).exists()
    assert run.events.filter(tipo=AutoCycleEvent.Tipo.MATRICULA).count() == 2

    # E-mail RH: 1 envio por admin ativo.
    assert send_mock.call_count == 1
    assert send_mock.call_args.kwargs['usuario_alertado'].pk == seed['alertado'].pk
    assert send_mock.call_args.args[0].pk == admin.pk
    referencia = referencia_alerta_ciclo_ainda_aberto(seed['alertado'])
    assert _logs_alerta(destinatario=admin, referencia=referencia).count() == 1


@pytest.mark.django_db
def test_dedupe_email_alerta_mesmo_dia(admin, lider, area, cargo_colab):
    """Reexecução no mesmo dia → 0 reenvios (NotificacaoLog + already_sent)."""
    seed = _seed_v4(lider, area, cargo_colab)
    referencia = referencia_alerta_ciclo_ainda_aberto(seed['alertado'])
    janela = timezone.localdate().isoformat()

    with patch(
        'apps.notifications.tasks.send_alerta_ciclo_ainda_aberto_email',
    ) as send_mock:
        first = enviar_alerta_ciclo_ainda_aberto(seed['alertado'].pk)
        second = enviar_alerta_ciclo_ainda_aberto(seed['alertado'].pk)

    assert first['resultado'] == 'ok'
    assert first['enviados'] == 1
    assert first['pulados'] == 0
    assert first['janela'] == janela

    assert second['enviados'] == 0
    assert second['pulados'] == 1
    assert send_mock.call_count == 1
    assert _logs_alerta(destinatario=admin, referencia=referencia).count() == 1


@pytest.mark.django_db
def test_reexecucao_lote_mesmo_dia_nao_reenvia_email_alerta(
    admin,
    lider,
    area,
    cargo_colab,
):
    """2ª run do lote no mesmo dia: events podem repetir; e-mail dedupe."""
    seed = _seed_v4(lider, area, cargo_colab)

    with patch(
        'apps.notifications.tasks.send_alerta_ciclo_ainda_aberto_email',
    ) as send_mock:
        first = run_auto_cycle_admission_daily(data_referencia=REF_FIRST)
        second = run_auto_cycle_admission_daily(data_referencia=REF_FIRST)

    assert first['status'] == AutoCycleRun.Status.SUCESSO
    assert second['status'] == AutoCycleRun.Status.SUCESSO
    # 1ª run: 1 alerta → 1 e-mail; 2ª: alertados incluem coorte B, mas
    # referência do alertado original já foi enviada na janela do dia.
    assert send_mock.call_count >= 1
    referencia = referencia_alerta_ciclo_ainda_aberto(seed['alertado'])
    assert _logs_alerta(destinatario=admin, referencia=referencia).count() == 1

    # Sem segundo ciclo automático / sem Avaliação duplicada nos livres.
    assert (
        Ciclo.objects.filter(
            origem=Ciclo.Origem.AUTOMATICO,
            marco_competencia=MARCO_JUL,
        ).count()
        == 1
    )
    ciclo_b = Ciclo.objects.get(
        origem=Ciclo.Origem.AUTOMATICO,
        marco_competencia=MARCO_JUL,
    )
    for user in seed['livres']:
        assert Avaliacao.objects.filter(ciclo=ciclo_b, usuario=user).count() == 1
    assert not Avaliacao.objects.filter(
        ciclo=ciclo_b,
        usuario=seed['alertado'],
    ).exists()
