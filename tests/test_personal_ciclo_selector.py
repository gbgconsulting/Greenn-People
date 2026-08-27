"""Meu painel: seletor de ciclo só com participação do usuário.

Contrato: default = aberto se participa; ``?ciclo=`` explícito; sem fallback
silencioso para encerrado; sem listar ciclo sem ``Avaliacao`` do usuário;
sem ``visao=historico``.
"""

from __future__ import annotations

from datetime import date, timedelta

import pytest
from django.test import Client
from django.urls import reverse

from apps.cycles.models import Ciclo
from apps.cycles.services.cycle import close_cycle
from apps.reviews.models import Avaliacao


def _personal_url() -> str:
    return reverse('dashboard:personal')


def _login(user) -> Client:
    client = Client()
    client.force_login(user)
    return client


def _ciclo_encerrado(*, nome: str, data_inicio: date) -> Ciclo:
    return Ciclo.objects.create(
        nome=nome,
        data_inicio=data_inicio,
        data_fim=data_inicio + timedelta(days=90),
        status=Ciclo.Status.ENCERRADO,
    )


@pytest.mark.django_db
def test_personal_default_abre_ciclo_aberto_quando_participa(
    colaborador,
    ciclo_aberto,
    avaliacao,
):
    """Sem ``?ciclo=``: dados do aberto em que o colaborador participa."""
    assert avaliacao.ciclo_id == ciclo_aberto.pk
    client = _login(colaborador)
    resp = client.get(_personal_url())

    assert resp.status_code == 200
    assert resp.context['ciclo_aberto'].pk == ciclo_aberto.pk
    assert resp.context['ciclo_selecionado'].pk == ciclo_aberto.pk
    assert resp.context['avaliacao'].pk == avaliacao.pk
    html = resp.content.decode()
    assert 'data-component="ciclo-selector"' in html or 'name="ciclo"' in html
    assert 'visao=historico' not in html


@pytest.mark.django_db
def test_personal_sem_aberto_nao_defaulta_encerrado(
    colaborador,
    ciclo_aberto,
    avaliacao,
):
    """Sem ciclo aberto: empty operacional — não escolhe encerrado sozinho."""
    arquivo = _ciclo_encerrado(
        nome='PESSOAL-ARQ-1',
        data_inicio=date(2024, 1, 1),
    )
    Avaliacao.objects.create(
        ciclo=arquivo,
        usuario=colaborador,
        etapa=Avaliacao.Etapa.FEEDBACK,
        concluida=True,
    )
    close_cycle(ciclo_aberto)

    client = _login(colaborador)
    resp = client.get(_personal_url())

    assert resp.status_code == 200
    assert resp.context['ciclo_aberto'] is None
    assert resp.context['ciclo_selecionado'] is None
    assert resp.context['avaliacao'] is None
    opts = resp.context['grouped_ciclo_options']
    assert opts['operacional'] == []
    assert arquivo.pk in {c.pk for c in opts['arquivo']}


@pytest.mark.django_db
def test_personal_ciclo_query_honra_participacao(
    colaborador,
    ciclo_aberto,
    avaliacao,
):
    """``?ciclo=`` de ciclo em que participa carrega aquela avaliação."""
    arquivo = _ciclo_encerrado(
        nome='PESSOAL-ARQ-2',
        data_inicio=date(2023, 6, 1),
    )
    av_arquivo = Avaliacao.objects.create(
        ciclo=arquivo,
        usuario=colaborador,
        etapa=Avaliacao.Etapa.FEEDBACK,
        concluida=True,
    )

    client = _login(colaborador)
    resp = client.get(_personal_url(), {'ciclo': arquivo.pk})

    assert resp.status_code == 200
    assert resp.context['ciclo_aberto'].pk == ciclo_aberto.pk
    assert resp.context['ciclo_selecionado'].pk == arquivo.pk
    assert resp.context['avaliacao'].pk == av_arquivo.pk
    assert resp.context['avaliacao'].pk != avaliacao.pk
    # Arquivo = leitura (próximo passo não empurra etapa do aberto).
    next_step = resp.context['next_step']
    assert next_step.title == 'Ciclo concluído para você'


@pytest.mark.django_db
def test_personal_ciclo_alheio_nao_lista_nem_resolve(
    colaborador,
    lider,
    ciclo_aberto,
    avaliacao,
):
    """Ciclo sem avaliação do usuário: fora do seletor; ``?ciclo=`` ignora."""
    from decimal import Decimal

    from apps.competencies.models import Competencia
    from apps.reviews.models import AvaliacaoCompetencia

    alheio = _ciclo_encerrado(
        nome='PESSOAL-ALHEIO',
        data_inicio=date(2022, 3, 1),
    )
    av_lider = Avaliacao.objects.create(
        ciclo=alheio,
        usuario=lider,
        etapa=Avaliacao.Etapa.FEEDBACK,
        concluida=True,
        nota_final_lider=Decimal('9.87'),
    )
    # Nota só do líder — nunca pode aparecer no painel do colaborador.
    competencia = Competencia.objects.first()
    if competencia is not None:
        AvaliacaoCompetencia.objects.create(
            avaliacao=av_lider,
            competencia=competencia,
            nota_lider=Decimal('9.87'),
            peso_utilizado=Decimal('1'),
            nivel_esperado_utilizado=Decimal('3'),
        )

    client = _login(colaborador)
    resp = client.get(_personal_url(), {'ciclo': alheio.pk})

    assert resp.status_code == 200
    assert resp.context['ciclo_selecionado'].pk == ciclo_aberto.pk
    assert resp.context['avaliacao'].pk == avaliacao.pk
    assert resp.context['avaliacao'].usuario_id == colaborador.pk
    opts = resp.context['grouped_ciclo_options']
    assert alheio.pk not in {c.pk for c in opts['arquivo']}
    assert alheio.pk not in {c.pk for c in opts['operacional']}
    html = resp.content.decode()
    assert '9.87' not in html
    assert 'PESSOAL-ALHEIO' not in html


@pytest.mark.django_db
def test_personal_avaliacao_no_contexto_sempre_do_request_user(
    colaborador,
    ciclo_aberto,
    avaliacao,
):
    """Invariante: ``avaliacao`` do Meu painel pertence ao usuário autenticado."""
    client = _login(colaborador)
    resp = client.get(_personal_url())
    assert resp.status_code == 200
    av = resp.context['avaliacao']
    assert av is not None
    assert av.usuario_id == colaborador.pk
    assert av.pk == avaliacao.pk


@pytest.mark.django_db
def test_personal_seletor_so_ciclos_com_participacao(
    colaborador,
    ciclo_aberto,
    avaliacao,
):
    """Arquivo do seletor = só encerrados com Avaliacao do colaborador."""
    comigo = _ciclo_encerrado(
        nome='PESSOAL-COMIGO',
        data_inicio=date(2021, 1, 1),
    )
    Avaliacao.objects.create(
        ciclo=comigo,
        usuario=colaborador,
        etapa=Avaliacao.Etapa.AVALIACAO,
        concluida=True,
    )
    sem_mim = _ciclo_encerrado(
        nome='PESSOAL-SEM-MIM',
        data_inicio=date(2021, 6, 1),
    )

    client = _login(colaborador)
    resp = client.get(_personal_url())

    assert resp.status_code == 200
    opts = resp.context['grouped_ciclo_options']
    arquivo_pks = {c.pk for c in opts['arquivo']}
    assert comigo.pk in arquivo_pks
    assert sem_mim.pk not in arquivo_pks
    assert ciclo_aberto.pk in {c.pk for c in opts['operacional']}
