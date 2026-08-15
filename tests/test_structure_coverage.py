"""T020 / T023 [US2] — cobertura estrutura ⊂ escopo + empty + Top-N.

Asserts presentation/composição em ``apps.dashboard.services.structure``:
- totais/agregações ⊆ ``get_visible_users`` (visible já resolvido);
- empty ``has_data`` falso sem ciclo / escopo vazio (FR-003 / FR-006 / FR-013);
- T023: eixo >8 → ≤8 rótulos + ``Outros`` ponderado; cobertura ≠ aderência;
  builder **recebe** ``visible`` (nunca chama ``get_visible_users``).
Não altera asserts de stage/approval; sem mutar ``scope.py``.
**MUST NOT** ler ``data/legado-solides/raw/``.
"""

from __future__ import annotations

import inspect

import pytest
from django.utils import timezone

from apps.accounts.models import CustomUser
from apps.accounts.services.scope import get_visible_users
from apps.dashboard.chart_payloads import (
    ADERENCIA_LABELS,
    CHART_TYPE_BAR_HORIZONTAL,
    CHART_TYPE_DOUGHNUT,
    DENSITY_TOP_N,
    EMPTY_KIND_COPY,
    EMPTY_KIND_ESCOPO,
    EMPTY_KIND_OPERACIONAL,
    OTHERS_LABEL,
)
from apps.dashboard.services.structure import (
    build_structure_coverage,
    coverage_by_area,
    coverage_by_cargo,
    coverage_summary,
)
from apps.organization.models import Area, Cargo
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
        assert chart['empty_message'] == EMPTY_KIND_COPY[EMPTY_KIND_OPERACIONAL]


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
        assert chart['empty_message'] == EMPTY_KIND_COPY[EMPTY_KIND_ESCOPO]


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


# --- T023: Top-N cobertura + cobertura ≠ aderência + receives visible ---


def _bulk_users(
    *,
    prefix: str,
    count: int,
    area: Area,
    cargo: Cargo,
    line_manager: CustomUser | None,
) -> list[CustomUser]:
    """Cria usuários sem hash de senha (só agregação de cobertura)."""
    now = timezone.now()
    users = [
        CustomUser(
            email=f'{prefix}.{i}@test.greenn.com.br',
            nome=f'{prefix} {i}',
            area=area,
            cargo=cargo,
            line_manager=line_manager,
            email_confirmado_em=now,
            is_active=True,
            password='!',
        )
        for i in range(count)
    ]
    return CustomUser.objects.bulk_create(users)


def _seed_coverage_over_n_areas(
    *,
    lider: CustomUser,
    cargo: Cargo,
    ciclo,
) -> list[int]:
    """15 áreas com volumes estritos: Top-8 + residual com isca de média.

    Top (totais 10..3): metade com Avaliacao.
    Residual: totais 2,2,1,1,1,1,1 — 3 com 100% + 4 com 0% →
    ponderado 3/9=33%; média de % ≈42,9% (não deve ser o valor de Outros).
    """
    top_totals = (10, 9, 8, 7, 6, 5, 4, 3)
    residual_specs = (
        (2, 2),  # 100%
        (2, 2),  # 100%
        (1, 1),  # 100%
        (1, 0),
        (1, 0),
        (1, 0),
        (1, 0),
    )
    created_ids: list[int] = []

    for idx, total in enumerate(top_totals, start=1):
        area = Area.objects.create(nome=f'CovArea-{idx}')
        users = _bulk_users(
            prefix=f'covarea{idx}',
            count=total,
            area=area,
            cargo=cargo,
            line_manager=lider,
        )
        created_ids.extend(u.pk for u in users)
        for user in users[: total // 2]:
            Avaliacao.objects.get_or_create(ciclo=ciclo, usuario=user)

    for idx, (total, com) in enumerate(residual_specs, start=1):
        area = Area.objects.create(nome=f'CovArea-R{idx}')
        users = _bulk_users(
            prefix=f'covarear{idx}',
            count=total,
            area=area,
            cargo=cargo,
            line_manager=lider,
        )
        created_ids.extend(u.pk for u in users)
        for user in users[:com]:
            Avaliacao.objects.get_or_create(ciclo=ciclo, usuario=user)

    assert 12 <= len(top_totals) + len(residual_specs) <= 20
    return created_ids


def _seed_coverage_over_n_cargos(
    *,
    lider: CustomUser,
    area: Area,
    ciclo,
) -> list[int]:
    """15 cargos com o mesmo desenho de volumes / residual ponderado."""
    top_totals = (10, 9, 8, 7, 6, 5, 4, 3)
    residual_specs = (
        (2, 2),
        (2, 2),
        (1, 1),
        (1, 0),
        (1, 0),
        (1, 0),
        (1, 0),
    )
    created_ids: list[int] = []

    for idx, total in enumerate(top_totals, start=1):
        cargo = Cargo.objects.create(nome=f'CovCargo-{idx}', nivel=10 + idx)
        users = _bulk_users(
            prefix=f'covcargo{idx}',
            count=total,
            area=area,
            cargo=cargo,
            line_manager=lider,
        )
        created_ids.extend(u.pk for u in users)
        for user in users[: total // 2]:
            Avaliacao.objects.get_or_create(ciclo=ciclo, usuario=user)

    for idx, (total, com) in enumerate(residual_specs, start=1):
        cargo = Cargo.objects.create(nome=f'CovCargo-R{idx}', nivel=50 + idx)
        users = _bulk_users(
            prefix=f'covcargor{idx}',
            count=total,
            area=area,
            cargo=cargo,
            line_manager=lider,
        )
        created_ids.extend(u.pk for u in users)
        for user in users[:com]:
            Avaliacao.objects.get_or_create(ciclo=ciclo, usuario=user)

    assert 12 <= len(top_totals) + len(residual_specs) <= 20
    return created_ids


def _assert_top_n_weighted_others(chart: dict, *, expected_top_labels: set[str]):
    """≤8 rótulos nomeados + ``Outros``; % residual = sum(com)/sum(total)."""
    assert chart['has_data'] is True
    assert chart['type'] == CHART_TYPE_BAR_HORIZONTAL
    assert len(chart['labels']) == DENSITY_TOP_N + 1
    assert len(chart['labels']) <= DENSITY_TOP_N + 1
    assert chart['labels'][-1] == OTHERS_LABEL
    assert OTHERS_LABEL not in chart['labels'][:-1]
    assert set(chart['labels'][:-1]) == expected_top_labels

    # Residual: com=2+2+1=5, total=2+2+1+1+1+1+1=9 → 55,555… → 56 half-up.
    weighted_int = 56
    mean_of_pct = (100.0 + 100.0 + 100.0 + 0.0 + 0.0 + 0.0 + 0.0) / 7
    others_pct = chart['values'][-1]
    assert others_pct == weighted_int
    assert isinstance(others_pct, int)
    assert chart.get('value_unit') == '%'
    assert others_pct != pytest.approx(mean_of_pct)
    assert all(isinstance(v, int) for v in chart['values'])
    assert len(chart['values']) == len(chart['labels'])


@pytest.mark.django_db
def test_structure_coverage_area_top_n_weighted_others(
    ciclo_aberto,
    lider,
    cargo_colab,
    outsider,
):
    """T023: >8 áreas → chart Top-8 + Outros ponderado; visible explícito."""
    ids = _seed_coverage_over_n_areas(
        lider=lider,
        cargo=cargo_colab,
        ciclo=ciclo_aberto,
    )
    # QS hand-picked — prova que o builder NÃO resolve AuthZ sozinho.
    visible = CustomUser.objects.filter(pk__in=ids)
    assert outsider.pk not in set(visible.values_list('pk', flat=True))
    assert visible.count() > DENSITY_TOP_N

    pack = build_structure_coverage(visible, ciclo_aberto)

    # Rows brutos preservam todas as categorias; densidade só no chart.
    assert len(pack['por_area']) == 15
    _assert_top_n_weighted_others(
        pack['chart_por_area'],
        expected_top_labels={f'CovArea-{i}' for i in range(1, 9)},
    )
    assert pack['resumo']['total'] == visible.count()


@pytest.mark.django_db
def test_structure_coverage_cargo_top_n_weighted_others(
    ciclo_aberto,
    lider,
    area,
    outsider,
):
    """T023: >8 cargos → chart Top-8 + Outros ponderado; visible explícito."""
    ids = _seed_coverage_over_n_cargos(
        lider=lider,
        area=area,
        ciclo=ciclo_aberto,
    )
    visible = CustomUser.objects.filter(pk__in=ids)
    assert outsider.pk not in set(visible.values_list('pk', flat=True))

    pack = build_structure_coverage(visible, ciclo_aberto)

    assert len(pack['por_cargo']) == 15
    _assert_top_n_weighted_others(
        pack['chart_por_cargo'],
        expected_top_labels={f'CovCargo-{i}' for i in range(1, 9)},
    )
    assert pack['resumo']['total'] == visible.count()


@pytest.mark.django_db
def test_structure_coverage_labels_distinct_from_adherence(
    ciclo_aberto,
    lider,
    colaborador,
):
    """T023 / FR-011: cobertura ≠ aderência (títulos, type, seções, labels)."""
    visible = _visible_ativos(lider)
    pack = build_structure_coverage(visible, ciclo_aberto)

    triad_labels = set(ADERENCIA_LABELS.values())
    for chart, chart_id, title in (
        (pack['chart_por_area'], 'chart-cobertura-area', 'Cobertura por área'),
        (pack['chart_por_cargo'], 'chart-cobertura-cargo', 'Cobertura por cargo'),
    ):
        assert chart['id'] == chart_id
        assert chart['title'] == title
        assert 'cobertura' in chart['id']
        assert 'Cobertura' in chart['title']
        assert 'aderência' not in chart['title'].lower()
        assert 'aderencia' not in chart['id']
        assert chart['type'] == CHART_TYPE_BAR_HORIZONTAL
        assert chart['type'] != CHART_TYPE_DOUGHNUT
        assert triad_labels.isdisjoint(set(chart['labels']))

    # Pacote de cobertura não embute doughnut/Status Triad de aderência.
    assert 'chart_aderencia' not in pack
    assert 'aderencia_distribuicao' not in pack
    assert set(pack.keys()) >= {
        'resumo',
        'por_area',
        'por_cargo',
        'chart_por_area',
        'chart_por_cargo',
    }


@pytest.mark.django_db
def test_build_structure_coverage_receives_visible_never_calls_scope(
    ciclo_aberto,
    lider,
    colaborador,
    outsider,
    monkeypatch,
):
    """T023: builder recebe ``visible``; MUST NOT chamar ``get_visible_users``."""
    sig = inspect.signature(build_structure_coverage)
    assert 'visible' in sig.parameters

    def _boom(*_args, **_kwargs):
        raise AssertionError(
            'build_structure_coverage não deve chamar get_visible_users',
        )

    monkeypatch.setattr(
        'apps.accounts.services.scope.get_visible_users',
        _boom,
    )

    # QS deliberadamente sem outsider — mesmo se get_visible_users existisse.
    visible = CustomUser.objects.filter(pk=colaborador.pk)
    assert outsider.pk not in set(visible.values_list('pk', flat=True))

    pack = build_structure_coverage(visible, ciclo_aberto)

    assert pack['resumo']['total'] == 1
    assert pack['resumo']['total'] == visible.count()
    assert lider.pk not in set(visible.values_list('pk', flat=True))
    # Outsider com avaliação fora do QS não infla cobertura.
    Avaliacao.objects.get_or_create(ciclo=ciclo_aberto, usuario=outsider)
    pack_after = build_structure_coverage(visible, ciclo_aberto)
    assert pack_after['resumo']['total'] == 1
    assert pack_after['resumo']['com_avaliacao'] <= 1
