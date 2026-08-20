"""T020 [US3]: mid-cycle enrollment com predicado 015.

Contrato: ``specs/015-cycle-admission-cutoff/contracts/eligibility-predicate-contract.md``
+ SC-003 / SC-004 — elegível cria; entrada > D / sem data → None;
snapshot (editar ``data_entrada`` após matrícula **não** remove Avaliacao);
ciclo encerrado → 0.
"""

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


def _make_user(
    *,
    email: str,
    nome: str,
    lider,
    area,
    cargo_colab,
    data_entrada: date | None,
    is_active: bool = True,
) -> CustomUser:
    return CustomUser.objects.create_user(
        email=email,
        password=DEFAULT_PASSWORD,
        nome=nome,
        cargo=cargo_colab,
        area=area,
        line_manager=lider,
        data_entrada=data_entrada,
        is_active=is_active,
        email_confirmado_em=timezone.now(),
    )


@pytest.mark.django_db
def test_ensure_cria_avaliacao_para_ativo_elegivel(
    ciclo_aberto, lider, area, cargo_colab,
):
    """SC-003: ciclo aberto + ativo com entrada ≤ D → 1 Avaliação em input_metas."""
    cutoff = ciclo_aberto.admitidos_ate
    assert cutoff is not None

    novo = _make_user(
        email='midcycle@test.greenn.com.br',
        nome='Admitido Mid-Cycle Elegível',
        lider=lider,
        area=area,
        cargo_colab=cargo_colab,
        data_entrada=cutoff,  # inclusivo
    )
    assert not Avaliacao.objects.filter(ciclo=ciclo_aberto, usuario=novo).exists()

    result = ensure_avaliacao_for_user(novo)

    assert result is not None
    assert result.ciclo_id == ciclo_aberto.pk
    assert result.usuario_id == novo.pk
    assert result.etapa == Avaliacao.Etapa.INPUT_METAS
    assert Avaliacao.objects.filter(ciclo=ciclo_aberto, usuario=novo).count() == 1


@pytest.mark.django_db
def test_ensure_noop_entrada_posterior_ao_corte(
    ciclo_aberto, lider, area, cargo_colab,
):
    """SC-003: ativo com data_entrada > D → None, 0 Avaliações."""
    cutoff = ciclo_aberto.admitidos_ate
    assert cutoff is not None

    posterior = _make_user(
        email='posterior-mid@test.greenn.com.br',
        nome='Inelegível Mid-Cycle > D',
        lider=lider,
        area=area,
        cargo_colab=cargo_colab,
        data_entrada=cutoff + timedelta(days=1),
    )

    result = ensure_avaliacao_for_user(posterior)

    assert result is None
    assert not Avaliacao.objects.filter(
        ciclo=ciclo_aberto, usuario=posterior,
    ).exists()


@pytest.mark.django_db
def test_ensure_noop_sem_data_entrada(
    ciclo_aberto, lider, area, cargo_colab,
):
    """SC-003: ativo sem data_entrada → None, 0 Avaliações."""
    sem_data = _make_user(
        email='semdata-mid@test.greenn.com.br',
        nome='Inelegível Mid-Cycle Sem Data',
        lider=lider,
        area=area,
        cargo_colab=cargo_colab,
        data_entrada=None,
    )

    result = ensure_avaliacao_for_user(sem_data)

    assert result is None
    assert not Avaliacao.objects.filter(
        ciclo=ciclo_aberto, usuario=sem_data,
    ).exists()


@pytest.mark.django_db
def test_ensure_snapshot_editar_data_entrada_nao_remove_avaliacao(
    ciclo_aberto, lider, area, cargo_colab,
):
    """SC-004: após matrícula, editar data_entrada (inclusive > D ou NULL) não remove Avaliacao."""
    cutoff = ciclo_aberto.admitidos_ate
    assert cutoff is not None

    user = _make_user(
        email='snapshot-mid@test.greenn.com.br',
        nome='Snapshot Mid-Cycle',
        lider=lider,
        area=area,
        cargo_colab=cargo_colab,
        data_entrada=cutoff - timedelta(days=5),
    )

    created = ensure_avaliacao_for_user(user)
    assert created is not None
    pk = created.pk
    etapa = created.etapa

    user.data_entrada = cutoff + timedelta(days=30)
    user.save(update_fields=['data_entrada'])
    after_posterior = ensure_avaliacao_for_user(user)

    assert after_posterior is not None
    assert after_posterior.pk == pk
    assert after_posterior.etapa == etapa
    assert Avaliacao.objects.filter(ciclo=ciclo_aberto, usuario=user).count() == 1

    user.data_entrada = None
    user.save(update_fields=['data_entrada'])
    after_null = ensure_avaliacao_for_user(user)

    assert after_null is not None
    assert after_null.pk == pk
    assert after_null.etapa == etapa
    assert Avaliacao.objects.filter(ciclo=ciclo_aberto, usuario=user).count() == 1
    assert Avaliacao.objects.filter(pk=pk).exists()


@pytest.mark.django_db
def test_ensure_nao_duplica_avaliacao(ciclo_aberto, lider, area, cargo_colab):
    """Segundo ensure sem mudança de elegibilidade → ainda 1 Avaliação."""
    cutoff = ciclo_aberto.admitidos_ate
    assert cutoff is not None

    novo = _make_user(
        email='dedupe@test.greenn.com.br',
        nome='Dedupe Mid-Cycle',
        lider=lider,
        area=area,
        cargo_colab=cargo_colab,
        data_entrada=cutoff - timedelta(days=1),
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
    """Usuário inativo → None (não cria Avaliação), mesmo com data ≤ D."""
    cutoff = ciclo_aberto.admitidos_ate
    assert cutoff is not None

    inativo = _make_user(
        email='inativo@test.greenn.com.br',
        nome='Inativo Mid-Cycle',
        lider=lider,
        area=area,
        cargo_colab=cargo_colab,
        data_entrada=cutoff - timedelta(days=10),
        is_active=False,
    )

    result = ensure_avaliacao_for_user(inativo)

    assert result is None
    assert not Avaliacao.objects.filter(ciclo=ciclo_aberto, usuario=inativo).exists()


@pytest.mark.django_db
def test_ensure_noop_ciclo_encerrado_passado(colaborador):
    """Ciclo explícito encerrado → None (0 Avaliações novas)."""
    for aberto in Ciclo.objects.filter(status=Ciclo.Status.ABERTO):
        close_cycle(aberto)

    today = date.today()
    encerrado = Ciclo.objects.create(
        nome='Ciclo Encerrado Mid-Cycle',
        data_inicio=today - timedelta(days=90),
        data_fim=today - timedelta(days=1),
        status=Ciclo.Status.ENCERRADO,
        admitidos_ate=today,
    )
    before = Avaliacao.objects.filter(ciclo=encerrado, usuario=colaborador).count()

    result = ensure_avaliacao_for_user(colaborador, ciclo=encerrado)

    assert result is None
    assert (
        Avaliacao.objects.filter(ciclo=encerrado, usuario=colaborador).count()
        == before
    )
    assert before == 0
