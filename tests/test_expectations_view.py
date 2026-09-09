"""Tela de expectativas: apresentação alinhada ao mock (sem mudar AuthZ/FR-005)."""

from __future__ import annotations

from decimal import Decimal

import pytest
from django.urls import reverse

from apps.competencies.models import CargoCompetencia, Competencia, Escala
from apps.goals.models import Meta
from apps.goals.views import (
    _competencia_segments,
    _competencia_target_level,
    _escala_legenda,
    _resumo_autoavaliacao_strip,
)
from apps.reviews.models import Avaliacao


def _vincular_competencias(cargo, *, n=2) -> list[CargoCompetencia]:
    escala = Escala.objects.create(
        nome='Escala Expectativas',
        valor_minimo=1,
        valor_maximo=5,
        rotulos_por_nivel={'1': 'Inicial', '2': 'Básico', '3': 'Intermediário'},
    )
    criadas = []
    for i in range(n):
        competencia = Competencia.objects.create(
            nome=f'Competência Expectativa {i + 1}',
            descricao=f'Descrição da competência {i + 1}.',
            tipo=Competencia.Tipo.COMPORTAMENTAL,
            escala=escala,
        )
        criadas.append(
            CargoCompetencia.objects.create(
                cargo=cargo,
                competencia=competencia,
                nivel_esperado=Decimal('2.00'),
                peso=Decimal('1.00'),
            ),
        )
    return criadas


@pytest.mark.django_db
def test_competencia_segments_e_alvo():
    assert _competencia_segments(2, 1, 5) == [True, True, False, False, False]
    assert _competencia_target_level(2, 1, 5) == 2
    assert _competencia_target_level(99, 1, 5) == 5
    assert _competencia_segments(None, 1, 5) == []


@pytest.mark.django_db
def test_escala_legenda_unica(cargo_colab):
    _vincular_competencias(cargo_colab, n=2)
    items = [
        {
            'competencia': cc.competencia,
            'nivel_esperado': cc.nivel_esperado,
        }
        for cc in CargoCompetencia.objects.filter(cargo=cargo_colab).select_related(
            'competencia',
            'competencia__escala',
        )
    ]
    assert _escala_legenda(items) == {'minimo': 1, 'maximo': 5}
    assert _escala_legenda([]) is None


@pytest.mark.django_db
def test_resumo_autoavaliacao_strip_etapa_aberta(avaliacao):
    avaliacao.etapa = Avaliacao.Etapa.AVALIACAO
    avaliacao.save(update_fields=['etapa', 'updated_at'])
    strip = _resumo_autoavaliacao_strip(
        {
            'autoavaliacao_enviada': False,
            'avaliacao': avaliacao,
        },
    )
    assert strip['badge'] == 'Etapa aberta'
    assert 'Aguardando' in strip['detail']


@pytest.mark.django_db
def test_expectations_view_mock_layout(
    client,
    colaborador,
    cargo_colab,
    ciclo_aberto,
    meta,
):
    _vincular_competencias(cargo_colab, n=2)
    meta.status = Meta.Status.APROVADA
    meta.progresso = Meta.PROGRESSO_CONCLUIDA
    meta.save(update_fields=['status', 'progresso', 'updated_at'])

    client.force_login(colaborador)
    resp = client.get(reverse('goals:expectations'))

    assert resp.status_code == 200
    html = resp.content.decode()
    assert 'Minhas Expectativas' in html
    assert 'Cargo Atual Mapeado' in html
    assert 'Competências do Cargo' in html
    assert 'Nível Esperado (Alvo)' in html
    assert 'Metas Vinculadas' in html
    assert 'Validação da Liderança' in html
    assert 'Nota Consolidada do Ciclo' in html
    assert '2 / 5 (Básico)' in html
    assert 'Meta' in html
    assert '70%' not in html  # não inventa composição falsa (PRD / RF-15)
    assert '30%' not in html
    assert resp.context['escala_legenda'] == {'minimo': 1, 'maximo': 5}
    assert len(resp.context['competencias_cards']) == 2
    card = resp.context['competencias_cards'][0]
    assert card['target_level'] == 2
    assert card['nivel_esperado_badge'] == '2 / 5 (Básico)'
    assert card['autoavaliacao_label'] == 'Ainda não avaliada'


@pytest.mark.django_db
def test_expectations_vinculo_pendente(client, colaborador, ciclo_aberto):
    client.force_login(colaborador)
    resp = client.get(reverse('goals:expectations'))

    assert resp.status_code == 200
    html = resp.content.decode()
    assert 'Vínculo pendente' in html or 'Vínculo de cargo/competências pendente' in html
    assert resp.context['vinculo_pendente'] is True


@pytest.mark.django_db
def test_expectations_requer_login(client):
    resp = client.get(reverse('goals:expectations'))
    assert resp.status_code == 302
