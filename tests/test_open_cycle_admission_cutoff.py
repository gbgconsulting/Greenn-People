"""T010 [US1]: abertura de ciclo com corte ``admitidos_ate``.

Contrato: ``specs/015-cycle-admission-cutoff/contracts/open-cycle-cutoff-contract.md``
(T-open-1…T-open-5) + plan §Testes / SC-001, SC-002, SC-008.
"""

from __future__ import annotations

from datetime import date, timedelta

import pytest
from django.contrib.messages import get_messages
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import CustomUser
from apps.cycles.exceptions import CycleAlreadyOpenError, CycleMissingCutoffError
from apps.cycles.models import Ciclo
from apps.cycles.services.cycle import close_cycle, open_cycle
from apps.reviews.models import Avaliacao

DEFAULT_PASSWORD = 'TestPass123!'
CUTOFF = date(2024, 6, 30)


def _close_all_open() -> None:
    for aberto in Ciclo.objects.filter(status=Ciclo.Status.ABERTO):
        close_cycle(aberto)


def _make_encerrado(*, nome: str = 'Ciclo Corte Teste') -> Ciclo:
    today = date.today()
    return Ciclo.objects.create(
        nome=nome,
        data_inicio=today - timedelta(days=30),
        data_fim=today + timedelta(days=30),
        status=Ciclo.Status.ENCERRADO,
    )


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


def _has_avaliacao(ciclo: Ciclo, user: CustomUser) -> bool:
    return Avaliacao.objects.filter(ciclo=ciclo, usuario=user).exists()


@pytest.mark.django_db
def test_open_cycle_matricula_so_elegiveis(lider, area, cargo_colab):
    """T-open-1 / SC-001: 1 Avaliacao por elegível; 0 nos demais."""
    _close_all_open()
    ciclo = _make_encerrado()

    elegivel = _make_user(
        email='elegivel@test.greenn.com.br',
        nome='Elegível ≤ D',
        lider=lider,
        area=area,
        cargo_colab=cargo_colab,
        data_entrada=CUTOFF,  # inclusivo
    )
    borda_antes = _make_user(
        email='borda@test.greenn.com.br',
        nome='Elegível antes de D',
        lider=lider,
        area=area,
        cargo_colab=cargo_colab,
        data_entrada=CUTOFF - timedelta(days=1),
    )
    posterior = _make_user(
        email='posterior@test.greenn.com.br',
        nome='Inelegível > D',
        lider=lider,
        area=area,
        cargo_colab=cargo_colab,
        data_entrada=CUTOFF + timedelta(days=1),
    )
    sem_data = _make_user(
        email='semdata@test.greenn.com.br',
        nome='Inelegível sem data',
        lider=lider,
        area=area,
        cargo_colab=cargo_colab,
        data_entrada=None,
    )
    inativo = _make_user(
        email='inativo-corte@test.greenn.com.br',
        nome='Inativo com data ≤ D',
        lider=lider,
        area=area,
        cargo_colab=cargo_colab,
        data_entrada=CUTOFF - timedelta(days=10),
        is_active=False,
    )

    before = Avaliacao.objects.count()
    opened = open_cycle(ciclo, admitidos_ate=CUTOFF)
    opened.refresh_from_db()

    assert opened.status == Ciclo.Status.ABERTO
    assert opened.admitidos_ate == CUTOFF

    assert _has_avaliacao(opened, elegivel)
    assert _has_avaliacao(opened, borda_antes)
    assert not _has_avaliacao(opened, posterior)
    assert not _has_avaliacao(opened, sem_data)
    assert not _has_avaliacao(opened, inativo)

    assert Avaliacao.objects.filter(ciclo=opened, usuario=elegivel).count() == 1
    assert Avaliacao.objects.filter(ciclo=opened, usuario=borda_antes).count() == 1
    assert Avaliacao.objects.count() >= before + 2


@pytest.mark.django_db
def test_open_cycle_sem_corte_falha_status_intacto_zero_avaliacoes(
    lider, area, cargo_colab,
):
    """T-open-2 / SC-002: sem D → CycleMissingCutoffError; não abre; 0 Avaliações."""
    _close_all_open()
    ciclo = _make_encerrado(nome='Ciclo Sem Corte')
    assert ciclo.admitidos_ate is None

    _make_user(
        email='candidato@test.greenn.com.br',
        nome='Candidato Sem Corte',
        lider=lider,
        area=area,
        cargo_colab=cargo_colab,
        data_entrada=CUTOFF,
    )

    before_count = Avaliacao.objects.filter(ciclo=ciclo).count()
    assert before_count == 0

    with pytest.raises(CycleMissingCutoffError):
        open_cycle(ciclo)

    ciclo.refresh_from_db()
    assert ciclo.status == Ciclo.Status.ENCERRADO
    assert ciclo.admitidos_ate is None
    assert Avaliacao.objects.filter(ciclo=ciclo).count() == 0


@pytest.mark.django_db
def test_open_cycle_um_aberto_intacto(ciclo_aberto):
    """T-open-4: já existe aberto → CycleAlreadyOpenError intacto."""
    outro = _make_encerrado(nome='Segundo Ciclo Concorrente')

    with pytest.raises(CycleAlreadyOpenError):
        open_cycle(outro, admitidos_ate=CUTOFF)

    outro.refresh_from_db()
    assert outro.status == Ciclo.Status.ENCERRADO
    ciclo_aberto.refresh_from_db()
    assert ciclo_aberto.status == Ciclo.Status.ABERTO


@pytest.mark.django_db
def test_open_cycle_reenvio_ciclo_ja_aberto_nao_duplica(ciclo_aberto, colaborador):
    """T-open-5: reabrir o mesmo ciclo → erro existente; sem duplicar Avaliações."""
    before = Avaliacao.objects.filter(ciclo=ciclo_aberto).count()
    assert Avaliacao.objects.filter(ciclo=ciclo_aberto, usuario=colaborador).count() == 1

    with pytest.raises(CycleAlreadyOpenError):
        open_cycle(ciclo_aberto, admitidos_ate=CUTOFF)

    ciclo_aberto.refresh_from_db()
    assert ciclo_aberto.status == Ciclo.Status.ABERTO
    assert Avaliacao.objects.filter(ciclo=ciclo_aberto).count() == before
    assert Avaliacao.objects.filter(ciclo=ciclo_aberto, usuario=colaborador).count() == 1


@pytest.mark.django_db
def test_ciclo_open_view_mensagem_sucesso_sem_todos_os_ativos(admin, lider, area, cargo_colab):
    """T-open-3 / SC-008: mensagem sem “todos os ativos” / “colaboradores ativos”."""
    _close_all_open()
    ciclo = _make_encerrado(nome='Ciclo Mensagem')
    _make_user(
        email='msg-elegivel@test.greenn.com.br',
        nome='Elegível Mensagem',
        lider=lider,
        area=area,
        cargo_colab=cargo_colab,
        data_entrada=CUTOFF,
    )

    client = Client()
    client.force_login(admin)
    url = reverse('cycles:ciclo_open', kwargs={'pk': ciclo.pk})
    response = client.post(url, data={'admitidos_ate': CUTOFF.isoformat()})

    assert response.status_code == 302
    assert response.url == reverse('cycles:ciclo_list')

    texts = [str(m.message) for m in get_messages(response.wsgi_request)]
    assert texts, 'esperava messages.success após abertura'
    joined = ' '.join(texts).lower()

    assert 'todos os ativos' not in joined
    assert 'colaboradores ativos' not in joined

    ciclo.refresh_from_db()
    assert ciclo.status == Ciclo.Status.ABERTO
    assert ciclo.admitidos_ate == CUTOFF
