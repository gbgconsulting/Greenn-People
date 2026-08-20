"""Fixtures reutilizáveis para a suíte pytest-django."""

from __future__ import annotations

from datetime import date, timedelta

import pytest
from django.utils import timezone

from apps.accounts.models import CustomUser
from apps.cycles.models import Ciclo
from apps.cycles.services.cycle import close_cycle, open_cycle
from apps.goals.models import Meta, ObjetivoEstrategico
from apps.organization.models import Area, Cargo
from apps.reviews.models import Avaliacao

DEFAULT_PASSWORD = 'TestPass123!'

# Admissão padrão das fixtures: elegível sob o corte de ``ciclo_aberto``.
FIXTURE_DATA_ENTRADA = date(2020, 1, 15)


@pytest.fixture
def area(db) -> Area:
    return Area.objects.create(nome='Área Teste')


@pytest.fixture
def cargo_lider(db) -> Cargo:
    return Cargo.objects.create(nome='Líder Teste', nivel=2)


@pytest.fixture
def cargo_colab(db) -> Cargo:
    return Cargo.objects.create(nome='Analista Teste', nivel=1)


@pytest.fixture
def admin(db) -> CustomUser:
    return CustomUser.objects.create_user(
        email='admin@test.greenn.com.br',
        password=DEFAULT_PASSWORD,
        nome='Admin Teste',
        is_admin=True,
        is_staff=True,
        data_entrada=FIXTURE_DATA_ENTRADA,
        email_confirmado_em=timezone.now(),
    )


@pytest.fixture
def lider(db, admin, area, cargo_lider) -> CustomUser:
    return CustomUser.objects.create_user(
        email='lider@test.greenn.com.br',
        password=DEFAULT_PASSWORD,
        nome='Líder Teste',
        cargo=cargo_lider,
        area=area,
        line_manager=admin,
        data_entrada=FIXTURE_DATA_ENTRADA,
        email_confirmado_em=timezone.now(),
    )


@pytest.fixture
def colaborador(db, lider, area, cargo_colab) -> CustomUser:
    return CustomUser.objects.create_user(
        email='colab@test.greenn.com.br',
        password=DEFAULT_PASSWORD,
        nome='Colaborador Teste',
        cargo=cargo_colab,
        area=area,
        line_manager=lider,
        data_entrada=FIXTURE_DATA_ENTRADA,
        email_confirmado_em=timezone.now(),
    )


@pytest.fixture
def ciclo_aberto(db, colaborador) -> Ciclo:
    """Ciclo aberto com Avaliações para elegíveis ativos (via open_cycle).

    Depende de ``colaborador`` para garantir a hierarquia admin→líder→colab
    antes de abrir o ciclo. Define ``admitidos_ate`` e preenche ``data_entrada``
    ausente nos ativos para o predicado 015 não deixar a suite sem Avaliações.
    """
    for aberto in Ciclo.objects.filter(status=Ciclo.Status.ABERTO):
        close_cycle(aberto)

    today = date.today()
    CustomUser.objects.filter(is_active=True, data_entrada__isnull=True).update(
        data_entrada=FIXTURE_DATA_ENTRADA,
    )
    ciclo = Ciclo.objects.create(
        nome='Ciclo Teste Aberto',
        data_inicio=today - timedelta(days=30),
        data_fim=today + timedelta(days=30),
        admitidos_ate=today,
        status=Ciclo.Status.ENCERRADO,
    )
    open_cycle(ciclo)
    ciclo.refresh_from_db()
    return ciclo


@pytest.fixture
def avaliacao(ciclo_aberto, colaborador) -> Avaliacao:
    return Avaliacao.objects.get(ciclo=ciclo_aberto, usuario=colaborador)


@pytest.fixture
def objetivo(ciclo_aberto) -> ObjetivoEstrategico:
    return ObjetivoEstrategico.objects.create(
        descricao='Objetivo estratégico de teste',
        ciclo=ciclo_aberto,
    )


@pytest.fixture
def meta(colaborador, objetivo) -> Meta:
    return Meta.objects.create(
        usuario=colaborador,
        objetivo_estrategico=objetivo,
        descricao='Meta de teste',
    )


@pytest.fixture
def metas(colaborador, objetivo) -> list[Meta]:
    """Duas metas no mesmo colaborador/ciclo (cenários de aprovação parcial)."""
    return [
        Meta.objects.create(
            usuario=colaborador,
            objetivo_estrategico=objetivo,
            descricao='Meta A de teste',
        ),
        Meta.objects.create(
            usuario=colaborador,
            objetivo_estrategico=objetivo,
            descricao='Meta B de teste',
        ),
    ]
