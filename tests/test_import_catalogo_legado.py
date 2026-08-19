"""T023+: importação do catálogo legado — fixtures CSV e de-paras.

T023: fixtures CSV temporárias + de-para ``Cargo.nivel`` / ``nivel_esperado``.
T024: filtro KPI (§6.1) + ambíguos (§6.2) — classificação e não-persistência.
T025: reconciliação de matriz (§8) + divergências reportadas (SC-004).
T026: idempotência (2ª execução) + soft-delete não reativado (§9 / SC-006).
T027: arquivo inválido/ausente → exit 1, DB inalterado (C5 / T021).
"""

from __future__ import annotations

import csv
from decimal import Decimal
from pathlib import Path

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from apps.competencies.models import CargoCompetencia, Competencia, Escala
from apps.competencies.services.catalog_import import CatalogParseError, import_catalog
from apps.competencies.services.catalog_import.mapping import (
    AMBIGUOUS_LEGACY_NAMES,
    classify_competencia,
    infer_cargo_nivel,
    is_ambiguous,
    is_kpi,
    nivel_esperado_for,
)
from apps.competencies.services.catalog_import.normalize import canonical_key
from apps.competencies.services.catalog_import.parse import CargoRow, CompetenciaRow
from apps.competencies.services.catalog_import.reconcile import (
    FONTE_LISTA_CARGOS,
    FONTE_LISTA_COMPETENCIAS,
    avaliavel_competencia_keys,
    detect_divergencias,
    extract_pairs_vista_a,
    extract_pairs_vista_b,
    reconcile_matrix,
)
from apps.organization.models import Cargo

# (nome do cargo, Cargo.nivel esperado, nivel_esperado do vínculo)
_SENIORIDADE_CASES: tuple[tuple[str, int, int], ...] = (
    ('Estagiário em Teste', 1, 2),
    ('Developer JR', 2, 2),
    ('Developer PL', 3, 3),
    ('Developer SR', 4, 4),
    ('Tech Lead Fullstack', 5, 4),
    ('Gerente Comercial', 6, 4),
    ('Analista Sem Sufixo', 6, 4),  # default §3
)

_COMPETENCIA_NOME = 'Aprendizado Contínuo'
_COMPETENCIA_GRUPO = 'Comportamento'


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> Path:
    with path.open('w', encoding='utf-8', newline='') as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return path


@pytest.fixture
def catalog_csv_paths(tmp_path: Path) -> tuple[Path, Path]:
    """Fixtures CSV mínimas cobrindo todos os níveis de senioridade (§3–4)."""
    cargo_names = [nome for nome, _, _ in _SENIORIDADE_CASES]
    pipe_cargos = '|'.join(cargo_names)
    pipe_comp = _COMPETENCIA_NOME

    cargos_path = _write_csv(
        tmp_path / 'lista-cargos.xlsx',
        ['Cargo', 'Competência'],
        [{'Cargo': nome, 'Competência': pipe_comp} for nome in cargo_names],
    )
    competencias_path = _write_csv(
        tmp_path / 'lista-competencias.xlsx',
        [
            'Competência',
            'Grupo de competência',
            'Descrição',
            'Peso',
            'Tipo de Avaliação',
            'Cargo',
        ],
        [
            {
                'Competência': _COMPETENCIA_NOME,
                'Grupo de competência': _COMPETENCIA_GRUPO,
                'Descrição': 'Demonstra curiosidade e aplica aprendizado.',
                'Peso': '1',
                'Tipo de Avaliação': 'Desempenho',
                'Cargo': pipe_cargos,
            }
        ],
    )
    return cargos_path, competencias_path


# --- De-para unitário (mapping) -------------------------------------------------


@pytest.mark.parametrize(
    ('nome', 'nivel_esperado'),
    [(nome, nivel) for nome, nivel, _ in _SENIORIDADE_CASES],
)
def test_infer_cargo_nivel_de_para(nome: str, nivel_esperado: int):
    """§3: primeira regra de token delimitado define ``Cargo.nivel``."""
    assert infer_cargo_nivel(nome) == nivel_esperado


@pytest.mark.parametrize(
    ('nivel', 'esperado'),
    [
        (1, 2),
        (2, 2),
        (3, 3),
        (4, 4),
        (5, 4),
        (6, 4),
    ],
)
def test_nivel_esperado_for_de_para(nivel: int, esperado: int):
    """§4: ``Cargo.nivel`` → ``CargoCompetencia.nivel_esperado``."""
    assert nivel_esperado_for(nivel) == esperado


def test_nivel_esperado_for_invalido():
    with pytest.raises(ValueError, match='Cargo.nivel inválido'):
        nivel_esperado_for(0)
    with pytest.raises(ValueError, match='Cargo.nivel inválido'):
        nivel_esperado_for(7)


def test_infer_cargo_nivel_token_boundary_nao_substring():
    """Tokens curtos (jr/pl/sr) não casam como substring de outra palavra."""
    assert infer_cargo_nivel('Surplus Role') == 6  # 'sr' dentro de surplus
    assert infer_cargo_nivel('Developer SR') == 4


# --- De-para via importação (fixtures CSV) --------------------------------------


@pytest.mark.django_db
def test_import_persiste_cargo_nivel_por_senioridade(catalog_csv_paths):
    """Após import, cada cargo tem ``nivel`` conforme de-para §3."""
    cargos_path, competencias_path = catalog_csv_paths

    import_catalog(cargos_path, competencias_path)

    for nome, nivel, _ in _SENIORIDADE_CASES:
        cargo = Cargo.objects.get(nome=nome, is_active=True)
        assert cargo.nivel == nivel, f'{nome!r}: nivel={cargo.nivel}, esperado={nivel}'


@pytest.mark.django_db
def test_import_persiste_nivel_esperado_e_peso(catalog_csv_paths):
    """Vínculos têm ``peso=1`` e ``nivel_esperado`` derivado do ``Cargo.nivel`` (§4)."""
    cargos_path, competencias_path = catalog_csv_paths

    import_catalog(cargos_path, competencias_path)

    competencia = Competencia.objects.get(nome=_COMPETENCIA_NOME, is_active=True)
    assert competencia.tipo == Competencia.Tipo.COMPORTAMENTAL

    for nome, nivel, nivel_esp in _SENIORIDADE_CASES:
        cargo = Cargo.objects.get(nome=nome, is_active=True)
        vinculo = CargoCompetencia.objects.get(cargo=cargo, competencia=competencia)
        assert vinculo.peso == Decimal('1')
        assert vinculo.nivel_esperado == Decimal(nivel_esp)
        assert nivel_esperado_for(nivel) == nivel_esp


# --- T024: Filtro KPI + ambíguos (§6) -------------------------------------------

_KPI_EXATOS: tuple[str, ...] = (
    'SLA',
    'Lead time discovery',
    'Custo de nuvem por transação',
    'Throughput por Colaborador',
    'Índice de incidentes',
    'Tempo médio de espera na esteira',
)

_KPI_FAMILIA: tuple[str, ...] = (
    'Throughput por colaborador - Arquiteto',
    'Índice de incidentes - QA Lead',
)

_AVALIAVEL_NOME = 'Comunicação Assertiva'
_CARGO_KPI_FIXTURE = 'Developer JR'


@pytest.mark.parametrize('nome', _KPI_EXATOS)
def test_is_kpi_match_exato(nome: str):
    """§6.1: igualdade canônica → KPI."""
    assert is_kpi(nome) is True


@pytest.mark.parametrize('nome', _KPI_FAMILIA)
def test_is_kpi_match_familia_sufixo(nome: str):
    """§6.1: base + separador + sufixo → mesma família KPI."""
    assert is_kpi(nome) is True


@pytest.mark.parametrize('nome', AMBIGUOUS_LEGACY_NAMES)
def test_is_ambiguous_lista_documentada(nome: str):
    """§6.2: nomes da lista documentada → ambíguo (igualdade canônica)."""
    assert is_ambiguous(nome) is True
    assert is_kpi(nome) is False


@pytest.mark.parametrize('nome', _KPI_EXATOS + _KPI_FAMILIA)
def test_classify_competencia_kpi_precede_grupo(nome: str):
    """§6 ordem 1: KPI → excluidos_kpi mesmo com grupo mapeável."""
    result = classify_competencia(nome, 'Desempenho')
    assert result.kind == 'excluidos_kpi'
    assert result.motivo == 'kpi_operacional'
    assert result.tipo is None


@pytest.mark.parametrize('nome', AMBIGUOUS_LEGACY_NAMES)
def test_classify_competencia_ambiguo_bloqueia_persistencia(nome: str):
    """§6.2: ambíguo → nao_mapeados (motivo=ambiguo); não avaliável."""
    result = classify_competencia(nome, 'Desempenho')
    assert result.kind == 'nao_mapeados'
    assert result.motivo == 'ambiguo'
    assert result.tipo is None


def test_classify_competencia_avaliavel_nao_kpi():
    """Habilidade com grupo mapeável permanece avaliável."""
    result = classify_competencia(_AVALIAVEL_NOME, 'Comportamento')
    assert result.kind == 'avaliavel'
    assert result.tipo == 'comportamental'


def test_is_kpi_nao_casa_substring_sem_separador():
    """Família exige separador após a base; substring solta não é KPI."""
    assert is_kpi('Throughput por ColaboradorExtra') is False
    assert is_kpi(_AVALIAVEL_NOME) is False


@pytest.fixture
def catalog_csv_kpi_ambiguos(tmp_path: Path) -> tuple[Path, Path]:
    """CSV com avaliável + KPIs (exatos/família) + ambíguos no mesmo cargo."""
    kpi_names = list(_KPI_EXATOS) + list(_KPI_FAMILIA)
    ambiguos = list(AMBIGUOUS_LEGACY_NAMES)
    pipe_comps = '|'.join([_AVALIAVEL_NOME, *kpi_names, *ambiguos])

    cargos_path = _write_csv(
        tmp_path / 'lista-cargos.xlsx',
        ['Cargo', 'Competência'],
        [{'Cargo': _CARGO_KPI_FIXTURE, 'Competência': pipe_comps}],
    )

    competencia_rows: list[dict[str, str]] = [
        {
            'Competência': _AVALIAVEL_NOME,
            'Grupo de competência': 'Comportamento',
            'Descrição': 'Comunica com clareza.',
            'Peso': '1',
            'Tipo de Avaliação': 'Desempenho',
            'Cargo': _CARGO_KPI_FIXTURE,
        },
    ]
    for nome in kpi_names:
        competencia_rows.append(
            {
                'Competência': nome,
                'Grupo de competência': 'Desempenho',
                'Descrição': 'Métrica operacional.',
                'Peso': '1',
                'Tipo de Avaliação': 'Desempenho',
                'Cargo': _CARGO_KPI_FIXTURE,
            }
        )
    for nome in ambiguos:
        competencia_rows.append(
            {
                'Competência': nome,
                'Grupo de competência': 'Desempenho',
                'Descrição': 'Item ambíguo documentado.',
                'Peso': '1',
                'Tipo de Avaliação': 'Desempenho',
                'Cargo': _CARGO_KPI_FIXTURE,
            }
        )

    competencias_path = _write_csv(
        tmp_path / 'lista-competencias.xlsx',
        [
            'Competência',
            'Grupo de competência',
            'Descrição',
            'Peso',
            'Tipo de Avaliação',
            'Cargo',
        ],
        competencia_rows,
    )
    return cargos_path, competencias_path


@pytest.mark.django_db
def test_import_exclui_kpi_do_catalogo_ativo(catalog_csv_kpi_ambiguos):
    """SC-005 / C3: KPIs no relatório ``excluidos_kpi`` e ausentes como ativas."""
    cargos_path, competencias_path = catalog_csv_kpi_ambiguos
    kpi_names = list(_KPI_EXATOS) + list(_KPI_FAMILIA)

    report = import_catalog(cargos_path, competencias_path)

    assert report.n_excluidos_kpi == len(kpi_names)
    excluidos_labels = {e.label for e in report.excluidos_kpi}
    for nome in kpi_names:
        assert nome in excluidos_labels
    assert all(e.motivo == 'kpi_operacional' for e in report.excluidos_kpi)

    for nome in kpi_names:
        assert not Competencia.objects.filter(nome=nome, is_active=True).exists()

    avaliavel = Competencia.objects.get(nome=_AVALIAVEL_NOME, is_active=True)
    assert avaliavel.tipo == Competencia.Tipo.COMPORTAMENTAL


@pytest.mark.django_db
def test_import_ambiguos_em_nao_mapeados_sem_persistir(catalog_csv_kpi_ambiguos):
    """§6.2: ambíguos em ``nao_mapeados`` (motivo=ambiguo); não criam Competencia."""
    cargos_path, competencias_path = catalog_csv_kpi_ambiguos

    report = import_catalog(cargos_path, competencias_path)

    ambiguos_entries = [e for e in report.nao_mapeados if e.motivo == 'ambiguo']
    assert len(ambiguos_entries) == len(AMBIGUOUS_LEGACY_NAMES)
    labels = {e.label for e in ambiguos_entries}
    for nome in AMBIGUOUS_LEGACY_NAMES:
        assert nome in labels
        assert not Competencia.objects.filter(nome=nome, is_active=True).exists()
        assert not Competencia.objects.filter(nome=nome).exists()


@pytest.mark.django_db
def test_import_kpi_e_ambiguo_nao_viram_vinculo(catalog_csv_kpi_ambiguos):
    """Pares com competência KPI/ambígua não entram na matriz (§8)."""
    cargos_path, competencias_path = catalog_csv_kpi_ambiguos
    kpi_names = list(_KPI_EXATOS) + list(_KPI_FAMILIA)

    import_catalog(cargos_path, competencias_path)

    cargo = Cargo.objects.get(nome=_CARGO_KPI_FIXTURE, is_active=True)
    avaliavel = Competencia.objects.get(nome=_AVALIAVEL_NOME, is_active=True)
    assert CargoCompetencia.objects.filter(
        cargo=cargo, competencia=avaliavel
    ).exists()

    for nome in (*kpi_names, *AMBIGUOUS_LEGACY_NAMES):
        assert not CargoCompetencia.objects.filter(
            cargo=cargo, competencia__nome=nome
        ).exists()


# --- T025: Reconciliação de matriz + divergências (§8 / SC-004) -----------------

_COMP_SHARED = 'Aprendizado Contínuo'
_COMP_ONLY_A = 'Comunicação Assertiva'
_COMP_ONLY_B = 'Resolução de Problemas'
_COMP_KPI = 'SLA'
_CARGO_A = 'Developer JR'
_CARGO_B = 'Developer PL'


def _competencia_row(
    nome: str,
    cargos: tuple[str, ...],
    *,
    grupo: str = 'Comportamento',
) -> CompetenciaRow:
    return CompetenciaRow(
        nome=nome,
        grupo=grupo,
        descricao=f'Desc {nome}',
        cargos=cargos,
    )


def test_extract_pairs_vistas_a_e_b():
    """§8: Vista A expande pipe de competências; Vista B expande pipe de cargos."""
    pairs_a = extract_pairs_vista_a(
        [
            CargoRow(nome=_CARGO_A, competencias=(_COMP_SHARED, _COMP_ONLY_A)),
        ]
    )
    pairs_b = extract_pairs_vista_b(
        [
            _competencia_row(_COMP_SHARED, (_CARGO_A, _CARGO_B)),
            _competencia_row(_COMP_ONLY_B, (_CARGO_A,)),
        ]
    )

    assert set(pairs_a) == {
        (canonical_key(_CARGO_A), canonical_key(_COMP_SHARED)),
        (canonical_key(_CARGO_A), canonical_key(_COMP_ONLY_A)),
    }
    assert set(pairs_b) == {
        (canonical_key(_CARGO_A), canonical_key(_COMP_SHARED)),
        (canonical_key(_CARGO_B), canonical_key(_COMP_SHARED)),
        (canonical_key(_CARGO_A), canonical_key(_COMP_ONLY_B)),
    }


def test_detect_divergencias_symmetric_difference():
    """§8: divergências = A' ⊖ B' com motivo = fonte exclusiva."""
    pairs_a = extract_pairs_vista_a(
        [CargoRow(nome=_CARGO_A, competencias=(_COMP_SHARED, _COMP_ONLY_A))]
    )
    pairs_b = extract_pairs_vista_b(
        [
            _competencia_row(_COMP_SHARED, (_CARGO_A, _CARGO_B)),
            _competencia_row(_COMP_ONLY_B, (_CARGO_A,)),
        ]
    )

    divergencias = detect_divergencias(pairs_a, pairs_b)

    by_motivo = {(e.label, e.extra, e.motivo) for e in divergencias}
    assert (_CARGO_A, _COMP_ONLY_A, FONTE_LISTA_CARGOS) in by_motivo
    assert (_CARGO_B, _COMP_SHARED, FONTE_LISTA_COMPETENCIAS) in by_motivo
    assert (_CARGO_A, _COMP_ONLY_B, FONTE_LISTA_COMPETENCIAS) in by_motivo
    assert len(divergencias) == 3
    # Par comum não entra em divergências
    assert not any(e.extra == _COMP_SHARED and e.label == _CARGO_A for e in divergencias)


def test_reconcile_matrix_uniao_e_filtra_kpi():
    """§8: matriz = união A'∪B'; KPI não entra em matriz nem em divergências."""
    pairs_a = extract_pairs_vista_a(
        [
            CargoRow(
                nome=_CARGO_A,
                competencias=(_COMP_SHARED, _COMP_ONLY_A, _COMP_KPI),
            )
        ]
    )
    pairs_b = extract_pairs_vista_b(
        [
            _competencia_row(_COMP_SHARED, (_CARGO_A,)),
            _competencia_row(_COMP_ONLY_B, (_CARGO_A,)),
            _competencia_row(_COMP_KPI, (_CARGO_A,), grupo='Desempenho'),
        ]
    )
    comps = [
        _competencia_row(_COMP_SHARED, (_CARGO_A,)),
        _competencia_row(_COMP_ONLY_A, (_CARGO_A,)),
        _competencia_row(_COMP_ONLY_B, (_CARGO_A,)),
        _competencia_row(_COMP_KPI, (_CARGO_A,), grupo='Desempenho'),
    ]
    avaliavel = avaliavel_competencia_keys(comps)
    cargo_k = canonical_key(_CARGO_A)
    resolved_comps = avaliavel  # todas avaliáveis resolvidas

    result = reconcile_matrix(
        pairs_a,
        pairs_b,
        avaliavel_keys=avaliavel,
        resolved_cargo_keys={cargo_k},
        resolved_competencia_keys=resolved_comps,
    )

    matriz_keys = {p.key for p in result.matriz}
    assert matriz_keys == {
        (cargo_k, canonical_key(_COMP_SHARED)),
        (cargo_k, canonical_key(_COMP_ONLY_A)),
        (cargo_k, canonical_key(_COMP_ONLY_B)),
    }
    assert canonical_key(_COMP_KPI) not in avaliavel
    assert all(p.competencia_key != canonical_key(_COMP_KPI) for p in result.matriz)
    assert all(e.extra != _COMP_KPI for e in result.divergencias)

    div_motivos = {(e.extra, e.motivo) for e in result.divergencias}
    assert (_COMP_ONLY_A, FONTE_LISTA_CARGOS) in div_motivos
    assert (_COMP_ONLY_B, FONTE_LISTA_COMPETENCIAS) in div_motivos


def test_reconcile_matrix_identica_zero_divergencias():
    """FR-005: mesmas vistas após normalização → matriz idêntica, 0 divergências."""
    pairs_a = extract_pairs_vista_a(
        [CargoRow(nome=_CARGO_A, competencias=(_COMP_SHARED,))]
    )
    pairs_b = extract_pairs_vista_b(
        [_competencia_row(_COMP_SHARED, (_CARGO_A,))]
    )
    avaliavel = frozenset({canonical_key(_COMP_SHARED)})

    result = reconcile_matrix(
        pairs_a,
        pairs_b,
        avaliavel_keys=avaliavel,
        resolved_cargo_keys={canonical_key(_CARGO_A)},
        resolved_competencia_keys=avaliavel,
    )

    assert len(result.divergencias) == 0
    assert len(result.matriz) == 1
    assert result.matriz[0].key == (
        canonical_key(_CARGO_A),
        canonical_key(_COMP_SHARED),
    )


@pytest.fixture
def catalog_csv_matriz_identica(tmp_path: Path) -> tuple[Path, Path]:
    """Duas fontes com o mesmo par cargo↔competência (SC-004 matriz idêntica)."""
    cargos_path = _write_csv(
        tmp_path / 'lista-cargos.xlsx',
        ['Cargo', 'Competência'],
        [{'Cargo': _CARGO_A, 'Competência': _COMP_SHARED}],
    )
    competencias_path = _write_csv(
        tmp_path / 'lista-competencias.xlsx',
        [
            'Competência',
            'Grupo de competência',
            'Descrição',
            'Peso',
            'Tipo de Avaliação',
            'Cargo',
        ],
        [
            {
                'Competência': _COMP_SHARED,
                'Grupo de competência': 'Comportamento',
                'Descrição': 'Aprende continuamente.',
                'Peso': '1',
                'Tipo de Avaliação': 'Desempenho',
                'Cargo': _CARGO_A,
            }
        ],
    )
    return cargos_path, competencias_path


@pytest.fixture
def catalog_csv_matriz_divergente(tmp_path: Path) -> tuple[Path, Path]:
    """Fontes com pares exclusivos em A e em B (união + divergências)."""
    # A: CargoA↔Shared, CargoA↔OnlyA | B: Shared↔CargoA|CargoB, OnlyB↔CargoA
    cargos_path = _write_csv(
        tmp_path / 'lista-cargos.xlsx',
        ['Cargo', 'Competência'],
        [
            {
                'Cargo': _CARGO_A,
                'Competência': f'{_COMP_SHARED}|{_COMP_ONLY_A}',
            },
            {'Cargo': _CARGO_B, 'Competência': ''},
        ],
    )
    competencias_path = _write_csv(
        tmp_path / 'lista-competencias.xlsx',
        [
            'Competência',
            'Grupo de competência',
            'Descrição',
            'Peso',
            'Tipo de Avaliação',
            'Cargo',
        ],
        [
            {
                'Competência': _COMP_SHARED,
                'Grupo de competência': 'Comportamento',
                'Descrição': 'Compartilhada nas duas vistas.',
                'Peso': '1',
                'Tipo de Avaliação': 'Desempenho',
                'Cargo': f'{_CARGO_A}|{_CARGO_B}',
            },
            {
                'Competência': _COMP_ONLY_A,
                'Grupo de competência': 'Comportamento',
                'Descrição': 'Só listada em cargos (sem cargos na vista B).',
                'Peso': '1',
                'Tipo de Avaliação': 'Desempenho',
                'Cargo': '',
            },
            {
                'Competência': _COMP_ONLY_B,
                'Grupo de competência': 'Comportamento',
                'Descrição': 'Só na lista de competências.',
                'Peso': '1',
                'Tipo de Avaliação': 'Desempenho',
                'Cargo': _CARGO_A,
            },
        ],
    )
    return cargos_path, competencias_path


@pytest.mark.django_db
def test_import_matriz_identica_zero_divergencias(catalog_csv_matriz_identica):
    """SC-004: fontes alinhadas → ``divergencias: 0`` e vínculo único."""
    cargos_path, competencias_path = catalog_csv_matriz_identica

    report = import_catalog(cargos_path, competencias_path)

    assert len(report.divergencias) == 0
    assert report.vinculos_criados == 1

    cargo = Cargo.objects.get(nome=_CARGO_A, is_active=True)
    competencia = Competencia.objects.get(nome=_COMP_SHARED, is_active=True)
    assert CargoCompetencia.objects.filter(
        cargo=cargo, competencia=competencia
    ).exists()


@pytest.mark.django_db
def test_import_reporta_divergencias_e_grava_uniao(catalog_csv_matriz_divergente):
    """SC-004 / §8: divergências no relatório; união grava pares elegíveis."""
    cargos_path, competencias_path = catalog_csv_matriz_divergente

    report = import_catalog(cargos_path, competencias_path)

    by_pair = {(e.label, e.extra, e.motivo) for e in report.divergencias}
    assert (_CARGO_A, _COMP_ONLY_A, FONTE_LISTA_CARGOS) in by_pair
    assert (_CARGO_B, _COMP_SHARED, FONTE_LISTA_COMPETENCIAS) in by_pair
    assert (_CARGO_A, _COMP_ONLY_B, FONTE_LISTA_COMPETENCIAS) in by_pair
    assert len(report.divergencias) == 3
    # Par comum não é divergência
    assert not any(
        e.label == _CARGO_A and e.extra == _COMP_SHARED for e in report.divergencias
    )

    cargo_a = Cargo.objects.get(nome=_CARGO_A, is_active=True)
    cargo_b = Cargo.objects.get(nome=_CARGO_B, is_active=True)
    shared = Competencia.objects.get(nome=_COMP_SHARED, is_active=True)
    only_a = Competencia.objects.get(nome=_COMP_ONLY_A, is_active=True)
    only_b = Competencia.objects.get(nome=_COMP_ONLY_B, is_active=True)

    expected_pairs = {
        (cargo_a.pk, shared.pk),
        (cargo_a.pk, only_a.pk),
        (cargo_a.pk, only_b.pk),
        (cargo_b.pk, shared.pk),
    }
    actual_pairs = set(
        CargoCompetencia.objects.values_list('cargo_id', 'competencia_id')
    )
    assert actual_pairs == expected_pairs
    assert report.vinculos_criados == 4


# --- T026: Idempotência (2ª execução) + soft-delete (§9 / SC-006) --------------


@pytest.mark.django_db
def test_import_segunda_execucao_sem_duplicatas(catalog_csv_matriz_identica):
    """SC-006 / C4: 2ª execução idêntica → delta de ativos duplicados = 0."""
    cargos_path, competencias_path = catalog_csv_matriz_identica

    first = import_catalog(cargos_path, competencias_path)
    assert first.cargos_criados == 1
    assert first.competencias_criadas == 1
    assert first.vinculos_criados == 1

    n_cargos = Cargo.objects.filter(is_active=True).count()
    n_comps = Competencia.objects.filter(is_active=True).count()
    n_vinculos = CargoCompetencia.objects.count()

    second = import_catalog(cargos_path, competencias_path)

    assert second.cargos_criados == 0
    assert second.competencias_criadas == 0
    assert second.vinculos_criados == 0
    assert second.cargos_inalterados == 1
    assert second.competencias_inalteradas == 1
    assert second.vinculos_inalterados == 1

    assert Cargo.objects.filter(is_active=True).count() == n_cargos
    assert Competencia.objects.filter(is_active=True).count() == n_comps
    assert CargoCompetencia.objects.count() == n_vinculos
    assert Cargo.objects.filter(is_active=True, nome=_CARGO_A).count() == 1
    assert Competencia.objects.filter(is_active=True, nome=_COMP_SHARED).count() == 1


@pytest.mark.django_db
def test_import_soft_delete_cargo_nao_reativado(catalog_csv_matriz_identica):
    """§9 / C4: cargo inativo permanece inativo; conflito ``inativo_existente``."""
    cargos_path, competencias_path = catalog_csv_matriz_identica
    import_catalog(cargos_path, competencias_path)

    cargo = Cargo.objects.get(nome=_CARGO_A, is_active=True)
    cargo.is_active = False
    cargo.save(update_fields=['is_active', 'updated_at'])

    report = import_catalog(cargos_path, competencias_path)

    cargo.refresh_from_db()
    assert cargo.is_active is False
    assert not Cargo.objects.filter(nome=_CARGO_A, is_active=True).exists()
    assert report.cargos_criados == 0

    conflitos = [
        (e.label, e.extra, e.motivo) for e in report.conflitos
    ]
    assert ('cargo', _CARGO_A, 'inativo_existente') in conflitos


@pytest.mark.django_db
def test_import_soft_delete_competencia_nao_reativada(catalog_csv_matriz_identica):
    """§9 / C4: competência inativa permanece inativa; conflito reportado."""
    cargos_path, competencias_path = catalog_csv_matriz_identica
    import_catalog(cargos_path, competencias_path)

    competencia = Competencia.objects.get(nome=_COMP_SHARED, is_active=True)
    competencia.is_active = False
    competencia.save(update_fields=['is_active', 'updated_at'])

    report = import_catalog(cargos_path, competencias_path)

    competencia.refresh_from_db()
    assert competencia.is_active is False
    assert not Competencia.objects.filter(
        nome=_COMP_SHARED, is_active=True
    ).exists()
    assert report.competencias_criadas == 0

    conflitos = [
        (e.label, e.extra, e.motivo) for e in report.conflitos
    ]
    assert ('competencia', _COMP_SHARED, 'inativo_existente') in conflitos


# --- T027: Arquivo inválido/ausente (exit 1, DB inalterado) — C5 / T021 --------


def _catalog_db_counts() -> tuple[int, int, int, int]:
    """Snapshot de Escala / Cargo / Competencia / CargoCompetencia."""
    return (
        Escala.objects.count(),
        Cargo.objects.count(),
        Competencia.objects.count(),
        CargoCompetencia.objects.count(),
    )


@pytest.mark.django_db
def test_import_arquivo_ausente_exit_1_db_inalterado(
    catalog_csv_matriz_identica, tmp_path: Path
):
    """C5: path inexistente → exit 1; nenhuma escrita parcial."""
    cargos_path, _ = catalog_csv_matriz_identica
    missing = tmp_path / 'lista-competencias-inexistente.xlsx'
    before = _catalog_db_counts()

    with pytest.raises(CommandError) as exc_info:
        call_command(
            'importar_competencias_cargo',
            cargos=str(cargos_path),
            competencias=str(missing),
        )

    assert exc_info.value.returncode == 1
    assert 'não encontrado' in str(exc_info.value).lower()
    assert _catalog_db_counts() == before

    with pytest.raises(CatalogParseError, match='não encontrado'):
        import_catalog(cargos_path, missing)
    assert _catalog_db_counts() == before


@pytest.mark.django_db
def test_import_csv_colunas_invalidas_exit_1_db_inalterado(tmp_path: Path):
    """C5: CSV sem colunas obrigatórias → exit 1; DB inalterado."""
    cargos_path = _write_csv(
        tmp_path / 'lista-cargos.xlsx',
        ['Cargo', 'Competência'],
        [{'Cargo': _CARGO_A, 'Competência': _COMP_SHARED}],
    )
    competencias_path = _write_csv(
        tmp_path / 'lista-competencias.xlsx',
        ['NomeErrado', 'OutraColuna'],
        [{'NomeErrado': _COMP_SHARED, 'OutraColuna': 'x'}],
    )
    before = _catalog_db_counts()

    with pytest.raises(CommandError) as exc_info:
        call_command(
            'importar_competencias_cargo',
            cargos=str(cargos_path),
            competencias=str(competencias_path),
        )

    assert exc_info.value.returncode == 1
    assert 'colunas obrigatórias ausentes' in str(exc_info.value).lower()
    assert _catalog_db_counts() == before

    with pytest.raises(CatalogParseError, match='Colunas obrigatórias ausentes'):
        import_catalog(cargos_path, competencias_path)
    assert _catalog_db_counts() == before
