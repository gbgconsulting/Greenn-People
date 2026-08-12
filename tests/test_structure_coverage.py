"""T020 [US2] — cobertura estrutura ⊂ escopo + empty honesto.

Asserts presentation/composição em ``apps/dashboard.services.structure``:
- totais/agregações ⊆ ``get_visible_users`` (visible já resolvido);
- empty ``has_data`` falso sem ciclo / escopo vazio (FR-003 / FR-006 / FR-013).
Não altera asserts de stage/approval; sem mutar ``scope.py``.
"""

from __future__ import annotations

import pytest
from django.utils import timezone

from apps.accounts.models import CustomUser
from apps.accounts.services.scope import get_visible_users
from apps.dashboard.services.structure import (
    build_structure_coverage,
    coverage_by_area,
    coverage_by_cargo,
    coverage_summary,
)
from apps.organization.models import Area
from apps.reviews.models import Avaliacao
from tests.conftest import DEFAULT_PASSWORD


@pytest.fixture
def outsider(db, area, cargo_colab) -> CustomUser:
    """Usuário fora da hierarquia do líder (mesmo padrão de test_scope)."""
    return CustomUser.objects.create_user(
        email='outsider.cobertura@test.greenn.com.br',
        password=DEFAULT_PASSWORD,
        nome='Outsider Cobertura',
        cargo=cargo_colab,
        area=area,
        line_manager=None,
        email_confirmado_em=timezone.now(),
    )


def _visible_ativos(user: CustomUser):
    """Mesmo QS que a StructureDashboardView passa ao builder (AuthZ intacta)."""
    return get_visible_users(user).filter(is_active=True)


# --- Subset de escopo (cobertura ⊂ get_visible_users) ---


@pytest.mark.django_db
def test_coverage_summary_total_equals_visible(
    ciclo_aberto,
    lider,
    colaborador,
    outsider,
):
    """KPI ``total`` = count do QS visível ativo — não inclui outsider."""
    visible = _visible_ativos(lider)
    visible_ids = set(visible.values_list('pk', flat=True))

    assert colaborador.pk in visible_ids
    assert outsider.pk not in visible_ids

    resumo = coverage_summary(visible, ciclo_aberto)
    assert resumo['total'] == visible.count()
    assert resumo['has_ciclo'] is True
    assert resumo['total'] == len(visible_ids)


@pytest.mark.django_db
def test_coverage_excludes_outsider_even_with_avaliacao(
    ciclo_aberto,
    lider,
    colaborador,
    outsider,
):
    """Avaliação de outsider não entra em ``com_avaliacao`` do líder (⊂ escopo)."""
    Avaliacao.objects.get_or_create(ciclo=ciclo_aberto, usuario=outsider)

    visible = _visible_ativos(lider)
    resumo = coverage_summary(visible, ciclo_aberto)

    in_scope_com_av = (
        Avaliacao.objects.filter(
            ciclo=ciclo_aberto,
            usuario_id__in=visible.values('pk'),
        )
        .values('usuario_id')
        .distinct()
        .count()
    )
    assert resumo['com_avaliacao'] == in_scope_com_av
    assert Avaliacao.objects.filter(
        ciclo=ciclo_aberto,
        usuario=outsider,
    ).exists()
    # Outsider tem avaliação, mas não está no QS → não infla cobertura.
    assert resumo['com_avaliacao'] <= resumo['total']
    assert colaborador.pk in set(visible.values_list('pk', flat=True))


@pytest.mark.django_db
def test_coverage_by_dimension_rows_subset_of_visible(
    ciclo_aberto,
    lider,
    admin,
    area,
    cargo_colab,
):
    """Somas por área/cargo = tamanho do escopo; labels só de grupos no visible."""
    outra_area = Area.objects.create(nome='Área Fora do Líder')
    # Colab extra no mesmo líder (mesma área) — entra no escopo.
    CustomUser.objects.create_user(
        email='colab2.cobertura@test.greenn.com.br',
        password=DEFAULT_PASSWORD,
        nome='Colab Dois',
        cargo=cargo_colab,
        area=area,
        line_manager=lider,
        email_confirmado_em=timezone.now(),
    )
    # Usuário em outra área sob admin — fora do escopo do líder.
    CustomUser.objects.create_user(
        email='colab.outra.area@test.greenn.com.br',
        password=DEFAULT_PASSWORD,
        nome='Colab Outra Área',
        cargo=cargo_colab,
        area=outra_area,
        line_manager=admin,
        email_confirmado_em=timezone.now(),
    )

    visible = _visible_ativos(lider)
    por_area = coverage_by_area(visible, ciclo_aberto)
    por_cargo = coverage_by_cargo(visible, ciclo_aberto)

    assert sum(r['total'] for r in por_area) == visible.count()
    assert sum(r['total'] for r in por_cargo) == visible.count()
    assert all(r['area_nome'] != outra_area.nome for r in por_area)

    for row in por_area:
        assert row['com_avaliacao'] + row['sem_avaliacao'] == row['total']
        assert 0 <= row['com_avaliacao'] <= row['total']


@pytest.mark.django_db
def test_build_structure_coverage_leader_subset_admin(
    ciclo_aberto,
    admin,
    lider,
    outsider,
):
    """Pacote completo: totais do líder ⊆ admin; outsider só no admin."""
    visible_lider = _visible_ativos(lider)
    visible_admin = _visible_ativos(admin)

    assert outsider.pk in set(visible_admin.values_list('pk', flat=True))
    assert outsider.pk not in set(visible_lider.values_list('pk', flat=True))

    pack_lider = build_structure_coverage(visible_lider, ciclo_aberto)
    pack_admin = build_structure_coverage(visible_admin, ciclo_aberto)

    assert pack_lider['resumo']['total'] <= pack_admin['resumo']['total']
    assert pack_lider['resumo']['total'] == visible_lider.count()
    assert pack_admin['resumo']['total'] == visible_admin.count()

    assert set(visible_lider.values_list('pk', flat=True)).issubset(
        set(visible_admin.values_list('pk', flat=True)),
    )


# --- Empty honesto ---


@pytest.mark.django_db
def test_build_structure_coverage_empty_sem_ciclo(lider, colaborador):
    """Sem ciclo ⇒ empty charts + KPI sem % (FR-003)."""
    visible = _visible_ativos(lider)
    pack = build_structure_coverage(visible, None)

    assert pack['resumo']['has_ciclo'] is False
    assert pack['resumo']['percentual'] is None
    assert pack['resumo']['com_avaliacao'] is None
    assert pack['resumo']['total'] == visible.count()
    assert pack['por_area'] == []
    assert pack['por_cargo'] == []

    for chart in (pack['chart_por_area'], pack['chart_por_cargo']):
        assert chart['has_data'] is False
        assert chart['labels'] == []
        assert chart['values'] == []
        assert 'ciclo' in chart['empty_message'].lower()


@pytest.mark.django_db
def test_build_structure_coverage_empty_escopo(ciclo_aberto):
    """QS vazio ⇒ empty de escopo, sem série inventada."""
    empty_qs = CustomUser.objects.none()
    pack = build_structure_coverage(empty_qs, ciclo_aberto)

    assert pack['resumo']['total'] == 0
    assert pack['resumo']['com_avaliacao'] == 0
    assert pack['resumo']['percentual'] is None
    assert pack['por_area'] == []
    assert pack['por_cargo'] == []

    for chart in (pack['chart_por_area'], pack['chart_por_cargo']):
        assert chart['has_data'] is False
        assert chart['labels'] == []
        assert chart['values'] == []
        assert 'escopo' in chart['empty_message'].lower()


@pytest.mark.django_db
def test_coverage_summary_empty_escopo_com_ciclo(ciclo_aberto):
    resumo = coverage_summary(CustomUser.objects.none(), ciclo_aberto)
    assert resumo == {
        'total': 0,
        'com_avaliacao': 0,
        'sem_avaliacao': 0,
        'percentual': None,
        'has_ciclo': True,
    }
