"""Detalhe «Minha Avaliação» (colaborador) — apresentação e template."""

from __future__ import annotations

from decimal import Decimal

import pytest
from django.urls import reverse

from apps.competencies.models import CargoCompetencia, Competencia, Escala
from apps.reviews.models import Avaliacao, AvaliacaoCompetencia
from apps.reviews.services.display import format_nivel_display


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
) -> AvaliacaoCompetencia:
    return AvaliacaoCompetencia.objects.create(
        avaliacao=avaliacao,
        competencia=cc.competencia,
        peso_utilizado=cc.peso,
        nivel_esperado_utilizado=cc.nivel_esperado,
        nota_autoavaliacao=nota_autoavaliacao,
        nota_lider=nota_lider,
    )


def test_format_nivel_display_compacto():
    assert format_nivel_display(Decimal('3.00')) == '3'
    assert format_nivel_display(Decimal('4.50')) == '4.5'
    assert format_nivel_display(None) == '—'


@pytest.mark.django_db
def test_colaborador_detail_usa_template_dedicado(client, colaborador, avaliacao):
    avaliacao.nota_final_lider = Decimal('0.8300')
    avaliacao.nota_final_autoavaliacao = Decimal('0.7100')
    avaliacao.autoavaliacao_enviada = True
    avaliacao.save(
        update_fields=[
            'nota_final_lider',
            'nota_final_autoavaliacao',
            'autoavaliacao_enviada',
        ],
    )
    client.force_login(colaborador)
    resp = client.get(reverse('reviews:detail', kwargs={'pk': avaliacao.pk}))
    assert resp.status_code == 200
    body = resp.content.decode()
    assert 'Minha Avaliação' in body
    assert 'Linha do Tempo do Ciclo' in body
    assert '83%' in body
    assert '71%' in body
    template_names = [t.name for t in resp.templates if t.name]
    assert 'reviews/avaliacao_detail_colaborador.html' in template_names
    assert 'components/stage_stepper.html' in template_names
    assert 'components/card.html' in template_names


@pytest.mark.django_db
def test_lider_detail_mantem_template_operacional(client, lider, avaliacao):
    client.force_login(lider)
    resp = client.get(reverse('reviews:detail', kwargs={'pk': avaliacao.pk}))
    assert resp.status_code == 200
    template_names = [t.name for t in resp.templates if t.name]
    assert 'reviews/avaliacao_detail.html' in template_names
    assert 'reviews/avaliacao_detail_colaborador.html' not in template_names


@pytest.mark.django_db
def test_colaborador_detail_competencias_exibe_peso_numerico(
    client,
    colaborador,
    avaliacao,
    cargo_colab,
):
    cc = _vincular_competencia(cargo_colab, nome='Comunicação Assertiva', peso='2.00')
    _linha(
        avaliacao,
        cc,
        nota_autoavaliacao=Decimal('2.00'),
        nota_lider=Decimal('3.00'),
    )
    client.force_login(colaborador)
    resp = client.get(reverse('reviews:detail', kwargs={'pk': avaliacao.pk}))
    body = resp.content.decode()
    assert 'Comunicação Assertiva' in body
    assert 'Competências' in body
    assert '>2<' in body.replace(' ', '')
    assert '>3<' in body.replace(' ', '')


@pytest.mark.django_db
def test_colaborador_detail_ciclo_encerrado_stepper_verde_sem_msg_ciclo(
    client,
    colaborador,
    db,
):
    from datetime import date, timedelta

    from apps.cycles.models import Ciclo

    today = date.today()
    ciclo = Ciclo.objects.create(
        nome='Ciclo avaliação_lider',
        data_inicio=today - timedelta(days=400),
        data_fim=today - timedelta(days=200),
        status=Ciclo.Status.ENCERRADO,
        admitidos_ate=today - timedelta(days=400),
    )
    avaliacao = Avaliacao.objects.create(
        ciclo=ciclo,
        usuario=colaborador,
        etapa=Avaliacao.Etapa.FEEDBACK,
    )
    client.force_login(colaborador)
    resp = client.get(reverse('reviews:detail', kwargs={'pk': avaliacao.pk}))
    body = resp.content.decode()
    assert resp.status_code == 200
    assert 'Ciclo avaliação_lider' in body
    assert 'Sem ciclo em andamento' not in body
    assert 'Não há ciclo de desempenho aberto' not in body
    assert 'data-stage-state="concluida"' in body
    assert 'data-stage-state="bloqueada"' not in body


@pytest.mark.django_db
def test_colaborador_detail_ciclo_aberto_marca_etapa_atual(
    client,
    colaborador,
    avaliacao,
):
    avaliacao.etapa = Avaliacao.Etapa.FEEDBACK
    avaliacao.save(update_fields=['etapa', 'updated_at'])
    client.force_login(colaborador)
    resp = client.get(reverse('reviews:detail', kwargs={'pk': avaliacao.pk}))
    body = resp.content.decode()
    assert 'data-stage-key="feedback"' in body
    assert 'data-stage-state="atual"' in body
    assert 'data-stage-state="concluida"' in body
    assert 'Sem ciclo em andamento' not in body
