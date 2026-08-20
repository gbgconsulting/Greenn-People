"""T010 [US1]: abertura de ciclo com corte ``admitidos_ate``.

Contrato: ``specs/015-cycle-admission-cutoff/contracts/open-cycle-cutoff-contract.md``
(T-open-1…T-open-5) + plan §Testes / SC-001, SC-002, SC-008.
"""

from __future__ import annotations

from datetime import date, timedelta
from urllib.parse import quote

import pytest
from django.contrib.messages import get_messages
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import CustomUser
from apps.cycles.exceptions import CycleAlreadyOpenError, CycleMissingCutoffError
from apps.cycles.models import Ciclo
from apps.cycles.services.cycle import close_cycle, open_cycle
from apps.cycles.services.eligibility import (
    preview_admission_counts,
    user_eligible_for_ciclo,
)
from apps.reviews.models import Avaliacao
from apps.reviews.services.enrollment import ensure_avaliacao_for_user

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
    """T-open-3 / SC-008: mensagem sem “todos os ativos” / “colaboradores ativos”.

    UX: corte já vem do cadastro; POST Abrir sem campo ``admitidos_ate``.
    """
    _close_all_open()
    ciclo = _make_encerrado(nome='Ciclo Mensagem')
    ciclo.admitidos_ate = CUTOFF
    ciclo.save(update_fields=['admitidos_ate'])
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
    response = client.post(url)  # sem override — usa corte do cadastro

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


@pytest.mark.django_db
def test_ciclo_form_exige_admitidos_ate_no_create(admin):
    """Create UI exige Admitidos até; listagem Abrir não coleta a data."""
    from apps.cycles.forms import CicloForm

    today = date.today()
    form = CicloForm(
        data={
            'nome': 'Ciclo Com Corte',
            'data_inicio': today.isoformat(),
            'data_fim': (today + timedelta(days=30)).isoformat(),
        },
    )
    assert not form.is_valid()
    assert 'admitidos_ate' in form.errors

    form_ok = CicloForm(
        data={
            'nome': 'Ciclo Com Corte',
            'data_inicio': today.isoformat(),
            'data_fim': (today + timedelta(days=30)).isoformat(),
            'admitidos_ate': CUTOFF.isoformat(),
        },
    )
    assert form_ok.is_valid(), form_ok.errors
    ciclo = form_ok.save()
    assert ciclo.admitidos_ate == CUTOFF
    assert ciclo.status == Ciclo.Status.ENCERRADO

    client = Client()
    client.force_login(admin)
    list_resp = client.get(reverse('cycles:ciclo_list'))
    assert list_resp.status_code == 200
    html = list_resp.content.decode()
    assert 'name="admitidos_ate"' not in html
    assert 'data-ciclo-open-form' in html


@pytest.mark.django_db
def test_ciclo_create_unifica_abrir_e_matricula_elegiveis(admin, lider, area, cargo_colab):
    """Create + open: elegíveis matriculados; inelegíveis fora; um-aberto."""
    _close_all_open()
    today = date.today()
    elegivel = _make_user(
        email='create-elegivel@test.greenn.com.br',
        nome='Elegível Create',
        lider=lider,
        area=area,
        cargo_colab=cargo_colab,
        data_entrada=CUTOFF,
    )
    _make_user(
        email='create-posterior@test.greenn.com.br',
        nome='Posterior Create',
        lider=lider,
        area=area,
        cargo_colab=cargo_colab,
        data_entrada=CUTOFF + timedelta(days=1),
    )
    _make_user(
        email='create-sem-data@test.greenn.com.br',
        nome='Sem Data Create',
        lider=lider,
        area=area,
        cargo_colab=cargo_colab,
        data_entrada=None,
    )

    client = Client()
    client.force_login(admin)
    response = client.post(
        reverse('cycles:ciclo_create'),
        data={
            'nome': 'Ciclo Unificado',
            'data_inicio': today.isoformat(),
            'data_fim': (today + timedelta(days=30)).isoformat(),
            'admitidos_ate': CUTOFF.isoformat(),
        },
    )
    assert response.status_code == 302
    assert response.url == reverse('cycles:ciclo_list')

    ciclo = Ciclo.objects.get(nome='Ciclo Unificado')
    assert ciclo.status == Ciclo.Status.ABERTO
    assert ciclo.admitidos_ate == CUTOFF
    assert Avaliacao.objects.filter(ciclo=ciclo, usuario=elegivel).count() == 1
    assert Avaliacao.objects.filter(ciclo=ciclo).count() == Avaliacao.objects.filter(
        ciclo=ciclo,
        usuario__data_entrada__lte=CUTOFF,
        usuario__is_active=True,
        usuario__data_entrada__isnull=False,
    ).count()

    texts = [str(m.message) for m in get_messages(response.wsgi_request)]
    joined = ' '.join(texts).lower()
    assert 'criado e aberto' in joined
    assert 'todos os ativos' not in joined


@pytest.mark.django_db
def test_ciclo_create_com_outro_aberto_salva_encerrado_sem_matricular(
    admin, ciclo_aberto, lider, area, cargo_colab,
):
    """Se já há ciclo aberto: cria encerrado, não matricula, avisa."""
    today = date.today()
    before = Avaliacao.objects.filter(ciclo=ciclo_aberto).count()
    client = Client()
    client.force_login(admin)
    response = client.post(
        reverse('cycles:ciclo_create'),
        data={
            'nome': 'Ciclo Em Espera',
            'data_inicio': today.isoformat(),
            'data_fim': (today + timedelta(days=30)).isoformat(),
            'admitidos_ate': CUTOFF.isoformat(),
        },
    )
    assert response.status_code == 302
    novo = Ciclo.objects.get(nome='Ciclo Em Espera')
    assert novo.status == Ciclo.Status.ENCERRADO
    assert novo.admitidos_ate == CUTOFF
    assert Avaliacao.objects.filter(ciclo=novo).count() == 0
    assert Avaliacao.objects.filter(ciclo=ciclo_aberto).count() == before
    ciclo_aberto.refresh_from_db()
    assert ciclo_aberto.status == Ciclo.Status.ABERTO

    texts = [str(m.message).lower() for m in get_messages(response.wsgi_request)]
    assert any('não foi aberto' in t for t in texts)


# --- T015/T016 [US2]: preview de contagens ------------------------------------


def _preview_url(ciclo: Ciclo) -> str:
    return reverse('cycles:ciclo_open_preview', kwargs={'pk': ciclo.pk})


def _seed_preview_cohort(lider, area, cargo_colab) -> dict[str, object]:
    """Base controlada para as 3 contagens (fixtures admin+lider também contam).

    Com ``lider`` (puxa ``admin``): 2 ativos com entrada ≤ D já existem.
    Acrescenta 2 elegíveis, 5 posteriores, 7 sem data e 1 inativo (fora).
    Contagens distintas (4 / 5 / 7) para asserts estáveis no HTML.
    """
    elegivel_a = _make_user(
        email='prev-elegivel-a@test.greenn.com.br',
        nome='Preview Elegível A',
        lider=lider,
        area=area,
        cargo_colab=cargo_colab,
        data_entrada=CUTOFF,
    )
    elegivel_b = _make_user(
        email='prev-elegivel-b@test.greenn.com.br',
        nome='Preview Elegível B',
        lider=lider,
        area=area,
        cargo_colab=cargo_colab,
        data_entrada=CUTOFF - timedelta(days=5),
    )
    posteriores = [
        _make_user(
            email=f'prev-post-{i}@test.greenn.com.br',
            nome=f'Preview Posterior {i}',
            lider=lider,
            area=area,
            cargo_colab=cargo_colab,
            data_entrada=CUTOFF + timedelta(days=i + 1),
        )
        for i in range(5)
    ]
    sem_data = [
        _make_user(
            email=f'prev-sem-{i}@test.greenn.com.br',
            nome=f'Preview Sem Data {i}',
            lider=lider,
            area=area,
            cargo_colab=cargo_colab,
            data_entrada=None,
        )
        for i in range(7)
    ]
    inativo = _make_user(
        email='prev-inativo@test.greenn.com.br',
        nome='Preview Inativo Excluído',
        lider=lider,
        area=area,
        cargo_colab=cargo_colab,
        data_entrada=CUTOFF - timedelta(days=10),
        is_active=False,
    )
    # admin + lider (fixtures) + elegivel_a/b
    return {
        'elegiveis': 4,
        'excluidos_admissao_posterior': 5,
        'sem_data_entrada': 7,
        'pii_emails': [
            elegivel_a.email,
            elegivel_b.email,
            *[u.email for u in posteriores],
            *[u.email for u in sem_data],
            inativo.email,
        ],
        'pii_nomes': [
            elegivel_a.nome,
            elegivel_b.nome,
            *[u.nome for u in posteriores],
            *[u.nome for u in sem_data],
            inativo.nome,
        ],
    }


@pytest.mark.django_db
def test_preview_admission_counts_agrega_somente_ativos(lider, area, cargo_colab):
    """T016: agregações ORM batem; inativos fora; sem lista nominativa."""
    expected = _seed_preview_cohort(lider, area, cargo_colab)
    counts = preview_admission_counts(CUTOFF)

    assert counts == {
        'elegiveis': expected['elegiveis'],
        'excluidos_admissao_posterior': expected['excluidos_admissao_posterior'],
        'sem_data_entrada': expected['sem_data_entrada'],
    }
    assert set(counts.keys()) == {
        'elegiveis',
        'excluidos_admissao_posterior',
        'sem_data_entrada',
    }


@pytest.mark.django_db
def test_ciclo_open_preview_admin_200_tres_contagens(admin, lider, area, cargo_colab):
    """T015 / SC-006: admin → 200; HTML com as 3 contagens; sem PII nominativa."""
    _close_all_open()
    ciclo = _make_encerrado(nome='Ciclo Preview Contagens')
    expected = _seed_preview_cohort(lider, area, cargo_colab)

    client = Client()
    client.force_login(admin)
    url = _preview_url(ciclo)
    response = client.get(url, data={'admitidos_ate': CUTOFF.isoformat()})

    assert response.status_code == 200
    body = response.content.decode()

    assert str(expected['elegiveis']) in body
    assert str(expected['excluidos_admissao_posterior']) in body
    assert str(expected['sem_data_entrada']) in body

    for email in expected['pii_emails']:
        assert email not in body
    for nome in expected['pii_nomes']:
        assert nome not in body


@pytest.mark.django_db
def test_ciclo_open_preview_lider_403(lider, area, cargo_colab):
    """T015: líder autenticado (não-admin) → 403."""
    assert not lider.is_admin
    _close_all_open()
    ciclo = _make_encerrado(nome='Ciclo Preview Líder')
    _seed_preview_cohort(lider, area, cargo_colab)

    client = Client()
    client.force_login(lider)
    response = client.get(
        _preview_url(ciclo),
        data={'admitidos_ate': CUTOFF.isoformat()},
    )

    assert response.status_code == 403
    body = response.content.decode()
    assert 'prev-post-0@test.greenn.com.br' not in body
    assert 'Preview Posterior 0' not in body


@pytest.mark.django_db
def test_ciclo_open_preview_colaborador_403(colaborador, lider, area, cargo_colab):
    """T015: colaborador autenticado (não-admin) → 403."""
    assert not colaborador.is_admin
    _close_all_open()
    ciclo = _make_encerrado(nome='Ciclo Preview Colab')
    _seed_preview_cohort(lider, area, cargo_colab)

    client = Client()
    client.force_login(colaborador)
    response = client.get(
        _preview_url(ciclo),
        data={'admitidos_ate': CUTOFF.isoformat()},
    )

    assert response.status_code == 403
    body = response.content.decode()
    assert 'prev-sem-0@test.greenn.com.br' not in body
    assert 'Preview Sem Data 0' not in body


@pytest.mark.django_db
def test_ciclo_open_preview_anonimo_redirect_login(lider, area, cargo_colab):
    """T015: anônimo → redirect para login (LoginRequiredMixin)."""
    _close_all_open()
    ciclo = _make_encerrado(nome='Ciclo Preview Anônimo')
    _seed_preview_cohort(lider, area, cargo_colab)

    client = Client()
    url = _preview_url(ciclo)
    response = client.get(url, data={'admitidos_ate': CUTOFF.isoformat()})

    assert response.status_code == 302
    login_url = reverse('accounts:login')
    assert response.url.startswith(login_url)
    assert f'next={quote(url)}' in response.url


# --- T032 [US5]: ciclo 011 / arquivo com admitidos_ate NULL (SC-005) ----------


@pytest.mark.django_db
def test_ciclo_historico_admitidos_ate_null_conjunto_avaliacoes_intacto(
    lider, area, cargo_colab,
):
    """SC-005 / FR-008: encerrado com corte NULL — 0 criações/remoções ao reler.

    Simula ciclo importado 011: ``admitidos_ate IS NULL``, Avaliações já
    persistidas. Chamar ``ensure_avaliacao_for_user`` / predicado não altera
    o conjunto de Avaliações.
    """
    _close_all_open()
    today = date.today()
    historico = Ciclo.objects.create(
        nome='Ciclo 011 Arquivo Sem Corte',
        data_inicio=today - timedelta(days=180),
        data_fim=today - timedelta(days=90),
        status=Ciclo.Status.ENCERRADO,
        admitidos_ate=None,
    )
    assert historico.admitidos_ate is None

    matriculado_a = _make_user(
        email='hist-a@test.greenn.com.br',
        nome='Histórico Matriculado A',
        lider=lider,
        area=area,
        cargo_colab=cargo_colab,
        data_entrada=CUTOFF - timedelta(days=30),
    )
    matriculado_b = _make_user(
        email='hist-b@test.greenn.com.br',
        nome='Histórico Matriculado B',
        lider=lider,
        area=area,
        cargo_colab=cargo_colab,
        data_entrada=None,  # no arquivo 011 pode não ter data
    )
    sem_avaliacao = _make_user(
        email='hist-fora@test.greenn.com.br',
        nome='Ativo Sem Avaliacao No Arquivo',
        lider=lider,
        area=area,
        cargo_colab=cargo_colab,
        data_entrada=CUTOFF,
    )

    av_a = Avaliacao.objects.create(
        ciclo=historico,
        usuario=matriculado_a,
        etapa=Avaliacao.Etapa.FEEDBACK,
    )
    av_b = Avaliacao.objects.create(
        ciclo=historico,
        usuario=matriculado_b,
        etapa=Avaliacao.Etapa.AVALIACAO,
    )
    snapshot_ids = frozenset(
        Avaliacao.objects.filter(ciclo=historico).values_list('pk', flat=True)
    )
    snapshot_pairs = frozenset(
        Avaliacao.objects.filter(ciclo=historico).values_list(
            'usuario_id', flat=True,
        )
    )
    assert snapshot_ids == frozenset({av_a.pk, av_b.pk})
    assert snapshot_pairs == frozenset({matriculado_a.pk, matriculado_b.pk})

    # Fail-closed no predicado; ensure no-op por ciclo encerrado — sem mutação.
    assert user_eligible_for_ciclo(matriculado_a, historico) is False
    assert user_eligible_for_ciclo(sem_avaliacao, historico) is False

    for user in (matriculado_a, matriculado_b, sem_avaliacao, lider):
        assert ensure_avaliacao_for_user(user, ciclo=historico) is None

    historico.refresh_from_db()
    assert historico.status == Ciclo.Status.ENCERRADO
    assert historico.admitidos_ate is None

    after_ids = frozenset(
        Avaliacao.objects.filter(ciclo=historico).values_list('pk', flat=True)
    )
    after_pairs = frozenset(
        Avaliacao.objects.filter(ciclo=historico).values_list(
            'usuario_id', flat=True,
        )
    )
    assert after_ids == snapshot_ids
    assert after_pairs == snapshot_pairs
    assert Avaliacao.objects.filter(ciclo=historico).count() == 2
    assert not Avaliacao.objects.filter(
        ciclo=historico, usuario=sem_avaliacao,
    ).exists()
    assert Avaliacao.objects.filter(ciclo=historico, usuario=matriculado_a).count() == 1
    assert Avaliacao.objects.filter(ciclo=historico, usuario=matriculado_b).count() == 1
