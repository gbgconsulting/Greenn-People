"""Visibilidade de nota_atual: somente nota do líder (FR-005)."""

from __future__ import annotations

from decimal import Decimal

import pytest
from django.urls import reverse

from apps.competencies.models import CargoCompetencia, Competencia, Escala
from apps.reviews.models import Avaliacao, AvaliacaoCompetencia
from apps.reviews.services.evaluation import (
    NOTA_ORIGEM_LIDER,
    build_fr005_context,
    nota_atual_competencia,
    resolve_nota_atual,
)


def _vincular_competencia(cargo) -> CargoCompetencia:
    escala = Escala.objects.create(
        nome='Escala Visibilidade Nota',
        valor_minimo=1,
        valor_maximo=5,
    )
    competencia = Competencia.objects.create(
        nome='Competência Visibilidade Nota',
        tipo=Competencia.Tipo.TECNICA,
        escala=escala,
    )
    return CargoCompetencia.objects.create(
        cargo=cargo,
        competencia=competencia,
        nivel_esperado=Decimal('3.00'),
        peso=Decimal('1.00'),
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


@pytest.mark.django_db
def test_resolve_nota_atual_ignora_autoavaliacao(avaliacao):
    avaliacao.nota_final_autoavaliacao = Decimal('0.7500')
    avaliacao.save(update_fields=['nota_final_autoavaliacao', 'updated_at'])

    nota, origem = resolve_nota_atual(avaliacao)

    assert nota is None
    assert origem == ''


@pytest.mark.django_db
def test_resolve_nota_atual_retorna_lider(avaliacao):
    avaliacao.nota_final_lider = Decimal('0.8000')
    avaliacao.nota_final_autoavaliacao = Decimal('0.5000')
    avaliacao.save(
        update_fields=[
            'nota_final_lider',
            'nota_final_autoavaliacao',
            'updated_at',
        ],
    )

    nota, origem = resolve_nota_atual(avaliacao)

    assert nota == Decimal('0.8000')
    assert origem == NOTA_ORIGEM_LIDER


@pytest.mark.django_db
def test_nota_atual_competencia_ignora_autoavaliacao(avaliacao, cargo_colab):
    cc = _vincular_competencia(cargo_colab)
    linha = _linha(avaliacao, cc, nota_autoavaliacao=Decimal('4.00'))

    assert nota_atual_competencia(linha) is None


@pytest.mark.django_db
def test_nota_atual_competencia_retorna_lider(avaliacao, cargo_colab):
    cc = _vincular_competencia(cargo_colab)
    linha = _linha(
        avaliacao,
        cc,
        nota_autoavaliacao=Decimal('3.00'),
        nota_lider=Decimal('5.00'),
    )

    assert nota_atual_competencia(linha) == Decimal('5.00')


@pytest.mark.django_db
def test_build_fr005_separa_nota_oficial_e_autoavaliacao(colaborador, avaliacao, cargo_colab):
    cc = _vincular_competencia(cargo_colab)
    _linha(avaliacao, cc, nota_autoavaliacao=Decimal('4.00'))
    avaliacao.autoavaliacao_enviada = True
    avaliacao.nota_final_autoavaliacao = Decimal('0.6000')
    avaliacao.save(
        update_fields=[
            'autoavaliacao_enviada',
            'nota_final_autoavaliacao',
            'updated_at',
        ],
    )

    ctx = build_fr005_context(colaborador)

    assert ctx['nota_atual'] is None
    assert ctx['nota_atual_origem'] == ''
    assert ctx['nota_autoavaliacao'] == Decimal('0.6000')
    assert ctx['autoavaliacao_enviada'] is True
    resumo = ctx['competencias_resumo'][0]
    assert resumo['nota_atual'] is None
    assert resumo['nota_autoavaliacao'] == Decimal('4.00')


@pytest.mark.django_db
def test_personal_dashboard_nao_exibe_auto_como_nota_atual(
    client,
    colaborador,
    avaliacao,
    cargo_colab,
):
    cc = _vincular_competencia(cargo_colab)
    _linha(avaliacao, cc, nota_autoavaliacao=Decimal('4.00'))
    avaliacao.autoavaliacao_enviada = True
    avaliacao.nota_final_autoavaliacao = Decimal('0.6000')
    avaliacao.save(
        update_fields=[
            'autoavaliacao_enviada',
            'nota_final_autoavaliacao',
            'updated_at',
        ],
    )

    client.force_login(colaborador)
    resp = client.get(reverse('dashboard:personal'))

    assert resp.status_code == 200
    html = resp.content.decode()
    assert 'Aguardando líder' in html or 'Aguardando avaliação do líder' in html
    assert 'Autoavaliação' in html
    assert resp.context['nota_atual'] is None


@pytest.mark.django_db
def test_personal_gap_chart_sem_nota_lider(client, colaborador, avaliacao, cargo_colab):
    from apps.dashboard.views import PersonalDashboardView

    cc = _vincular_competencia(cargo_colab)
    _linha(avaliacao, cc, nota_autoavaliacao=Decimal('4.00'))
    avaliacao.autoavaliacao_enviada = True
    avaliacao.nota_final_autoavaliacao = Decimal('0.6000')
    avaliacao.save(
        update_fields=[
            'autoavaliacao_enviada',
            'nota_final_autoavaliacao',
            'updated_at',
        ],
    )

    client.force_login(colaborador)
    resp = client.get(reverse('dashboard:personal'))

    chart = resp.context['chart_gaps_competencia']
    assert chart['has_data'] is False

    fr005 = build_fr005_context(colaborador)
    chart_direct = PersonalDashboardView()._chart_gaps_competencia(fr005)
    assert chart_direct['has_data'] is False
