"""Contrato listagem PDI com atraso + AuthZ de escopo (US1 / T011 + US3 / T022).

Cobre [contracts/pdi-overdue-list.md] + [contracts/backend-scope-authz.md]:
atrasadas=1, contagem no card, colaborador sem leak, arquivado fora do operacional;
vista tabela (colunas, faixa_atraso, modo forçado a cards sem permissão).
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
    assert response.context['mostrar_toggle_modo'] is False
    assert response.context['modo'] == 'cards'
    ids = _pdi_ids(response)
    assert proprio.pk in ids
    assert do_lider.pk not in ids
    assert do_outsider.pk not in ids
    # Sem superfície de filtro gestor para colaborador puro.
    assert 'gestor_filtro' not in response.context
    assert 'filtro_gestores' not in response.context
    assert b'leader-team-table' not in response.content


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


# --- US3 / T022: vista tabela operacional ---------------------------------


@pytest.mark.django_db
def test_admin_modo_tabela_exibe_colunas_operacionais(
    client,
    admin,
    lider,
    colaborador,
    area,
):
    """Contrato §Testes #4: visao=equipe&modo=tabela → colunas acordadas."""
    com_atraso = PDI.objects.create(
        usuario=colaborador,
        titulo='PDI tabela com atraso',
        status=PDI.Status.ATIVO,
    )
    sem_atraso = PDI.objects.create(
        usuario=lider,
        titulo='PDI tabela sem atraso',
        status=PDI.Status.ATIVO,
    )
    prazo_atrasado = _prazo_atrasado(dias=5)
    prazo_futuro = _prazo_futuro(dias=14)
    _criar_acao(
        com_atraso,
        responsavel=colaborador,
        status=AcaoPDI.Status.ATRASADA,
        prazo=prazo_atrasado,
        descricao='Atrasada na tabela',
    )
    _criar_acao(
        sem_atraso,
        responsavel=lider,
        status=AcaoPDI.Status.PENDENTE,
        prazo=prazo_futuro,
        descricao='No prazo na tabela',
    )

    client.force_login(admin)
    response = client.get(
        reverse('pdi:list'),
        {'visao': VISAO_EQUIPE, 'modo': 'tabela'},
    )
    assert response.status_code == 200
    assert response.context['visao'] == VISAO_EQUIPE
    assert response.context['modo'] == 'tabela'
    assert response.context['mostrar_toggle_modo'] is True
    assert b'leader-team-table' in response.content
    for label in (
        b'Colaborador',
        b'Gestor',
        b'\xc3\x81rea',  # Área
        b'Progresso',
        b'Atrasadas',
        b'Dias m\xc3\xa1x.',  # Dias máx.
        b'Pr\xc3\xb3ximo prazo',  # Próximo prazo
    ):
        assert label in response.content

    row_atraso = _row_for(response, com_atraso)
    assert row_atraso['colaborador'] == colaborador.nome
    assert row_atraso['gestor'] == lider
    assert row_atraso['area'] == area
    assert row_atraso['acoes_atrasadas_count'] == 1
    assert row_atraso['dias_atraso_max'] == 5
    assert row_atraso['proximo_prazo'] == prazo_atrasado
    assert 'progresso' in row_atraso

    row_ok = _row_for(response, sem_atraso)
    assert row_ok['acoes_atrasadas_count'] == 0
    assert row_ok['dias_atraso_max'] is None
    assert row_ok['proximo_prazo'] == prazo_futuro


@pytest.mark.django_db
def test_faixa_atraso_1_7_exclui_plano_com_max_dias_10(
    client,
    admin,
    colaborador,
    lider,
):
    """Contrato §Testes #5: faixa_atraso=1-7 exclui dias_atraso_max=10."""
    pdi_3 = PDI.objects.create(
        usuario=colaborador,
        titulo='PDI atraso 3 dias',
        status=PDI.Status.ATIVO,
    )
    pdi_10 = PDI.objects.create(
        usuario=lider,
        titulo='PDI atraso 10 dias',
        status=PDI.Status.ATIVO,
    )
    _criar_acao(
        pdi_3,
        responsavel=colaborador,
        status=AcaoPDI.Status.ATRASADA,
        prazo=_prazo_atrasado(dias=3),
    )
    _criar_acao(
        pdi_10,
        responsavel=lider,
        status=AcaoPDI.Status.ATRASADA,
        prazo=_prazo_atrasado(dias=10),
    )

    client.force_login(admin)
    url = reverse('pdi:list')
    params = {
        'visao': VISAO_EQUIPE,
        'modo': 'tabela',
        'faixa_atraso': '1-7',
    }

    response = client.get(url, params)
    assert response.status_code == 200
    assert response.context['faixa_atraso_filtro'] == '1-7'
    ids = _pdi_ids(response)
    assert pdi_3.pk in ids
    assert pdi_10.pk not in ids
    assert _row_for(response, pdi_3)['dias_atraso_max'] == 3


@pytest.mark.django_db
def test_colaborador_modo_tabela_forcado_a_cards_sem_permissao(
    client,
    colaborador,
):
    """AuthZ US3: sem can_view_team, modo=tabela → cards; sem toggle gerencial."""
    pdi = PDI.objects.create(
        usuario=colaborador,
        titulo='PDI próprio modo forçado',
        status=PDI.Status.ATIVO,
    )
    _criar_acao(
        pdi,
        responsavel=colaborador,
        status=AcaoPDI.Status.PENDENTE,
        prazo=_prazo_futuro(),
    )

    client.force_login(colaborador)
    response = client.get(
        reverse('pdi:list'),
        {'visao': VISAO_EQUIPE, 'modo': 'tabela', 'faixa_atraso': '1-7'},
    )
    assert response.status_code == 200
    assert response.context['visao'] == VISAO_PROPRIAS
    assert response.context['modo'] == 'cards'
    assert response.context['mostrar_toggle_modo'] is False
    assert response.context['mostrar_toggle_visao'] is False
    assert pdi.pk in _pdi_ids(response)
    assert 'faixa_atraso_filtro' not in response.context
    assert b'leader-team-table' not in response.content
    assert b'data-component="pdi-modo-toggle"' not in response.content
    # Filtro gerencial ignorado: PDI sem atraso permanece listado.
