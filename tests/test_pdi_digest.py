"""Contrato digest RH de atrasos PDI (US4 / T027).

Cobre [contracts/pdi-overdue-notifications.md] §fluxo digest + quickstart §D:
com atrasos → 1 e-mail/admin/semana; silêncio se zero; não-admin excluído;
dedupe semanal (janela ISO ``YYYY-Www``).
"""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import patch

import pytest
from django.utils import timezone

from apps.accounts.models import CustomUser
from apps.notifications.emails import REFERENCIA_DIGEST_PDI_ATRASOS
from apps.notifications.models import NotificacaoLog
from apps.notifications.tasks import (
    _janela_semana_iso,
    enviar_digest_pdi_atrasos,
)
from apps.pdi.models import AcaoPDI, PDI
from tests.conftest import DEFAULT_PASSWORD, FIXTURE_DATA_ENTRADA


def _prazo_atrasado(*, dias: int = 3):
    return timezone.localdate() - timedelta(days=dias)


def _criar_pdi_com_acao_atrasada(
    dono: CustomUser,
    *,
    status_pdi: str = PDI.Status.ATIVO,
    descricao: str = 'Ação atrasada digest',
) -> tuple[PDI, AcaoPDI]:
    pdi = PDI.objects.create(
        usuario=dono,
        titulo='PDI digest atraso',
        status=status_pdi,
    )
    acao = AcaoPDI.objects.create(
        pdi=pdi,
        descricao=descricao,
        responsavel=dono,
        prazo=_prazo_atrasado(),
        status=AcaoPDI.Status.ATRASADA,
    )
    return pdi, acao


def _logs_digest(*, destinatario: CustomUser | None = None):
    qs = NotificacaoLog.objects.filter(
        tipo=NotificacaoLog.Tipo.DIGEST_PDI_ATRASOS,
        status=NotificacaoLog.Status.ENVIADO,
        referencia=REFERENCIA_DIGEST_PDI_ATRASOS,
    )
    if destinatario is not None:
        qs = qs.filter(destinatario=destinatario)
    return qs


@pytest.mark.django_db
def test_digest_com_atrasos_envia_um_email_por_admin(admin, colaborador):
    """Contrato #4 / quickstart §D.1: com atrasos → 1 e-mail por admin ativo."""
    _criar_pdi_com_acao_atrasada(colaborador)
    segundo_admin = CustomUser.objects.create_user(
        email='admin2@test.greenn.com.br',
        password=DEFAULT_PASSWORD,
        nome='Admin Dois',
        is_admin=True,
        is_staff=True,
        data_entrada=FIXTURE_DATA_ENTRADA,
        email_confirmado_em=timezone.now(),
    )
    janela = _janela_semana_iso()

    with patch(
        'apps.notifications.tasks.send_digest_pdi_atrasos_email',
    ) as send_mock:
        result = enviar_digest_pdi_atrasos()

    assert result['resultado'] == 'ok'
    assert result['enviados'] == 2
    assert result['falhas'] == 0
    assert result['pulados'] == 0
    assert result['pdis_com_atraso'] >= 1
    assert result['acoes_atrasadas'] >= 1
    assert result['janela'] == janela
    assert send_mock.call_count == 2
    dest_ids = {call.args[0].pk for call in send_mock.call_args_list}
    assert dest_ids == {admin.pk, segundo_admin.pk}
    for dest in (admin, segundo_admin):
        aggregation = next(
            call.args[1]
            for call in send_mock.call_args_list
            if call.args[0].pk == dest.pk
        )
        assert aggregation.acoes_atrasadas >= 1
        assert aggregation.pdis_com_atraso >= 1
    assert _logs_digest().count() == 2
    assert _logs_digest(destinatario=admin).filter(janela=janela).exists()
    assert _logs_digest(destinatario=segundo_admin).filter(
        janela=janela,
    ).exists()


@pytest.mark.django_db
def test_digest_sem_atrasos_silencio(admin, colaborador):
    """Contrato #4 / quickstart §D.2: sem atrasos elegíveis → silêncio (0 e-mails)."""
    # PDI ativo sem ação atrasada — não deve disparar digest.
    pdi_ok = PDI.objects.create(
        usuario=colaborador,
        titulo='PDI sem atraso',
        status=PDI.Status.ATIVO,
    )
    AcaoPDI.objects.create(
        pdi=pdi_ok,
        descricao='Pendente no prazo',
        responsavel=colaborador,
        prazo=timezone.localdate() + timedelta(days=7),
        status=AcaoPDI.Status.PENDENTE,
    )
    # Arquivado com atraso permanece fora do operacional (FR-015).
    _criar_pdi_com_acao_atrasada(
        colaborador,
        status_pdi=PDI.Status.ARQUIVADO,
        descricao='Atraso em arquivado',
    )

    with patch(
        'apps.notifications.tasks.send_digest_pdi_atrasos_email',
    ) as send_mock:
        result = enviar_digest_pdi_atrasos()

    assert result['resultado'] == 'silencio'
    assert result['enviados'] == 0
    assert result['falhas'] == 0
    assert result['pulados'] == 0
    assert result['acoes_atrasadas'] == 0
    assert send_mock.call_count == 0
    assert NotificacaoLog.objects.filter(
        tipo=NotificacaoLog.Tipo.DIGEST_PDI_ATRASOS,
    ).count() == 0


@pytest.mark.django_db
def test_digest_nao_admin_excluido(admin, lider, colaborador):
    """Contrato #5 / quickstart §D.3: gestor não-admin não recebe digest."""
    assert not lider.is_admin
    _criar_pdi_com_acao_atrasada(colaborador)

    with patch(
        'apps.notifications.tasks.send_digest_pdi_atrasos_email',
    ) as send_mock:
        result = enviar_digest_pdi_atrasos()

    assert result['enviados'] == 1
    assert send_mock.call_count == 1
    assert send_mock.call_args.args[0].pk == admin.pk
    assert _logs_digest(destinatario=admin).exists()
    assert not _logs_digest(destinatario=lider).exists()
    assert not NotificacaoLog.objects.filter(
        tipo=NotificacaoLog.Tipo.DIGEST_PDI_ATRASOS,
        destinatario=colaborador,
    ).exists()


@pytest.mark.django_db
def test_digest_dedupe_semanal(admin, colaborador):
    """Contrato #4: 2ª run na mesma semana ISO → 0 reenvios (pulados)."""
    _criar_pdi_com_acao_atrasada(colaborador)
    janela = _janela_semana_iso()
    assert janela.count('-W') == 1

    with patch(
        'apps.notifications.tasks.send_digest_pdi_atrasos_email',
    ) as send_mock:
        first = enviar_digest_pdi_atrasos()
        second = enviar_digest_pdi_atrasos()

    assert first['enviados'] == 1
    assert first['janela'] == janela
    assert second['enviados'] == 0
    assert second['pulados'] == 1
    assert second['janela'] == janela
    assert send_mock.call_count == 1
    assert _logs_digest(destinatario=admin).filter(janela=janela).count() == 1
