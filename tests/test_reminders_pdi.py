"""C6 / US5: lembretes dedupe + recálculo de atraso PDI."""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import patch

import pytest
from django.conf import settings
from django.utils import timezone

from apps.audit.context import audit_actor
from apps.audit.models import AuditLog
from apps.notifications.models import NotificacaoLog
from apps.notifications.tasks import (
    enviar_lembrete_acao_pdi_vencendo,
    enviar_lembrete_prazo_etapa,
)
from apps.pdi.models import AcaoPDI, PDI


@pytest.fixture
def pdi(colaborador) -> PDI:
    return PDI.objects.create(
        usuario=colaborador,
        titulo='PDI de teste C6',
    )


@pytest.mark.django_db
def test_lembrete_etapa_duas_vezes_mesma_janela_um_envio(avaliacao, ciclo_aberto):
    """C6 passo 1: job 2× na mesma janela → 1 envio efetivo por chave."""
    reminder_days = int(getattr(settings, 'NOTIFICATION_REMINDER_DAYS', 3))
    target = timezone.localdate() + timedelta(days=reminder_days)
    ciclo_aberto.data_fim = target
    ciclo_aberto.save(update_fields=['data_fim', 'updated_at'])

    with patch(
        'apps.notifications.tasks.send_lembrete_etapa_email',
    ) as send_mock:
        first = enviar_lembrete_prazo_etapa()
        second = enviar_lembrete_prazo_etapa()

    assert first['enviados'] >= 1
    assert second['enviados'] == 0
    assert second['pulados'] >= first['enviados']
    assert send_mock.call_count == first['enviados']
    assert (
        NotificacaoLog.objects.filter(
            destinatario=avaliacao.usuario,
            tipo=NotificacaoLog.Tipo.LEMBRETE_ETAPA,
            status=NotificacaoLog.Status.ENVIADO,
        ).count()
        == 1
    )
    # Segunda execução não cria novos logs enviado para a mesma janela.
    assert (
        NotificacaoLog.objects.filter(
            tipo=NotificacaoLog.Tipo.LEMBRETE_ETAPA,
            status=NotificacaoLog.Status.ENVIADO,
            janela=target.isoformat(),
        ).count()
        == first['enviados']
    )


@pytest.mark.django_db
def test_lembrete_pdi_duas_vezes_mesma_janela_um_envio(pdi, colaborador):
    """C6 passo 1 (variante PDI): job 2× → 1 envio."""
    reminder_days = int(getattr(settings, 'NOTIFICATION_REMINDER_DAYS', 3))
    target = timezone.localdate() + timedelta(days=reminder_days)
    AcaoPDI.objects.create(
        pdi=pdi,
        descricao='Ação com prazo na janela de lembrete',
        responsavel=colaborador,
        prazo=target,
        status=AcaoPDI.Status.PENDENTE,
    )

    with patch(
        'apps.notifications.tasks.send_lembrete_pdi_email',
    ) as send_mock:
        first = enviar_lembrete_acao_pdi_vencendo()
        second = enviar_lembrete_acao_pdi_vencendo()

    assert first['enviados'] == 1
    assert second['enviados'] == 0
    assert send_mock.call_count == 1
    assert (
        NotificacaoLog.objects.filter(
            destinatario=colaborador,
            tipo=NotificacaoLog.Tipo.LEMBRETE_PDI,
            status=NotificacaoLog.Status.ENVIADO,
        ).count()
        == 1
    )


@pytest.mark.django_db
def test_estender_prazo_atrasada_para_futuro_vira_pendente_com_audit(
    pdi,
    colaborador,
    admin,
):
    """C6 passo 2: atrasada + prazo futuro → pendente + audit de prazo/status."""
    past = timezone.localdate() - timedelta(days=5)
    future = timezone.localdate() + timedelta(days=10)
    acao = AcaoPDI.objects.create(
        pdi=pdi,
        descricao='Ação atrasada a estender',
        responsavel=colaborador,
        prazo=past,
        status=AcaoPDI.Status.ATRASADA,
    )
    assert acao.status == AcaoPDI.Status.ATRASADA

    with audit_actor(admin):
        acao.prazo = future
        acao.save(update_fields=['prazo', 'updated_at'])

    acao.refresh_from_db()
    assert acao.status == AcaoPDI.Status.PENDENTE

    prazo_logs = AuditLog.objects.filter(
        entity_type='pdi.AcaoPDI',
        entity_id=acao.pk,
        campo='prazo',
        acao=AuditLog.Acao.UPDATE,
    )
    status_logs = AuditLog.objects.filter(
        entity_type='pdi.AcaoPDI',
        entity_id=acao.pk,
        campo='status',
        acao=AuditLog.Acao.UPDATE,
    )
    assert prazo_logs.exists()
    assert status_logs.filter(
        valor_anterior=AcaoPDI.Status.ATRASADA,
        valor_novo=AcaoPDI.Status.PENDENTE,
    ).exists()
    assert prazo_logs.first().usuario_id == admin.pk


@pytest.mark.django_db
def test_prazo_ainda_passado_permanece_atrasada(pdi, colaborador):
    """C6: atrasada + prazo ainda no passado → permanece atrasada."""
    past = timezone.localdate() - timedelta(days=10)
    still_past = timezone.localdate() - timedelta(days=1)
    acao = AcaoPDI.objects.create(
        pdi=pdi,
        descricao='Ação ainda atrasada',
        responsavel=colaborador,
        prazo=past,
        status=AcaoPDI.Status.ATRASADA,
    )

    acao.prazo = still_past
    acao.save(update_fields=['prazo', 'updated_at'])

    acao.refresh_from_db()
    assert acao.status == AcaoPDI.Status.ATRASADA
