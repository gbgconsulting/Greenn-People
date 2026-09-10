"""T030 [US5]: convivência multi-open, enrollment com ``ciclo=`` e snapshot SC-008.

Quickstart V6/V7; contratos multi-open-ciclo + SC-008 / SC-009.
"""

from __future__ import annotations

from datetime import date, timedelta

import pytest
from django.utils import timezone

from apps.accounts.models import CustomUser
from apps.cycles.models import AutoCycleRun, Ciclo
from apps.cycles.services.cycle import close_cycle, open_cycle
from apps.cycles.tasks import run_auto_cycle_admission_daily
from apps.goals.forms import get_open_ciclo, get_open_ciclos
from apps.reviews.models import Avaliacao
from apps.reviews.services.enrollment import ensure_avaliacao_for_user

DEFAULT_PASSWORD = 'TestPass123!'
CUTOFF = date(2024, 6, 30)

# jul/2026: 01/07 = quarta → 1º dia útil
REF_FIRST = date(2026, 7, 1)
MARCO_JUL = date(2026, 7, 1)


def _close_all_open() -> None:
    for aberto in Ciclo.objects.filter(status=Ciclo.Status.ABERTO):
        close_cycle(aberto)


def _make_user(
    *,
    email: str,
    lider,
    area,
    cargo_colab,
    data_entrada: date | None,
    is_active: bool = True,
) -> CustomUser:
    return CustomUser.objects.create_user(
        email=email,
        password=DEFAULT_PASSWORD,
        nome=email.split('@')[0],
        cargo=cargo_colab,
        area=area,
        line_manager=lider,
        data_entrada=data_entrada,
        is_active=is_active,
        email_confirmado_em=timezone.now(),
    )


def _make_manual_encerrado(*, nome: str = 'Manual Encerrado') -> Ciclo:
    today = date.today()
    return Ciclo.objects.create(
        nome=nome,
        data_inicio=today - timedelta(days=30),
        data_fim=today + timedelta(days=30),
        status=Ciclo.Status.ENCERRADO,
    )


def _make_auto_aberto(*, marco: date = MARCO_JUL, data_inicio: date | None = None) -> Ciclo:
    inicio = data_inicio or marco
    return Ciclo.objects.create(
        nome=f'Coorte Auto {marco.strftime("%b/%Y")}',
        data_inicio=inicio,
        data_fim=inicio + timedelta(days=20),
        status=Ciclo.Status.ABERTO,
        origem=Ciclo.Origem.AUTOMATICO,
        marco_competencia=marco,
    )


def _isolate_fixture_admission(lider) -> None:
    """Evita que admin/líder (jan/2020) entrem no lote de julho."""
    CustomUser.objects.filter(pk=lider.pk).update(data_entrada=date(2026, 2, 1))
    lider.refresh_from_db()
    if lider.line_manager_id:
        CustomUser.objects.filter(pk=lider.line_manager_id).update(
            data_entrada=date(2026, 2, 1),
        )


@pytest.mark.django_db
def test_manual_com_auto_aberto_ambos_abertos_e_get_open_ciclos(
    lider, area, cargo_colab,
):
    """V6 / SC-009: manual 015 + automático convivem; helpers listam N abertos."""
    _close_all_open()
    auto = _make_auto_aberto()
    manual = _make_manual_encerrado(nome='Manual Com Auto')
    _make_user(
        email='multi-open-elegivel@test.greenn.com.br',
        lider=lider,
        area=area,
        cargo_colab=cargo_colab,
        data_entrada=CUTOFF,
    )

    opened = open_cycle(manual, admitidos_ate=CUTOFF)
    opened.refresh_from_db()
    auto.refresh_from_db()

    assert opened.status == Ciclo.Status.ABERTO
    assert auto.status == Ciclo.Status.ABERTO
    assert Ciclo.objects.filter(status=Ciclo.Status.ABERTO).count() == 2

    abertos = list(get_open_ciclos())
    assert len(abertos) == 2
    assert {c.pk for c in abertos} == {auto.pk, opened.pk}
    assert get_open_ciclo() is not None
    assert get_open_ciclo().pk in {auto.pk, opened.pk}


@pytest.mark.django_db
def test_enrollment_com_ciclo_explicito_matricula_no_alvo(
    lider, area, cargo_colab,
):
    """Com N abertos, ``ciclo=`` explícito cria Avaliação só no ciclo alvo."""
    _close_all_open()
    auto = _make_auto_aberto()
    manual = _make_manual_encerrado(nome='Manual Alvo Explicit')
    opened = open_cycle(manual, admitidos_ate=CUTOFF)

    user_auto = _make_user(
        email='alvo-auto@test.greenn.com.br',
        lider=lider,
        area=area,
        cargo_colab=cargo_colab,
        # janeiro → próximo marco futuro em jul/2026 com REF_FIRST
        data_entrada=date(2026, 1, 12),
    )
    user_manual = _make_user(
        email='alvo-manual@test.greenn.com.br',
        lider=lider,
        area=area,
        cargo_colab=cargo_colab,
        data_entrada=CUTOFF - timedelta(days=3),
    )

    av_auto = ensure_avaliacao_for_user(
        user_auto, ciclo=auto, ref_date=REF_FIRST,
    )
    av_manual = ensure_avaliacao_for_user(user_manual, ciclo=opened)

    assert av_auto is not None
    assert av_auto.ciclo_id == auto.pk
    assert Avaliacao.objects.filter(ciclo=auto, usuario=user_auto).count() == 1
    assert not Avaliacao.objects.filter(ciclo=opened, usuario=user_auto).exists()

    assert av_manual is not None
    assert av_manual.ciclo_id == opened.pk
    assert Avaliacao.objects.filter(ciclo=opened, usuario=user_manual).count() == 1
    assert not Avaliacao.objects.filter(ciclo=auto, usuario=user_manual).exists()


@pytest.mark.django_db
def test_enrollment_sem_ciclo_com_n_abertos_nao_cria_ambiguo(
    lider, area, cargo_colab,
):
    """Sem ``ciclo=`` e com >1 aberto: fail-closed — não cria Avaliação nova."""
    _close_all_open()
    _make_auto_aberto()
    manual = _make_manual_encerrado(nome='Manual Ambiguo')
    open_cycle(manual, admitidos_ate=CUTOFF)

    user = _make_user(
        email='ambiguo-multi@test.greenn.com.br',
        lider=lider,
        area=area,
        cargo_colab=cargo_colab,
        data_entrada=CUTOFF,
    )
    before = Avaliacao.objects.filter(usuario=user).count()

    result = ensure_avaliacao_for_user(user)

    assert result is None
    assert Avaliacao.objects.filter(usuario=user).count() == before


@pytest.mark.django_db
def test_snapshot_editar_data_entrada_pos_matricula_nao_apaga(
    lider, area, cargo_colab,
):
    """V7 / SC-008: editar ``data_entrada`` pós-matrícula não apaga Avaliação."""
    _close_all_open()
    auto = _make_auto_aberto()
    user = _make_user(
        email='snapshot-multi@test.greenn.com.br',
        lider=lider,
        area=area,
        cargo_colab=cargo_colab,
        data_entrada=date(2026, 1, 10),
    )

    created = ensure_avaliacao_for_user(
        user, ciclo=auto, ref_date=REF_FIRST,
    )
    assert created is not None
    pk = created.pk
    etapa = created.etapa

    user.data_entrada = date(2026, 8, 1)
    user.save(update_fields=['data_entrada'])

    after_edit = ensure_avaliacao_for_user(
        user, ciclo=auto, ref_date=REF_FIRST,
    )
    assert after_edit is not None
    assert after_edit.pk == pk
    assert after_edit.etapa == etapa
    assert Avaliacao.objects.filter(pk=pk).exists()
    assert Avaliacao.objects.filter(ciclo=auto, usuario=user).count() == 1

    # Rotina no mesmo marco (idempotente) também não remove o snapshot.
    _isolate_fixture_admission(lider)
    run_auto_cycle_admission_daily(data_referencia=REF_FIRST)

    assert Avaliacao.objects.filter(pk=pk).exists()
    assert Avaliacao.objects.filter(ciclo=auto, usuario=user).count() == 1
    snap = Avaliacao.objects.get(pk=pk)
    assert snap.etapa == etapa
    assert snap.usuario_id == user.pk


@pytest.mark.django_db
def test_rotina_em_ciclo_encerrado_zero_create_delete(
    lider, area, cargo_colab,
):
    """SC-008: rodada da rotina não cria/apaga Avaliações de ciclo encerrado."""
    _close_all_open()
    _isolate_fixture_admission(lider)

    today = date.today()
    encerrado = Ciclo.objects.create(
        nome='Arquivo Encerrado Intocado',
        data_inicio=today - timedelta(days=200),
        data_fim=today - timedelta(days=120),
        status=Ciclo.Status.ENCERRADO,
        origem=Ciclo.Origem.AUTOMATICO,
        marco_competencia=date(2026, 1, 1),
        admitidos_ate=None,
    )
    matriculado = _make_user(
        email='encerrado-matriculado@test.greenn.com.br',
        lider=lider,
        area=area,
        cargo_colab=cargo_colab,
        data_entrada=date(2025, 7, 15),
    )
    fora = _make_user(
        email='encerrado-fora@test.greenn.com.br',
        lider=lider,
        area=area,
        cargo_colab=cargo_colab,
        data_entrada=date(2026, 1, 20),
    )
    av = Avaliacao.objects.create(
        ciclo=encerrado,
        usuario=matriculado,
        etapa=Avaliacao.Etapa.FEEDBACK,
    )
    snapshot_ids = frozenset(
        Avaliacao.objects.filter(ciclo=encerrado).values_list('pk', flat=True),
    )
    assert snapshot_ids == frozenset({av.pk})

    # Candidato novo ao marco jul — a rotina pode abrir outra coorte, mas
    # o arquivo encerrado permanece com o mesmo conjunto de Avaliações.
    _make_user(
        email='jul-novo@test.greenn.com.br',
        lider=lider,
        area=area,
        cargo_colab=cargo_colab,
        data_entrada=date(2026, 1, 18),
    )

    before_global = Avaliacao.objects.count()
    result = run_auto_cycle_admission_daily(data_referencia=REF_FIRST)

    assert result['status'] == AutoCycleRun.Status.SUCESSO
    assert result['matriculados'] >= 1

    encerrado.refresh_from_db()
    assert encerrado.status == Ciclo.Status.ENCERRADO

    after_ids = frozenset(
        Avaliacao.objects.filter(ciclo=encerrado).values_list('pk', flat=True),
    )
    assert after_ids == snapshot_ids
    assert Avaliacao.objects.filter(ciclo=encerrado).count() == 1
    assert Avaliacao.objects.filter(pk=av.pk).exists()
    assert not Avaliacao.objects.filter(ciclo=encerrado, usuario=fora).exists()

    # ensure explícito no encerrado continua no-op (0 create).
    assert ensure_avaliacao_for_user(matriculado, ciclo=encerrado) is None
    assert ensure_avaliacao_for_user(fora, ciclo=encerrado) is None
    assert (
        frozenset(
            Avaliacao.objects.filter(ciclo=encerrado).values_list('pk', flat=True),
        )
        == snapshot_ids
    )
    # Avaliações novas só na coorte aberta — nunca no encerrado.
    novo_ciclo_id = result['ciclo_id']
    assert novo_ciclo_id is not None
    assert novo_ciclo_id != encerrado.pk
    assert Avaliacao.objects.filter(ciclo=encerrado).count() == 1
    assert Avaliacao.objects.count() == before_global + result['matriculados']
