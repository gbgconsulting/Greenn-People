"""Ordem autoavaliação → avaliação do líder (backend)."""

from __future__ import annotations

from decimal import Decimal

import pytest
from django.contrib.messages import get_messages
from django.urls import reverse

from apps.competencies.models import CargoCompetencia, Competencia, Escala
from apps.cycles.services.stage import can_advance
from apps.reviews.forms import leader_assessment_permitted
from apps.reviews.models import Avaliacao, AvaliacaoCompetencia
from apps.reviews.services.evaluation import (
    MSG_AUTOAVALIACAO_INCOMPLETA,
    self_assessment_complete,
)


def _set_etapa(avaliacao: Avaliacao, etapa: str) -> Avaliacao:
    avaliacao.etapa = etapa
    avaliacao.save(update_fields=['etapa', 'updated_at'])
    return avaliacao


def _vincular_competencia(cargo) -> CargoCompetencia:
    escala = Escala.objects.create(
        nome='Escala Ordem Avaliação',
        valor_minimo=1,
        valor_maximo=5,
    )
    competencia = Competencia.objects.create(
        nome='Competência Ordem Avaliação',
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
def test_self_assessment_complete_exige_todas_as_linhas(avaliacao, cargo_colab):
    cc = _vincular_competencia(cargo_colab)
    assert self_assessment_complete(avaliacao) is False

    _linha(avaliacao, cc, nota_autoavaliacao=Decimal('4.00'))
    assert self_assessment_complete(avaliacao) is True


@pytest.mark.django_db
def test_leader_assessment_permitted_bloqueia_sem_auto(avaliacao, cargo_colab):
    _set_etapa(avaliacao, Avaliacao.Etapa.AVALIACAO)
    cc = _vincular_competencia(cargo_colab)
    _linha(avaliacao, cc, nota_lider=Decimal('4.00'))

    assert leader_assessment_permitted(avaliacao) is False


@pytest.mark.django_db
def test_leader_assessment_permitted_libera_com_auto_completa(
    avaliacao,
    cargo_colab,
):
    _set_etapa(avaliacao, Avaliacao.Etapa.AVALIACAO)
    cc = _vincular_competencia(cargo_colab)
    _linha(avaliacao, cc, nota_autoavaliacao=Decimal('3.00'))

    assert leader_assessment_permitted(avaliacao) is True


@pytest.mark.django_db
def test_leader_assessment_get_bloqueado_sem_auto(
    client,
    lider,
    avaliacao,
    cargo_colab,
):
    _set_etapa(avaliacao, Avaliacao.Etapa.AVALIACAO)
    cc = _vincular_competencia(cargo_colab)
    _linha(avaliacao, cc)

    client.force_login(lider)
    url = reverse('reviews:leader_assessment', kwargs={'pk': avaliacao.pk})
    resp = client.get(url)

    assert resp.status_code == 302
    assert resp.url == reverse('dashboard:personal')
    messages = [m.message for m in get_messages(resp.wsgi_request)]
    assert any(MSG_AUTOAVALIACAO_INCOMPLETA in m for m in messages)


@pytest.mark.django_db
def test_leader_assessment_get_liberado_com_auto_completa(
    client,
    lider,
    avaliacao,
    cargo_colab,
):
    _set_etapa(avaliacao, Avaliacao.Etapa.AVALIACAO)
    cc = _vincular_competencia(cargo_colab)
    linha = _linha(avaliacao, cc, nota_autoavaliacao=Decimal('3.00'))

    client.force_login(lider)
    url = reverse('reviews:leader_assessment', kwargs={'pk': avaliacao.pk})
    resp = client.get(url)

    assert resp.status_code == 200
    assert linha.competencia.nome.encode() in resp.content


@pytest.mark.django_db
def test_can_advance_avaliacao_exige_auto_completa(avaliacao, lider, cargo_colab):
    _set_etapa(avaliacao, Avaliacao.Etapa.AVALIACAO)
    cc = _vincular_competencia(cargo_colab)
    _linha(avaliacao, cc, nota_lider=Decimal('4.00'))
    avaliacao.nota_final_lider = Decimal('0.5000')
    avaliacao.save(update_fields=['nota_final_lider', 'updated_at'])

    ok, motivo = can_advance(avaliacao)
    assert ok is False
    assert 'autoavaliação' in motivo.lower()
