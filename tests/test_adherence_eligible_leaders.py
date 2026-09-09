"""População canônica de gestores elegíveis para aderência."""

from __future__ import annotations

from decimal import Decimal

import pytest
from django.utils import timezone

from apps.accounts.models import CustomUser
from apps.cycles.models import Ciclo
from apps.dashboard.models import AderenciaSnapshot
from apps.dashboard.services.eligible_leaders import (
    eligible_leader_queryset,
    filter_adherence_snapshots,
    leader_ids_with_team_in_ciclo,
)
from apps.dashboard.tasks import _leader_ids_for_ciclo

from .conftest import DEFAULT_PASSWORD


@pytest.mark.django_db
def test_eligible_leader_requires_active_team(admin, area, cargo_lider, cargo_colab):
    gestor = CustomUser.objects.create_user(
        email='gestor.ativo@test.greenn.com.br',
        password=DEFAULT_PASSWORD,
        nome='Gestor Ativo',
        cargo=cargo_lider,
        area=area,
        line_manager=admin,
        email_confirmado_em=timezone.now(),
    )
    CustomUser.objects.create_user(
        email='colab.ativo@test.greenn.com.br',
        password=DEFAULT_PASSWORD,
        nome='Colab Ativo',
        cargo=cargo_colab,
        area=area,
        line_manager=gestor,
        email_confirmado_em=timezone.now(),
    )
    ex_gestor = CustomUser.objects.create_user(
        email='ex.gestor@test.greenn.com.br',
        password=DEFAULT_PASSWORD,
        nome='Ex Gestor',
        cargo=cargo_lider,
        area=area,
        line_manager=admin,
        is_active=False,
        email_confirmado_em=timezone.now(),
    )
    CustomUser.objects.create_user(
        email='colab.ex@test.greenn.com.br',
        password=DEFAULT_PASSWORD,
        nome='Colab Ex',
        cargo=cargo_colab,
        area=area,
        line_manager=ex_gestor,
        email_confirmado_em=timezone.now(),
    )
    sem_time = CustomUser.objects.create_user(
        email='sem.time@test.greenn.com.br',
        password=DEFAULT_PASSWORD,
        nome='Sem Time',
        cargo=cargo_lider,
        area=area,
        line_manager=admin,
        email_confirmado_em=timezone.now(),
    )
    gestor_só_inativos = CustomUser.objects.create_user(
        email='gestor.inativos@test.greenn.com.br',
        password=DEFAULT_PASSWORD,
        nome='Gestor Só Inativos',
        cargo=cargo_lider,
        area=area,
        line_manager=admin,
        email_confirmado_em=timezone.now(),
    )
    inativo = CustomUser.objects.create_user(
        email='colab.inativo@test.greenn.com.br',
        password=DEFAULT_PASSWORD,
        nome='Colab Inativo',
        cargo=cargo_colab,
        area=area,
        line_manager=gestor_só_inativos,
        is_active=False,
        email_confirmado_em=timezone.now(),
    )
    del inativo

    elegiveis = set(eligible_leader_queryset().values_list('email', flat=True))

    assert gestor.email in elegiveis
    assert ex_gestor.email not in elegiveis
    assert sem_time.email not in elegiveis
    assert gestor_só_inativos.email not in elegiveis


@pytest.mark.django_db
def test_filter_adherence_snapshots_excludes_ineligible(
    admin,
    lider,
    ciclo_aberto,
    area,
    cargo_lider,
):
    autor_sem_time = CustomUser.objects.create_user(
        email='autor.sem.time@test.greenn.com.br',
        password=DEFAULT_PASSWORD,
        nome='Autor Sem Time',
        cargo=cargo_lider,
        area=area,
        line_manager=admin,
        email_confirmado_em=timezone.now(),
    )
    now = timezone.now()
    AderenciaSnapshot.objects.create(
        lider=lider,
        ciclo=ciclo_aberto,
        percentual=Decimal('80.00'),
        componentes={},
        calculado_em=now,
    )
    AderenciaSnapshot.objects.create(
        lider=autor_sem_time,
        ciclo=ciclo_aberto,
        percentual=Decimal('10.00'),
        componentes={},
        calculado_em=now,
    )

    qs = filter_adherence_snapshots(
        AderenciaSnapshot.objects.filter(ciclo=ciclo_aberto),
        ciclo=ciclo_aberto,
    )
    emails = set(qs.values_list('lider__email', flat=True))

    assert emails == {lider.email}


@pytest.mark.django_db
def test_leader_ids_for_ciclo_matches_team_in_ciclo(lider, colaborador, ciclo_aberto):
    del colaborador
    assert _leader_ids_for_ciclo(ciclo_aberto) == leader_ids_with_team_in_ciclo(
        ciclo_aberto,
    )
    assert lider.pk in leader_ids_with_team_in_ciclo(ciclo_aberto)
