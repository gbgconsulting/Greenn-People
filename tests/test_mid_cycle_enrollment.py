"""T033: mid-cycle enrollment — cria / não duplica / no-op sem ciclo."""

from __future__ import annotations

from datetime import date, timedelta

import pytest
from django.utils import timezone

from apps.accounts.models import CustomUser
from apps.cycles.models import Ciclo
from apps.cycles.services.cycle import close_cycle
from apps.reviews.models import Avaliacao
from apps.reviews.services.enrollment import ensure_avaliacao_for_user

DEFAULT_PASSWORD = 'TestPass123!'


@pytest.mark.django_db
def test_ensure_cria_avaliacao_para_ativo_com_ciclo_aberto(
    ciclo_aberto, lider, area, cargo_colab,
):
    """Ciclo aberto + novo ativo → 1 Avaliação em input_metas."""
    novo = CustomUser.objects.create_user(
        email='midcycle@test.greenn.com.br',
        password=DEFAULT_PASSWORD,
        nome='Admitido Mid-Cycle',
        cargo=cargo_colab,
        area=area,
        line_manager=lider,
        email_confirmado_em=timezone.now(),
    )
    assert not Avaliacao.objects.filter(ciclo=ciclo_aberto, usuario=novo).exists()

    result = ensure_avaliacao_for_user(novo)

    assert result is not None
    assert result.ciclo_id == ciclo_aberto.pk
    assert result.usuario_id == novo.pk
    assert result.etapa == Avaliacao.Etapa.INPUT_METAS
    assert Avaliacao.objects.filter(ciclo=ciclo_aberto, usuario=novo).count() == 1


@pytest.mark.django_db
def test_ensure_nao_duplica_avaliacao(ciclo_aberto, lider, area, cargo_colab):
    """Segundo ensure sem mudança de elegibilidade → ainda 1 Avaliação."""
    novo = CustomUser.objects.create_user(
        email='dedupe@test.greenn.com.br',
        password=DEFAULT_PASSWORD,
        nome='Dedupe Mid-Cycle',
        cargo=cargo_colab,
        area=area,
        line_manager=lider,
        email_confirmado_em=timezone.now(),
    )

    first = ensure_avaliacao_for_user(novo)
    second = ensure_avaliacao_for_user(novo)
    third = ensure_avaliacao_for_user(novo, ciclo=ciclo_aberto)

    assert first is not None
    assert second.pk == first.pk
    assert third.pk == first.pk
    assert Avaliacao.objects.filter(ciclo=ciclo_aberto, usuario=novo).count() == 1


@pytest.mark.django_db
def test_ensure_noop_sem_ciclo_aberto(colaborador):
    """Sem ciclo aberto → None e nenhuma Avaliação nova."""
    for aberto in Ciclo.objects.filter(status=Ciclo.Status.ABERTO):
        close_cycle(aberto)

    before = Avaliacao.objects.count()
    result = ensure_avaliacao_for_user(colaborador)

    assert result is None
    assert Avaliacao.objects.count() == before


@pytest.mark.django_db
def test_ensure_noop_usuario_inativo(ciclo_aberto, lider, area, cargo_colab):
    """Usuário inativo → None (não cria Avaliação)."""
    inativo = CustomUser.objects.create_user(
        email='inativo@test.greenn.com.br',
        password=DEFAULT_PASSWORD,
        nome='Inativo Mid-Cycle',
        cargo=cargo_colab,
        area=area,
        line_manager=lider,
        is_active=False,
        email_confirmado_em=timezone.now(),
    )

    result = ensure_avaliacao_for_user(inativo)

    assert result is None
    assert not Avaliacao.objects.filter(ciclo=ciclo_aberto, usuario=inativo).exists()


@pytest.mark.django_db
def test_ensure_noop_ciclo_encerrado_passado(colaborador):
    """Ciclo explícito encerrado → None (somente aberto é elegível)."""
    for aberto in Ciclo.objects.filter(status=Ciclo.Status.ABERTO):
        close_cycle(aberto)

    today = date.today()
    encerrado = Ciclo.objects.create(
        nome='Ciclo Encerrado Mid-Cycle',
        data_inicio=today - timedelta(days=90),
        data_fim=today - timedelta(days=1),
        status=Ciclo.Status.ENCERRADO,
    )
    before = Avaliacao.objects.filter(ciclo=encerrado, usuario=colaborador).count()

    result = ensure_avaliacao_for_user(colaborador, ciclo=encerrado)

    assert result is None
    assert (
        Avaliacao.objects.filter(ciclo=encerrado, usuario=colaborador).count()
        == before
    )
