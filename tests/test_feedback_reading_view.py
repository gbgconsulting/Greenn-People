"""Testes da tela de leitura/assinatura de feedbacks."""

from __future__ import annotations

from decimal import Decimal

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.competencies.models import CargoCompetencia, Competencia, Escala
from apps.goals.models import Meta
from apps.reviews.models import AvaliacaoCompetencia, Feedback
from apps.reviews.services.feedback_display import build_feedback_resumo

from .conftest import DEFAULT_PASSWORD


@pytest.mark.django_db
def test_build_feedback_resumo_metas_e_competencias(
    avaliacao,
    colaborador,
    meta,
    lider,
):
    escala = Escala.objects.create(
        nome='Escala 1-5',
        valor_minimo=1,
        valor_maximo=5,
        rotulos_por_nivel={'4': 'Supera Expectativas'},
    )
    competencia = Competencia.objects.create(
        nome='Comp teste',
        tipo='tecnica',
        escala=escala,
    )
    CargoCompetencia.objects.create(
        cargo=colaborador.cargo,
        competencia=competencia,
        peso=Decimal('1'),
        nivel_esperado=Decimal('3'),
    )
    AvaliacaoCompetencia.objects.create(
        avaliacao=avaliacao,
        competencia=competencia,
        nota_lider=Decimal('4'),
        peso_utilizado=Decimal('1'),
        nivel_esperado_utilizado=Decimal('3'),
    )
    avaliacao.nota_final_lider = Decimal('0.75')
    avaliacao.save(update_fields=['nota_final_lider', 'updated_at'])

    meta.status = Meta.Status.APROVADA
    meta.progresso = Decimal('95')
    meta.save(update_fields=['status', 'progresso', 'updated_at'])

    resumo = build_feedback_resumo(avaliacao)

    assert resumo['metas_atingimento'] == 95
    assert resumo['competencia_valor'] == Decimal('4.0')
    assert resumo['competencia_escala_max'] == 5
    assert resumo['classificacao'] == 'Supera Expectativas'


@pytest.mark.django_db
def test_feedback_list_colaborador_renderiza_ciencia(
    client,
    avaliacao,
    colaborador,
    lider,
):
    avaliacao.etapa = avaliacao.Etapa.FEEDBACK
    avaliacao.save(update_fields=['etapa', 'updated_at'])
    feedback = Feedback.objects.create(
        avaliacao=avaliacao,
        autor=lider,
        tipo=Feedback.Tipo.LIDER,
        conteudo='Excelente desempenho no ciclo.',
        ciente_em=None,
    )

    client.force_login(colaborador)
    url = reverse('reviews:feedback_list', kwargs={'pk': avaliacao.pk})
    resp = client.get(url)

    assert resp.status_code == 200
    html = resp.content.decode()
    assert 'Leitura e Assinatura de Feedbacks' in html
    assert 'Dar ciência' in html
    assert 'Li o feedback do meu gestor' in html
    assert 'Excelente desempenho no ciclo.' in html
    assert f'action="{reverse("reviews:feedback_acknowledge", kwargs={"pk": feedback.pk})}"' in html


@pytest.mark.django_db
def test_feedback_acknowledge_exige_declaracao(
    client,
    avaliacao,
    colaborador,
    lider,
):
    feedback = Feedback.objects.create(
        avaliacao=avaliacao,
        autor=lider,
        tipo=Feedback.Tipo.LIDER,
        conteudo='Feedback pendente.',
        ciente_em=None,
    )

    client.force_login(colaborador)
    url = reverse('reviews:feedback_acknowledge', kwargs={'pk': feedback.pk})
    resp = client.post(url, follow=True)

    assert resp.status_code == 200
    feedback.refresh_from_db()
    assert feedback.ciente_em is None

    resp_ok = client.post(
        url,
        {'declaro_ciencia': 'on'},
        follow=True,
    )
    assert resp_ok.status_code == 200
    feedback.refresh_from_db()
    assert feedback.ciente_em is not None


@pytest.mark.django_db
def test_feedback_acknowledge_outro_usuario_404(
    client,
    avaliacao,
    lider,
    admin,
):
    feedback = Feedback.objects.create(
        avaliacao=avaliacao,
        autor=lider,
        tipo=Feedback.Tipo.LIDER,
        conteudo='Feedback privado.',
        ciente_em=None,
    )

    client.force_login(admin)
    url = reverse('reviews:feedback_acknowledge', kwargs={'pk': feedback.pk})
    resp = client.post(url, {'declaro_ciencia': 'on'})

    assert resp.status_code == 404
