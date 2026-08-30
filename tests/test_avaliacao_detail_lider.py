"""Detalhe operacional (líder/gestor/admin) — apresentação e escopo."""

from __future__ import annotations

from decimal import Decimal

import pytest
from django.urls import reverse

from apps.competencies.models import CargoCompetencia, Competencia, Escala
from apps.reviews.models import Avaliacao, AvaliacaoCompetencia
from apps.reviews.services.display import (
    nota_lider_tone,
    nota_lider_trend,
)


def _vincular_competencia(cargo, *, nome: str, peso: str = '1.00') -> CargoCompetencia:
    escala = Escala.objects.create(
        nome=f'Escala {nome}',
        valor_minimo=1,
        valor_maximo=5,
    )
    competencia = Competencia.objects.create(
        nome=nome,
        tipo=Competencia.Tipo.TECNICA,
        escala=escala,
    )
    return CargoCompetencia.objects.create(
        cargo=cargo,
        competencia=competencia,
        nivel_esperado=Decimal('3.00'),
        peso=Decimal(peso),
    )


def _linha(
    avaliacao: Avaliacao,
    cc: CargoCompetencia,
    *,
    nota_autoavaliacao=None,
    nota_lider=None,
    nivel_esperado=None,
) -> AvaliacaoCompetencia:
    return AvaliacaoCompetencia.objects.create(
        avaliacao=avaliacao,
        competencia=cc.competencia,
        peso_utilizado=cc.peso,
        nivel_esperado_utilizado=nivel_esperado or cc.nivel_esperado,
        nota_autoavaliacao=nota_autoavaliacao,
        nota_lider=nota_lider,
    )


def test_nota_lider_tone_compara_com_nivel_esperado():
    assert nota_lider_tone(Decimal('3'), Decimal('3')) == 'success'
    assert nota_lider_tone(Decimal('4'), Decimal('3')) == 'success'
    assert nota_lider_tone(Decimal('2'), Decimal('3')) == 'warning'
    assert nota_lider_tone(None, Decimal('3')) == 'neutral'


def test_nota_lider_trend_compara_com_autoavaliacao():
    assert nota_lider_trend(Decimal('3'), Decimal('2')) == 'up'
    assert nota_lider_trend(Decimal('3'), Decimal('3')) == 'equal'
    assert nota_lider_trend(Decimal('2'), Decimal('3')) == 'down'
    assert nota_lider_trend(Decimal('3'), None) is None


@pytest.mark.django_db
def test_lider_detail_competencias_usa_tabela_compartilhada(
    client,
    lider,
    avaliacao,
    cargo_colab,
):
    cc = _vincular_competencia(
        cargo_colab,
        nome='Comunicação Assertiva',
        peso='2.00',
    )
    _linha(
        avaliacao,
        cc,
        nota_autoavaliacao=Decimal('2.00'),
        nota_lider=Decimal('3.00'),
        nivel_esperado=Decimal('3.00'),
    )

    client.force_login(lider)
    resp = client.get(reverse('reviews:detail', kwargs={'pk': avaliacao.pk}))
    body = resp.content.decode()
    template_names = [t.name for t in resp.templates if t.name]
    assert 'reviews/partials/avaliacao_detail_competencias_table.html' in template_names
    assert 'Comunicação Assertiva' in body
    assert 'bg-emerald-100' not in body


@pytest.mark.django_db
def test_admin_detail_usa_template_lider(client, admin, avaliacao):
    client.force_login(admin)
    resp = client.get(reverse('reviews:detail', kwargs={'pk': avaliacao.pk}))
    assert resp.status_code == 200
    template_names = [t.name for t in resp.templates if t.name]
    assert 'reviews/avaliacao_detail_lider.html' in template_names


@pytest.mark.django_db
def test_lider_detail_exibe_nome_colaborador(client, lider, avaliacao, colaborador):
    client.force_login(lider)
    resp = client.get(reverse('reviews:detail', kwargs={'pk': avaliacao.pk}))
    body = resp.content.decode()
    assert colaborador.nome in body or colaborador.email in body
