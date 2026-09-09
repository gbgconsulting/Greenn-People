"""Contrato alerta atraso PDI (US2 / T016).

Cobre [contracts/pdi-overdue-notifications.md] §fluxo atraso pontual:
dono+gestor, só dono, dedupe diário, arquivado=0, lembrete_pdi independente.
"""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import patch

import pytest
from django.conf import settings
from django.utils import timezone

from apps.accounts.models import CustomUser
from apps.notifications.models import NotificacaoLog
from apps.notifications.tasks import (
    enviar_alerta_acao_pdi_atrasada,
    enviar_lembrete_acao_pdi_vencendo,
)
from apps.pdi.models import AcaoPDI, PDI
from apps.pdi.tasks import mark_overdue_pdi_actions
from tests.conftest import DEFAULT_PASSWORD, FIXTURE_DATA_ENTRADA


def _prazo_atrasado(*, dias: int = 3):
    return timezone.localdate() - timedelta(days=dias)


def _criar_pdi_com_acao(
    dono: CustomUser,
    *,
    status_acao: str = AcaoPDI.Status.ATRASADA,
    status_pdi: str = PDI.Status.ATIVO,
    prazo=None,
    descricao: str = 'Ação atrasada teste',
) -> tuple[PDI, AcaoPDI]:
    pdi = PDI.objects.create(
        usuario=dono,
        titulo='PDI alerta atraso',
        status=status_pdi,
    )
    acao = AcaoPDI.objects.create(
        pdi=pdi,
        descricao=descricao,
        responsavel=dono,
        prazo=prazo if prazo is not None else _prazo_atrasado(),
        status=status_acao,
    )
    return pdi, acao


def _logs_atraso(*, referencia: str | None = None):
    qs = NotificacaoLog.objects.filter(
        tipo=NotificacaoLog.Tipo.ATRASO_PDI,
        status=NotificacaoLog.Status.ENVIADO,
    )
    if referencia is not None:
        qs = qs.filter(referencia=referencia)
    return qs


@pytest.mark.django_db
def test_alerta_atraso_envia_dono_e_gestor(colaborador, lider):
    """Contrato #1: marcação atrasada → 1 e-mail dono + 1 gestor."""
    assert colaborador.line_manager_id == lider.pk
    _pdi, acao = _criar_pdi_com_acao(colaborador)
    referencia = f'acao_pdi:{acao.pk}'

    with patch(
        'apps.notifications.tasks.send_atraso_pdi_email',
    ) as send_mock:
        result = enviar_alerta_acao_pdi_atrasada(acao.pk)

    assert result['enviados'] == 2
    assert result['falhas'] == 0
    assert send_mock.call_count == 2
    dest_ids = {call.args[1].pk for call in send_mock.call_args_list}
    assert dest_ids == {colaborador.pk, lider.pk}
    assert _logs_atraso(referencia=referencia).count() == 2
    assert _logs_atraso(referencia=referencia).filter(
        destinatario=colaborador,
    ).exists()
    assert _logs_atraso(referencia=referencia).filter(
        destinatario=lider,
    ).exists()


@pytest.mark.django_db
def test_alerta_atraso_segunda_run_mesmo_dia_dedupe(colaborador, lider):
    """Contrato #1: 2ª run no mesmo dia → 0 reenvios."""
    _pdi, acao = _criar_pdi_com_acao(colaborador)

    with patch('apps.notifications.tasks.send_atraso_pdi_email') as send_mock:
        first = enviar_alerta_acao_pdi_atrasada(acao.pk)
        second = enviar_alerta_acao_pdi_atrasada(acao.pk)

    assert first['enviados'] == 2
    assert second['enviados'] == 0
    assert second['pulados'] == 2
    assert send_mock.call_count == 2
    assert (
        _logs_atraso(referencia=f'acao_pdi:{acao.pk}').count() == 2
    )


@pytest.mark.django_db
def test_alerta_atraso_sem_gestor_so_dono(db, area, cargo_colab):
    """Contrato #2: sem gestor → só dono; sem falha."""
    dono = CustomUser.objects.create_user(
        email='dono-sem-gestor@test.greenn.com.br',
        password=DEFAULT_PASSWORD,
        nome='Dono Sem Gestor',
        area=area,
        cargo=cargo_colab,
        line_manager=None,
        data_entrada=FIXTURE_DATA_ENTRADA,
        email_confirmado_em=timezone.now(),
    )
    _pdi, acao = _criar_pdi_com_acao(dono)

    with patch(
        'apps.notifications.tasks.send_atraso_pdi_email',
    ) as send_mock:
        result = enviar_alerta_acao_pdi_atrasada(acao.pk)

    assert result['enviados'] == 1
    assert result['falhas'] == 0
    assert send_mock.call_count == 1
    assert send_mock.call_args.args[1].pk == dono.pk
    assert _logs_atraso(referencia=f'acao_pdi:{acao.pk}').count() == 1
    assert (
        _logs_atraso(referencia=f'acao_pdi:{acao.pk}')
        .filter(destinatario=dono)
        .exists()
    )


@pytest.mark.django_db
def test_alerta_atraso_pdi_arquivado_zero_emails(colaborador):
    """Contrato #3: PDI arquivado → 0 e-mails atraso."""
    _pdi, acao = _criar_pdi_com_acao(
        colaborador,
        status_pdi=PDI.Status.ARQUIVADO,
        status_acao=AcaoPDI.Status.ATRASADA,
    )

    with patch(
        'apps.notifications.tasks.send_atraso_pdi_email',
    ) as send_mock:
        result = enviar_alerta_acao_pdi_atrasada(acao.pk)

    assert result['enviados'] == 0
    assert result['resultado'] == 'ineligivel'
    assert send_mock.call_count == 0
    assert NotificacaoLog.objects.filter(
        tipo=NotificacaoLog.Tipo.ATRASO_PDI,
    ).count() == 0


@pytest.mark.django_db
def test_alerta_atraso_acao_concluida_zero_emails(colaborador):
    """US2 Independent Test: ação concluída → 0 e-mails atraso."""
    _pdi, acao = _criar_pdi_com_acao(
        colaborador,
        status_acao=AcaoPDI.Status.CONCLUIDA,
        prazo=_prazo_atrasado(),
    )

    with patch(
        'apps.notifications.tasks.send_atraso_pdi_email',
    ) as send_mock:
        result = enviar_alerta_acao_pdi_atrasada(acao.pk)

    assert result['enviados'] == 0
    assert result['resultado'] == 'ineligivel'
    assert send_mock.call_count == 0


@pytest.mark.django_db
def test_lembrete_pdi_permanece_independente_do_atraso(colaborador):
    """Contrato #6: lembrete_pdi preventivo independente (tipos não se confundem)."""
    reminder_days = int(getattr(settings, 'NOTIFICATION_REMINDER_DAYS', 3))
    target = timezone.localdate() + timedelta(days=reminder_days)

    # Ação elegível a lembrete (prazo = hoje+N) — distinta do fluxo atraso.
    pdi_lembrete = PDI.objects.create(
        usuario=colaborador,
        titulo='PDI lembrete preventivo',
    )
    acao_lembrete = AcaoPDI.objects.create(
        pdi=pdi_lembrete,
        descricao='Ação na janela de lembrete',
        responsavel=colaborador,
        prazo=target,
        status=AcaoPDI.Status.PENDENTE,
    )

    # Ação já atrasada — alerta pontual.
    _pdi_atraso, acao_atraso = _criar_pdi_com_acao(colaborador)

    with (
        patch('apps.notifications.tasks.send_atraso_pdi_email') as send_atraso,
        patch('apps.notifications.tasks.send_lembrete_pdi_email') as send_lembrete,
    ):
        alerta = enviar_alerta_acao_pdi_atrasada(acao_atraso.pk)
        lembrete = enviar_lembrete_acao_pdi_vencendo()

    assert alerta['enviados'] >= 1
    assert lembrete['enviados'] == 1
    assert send_atraso.call_count == alerta['enviados']
    assert send_lembrete.call_count == 1

    assert NotificacaoLog.objects.filter(
        tipo=NotificacaoLog.Tipo.ATRASO_PDI,
        status=NotificacaoLog.Status.ENVIADO,
        referencia=f'acao_pdi:{acao_atraso.pk}',
    ).exists()
    assert NotificacaoLog.objects.filter(
        tipo=NotificacaoLog.Tipo.LEMBRETE_PDI,
        status=NotificacaoLog.Status.ENVIADO,
        referencia=f'acao_pdi:{acao_lembrete.pk}',
    ).count() == 1
    # Alerta de atraso não gera lembrete_pdi (e vice-versa).
    assert not NotificacaoLog.objects.filter(
        tipo=NotificacaoLog.Tipo.LEMBRETE_PDI,
        referencia=f'acao_pdi:{acao_atraso.pk}',
    ).exists()
    assert not NotificacaoLog.objects.filter(
        tipo=NotificacaoLog.Tipo.ATRASO_PDI,
        referencia=f'acao_pdi:{acao_lembrete.pk}',
    ).exists()


@pytest.mark.django_db(transaction=True)
def test_mark_overdue_enfileira_alerta_dono_e_gestor(colaborador, lider):
    """Quickstart §B: mark_overdue → alerta atraso para dono + gestor."""
    pdi = PDI.objects.create(
        usuario=colaborador,
        titulo='PDI a marcar atrasada',
        status=PDI.Status.ATIVO,
    )
    acao = AcaoPDI.objects.create(
        pdi=pdi,
        descricao='Pendente com prazo ontem',
        responsavel=colaborador,
        prazo=_prazo_atrasado(dias=1),
        status=AcaoPDI.Status.PENDENTE,
    )

    def _run_sync(acao_id: int):
        return enviar_alerta_acao_pdi_atrasada(acao_id)

    with (
        patch(
            'apps.notifications.tasks.enviar_alerta_acao_pdi_atrasada.delay',
            side_effect=_run_sync,
        ),
        patch('apps.notifications.tasks.send_atraso_pdi_email') as send_mock,
    ):
        updated = mark_overdue_pdi_actions()

    acao.refresh_from_db()
    assert updated == 1
    assert acao.status == AcaoPDI.Status.ATRASADA
    assert send_mock.call_count == 2
    dest_ids = {call.args[1].pk for call in send_mock.call_args_list}
    assert dest_ids == {colaborador.pk, lider.pk}
    assert _logs_atraso(referencia=f'acao_pdi:{acao.pk}').count() == 2
