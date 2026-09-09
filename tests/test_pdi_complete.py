"""Contrato lifecycle concluir PDI + board coluna Atrasadas (US6 / T036).

Cobre [contracts/pdi-complete-lifecycle.md] + AuthZ de escopo:
100% → concluído; pendente rejeita; arquivado rejeita; coluna Atrasadas;
POST fora de escopo → 404.
"""

from __future__ import annotations

from datetime import timedelta

import pytest
from django.contrib.messages import get_messages
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import CustomUser
from apps.pdi.models import AcaoPDI, PDI
from apps.pdi.services.lifecycle import (
    PDINotCompletableError,
    complete_pdi,
    pdi_can_complete,
)
from tests.conftest import DEFAULT_PASSWORD, FIXTURE_DATA_ENTRADA


def _prazo_atrasado(*, dias: int = 5):
    return timezone.localdate() - timedelta(days=dias)


def _prazo_futuro(*, dias: int = 30):
    return timezone.localdate() + timedelta(days=dias)


def _criar_acao(
    pdi: PDI,
    *,
    responsavel: CustomUser,
    status: str,
    prazo=None,
    descricao: str = 'Ação teste',
) -> AcaoPDI:
    return AcaoPDI.objects.create(
        pdi=pdi,
        descricao=descricao,
        responsavel=responsavel,
        prazo=prazo if prazo is not None else _prazo_futuro(),
        status=status,
    )


@pytest.fixture
def outsider(db, area, cargo_colab) -> CustomUser:
    return CustomUser.objects.create_user(
        email='outsider-pdi-complete@test.greenn.com.br',
        password=DEFAULT_PASSWORD,
        nome='Outsider PDI Complete',
        area=area,
        cargo=cargo_colab,
        data_entrada=FIXTURE_DATA_ENTRADA,
        email_confirmado_em=timezone.now(),
    )


# --- Serviço complete_pdi ---


@pytest.mark.django_db
def test_complete_pdi_100_porcento_concluidas_marca_concluido(colaborador):
    """Contrato §Testes #1: ativo + todas concluídas → status concluido."""
    pdi = PDI.objects.create(
        usuario=colaborador,
        titulo='PDI pronto para concluir',
        status=PDI.Status.ATIVO,
    )
    _criar_acao(
        pdi,
        responsavel=colaborador,
        status=AcaoPDI.Status.CONCLUIDA,
        descricao='Ação 1 ok',
    )
    _criar_acao(
        pdi,
        responsavel=colaborador,
        status=AcaoPDI.Status.CONCLUIDA,
        descricao='Ação 2 ok',
    )

    assert pdi_can_complete(pdi) is True
    result = complete_pdi(pdi)
    pdi.refresh_from_db()

    assert result.status == PDI.Status.CONCLUIDO
    assert pdi.status == PDI.Status.CONCLUIDO
    assert pdi_can_complete(pdi) is False


@pytest.mark.django_db
def test_complete_pdi_com_pendente_rejeita_e_mantem_ativo(colaborador):
    """Contrato §Testes #2: 1 pendente → rejeita; status permanece ativo."""
    pdi = PDI.objects.create(
        usuario=colaborador,
        titulo='PDI incompleto',
        status=PDI.Status.ATIVO,
    )
    _criar_acao(
        pdi,
        responsavel=colaborador,
        status=AcaoPDI.Status.CONCLUIDA,
        descricao='Feita',
    )
    _criar_acao(
        pdi,
        responsavel=colaborador,
        status=AcaoPDI.Status.PENDENTE,
        descricao='Ainda aberta',
    )

    assert pdi_can_complete(pdi) is False
    with pytest.raises(PDINotCompletableError, match='concluídas'):
        complete_pdi(pdi)

    pdi.refresh_from_db()
    assert pdi.status == PDI.Status.ATIVO


@pytest.mark.django_db
def test_complete_pdi_arquivado_rejeita(colaborador):
    """Contrato §Testes #3: arquivado → rejeita."""
    pdi = PDI.objects.create(
        usuario=colaborador,
        titulo='PDI arquivado',
        status=PDI.Status.ARQUIVADO,
    )
    _criar_acao(
        pdi,
        responsavel=colaborador,
        status=AcaoPDI.Status.CONCLUIDA,
        descricao='Já feita',
    )

    assert pdi_can_complete(pdi) is False
    with pytest.raises(PDINotCompletableError, match='arquivados'):
        complete_pdi(pdi)

    pdi.refresh_from_db()
    assert pdi.status == PDI.Status.ARQUIVADO


# --- Board: coluna Atrasadas ---


@pytest.mark.django_db
def test_board_acao_atrasada_somente_na_coluna_atrasadas(client, colaborador):
    """Contrato §Testes #4: ação atrasada só em acoes_atrasadas (não em andamento)."""
    pdi = PDI.objects.create(
        usuario=colaborador,
        titulo='PDI board atraso',
        status=PDI.Status.ATIVO,
    )
    atrasada = _criar_acao(
        pdi,
        responsavel=colaborador,
        status=AcaoPDI.Status.ATRASADA,
        prazo=_prazo_atrasado(dias=4),
        descricao='Ação bem atrasada do board',
    )
    andamento = _criar_acao(
        pdi,
        responsavel=colaborador,
        status=AcaoPDI.Status.EM_ANDAMENTO,
        descricao='Ação em andamento board',
    )
    pendente = _criar_acao(
        pdi,
        responsavel=colaborador,
        status=AcaoPDI.Status.PENDENTE,
        descricao='Ação pendente board',
    )
    concluida = _criar_acao(
        pdi,
        responsavel=colaborador,
        status=AcaoPDI.Status.CONCLUIDA,
        descricao='Ação concluída board',
    )

    client.force_login(colaborador)
    response = client.get(reverse('pdi:detail', kwargs={'pk': pdi.pk}))
    assert response.status_code == 200

    ids_atrasadas = {row['acao'].pk for row in response.context['acoes_atrasadas']}
    ids_andamento = {row['acao'].pk for row in response.context['acoes_em_andamento']}
    ids_proximas = {row['acao'].pk for row in response.context['acoes_proximas']}
    ids_concluidas = {row['acao'].pk for row in response.context['acoes_concluidas']}

    assert ids_atrasadas == {atrasada.pk}
    assert andamento.pk in ids_andamento
    assert atrasada.pk not in ids_andamento
    assert pendente.pk in ids_proximas
    assert atrasada.pk not in ids_proximas
    assert concluida.pk in ids_concluidas
    assert response.context['total_atrasadas'] == 1
    assert response.context['can_complete'] is False

    content = response.content.decode()
    assert 'Atrasadas' in content
    assert 'Ação bem atrasada do board' in content
    assert 'acoes-atrasadas-heading' in content


# --- View POST complete + AuthZ ---


@pytest.mark.django_db
def test_post_complete_100_porcento_redireciona_concluidos(client, colaborador):
    """POST no escopo com 100% concluídas persiste concluido e redireciona."""
    pdi = PDI.objects.create(
        usuario=colaborador,
        titulo='PDI concluir via POST',
        status=PDI.Status.ATIVO,
    )
    _criar_acao(
        pdi,
        responsavel=colaborador,
        status=AcaoPDI.Status.CONCLUIDA,
        descricao='Única ação',
    )

    client.force_login(colaborador)
    url = reverse('pdi:complete', kwargs={'pk': pdi.pk})
    response = client.post(url)

    assert response.status_code == 302
    assert f'status={PDI.Status.CONCLUIDO}' in response['Location']

    pdi.refresh_from_db()
    assert pdi.status == PDI.Status.CONCLUIDO

    msgs = [m.message for m in get_messages(response.wsgi_request)]
    assert any('concluído' in m.lower() for m in msgs)


@pytest.mark.django_db
def test_post_complete_com_pendente_rejeita_via_view(client, colaborador):
    """POST com ação pendente: status ativo; feedback de erro."""
    pdi = PDI.objects.create(
        usuario=colaborador,
        titulo='PDI POST incompleto',
        status=PDI.Status.ATIVO,
    )
    _criar_acao(
        pdi,
        responsavel=colaborador,
        status=AcaoPDI.Status.PENDENTE,
        descricao='Ainda falta',
    )

    client.force_login(colaborador)
    url = reverse('pdi:complete', kwargs={'pk': pdi.pk})
    response = client.post(url)

    assert response.status_code == 302
    assert reverse('pdi:detail', kwargs={'pk': pdi.pk}) in response['Location']

    pdi.refresh_from_db()
    assert pdi.status == PDI.Status.ATIVO

    msgs = [m.message for m in get_messages(response.wsgi_request)]
    assert any('concluídas' in m.lower() for m in msgs)


@pytest.mark.django_db
def test_post_complete_fora_de_escopo_404(client, colaborador, outsider):
    """POST fora do escopo do dono → 404 (ScopedObjectMixin / IDOR)."""
    pdi = PDI.objects.create(
        usuario=outsider,
        titulo='PDI de outsider',
        status=PDI.Status.ATIVO,
    )
    _criar_acao(
        pdi,
        responsavel=outsider,
        status=AcaoPDI.Status.CONCLUIDA,
        descricao='Não autoriza',
    )

    client.force_login(colaborador)
    response = client.post(reverse('pdi:complete', kwargs={'pk': pdi.pk}))

    assert response.status_code == 404
    pdi.refresh_from_db()
    assert pdi.status == PDI.Status.ATIVO
