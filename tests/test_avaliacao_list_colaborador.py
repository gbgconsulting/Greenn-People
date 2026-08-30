"""Testes da listagem «Minhas Avaliações» (colaborador sem escopo de time)."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.urls import reverse

from apps.cycles.models import Ciclo
from apps.cycles.services.cycle import close_cycle, open_cycle
from apps.reviews.models import Avaliacao
from apps.reviews.services.collaborator_history import (
    build_collaborator_history_rows,
    is_collaborator_history_view,
    resolve_cycle_status,
)
from apps.reviews.services.display import format_nota_escala_cinco
from tests.conftest import DEFAULT_PASSWORD, FIXTURE_DATA_ENTRADA


@pytest.mark.django_db
def test_is_collaborator_history_view(colaborador, lider, admin):
    assert is_collaborator_history_view(colaborador) is True
    assert is_collaborator_history_view(lider) is False
    assert is_collaborator_history_view(admin) is False


@pytest.mark.django_db
def test_format_nota_escala_cinco():
    assert format_nota_escala_cinco(Decimal('0.84')) == '4.2'
    assert format_nota_escala_cinco(None) == '—'


@pytest.mark.django_db
def test_resolve_cycle_status_concluida(avaliacao):
    avaliacao.concluida = True
    avaliacao.save(update_fields=['concluida', 'updated_at'])
    label, variant = resolve_cycle_status(avaliacao)
    assert label == 'Concluído'
    assert variant == 'concluido'


@pytest.mark.django_db
def test_colaborador_ve_historico_pessoal(client, colaborador, ciclo_aberto):
    today = date.today()
    ciclo_antigo = Ciclo.objects.create(
        nome='2023.2',
        data_inicio=today - timedelta(days=400),
        data_fim=today - timedelta(days=200),
        status=Ciclo.Status.ENCERRADO,
        admitidos_ate=today - timedelta(days=400),
    )
    Avaliacao.objects.create(
        ciclo=ciclo_antigo,
        usuario=colaborador,
        etapa=Avaliacao.Etapa.FEEDBACK,
        concluida=True,
        nota_final_lider=Decimal('0.76'),
    )

    client.force_login(colaborador)
    url = reverse('reviews:list')
    response = client.get(url)

    assert response.status_code == 200
    html = response.content.decode()
    assert 'Minhas Avaliações' in html
    assert 'Histórico de Ciclos' in html
    assert ciclo_aberto.nome in html
    assert '2023.2' in html
    assert 'Colaborador</th>' not in html
    assert '<table class="collaborator-history-table">' in html


@pytest.mark.django_db
def test_colaborador_nao_ve_avaliacao_de_outro(client, colaborador, lider, ciclo_aberto):
    outro = colaborador.__class__.objects.create_user(
        email='outro@test.greenn.com.br',
        password=DEFAULT_PASSWORD,
        nome='Outro Colab',
        line_manager=lider,
        data_entrada=FIXTURE_DATA_ENTRADA,
    )
    ciclo_fechado = Ciclo.objects.create(
        nome='Ciclo Só Outro',
        data_inicio=date(2019, 1, 1),
        data_fim=date(2019, 6, 30),
        status=Ciclo.Status.ENCERRADO,
        admitidos_ate=date(2019, 1, 1),
    )
    Avaliacao.objects.create(
        ciclo=ciclo_fechado,
        usuario=outro,
        etapa=Avaliacao.Etapa.FEEDBACK,
        concluida=True,
    )

    client.force_login(colaborador)
    response = client.get(reverse('reviews:list'))

    assert response.status_code == 200
    assert 'Ciclo Só Outro' not in response.content.decode()


@pytest.mark.django_db
def test_lider_mantem_lista_operacional(client, lider, colaborador, ciclo_aberto):
    client.force_login(lider)
    response = client.get(reverse('reviews:list'))

    assert response.status_code == 200
    html = response.content.decode()
    assert 'Minhas Avaliações' not in html
    assert 'Avaliações' in html
    assert 'Colaborador</th>' in html
    assert colaborador.nome in html


@pytest.mark.django_db
def test_build_collaborator_history_rows_destaca_mais_recente(ciclo_aberto, colaborador):
    today = date.today()
    ciclo_antigo = Ciclo.objects.create(
        nome='2022.1',
        data_inicio=today - timedelta(days=800),
        data_fim=today - timedelta(days=600),
        status=Ciclo.Status.ENCERRADO,
        admitidos_ate=today - timedelta(days=800),
    )
    antiga = Avaliacao.objects.create(
        ciclo=ciclo_antigo,
        usuario=colaborador,
        etapa=Avaliacao.Etapa.FEEDBACK,
        concluida=True,
    )
    atual = Avaliacao.objects.get(ciclo=ciclo_aberto, usuario=colaborador)
    rows = build_collaborator_history_rows([atual, antiga])
    assert rows[0]['avaliacao'].pk == atual.pk
    assert rows[0]['is_highlight'] is True
    assert rows[1]['is_highlight'] is False


@pytest.mark.django_db
def test_colaborador_historico_pagina(client, colaborador, ciclo_aberto):
    today = date.today()
    for index in range(11):
        ciclo = Ciclo.objects.create(
            nome=f'Ciclo Arquivo {index}',
            data_inicio=today - timedelta(days=400 + index * 30),
            data_fim=today - timedelta(days=200 + index * 30),
            status=Ciclo.Status.ENCERRADO,
            admitidos_ate=today - timedelta(days=400),
        )
        Avaliacao.objects.create(
            ciclo=ciclo,
            usuario=colaborador,
            etapa=Avaliacao.Etapa.FEEDBACK,
            concluida=True,
        )

    client.force_login(colaborador)
    response = client.get(reverse('reviews:list'))
    html = response.content.decode()

    assert response.status_code == 200
    assert 'Página 1 de' in html
    assert 'Próxima' in html
    assert 'collaborator-history-table' in html


@pytest.mark.django_db
def test_colaborador_lista_inclui_ciclo_encerrado_proprio(
    client,
    colaborador,
    ciclo_aberto,
):
    close_cycle(ciclo_aberto)
    ciclo_aberto.refresh_from_db()

    ciclo_novo = Ciclo.objects.create(
        nome='2025.1',
        data_inicio=date.today() - timedelta(days=10),
        data_fim=date.today() + timedelta(days=80),
        status=Ciclo.Status.ENCERRADO,
        admitidos_ate=date.today(),
    )
    open_cycle(ciclo_novo)
    Avaliacao.objects.get(ciclo=ciclo_novo, usuario=colaborador)

    client.force_login(colaborador)
    response = client.get(reverse('reviews:list'))
    html = response.content.decode()

    assert ciclo_aberto.nome in html
    assert ciclo_novo.nome in html
