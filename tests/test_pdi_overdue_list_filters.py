"""Contrato listagem PDI com atraso + AuthZ de escopo (US1 / T011).

Cobre [contracts/pdi-overdue-list.md] + [contracts/backend-scope-authz.md]:
atrasadas=1, contagem no card, colaborador sem leak, arquivado fora do operacional.
"""

from __future__ import annotations

from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import CustomUser
from apps.accounts.services.scope import VISAO_EQUIPE, VISAO_PROPRIAS
from apps.pdi.models import AcaoPDI, PDI
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


def _pdi_ids(response) -> set[int]:
    return {row['pdi'].pk for row in response.context['pdi_rows']}


def _row_for(response, pdi: PDI) -> dict:
    for row in response.context['pdi_rows']:
        if row['pdi'].pk == pdi.pk:
            return row
    raise AssertionError(f'PDI {pdi.pk} ausente em pdi_rows')


@pytest.fixture
def outsider(db, area, cargo_colab) -> CustomUser:
    return CustomUser.objects.create_user(
        email='outsider-pdi-atraso@test.greenn.com.br',
        password=DEFAULT_PASSWORD,
        nome='Outsider PDI Atraso',
        area=area,
        cargo=cargo_colab,
        data_entrada=FIXTURE_DATA_ENTRADA,
        email_confirmado_em=timezone.now(),
    )


@pytest.mark.django_db
def test_atrasadas_1_retorna_somente_pdis_com_acao_atrasada(client, colaborador):
    """Contrato §Testes #1: base 2 PDIs → atrasadas=1 só o com atraso."""
    com_atraso = PDI.objects.create(
        usuario=colaborador,
        titulo='PDI com atraso',
        status=PDI.Status.ATIVO,
    )
    sem_atraso = PDI.objects.create(
        usuario=colaborador,
        titulo='PDI sem atraso',
        status=PDI.Status.ATIVO,
    )
    _criar_acao(
        com_atraso,
        responsavel=colaborador,
        status=AcaoPDI.Status.ATRASADA,
        prazo=_prazo_atrasado(dias=3),
        descricao='Ação atrasada',
    )
    _criar_acao(
        sem_atraso,
        responsavel=colaborador,
        status=AcaoPDI.Status.PENDENTE,
        prazo=_prazo_futuro(),
        descricao='Ação no prazo',
    )

    client.force_login(colaborador)
    url = reverse('pdi:list')

    todos = client.get(url)
    assert todos.status_code == 200
    assert {com_atraso.pk, sem_atraso.pk} <= _pdi_ids(todos)

    filtrados = client.get(url, {'atrasadas': '1'})
    assert filtrados.status_code == 200
    assert filtrados.context['atrasadas_filtro'] is True
    ids = _pdi_ids(filtrados)
    assert com_atraso.pk in ids
    assert sem_atraso.pk not in ids


@pytest.mark.django_db
def test_contagem_atrasadas_no_card_reflete_annotate(client, colaborador):
    """Contrato §Testes #2: acoes_atrasadas_count no row = count real."""
    pdi = PDI.objects.create(
        usuario=colaborador,
        titulo='PDI com duas atrasadas',
        status=PDI.Status.ATIVO,
    )
    _criar_acao(
        pdi,
        responsavel=colaborador,
        status=AcaoPDI.Status.ATRASADA,
        prazo=_prazo_atrasado(dias=2),
        descricao='Atrasada 1',
    )
    _criar_acao(
        pdi,
        responsavel=colaborador,
        status=AcaoPDI.Status.ATRASADA,
        prazo=_prazo_atrasado(dias=7),
        descricao='Atrasada 2',
    )
    _criar_acao(
        pdi,
        responsavel=colaborador,
        status=AcaoPDI.Status.PENDENTE,
        prazo=_prazo_futuro(),
        descricao='No prazo',
    )

    client.force_login(colaborador)
    response = client.get(reverse('pdi:list'))
    assert response.status_code == 200
    row = _row_for(response, pdi)
    assert row['acoes_atrasadas_count'] == 2
    assert row['acoes_atrasadas_label'] == '2 atrasadas'

    filtrado = client.get(reverse('pdi:list'), {'atrasadas': '1'})
    assert filtrado.status_code == 200
    row_f = _row_for(filtrado, pdi)
    assert row_f['acoes_atrasadas_count'] == 2


@pytest.mark.django_db
def test_colaborador_atrasadas_nao_vaza_pdi_de_terceiros(
    client,
    colaborador,
    lider,
    outsider,
):
    """Contrato AuthZ: query string manipulada não amplia escopo."""
    proprio = PDI.objects.create(
        usuario=colaborador,
        titulo='PDI próprio com atraso',
        status=PDI.Status.ATIVO,
    )
    _criar_acao(
        proprio,
        responsavel=colaborador,
        status=AcaoPDI.Status.ATRASADA,
        prazo=_prazo_atrasado(),
    )

    do_lider = PDI.objects.create(
        usuario=lider,
        titulo='PDI do líder com atraso',
        status=PDI.Status.ATIVO,
    )
    _criar_acao(
        do_lider,
        responsavel=lider,
        status=AcaoPDI.Status.ATRASADA,
        prazo=_prazo_atrasado(),
    )

    do_outsider = PDI.objects.create(
        usuario=outsider,
        titulo='PDI outsider com atraso',
        status=PDI.Status.ATIVO,
    )
    _criar_acao(
        do_outsider,
        responsavel=outsider,
        status=AcaoPDI.Status.ATRASADA,
        prazo=_prazo_atrasado(),
    )

    client.force_login(colaborador)
    response = client.get(
        reverse('pdi:list'),
        {
            'atrasadas': '1',
            'visao': VISAO_EQUIPE,
            'modo': 'tabela',
            'gestor': str(lider.pk),
        },
    )
    assert response.status_code == 200
    # Backend força próprias; UI não decide AuthZ.
    assert response.context['visao'] == VISAO_PROPRIAS
    assert response.context['mostrar_toggle_visao'] is False
    ids = _pdi_ids(response)
    assert proprio.pk in ids
    assert do_lider.pk not in ids
    assert do_outsider.pk not in ids
    # Sem superfície de filtro gestor para colaborador puro.
    assert 'gestor_filtro' not in response.context
    assert 'filtro_gestores' not in response.context


@pytest.mark.django_db
def test_arquivado_fora_do_filtro_operacional_de_atrasadas(client, colaborador):
    """Contrato §Testes #6: arquivado só com status=arquivado explícito."""
    ativo = PDI.objects.create(
        usuario=colaborador,
        titulo='PDI ativo atrasado',
        status=PDI.Status.ATIVO,
    )
    arquivado = PDI.objects.create(
        usuario=colaborador,
        titulo='PDI arquivado atrasado',
        status=PDI.Status.ARQUIVADO,
    )
    for pdi in (ativo, arquivado):
        _criar_acao(
            pdi,
            responsavel=colaborador,
            status=AcaoPDI.Status.ATRASADA,
            prazo=_prazo_atrasado(),
        )

    client.force_login(colaborador)
    url = reverse('pdi:list')

    operacional = client.get(url, {'atrasadas': '1'})
    assert operacional.status_code == 200
    ids_op = _pdi_ids(operacional)
    assert ativo.pk in ids_op
    assert arquivado.pk not in ids_op

    com_arquivados = client.get(
        url,
        {'atrasadas': '1', 'status': PDI.Status.ARQUIVADO},
    )
    assert com_arquivados.status_code == 200
    ids_arq = _pdi_ids(com_arquivados)
    assert arquivado.pk in ids_arq
    assert ativo.pk not in ids_arq
