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
    MSG_AUTOAVALIACAO_JA_ENVIADA,
    self_assessment_complete,
    self_assessment_submitted,
    submit_self_assessment,
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


def _enviar_autoavaliacao(avaliacao: Avaliacao) -> Avaliacao:
    avaliacao.autoavaliacao_enviada = True
    avaliacao.save(update_fields=['autoavaliacao_enviada', 'updated_at'])
    return avaliacao


@pytest.mark.django_db
def test_self_assessment_submitted_exige_flag(avaliacao, cargo_colab):
    cc = _vincular_competencia(cargo_colab)
    _linha(avaliacao, cc, nota_autoavaliacao=Decimal('4.00'))
    assert self_assessment_complete(avaliacao) is True
    assert self_assessment_submitted(avaliacao) is False
    _enviar_autoavaliacao(avaliacao)
    assert self_assessment_submitted(avaliacao) is True


@pytest.mark.django_db
def test_self_assessment_complete_exige_todas_as_linhas(avaliacao, cargo_colab):
    cc = _vincular_competencia(cargo_colab)
    assert self_assessment_complete(avaliacao) is False

    _linha(avaliacao, cc, nota_autoavaliacao=Decimal('4.00'))
    assert self_assessment_complete(avaliacao) is True


@pytest.mark.django_db
def test_leader_assessment_permitted_bloqueia_sem_envio(avaliacao, cargo_colab):
    _set_etapa(avaliacao, Avaliacao.Etapa.AVALIACAO)
    cc = _vincular_competencia(cargo_colab)
    _linha(avaliacao, cc, nota_autoavaliacao=Decimal('3.00'))

    assert leader_assessment_permitted(avaliacao) is False


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
    _enviar_autoavaliacao(avaliacao)

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
    _enviar_autoavaliacao(avaliacao)

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


@pytest.mark.django_db
def test_self_assessment_post_enviar_trava_edicao(
    client,
    colaborador,
    avaliacao,
    cargo_colab,
):
    _set_etapa(avaliacao, Avaliacao.Etapa.AVALIACAO)
    cc = _vincular_competencia(cargo_colab)
    linha = _linha(avaliacao, cc)

    client.force_login(colaborador)
    url = reverse('reviews:self_assessment', kwargs={'pk': avaliacao.pk})

    resp = client.post(
        url,
        {
            'form-TOTAL_FORMS': '1',
            'form-INITIAL_FORMS': '1',
            'form-MIN_NUM_FORMS': '0',
            'form-MAX_NUM_FORMS': '1000',
            f'form-0-id': str(linha.pk),
            f'form-0-nota_autoavaliacao': '4.00',
            'action': 'submit',
        },
    )
    assert resp.status_code == 302
    avaliacao.refresh_from_db()
    assert avaliacao.autoavaliacao_enviada is True
    assert avaliacao.nota_final_autoavaliacao is not None

    resp_post = client.post(
        url,
        {
            'form-TOTAL_FORMS': '1',
            'form-INITIAL_FORMS': '1',
            'form-MIN_NUM_FORMS': '0',
            'form-MAX_NUM_FORMS': '1000',
            f'form-0-id': str(linha.pk),
            f'form-0-nota_autoavaliacao': '5.00',
            'action': 'save',
        },
    )
    assert resp_post.status_code == 302
    assert resp_post.url == reverse('dashboard:personal')
    linha.refresh_from_db()
    assert linha.nota_autoavaliacao == Decimal('4.00')


@pytest.mark.django_db
def test_self_assessment_get_readonly_apos_envio(
    client,
    colaborador,
    avaliacao,
    cargo_colab,
):
    _set_etapa(avaliacao, Avaliacao.Etapa.AVALIACAO)
    cc = _vincular_competencia(cargo_colab)
    _linha(avaliacao, cc, nota_autoavaliacao=Decimal('3.00'))
    _enviar_autoavaliacao(avaliacao)

    client.force_login(colaborador)
    url = reverse('reviews:self_assessment', kwargs={'pk': avaliacao.pk})
    resp = client.get(url)

    assert resp.status_code == 200
    assert b'Enviar autoavalia' not in resp.content
    assert b'autoavalia\xc3\xa7\xc3\xa3o foi enviada' in resp.content.lower()


@pytest.mark.django_db
def test_submit_self_assessment_rejeita_incompleta(avaliacao, cargo_colab):
    from django.core.exceptions import ValidationError

    _set_etapa(avaliacao, Avaliacao.Etapa.AVALIACAO)
    cc = _vincular_competencia(cargo_colab)
    _linha(avaliacao, cc)

    with pytest.raises(ValidationError, match='Preencha a nota'):
        submit_self_assessment(avaliacao)
