"""Variante visual do card do hub PDI (status exibido na listagem)."""

from __future__ import annotations

from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.pdi.models import AcaoPDI, PDI
from apps.pdi.views import _hub_card_variant, _hub_cta_label, _hub_status_label


@pytest.mark.parametrize(
    ('status', 'total_acoes', 'expected'),
    [
        (PDI.Status.ATIVO, 0, 'aguardando'),
        (PDI.Status.ATIVO, 3, 'em_andamento'),
        (PDI.Status.CONCLUIDO, 5, 'concluido'),
        (PDI.Status.ARQUIVADO, 2, 'arquivado'),
    ],
)
def test_hub_card_variant(status, total_acoes, expected):
    pdi = PDI(status=status)
    assert _hub_card_variant(pdi, total_acoes) == expected


def test_plano_com_acoes_sem_conclusao_e_em_andamento():
    """Plano com ações registradas não deve ficar em 'Aguardando início'."""
    pdi = PDI(status=PDI.Status.ATIVO)
    variant = _hub_card_variant(pdi, total_acoes=1)
    assert variant == 'em_andamento'
    assert _hub_status_label(variant) == 'Em andamento'
    assert _hub_cta_label(variant) == 'Gerenciar'


@pytest.mark.django_db
def test_filtro_em_andamento_exclui_planos_sem_acoes(client, colaborador):
    """Filtro 'Em andamento' não deve listar planos 'Aguardando início'."""
    sem_acoes = PDI.objects.create(
        usuario=colaborador,
        titulo='Plano vazio',
        status=PDI.Status.ATIVO,
    )
    com_acoes = PDI.objects.create(
        usuario=colaborador,
        titulo='Plano com ações',
        status=PDI.Status.ATIVO,
    )
    AcaoPDI.objects.create(
        pdi=com_acoes,
        descricao='Ação de teste',
        responsavel=colaborador,
        prazo=timezone.localdate() + timedelta(days=30),
    )

    client.force_login(colaborador)
    url = reverse('pdi:list')
    response = client.get(url, {'status': PDI.Status.ATIVO})
    assert response.status_code == 200
    pdi_ids = {row['pdi'].pk for row in response.context['pdi_rows']}
    assert com_acoes.pk in pdi_ids
    assert sem_acoes.pk not in pdi_ids


@pytest.mark.django_db
def test_filtro_todos_inclui_planos_aguardando_inicio(client, colaborador):
    sem_acoes = PDI.objects.create(
        usuario=colaborador,
        titulo='Plano vazio',
        status=PDI.Status.ATIVO,
    )

    client.force_login(colaborador)
    response = client.get(reverse('pdi:list'))
    assert response.status_code == 200
    pdi_ids = {row['pdi'].pk for row in response.context['pdi_rows']}
    assert sem_acoes.pk in pdi_ids
