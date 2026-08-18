"""T006+: importação notas/comentários legado Sólides — relatório mascarado.

T006: ``format_notas_comentarios_report`` (seções estáveis, máx. 5,
sem comentário/nome/e-mail). Sem persistência. **Proibido** ``raw/``.

T007: ``resolve.py`` — mapa colapsado, ``resolve_avaliacao``, ``is_auto``,
``is_ciclo_aberto``, ``resolve_competencia`` (R11). **Proibido** ``raw/``.

T008: ``snapshots.py`` — peso do Fator, nível da tabela 003, write-once.
**Proibido** ``raw/``. **Proibido** ler ``CargoCompetencia``.

T009: fase Notas em ``importer.py`` — agrupa, upsert, fórmula vigente.
**Proibido** ``create_competency_lines`` / mutar ``etapa``/``concluida``.

T010: management command ``importar_notas_comentarios`` (args, relatório,
exit 0/1). Fase Comentários stub até US2.

T011: validação US1 via quickstart C2–C5 (auto vs líder, snapshots 003,
ID canônico/colapsado/órfão, dois líderes, ciclo aberto, fórmula vigente,
spy ``create_competency_lines``, ``git diff`` denylist).

T018–T023 estendem esta suíte (dry-run, IDs, conflitos, comentários).
"""

from __future__ import annotations

import shutil
import subprocess
from datetime import date
from decimal import Decimal
from io import StringIO
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from django.core.exceptions import ValidationError
from django.core.management import call_command, get_commands
from django.core.management.base import CommandError
from openpyxl import Workbook

from apps.accounts.services.legacy_import.report import (
    ImportReport,
    format_notas_comentarios_report,
    mask_solides_id,
    record_comentario_criado,
    record_comentario_inalterado,
    record_conflito,
    record_conflito_ciclo_aberto,
    record_conflito_lider_divergente,
    record_habilidade_extra_criada,
    record_id_colapsado_resolvido,
    record_nota_atualizada,
    record_nota_criada,
    record_nota_inalterada,
    record_orfao_autor,
    record_orfao_avaliacao,
    record_orfao_competencia,
)
from apps.competencies.models import CargoCompetencia, Competencia, Escala
from apps.cycles.models import Ciclo
from apps.reviews.exceptions import CalculationError
from apps.reviews.models import Avaliacao, AvaliacaoCompetencia, Feedback
from apps.reviews.services.evaluation import calcular_nota_final_lider
from apps.reviews.services.legacy_import import format_notas_comentarios_report as _reexport
from apps.reviews.services.legacy_import.importer import import_notas_comentarios
from apps.reviews.services.legacy_import.resolve import (
    build_collapsed_id_map,
    is_auto,
    is_ciclo_aberto,
    resolve_avaliacao,
    resolve_competencia,
)
from apps.reviews.services.legacy_import.snapshots import (
    SnapshotConflict,
    apply_snapshots,
    conflict_from_write_once,
    parse_peso_utilizado,
    resolve_nivel_esperado,
)

_SAMPLE_MAX = 5
_EMAIL = 'ana.silva@example.com'
_NOME = 'Ana Silva'
_COMENTARIO = 'Texto completo de feedback que NUNCA pode ir ao relatório.'
_CPF = '000.000.000-00'
_AVALIACAO_ID = 'SOLIDES-AV1001'
_COMPETENCIA_ID = 'HAB12'
_AUTOR_ID = 'USR88'
_SAMPLES_DIR = Path(__file__).resolve().parents[1] / 'data' / 'legado-solides' / 'samples'
_AVALIACOES_HEADERS_MIN = _SAMPLES_DIR / 'avaliacoes_headers_min.xlsx'
_REPO_ROOT = Path(__file__).resolve().parents[1]
_IMPORT_NOTAS_COMMAND = (
    _REPO_ROOT
    / 'apps'
    / 'reviews'
    / 'management'
    / 'commands'
    / 'importar_notas_comentarios.py'
)
_DENYLIST_IMPORT_TOKENS = (
    'apps.cycles.services.stage',
    'apps.cycles.services.cycle',
    'apps.goals.services.approval',
    'apps.accounts.services.scope',
    'create_competency_lines',
    'calcular_aderencia',
    'celery',
    'rest_framework',
    'openpyxl',
)
_DENYLIST_PATHS = (
    'apps/cycles/services/stage.py',
    'apps/cycles/services/cycle.py',
    'apps/goals/services/approval.py',
    'apps/accounts/services/scope.py',
    'apps/reviews/services/evaluation.py',
    'apps/dashboard/services/adherence.py',
    'apps/dashboard/urls.py',
    'apps/cycles/urls.py',
    'apps/pdi',
    'apps/talent',
)


def _amostra_items_by_section(text: str) -> dict[str, list[str]]:
    marker = '--- Amostra (mascarada, max 5 por seção) ---'
    assert marker in text
    body = text.split(marker, 1)[1].split('=== Fim ===', 1)[0]
    sections: dict[str, list[str]] = {}
    current: str | None = None
    for raw in body.splitlines():
        stripped = raw.strip()
        if not stripped:
            continue
        if stripped.endswith(':') and not stripped.startswith('-'):
            current = stripped
            sections[current] = []
            continue
        if current is not None and stripped.startswith('-'):
            sections[current].append(stripped)
    return sections


def test_format_notas_comentarios_report_reexportado_na_api_publica():
    assert _reexport is format_notas_comentarios_report


def test_format_notas_comentarios_report_mascara_e_trunca_max_5():
    """T006 / SC-010: amostra ≤ 5; sem comentário, nome, e-mail ou ID completo."""
    report = ImportReport(
        modo='persist',
        notas_file='samples/notas_min.xlsx',
        comentarios_file='samples/comentarios_min.xlsx',
        avaliacoes_file='samples/avaliacoes_headers_min.xlsx',
    )
    record_nota_criada(
        report,
        avaliacao_id=_AVALIACAO_ID,
        competencia_id=_COMPETENCIA_ID,
        lado='lider',
    )
    record_nota_atualizada(
        report,
        avaliacao_id=_AVALIACAO_ID,
        competencia_id=_COMPETENCIA_ID,
        lado='auto',
    )
    record_nota_inalterada(
        report,
        avaliacao_id=_AVALIACAO_ID,
        competencia_id=_COMPETENCIA_ID,
        lado='lider',
    )
    record_comentario_criado(
        report,
        avaliacao_id=_AVALIACAO_ID,
        autor_id=_AUTOR_ID,
        tipo='lider',
    )
    record_comentario_inalterado(
        report,
        avaliacao_id=_AVALIACAO_ID,
        autor_id=_AUTOR_ID,
        tipo='colaborador',
    )
    record_habilidade_extra_criada(
        report, solides_id='HAB80', tipo='tecnica'
    )
    record_conflito(
        report,
        tipo='nota_fora_da_escala',
        extra=f'avaliacao={_AVALIACAO_ID} | competencia={_COMPETENCIA_ID}',
        motivo=f'email={_EMAIL} | cpf={_CPF} | nome={_NOME}',
    )
    record_conflito(
        report,
        tipo='fator_invalido',
        motivo='linha=120',
    )
    record_conflito(
        report,
        tipo='snapshot_divergente',
        extra=f'avaliacao={_AVALIACAO_ID} | competencia={_COMPETENCIA_ID}',
    )
    record_conflito(
        report,
        tipo='calculo_lider',
        extra=f'avaliacao={_AVALIACAO_ID}',
    )
    record_conflito(
        report,
        tipo='ciencia_data_invalida',
        motivo='linha=30',
    )
    for i in range(8):
        record_orfao_avaliacao(report, id_legado=f'av{i:04d}')
        record_orfao_competencia(report, habilidade_id=f'hb{i:04d}')
        record_orfao_autor(report, avaliador_id=f'au{i:04d}')
        record_conflito_lider_divergente(
            report,
            avaliacao_id=f'ld{i:04d}',
            competencia_id=f'cp{i:04d}',
        )
        record_conflito_ciclo_aberto(
            report,
            avaliacao_id=f'ca{i:04d}',
            ciclo=f'ci{i:04d}',
        )
        record_id_colapsado_resolvido(
            report,
            colapsado=f'col{i:04d}',
            canonico=f'can{i:04d}',
        )
        if i == 0:
            continue
        record_nota_criada(
            report,
            avaliacao_id=f'nt{i:04d}',
            competencia_id=f'cm{i:04d}',
            lado='auto',
        )
        record_comentario_criado(
            report,
            avaliacao_id=f'fb{i:04d}',
            autor_id=f'at{i:04d}',
            tipo='lider',
        )
        record_conflito(
            report,
            tipo='nivel_irresolvivel',
            extra=f'avaliacao=nt{i:04d}',
            motivo=f'linha={i}',
        )

    text = format_notas_comentarios_report(report)

    assert text.startswith('=== Importação notas/comentários legado Sólides ===')
    assert 'modo: persist' in text
    assert 'notas_file: samples/notas_min.xlsx' in text
    assert 'habilidades_file: (omitido)' in text
    assert 'notas_criadas: 8' in text
    assert 'comentarios_criados: 8' in text
    assert 'orfaos_avaliacao: 8' in text
    assert 'orfaos_competencia: 8' in text
    assert 'orfaos_autor: 8' in text
    assert 'conflitos_lider_divergente: 8' in text
    assert 'conflitos_ciclo_aberto: 8' in text
    assert 'ids_colapsados_resolvidos: 8' in text
    assert 'habilidades_extras_criadas: 1' in text
    assert report.n_conflitos == 12
    assert 'conflitos: 12' in text

    assert _EMAIL not in text
    assert _EMAIL.lower() not in text.lower()
    assert _NOME not in text
    assert _COMENTARIO not in text
    assert _CPF not in text
    assert _AVALIACAO_ID not in text
    assert _COMPETENCIA_ID not in text
    assert _AUTOR_ID not in text
    assert mask_solides_id(_AVALIACAO_ID) in text
    assert mask_solides_id(_COMPETENCIA_ID) in text
    assert 'a***@example.com' in text
    assert 'cpf=***' in text.lower()
    assert 'lado=lider' in text
    assert 'tipo=colaborador' in text
    assert ' → canônico=' in text

    sections = _amostra_items_by_section(text)
    for header in (
        'notas_criadas:',
        'comentarios_criados:',
        'orfaos_avaliacao:',
        'orfaos_competencia:',
        'orfaos_autor:',
        'conflitos_lider_divergente:',
        'conflitos_ciclo_aberto:',
        'ids_colapsados_resolvidos:',
        'conflitos:',
    ):
        assert len(sections[header]) == _SAMPLE_MAX, header
    for header, items in sections.items():
        assert len(items) <= _SAMPLE_MAX, header
        for item in items:
            assert _COMENTARIO not in item
            assert _EMAIL not in item
            assert _NOME not in item


def test_t007_build_collapsed_id_map_consome_aggregate_011():
    """T007 / R3: mapa em memória; canônico→si; colapsados→canônico; sem raw/."""
    assert 'raw' not in _AVALIACOES_HEADERS_MIN.parts
    mapa = build_collapsed_id_map(_AVALIACOES_HEADERS_MIN)
    assert mapa['1001'] == '1001'
    assert mapa['1002'] == '1001'
    assert mapa['1003'] == '1001'
    assert mapa['2001'] == '2001'
    assert mapa['2003'] == '2001'
    assert mapa['2005'] == '2001'
    assert mapa['3001'] == '3001'


def test_t007_is_auto_via_canonical_key():
    """T007 / R5: mesmos nomes canônicos (acento/caixa) e ambos não-vazios."""
    assert is_auto('Ana Silva', 'Ana Silva') is True
    assert is_auto('ANA SILVA', 'Ana Silva') is True
    assert is_auto('José', 'Jose') is True
    assert is_auto('Ana Silva', 'Bruno Costa') is False
    assert is_auto('', 'Ana Silva') is False
    assert is_auto('Ana Silva', '') is False
    assert is_auto('', '') is False


def _ciclo_encerrado() -> Ciclo:
    return Ciclo.objects.create(
        nome='Ciclo Histórico T007',
        data_inicio=date(2024, 1, 1),
        data_fim=date(2024, 12, 31),
        status=Ciclo.Status.ENCERRADO,
    )


@pytest.mark.django_db
def test_t007_resolve_avaliacao_canonico_mapa_orfao(colaborador):
    """T007: canônico → hit direto; colapsado → mapa; órfão → None; zero create."""
    ciclo = _ciclo_encerrado()
    avaliacao = Avaliacao.objects.create(
        ciclo=ciclo,
        usuario=colaborador,
        etapa=Avaliacao.Etapa.FEEDBACK,
        concluida=True,
        solides_id='1001',
    )
    mapa = {'1001': '1001', '1002': '1001', '1003': '1001'}
    before = Avaliacao.objects.count()

    direto = resolve_avaliacao('1001', mapa)
    assert direto.avaliacao == avaliacao
    assert direto.via_collapsed is False

    colapsado = resolve_avaliacao('1002', mapa)
    assert colapsado.avaliacao == avaliacao
    assert colapsado.via_collapsed is True
    assert colapsado.avaliacao.solides_id == '1001'

    orfao = resolve_avaliacao('9999', mapa)
    assert orfao.avaliacao is None
    assert orfao.via_collapsed is False

    vazio = resolve_avaliacao('', mapa)
    assert vazio.avaliacao is None
    assert Avaliacao.objects.count() == before


@pytest.mark.django_db
def test_t007_is_ciclo_aberto_nao_usa_get_open_ciclo(colaborador, ciclo_aberto):
    """T007 / R10: skip se status=aberto; encerrado segue; sem get_open_ciclo."""
    historico = Avaliacao.objects.create(
        ciclo=_ciclo_encerrado(),
        usuario=colaborador,
        etapa=Avaliacao.Etapa.FEEDBACK,
        concluida=True,
        solides_id='1001',
    )
    operacional = Avaliacao.objects.get(ciclo=ciclo_aberto, usuario=colaborador)
    operacional.solides_id = '8001'
    operacional.save(update_fields=['solides_id'])

    assert is_ciclo_aberto(historico) is False
    assert is_ciclo_aberto(operacional) is True


@pytest.mark.django_db
def test_t007_resolve_competencia_r11_sem_cargo_competencia():
    """T007 / R11: hit por solides_id; extra mínima; KPI/ambíguo órfão; zero matriz."""
    escala = Escala.objects.create(
        nome='Escala T007',
        valor_minimo=1,
        valor_maximo=5,
        is_active=True,
    )
    catalogo = Competencia.objects.create(
        nome='Comunicação T007',
        tipo=Competencia.Tipo.COMPORTAMENTAL,
        escala=escala,
        solides_id='HAB10',
        is_active=True,
    )
    before_vinculos = CargoCompetencia.objects.count()

    hit = resolve_competencia('HAB10', 'Comunicação T007')
    assert hit.competencia == catalogo
    assert hit.created is False

    extra = resolve_competencia('99001', 'Habilidade Extra T007', grupo='Liderança')
    assert extra.created is True
    assert extra.competencia is not None
    assert extra.competencia.solides_id == '99001'
    assert extra.competencia.nome == 'Habilidade Extra T007'
    assert extra.competencia.tipo == Competencia.Tipo.LIDERANCA
    assert extra.competencia.descricao == ''
    assert extra.competencia.is_active is True

    replay = resolve_competencia('99001', 'Habilidade Extra T007', grupo='Liderança')
    assert replay.created is False
    assert replay.competencia == extra.competencia

    default_tipo = resolve_competencia('99002', 'Outra Extra T007')
    assert default_tipo.created is True
    assert default_tipo.competencia.tipo == Competencia.Tipo.TECNICA

    kpi = resolve_competencia('99003', 'SLA')
    assert kpi.competencia is None
    assert kpi.created is False

    assert CargoCompetencia.objects.count() == before_vinculos
    assert Competencia.objects.filter(solides_id='99003').exists() is False


# --- T008 snapshots ---


@pytest.mark.parametrize(
    ('fator', 'esperado'),
    [
        (1, Decimal('1.00')),
        (2.0, Decimal('2.00')),
        ('1,5', Decimal('1.50')),
        ('3.25', Decimal('3.25')),
        (Decimal('4'), Decimal('4.00')),
    ],
)
def test_t008_parse_peso_utilizado_fator_valido(fator, esperado):
    """T008 / R7: peso ← Decimal(Fator); não assume 1."""
    assert parse_peso_utilizado(fator) == esperado


@pytest.mark.parametrize(
    'fator',
    [None, '', '   ', 'abc', 0, 0.0, -1, Decimal('0'), True, False],
)
def test_t008_parse_peso_utilizado_fator_invalido(fator):
    """T008: ausente / não-numérico / ≤0 → fator_invalido; nunca peso 1."""
    with pytest.raises(SnapshotConflict) as excinfo:
        parse_peso_utilizado(fator)
    assert excinfo.value.code == 'fator_invalido'


def test_t008_resolve_nivel_esperado_tabela_003():
    """T008 / R7: 1→2, 2→2, 3→3, 4→4, 5→4, 6→4; cargo do avaliado."""
    mapping = {1: 2, 2: 2, 3: 3, 4: 4, 5: 4, 6: 4}
    for cargo_nivel, esperado in mapping.items():
        avaliado = SimpleNamespace(cargo=SimpleNamespace(nivel=cargo_nivel))
        assert resolve_nivel_esperado(avaliado) == esperado


@pytest.mark.parametrize(
    'avaliado',
    [
        None,
        SimpleNamespace(cargo=None),
        SimpleNamespace(cargo=SimpleNamespace(nivel=None)),
        SimpleNamespace(cargo=SimpleNamespace(nivel=0)),
        SimpleNamespace(cargo=SimpleNamespace(nivel=7)),
    ],
)
def test_t008_resolve_nivel_esperado_irresolvivel(avaliado):
    """T008: cargo None / nível ausente / ValueError → nivel_irresolvivel."""
    with pytest.raises(SnapshotConflict) as excinfo:
        resolve_nivel_esperado(avaliado)
    assert excinfo.value.code == 'nivel_irresolvivel'


def test_t008_resolve_nivel_esperado_nao_le_cargo_competencia():
    """T008: tabela 003 only — CargoCompetencia vigente divergente é ignorado."""
    cargo = SimpleNamespace(nivel=1)
    vigente = MagicMock()
    vigente.nivel_esperado = Decimal('9.00')
    vigente.peso = Decimal('99.00')
    avaliado = SimpleNamespace(cargo=cargo, cargo_competencia=vigente)
    assert resolve_nivel_esperado(avaliado) == 2
    vigente.assert_not_called()


def test_t008_apply_snapshots_primeira_run_preenche():
    """T008: 1ª save preenche peso do Fator e nível da tabela 003."""
    linha = AvaliacaoCompetencia(
        peso_utilizado=Decimal('0.01'),
        nivel_esperado_utilizado=Decimal('1'),
    )
    apply_snapshots(linha, Decimal('2.50'), 4)
    assert linha.peso_utilizado == Decimal('2.50')
    assert linha.nivel_esperado_utilizado == Decimal('4')


@pytest.mark.django_db
def test_t008_apply_snapshots_segunda_run_estavel_e_divergente(
    colaborador,
):
    """T008 / SC-005: 2ª run não reatribui; divergência → snapshot_divergente."""
    ciclo = _ciclo_encerrado()
    avaliacao = Avaliacao.objects.create(
        ciclo=ciclo,
        usuario=colaborador,
        etapa=Avaliacao.Etapa.FEEDBACK,
        concluida=True,
        solides_id='t008-av',
    )
    escala = Escala.objects.create(
        nome='Escala T008',
        valor_minimo=1,
        valor_maximo=5,
        is_active=True,
    )
    competencia = Competencia.objects.create(
        nome='Competência T008',
        tipo=Competencia.Tipo.TECNICA,
        escala=escala,
        is_active=True,
    )
    linha = AvaliacaoCompetencia(
        avaliacao=avaliacao,
        competencia=competencia,
        nota_lider=Decimal('4.00'),
    )
    apply_snapshots(linha, Decimal('1.50'), 2)
    linha.full_clean()
    linha.save()

    persistido_peso = linha.peso_utilizado
    persistido_nivel = linha.nivel_esperado_utilizado

    apply_snapshots(linha, Decimal('1.50'), 2)
    assert linha.peso_utilizado == persistido_peso
    assert linha.nivel_esperado_utilizado == persistido_nivel

    with pytest.raises(SnapshotConflict) as excinfo:
        apply_snapshots(linha, Decimal('9.99'), 2)
    assert excinfo.value.code == 'snapshot_divergente'
    linha.refresh_from_db()
    assert linha.peso_utilizado == persistido_peso
    assert linha.nivel_esperado_utilizado == persistido_nivel


@pytest.mark.django_db
def test_t008_validation_error_write_once_vira_snapshot_divergente(
    colaborador,
):
    """T008: ValidationError write-once do model → conflito, linha permanece."""
    ciclo = _ciclo_encerrado()
    avaliacao = Avaliacao.objects.create(
        ciclo=ciclo,
        usuario=colaborador,
        etapa=Avaliacao.Etapa.FEEDBACK,
        concluida=True,
        solides_id='t008-wo',
    )
    escala = Escala.objects.create(
        nome='Escala T008 WO',
        valor_minimo=1,
        valor_maximo=5,
        is_active=True,
    )
    competencia = Competencia.objects.create(
        nome='Competência T008 WO',
        tipo=Competencia.Tipo.TECNICA,
        escala=escala,
        is_active=True,
    )
    linha = AvaliacaoCompetencia.objects.create(
        avaliacao=avaliacao,
        competencia=competencia,
        peso_utilizado=Decimal('1.50'),
        nivel_esperado_utilizado=Decimal('2.00'),
        nota_lider=Decimal('4.00'),
    )
    linha.peso_utilizado = Decimal('9.99')
    with pytest.raises(ValidationError) as excinfo:
        linha.save()
    conflict = conflict_from_write_once(excinfo.value)
    assert conflict is not None
    assert conflict.code == 'snapshot_divergente'
    linha.refresh_from_db()
    assert linha.peso_utilizado == Decimal('1.50')
    assert linha.nivel_esperado_utilizado == Decimal('2.00')


# --- T009 fase Notas ---

_NOTAS_HEADERS = [
    'Identificador',
    'Identificador Avaliação',
    'Nome Avaliador',
    'Nome Avaliado',
    'Identificador Habilidade',
    'habilidade',
    'Fator no Momento',
    'Nota',
]
_COMENTARIOS_HEADERS = [
    'Identificador',
    'Identificador Avaliador',
    'Nome Avaliador',
    'Nome Avaliado',
    'Comentário',
    'Criado em',
]
_AVALIACOES_HEADERS = [
    'Identificador',
    'Identificador Solicitação',
    'Identificador Avaliado',
    'Nome Avaliado',
    'Nome Avaliador',
]


def _write_xlsx(path: Path, headers: list[str], rows: list[list]) -> Path:
    wb = Workbook()
    ws = wb.active
    ws.append(headers)
    for row in rows:
        ws.append(row)
    wb.save(path)
    assert 'raw' not in path.parts
    return path


def _t009_paths(
    tmp_path: Path,
    *,
    notas_rows: list[list],
    header_rows: list[list],
) -> tuple[Path, Path, Path]:
    notas = _write_xlsx(tmp_path / 'notas.xlsx', _NOTAS_HEADERS, notas_rows)
    comentarios = _write_xlsx(
        tmp_path / 'comentarios.xlsx', _COMENTARIOS_HEADERS, []
    )
    avaliacoes = _write_xlsx(
        tmp_path / 'avaliacoes.xlsx', _AVALIACOES_HEADERS, header_rows
    )
    return notas, comentarios, avaliacoes


def _t009_catalogo() -> Competencia:
    escala = Escala.objects.create(
        nome='Escala T009',
        valor_minimo=1,
        valor_maximo=5,
        is_active=True,
    )
    return Competencia.objects.create(
        nome='Comunicação T009',
        tipo=Competencia.Tipo.COMPORTAMENTAL,
        escala=escala,
        solides_id='HAB10',
        is_active=True,
    )


def _t009_avaliacao(colaborador, solides_id: str = '1001') -> Avaliacao:
    return Avaliacao.objects.create(
        ciclo=_ciclo_encerrado(),
        usuario=colaborador,
        etapa=Avaliacao.Etapa.FEEDBACK,
        concluida=True,
        solides_id=solides_id,
    )


def _header_row(
    identificador: str,
    *,
    solicitacao: str = '10',
    avaliado_id: str = '101',
    nome_avaliado: str,
    nome_avaliador: str,
) -> list:
    return [
        identificador,
        solicitacao,
        avaliado_id,
        nome_avaliado,
        nome_avaliador,
    ]


def _nota_row(
    *,
    ident: str,
    avaliacao_id: str,
    avaliador: str,
    avaliado: str,
    habilidade_id: str = 'HAB10',
    habilidade: str = 'Comunicação T009',
    fator: object = 1,
    nota: object = 4,
) -> list:
    return [
        ident,
        avaliacao_id,
        avaliador,
        avaliado,
        habilidade_id,
        habilidade,
        fator,
        nota,
    ]


@pytest.mark.django_db
def test_t009_auto_vs_lider_upsert_formula_sem_create_lines(
    colaborador, tmp_path
):
    """T009: auto→nota_auto; líder→nota_lider; fórmula chamada; etapa intacta."""
    competencia = _t009_catalogo()
    avaliacao = _t009_avaliacao(colaborador)
    nome = colaborador.nome
    notas, comentarios, avaliacoes = _t009_paths(
        tmp_path,
        notas_rows=[
            _nota_row(
                ident='n1',
                avaliacao_id='1001',
                avaliador=nome,
                avaliado=nome,
                nota=3,
            ),
            _nota_row(
                ident='n2',
                avaliacao_id='1001',
                avaliador='Líder Fixture',
                avaliado=nome,
                nota=4,
            ),
        ],
        header_rows=[
            _header_row('1001', nome_avaliado=nome, nome_avaliador=nome),
        ],
    )
    before_av = Avaliacao.objects.count()
    before_fb = Feedback.objects.count()
    etapa = avaliacao.etapa
    concluida = avaliacao.concluida

    with (
        patch(
            'apps.reviews.services.evaluation.create_competency_lines'
        ) as spy_lines,
        patch(
            'apps.reviews.services.legacy_import.importer.calcular_nota_final_lider',
            wraps=calcular_nota_final_lider,
        ) as spy_calc,
    ):
        report = import_notas_comentarios(notas, comentarios, avaliacoes)

    spy_lines.assert_not_called()
    assert spy_calc.called
    assert report.notas_criadas == 1
    linha = AvaliacaoCompetencia.objects.get(
        avaliacao=avaliacao, competencia=competencia
    )
    assert linha.nota_autoavaliacao == Decimal('3.00')
    assert linha.nota_lider == Decimal('4.00')
    assert linha.peso_utilizado == Decimal('1.00')
    assert linha.nivel_esperado_utilizado == Decimal('2.00')
    avaliacao.refresh_from_db()
    assert avaliacao.nota_final_lider is not None
    assert avaliacao.nota_final_autoavaliacao is not None
    assert avaliacao.etapa == etapa
    assert avaliacao.concluida == concluida
    assert Avaliacao.objects.count() == before_av
    assert Feedback.objects.count() == before_fb
    assert CargoCompetencia.objects.count() == 0


@pytest.mark.django_db
def test_t009_dois_lideres_divergentes_auto_univoca_persiste(
    colaborador, tmp_path
):
    """T009 / R6: dois líderes → conflito sem média; auto unívoca pode persistir."""
    competencia = _t009_catalogo()
    avaliacao = _t009_avaliacao(colaborador)
    nome = colaborador.nome
    notas, comentarios, avaliacoes = _t009_paths(
        tmp_path,
        notas_rows=[
            _nota_row(
                ident='a1',
                avaliacao_id='1001',
                avaliador=nome,
                avaliado=nome,
                nota=3,
            ),
            _nota_row(
                ident='l1',
                avaliacao_id='1001',
                avaliador='Líder A',
                avaliado=nome,
                nota=4,
            ),
            _nota_row(
                ident='l2',
                avaliacao_id='1001',
                avaliador='Líder B',
                avaliado=nome,
                nota=5,
            ),
        ],
        header_rows=[
            _header_row('1001', nome_avaliado=nome, nome_avaliador=nome),
        ],
    )

    report = import_notas_comentarios(notas, comentarios, avaliacoes)

    assert report.n_conflitos_lider_divergente == 1
    linha = AvaliacaoCompetencia.objects.get(
        avaliacao=avaliacao, competencia=competencia
    )
    assert linha.nota_autoavaliacao == Decimal('3.00')
    assert linha.nota_lider is None
    assert Avaliacao.objects.filter(solides_id='1001').count() == 1
    tipos = [entry.label for entry in report.conflitos]
    assert 'calculo_lider' in tipos


@pytest.mark.django_db
def test_t009_id_colapsado_resolve_na_canonica(colaborador, tmp_path):
    """T009 / R4: ID colapsado 1002 grava na canônica 1001; zero 2ª Avaliacao."""
    competencia = _t009_catalogo()
    avaliacao = _t009_avaliacao(colaborador, solides_id='1001')
    nome = colaborador.nome
    notas, comentarios, avaliacoes = _t009_paths(
        tmp_path,
        notas_rows=[
            _nota_row(
                ident='n-col',
                avaliacao_id='1002',
                avaliador='Líder Fixture',
                avaliado=nome,
                nota=4,
            ),
        ],
        header_rows=[
            _header_row('1001', nome_avaliado=nome, nome_avaliador=nome),
            _header_row(
                '1002',
                nome_avaliado=nome,
                nome_avaliador='Líder Fixture',
            ),
            _header_row(
                '1003',
                nome_avaliado=nome,
                nome_avaliador='Outro Líder',
            ),
        ],
    )
    before = Avaliacao.objects.count()

    report = import_notas_comentarios(notas, comentarios, avaliacoes)

    assert report.n_ids_colapsados_resolvidos == 1
    assert Avaliacao.objects.count() == before
    assert AvaliacaoCompetencia.objects.filter(
        avaliacao=avaliacao, competencia=competencia
    ).count() == 1
    assert Avaliacao.objects.filter(solides_id='1002').exists() is False


@pytest.mark.django_db
def test_t009_orfao_avaliacao_e_ciclo_aberto(
    colaborador, ciclo_aberto, tmp_path
):
    """T009: órfão não inventa Avaliacao; ciclo aberto → skip (R10)."""
    _t009_catalogo()
    operacional = Avaliacao.objects.get(ciclo=ciclo_aberto, usuario=colaborador)
    operacional.solides_id = '8001'
    operacional.save(update_fields=['solides_id'])
    etapa_antes = operacional.etapa
    concluida_antes = operacional.concluida
    nome = colaborador.nome
    notas, comentarios, avaliacoes = _t009_paths(
        tmp_path,
        notas_rows=[
            _nota_row(
                ident='orf',
                avaliacao_id='9999',
                avaliador='Líder Fixture',
                avaliado=nome,
            ),
            _nota_row(
                ident='ab',
                avaliacao_id='8001',
                avaliador='Líder Fixture',
                avaliado=nome,
            ),
        ],
        header_rows=[
            _header_row('8001', nome_avaliado=nome, nome_avaliador=nome),
        ],
    )
    before_av = Avaliacao.objects.count()
    before_linhas = AvaliacaoCompetencia.objects.count()

    report = import_notas_comentarios(notas, comentarios, avaliacoes)

    assert report.n_orfaos_avaliacao == 1
    assert report.n_conflitos_ciclo_aberto == 1
    assert Avaliacao.objects.count() == before_av
    assert AvaliacaoCompetencia.objects.count() == before_linhas
    operacional.refresh_from_db()
    assert operacional.etapa == etapa_antes
    assert operacional.concluida == concluida_antes
    assert Avaliacao.objects.filter(solides_id='9999').exists() is False


@pytest.mark.django_db
def test_t009_nota_fora_da_escala_sem_clip(colaborador, tmp_path):
    """T009 / R8: nota ∉ escala → conflito; valor não persistido; sem clip."""
    competencia = _t009_catalogo()
    avaliacao = _t009_avaliacao(colaborador)
    nome = colaborador.nome
    notas, comentarios, avaliacoes = _t009_paths(
        tmp_path,
        notas_rows=[
            _nota_row(
                ident='out',
                avaliacao_id='1001',
                avaliador='Líder Fixture',
                avaliado=nome,
                nota=9,
            ),
        ],
        header_rows=[
            _header_row('1001', nome_avaliado=nome, nome_avaliador=nome),
        ],
    )

    report = import_notas_comentarios(notas, comentarios, avaliacoes)

    assert any(e.label == 'nota_fora_da_escala' for e in report.conflitos)
    assert AvaliacaoCompetencia.objects.filter(
        avaliacao=avaliacao, competencia=competencia
    ).exists() is False
    avaliacao.refresh_from_db()
    assert avaliacao.nota_final_lider is None


def test_t010_command_registrado_e_sem_denylist():
    """T010: comando Discoverable; imports só na allowlist (sem UI/DRF/Celery)."""
    assert 'importar_notas_comentarios' in get_commands()
    text = _IMPORT_NOTAS_COMMAND.read_text(encoding='utf-8')
    import_blob = '\n'.join(
        line
        for line in text.splitlines()
        if line.lstrip().startswith(('import ', 'from '))
    )
    for token in _DENYLIST_IMPORT_TOKENS:
        assert token not in import_blob, token
    assert 'format_notas_comentarios_report' in text
    assert 'import_notas_comentarios' in text
    assert 'raw' not in _IMPORT_NOTAS_COMMAND.parts


def test_t010_args_faltando_exit_1():
    """T010 / contrato: args obrigatórios ausentes → CommandError returncode 1."""
    with pytest.raises(CommandError) as exc_info:
        call_command('importar_notas_comentarios')
    assert exc_info.value.returncode == 1

    with pytest.raises(CommandError) as exc_notas:
        call_command(
            'importar_notas_comentarios',
            comentarios='c.xlsx',
            avaliacoes='a.xlsx',
        )
    assert exc_notas.value.returncode == 1

    with pytest.raises(CommandError) as exc_com:
        call_command(
            'importar_notas_comentarios',
            notas='n.xlsx',
            avaliacoes='a.xlsx',
        )
    assert exc_com.value.returncode == 1

    with pytest.raises(CommandError) as exc_av:
        call_command(
            'importar_notas_comentarios',
            notas='n.xlsx',
            comentarios='c.xlsx',
        )
    assert exc_av.value.returncode == 1


@pytest.mark.django_db
def test_t010_arquivo_ausente_exit_1_db_inalterado(tmp_path):
    """T010: arquivo inexistente → exit 1; AvaliacaoCompetencia/Feedback intactos."""
    comentarios = _write_xlsx(
        tmp_path / 'comentarios.xlsx', _COMENTARIOS_HEADERS, []
    )
    avaliacoes = _write_xlsx(
        tmp_path / 'avaliacoes.xlsx', _AVALIACOES_HEADERS, []
    )
    missing = tmp_path / 'ausente.xlsx'
    before_linhas = AvaliacaoCompetencia.objects.count()
    before_fb = Feedback.objects.count()

    with pytest.raises(CommandError) as exc_info:
        call_command(
            'importar_notas_comentarios',
            notas=str(missing),
            comentarios=str(comentarios),
            avaliacoes=str(avaliacoes),
        )
    assert exc_info.value.returncode == 1
    assert AvaliacaoCompetencia.objects.count() == before_linhas
    assert Feedback.objects.count() == before_fb


@pytest.mark.django_db
def test_t010_command_fase_notas_relatorio_exit_0(colaborador, tmp_path):
    """T010: call_command persiste notas, imprime relatório mascarado, exit 0."""
    competencia = _t009_catalogo()
    avaliacao = _t009_avaliacao(colaborador)
    nome = colaborador.nome
    notas, comentarios, avaliacoes = _t009_paths(
        tmp_path,
        notas_rows=[
            _nota_row(
                ident='n1',
                avaliacao_id='1001',
                avaliador=nome,
                avaliado=nome,
                nota=3,
            ),
            _nota_row(
                ident='n2',
                avaliacao_id='1001',
                avaliador='Líder Fixture',
                avaliado=nome,
                nota=4,
            ),
        ],
        header_rows=[
            _header_row('1001', nome_avaliado=nome, nome_avaliador=nome),
        ],
    )
    report_path = tmp_path / 'relatorio-notas-comentarios.txt'
    stdout = StringIO()
    before_av = Avaliacao.objects.count()
    etapa = avaliacao.etapa
    concluida = avaliacao.concluida

    result = call_command(
        'importar_notas_comentarios',
        notas=str(notas),
        comentarios=str(comentarios),
        avaliacoes=str(avaliacoes),
        report_file=str(report_path),
        stdout=stdout,
    )

    text = stdout.getvalue()
    file_text = report_path.read_text(encoding='utf-8')
    assert result in (0, None)
    assert file_text == text
    assert '=== Importação notas/comentários legado Sólides ===' in text
    assert 'modo: persist' in text
    assert 'notas_criadas: 1' in text
    assert _EMAIL not in text
    assert _NOME not in text
    assert nome not in text
    assert 'Líder Fixture' not in text
    assert colaborador.email not in text
    assert Avaliacao.objects.count() == before_av
    linha = AvaliacaoCompetencia.objects.get(
        avaliacao=avaliacao, competencia=competencia
    )
    assert linha.nota_autoavaliacao == Decimal('3.00')
    assert linha.nota_lider == Decimal('4.00')
    avaliacao.refresh_from_db()
    assert avaliacao.nota_final_lider is not None
    assert avaliacao.etapa == etapa
    assert avaliacao.concluida == concluida
    assert Feedback.objects.count() == 0


# --- T011 validação US1 (quickstart C2–C5) ---


def _git_diff(*args: str) -> str:
    result = subprocess.run(
        ['git', 'diff', *args],
        cwd=_REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout


def _git_rev_exists(rev: str) -> bool:
    result = subprocess.run(
        ['git', 'rev-parse', '--verify', rev],
        cwd=_REPO_ROOT,
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


@pytest.mark.django_db
def test_t011_c2_auto_vs_lider_peso_fator_nivel_003_nao_cargo_competencia(
    colaborador, tmp_path
):
    """C2: auto só em nota_auto; líder só em nota_lider; peso=Fator; nível=003."""
    competencia = _t009_catalogo()
    avaliacao = _t009_avaliacao(colaborador)
    CargoCompetencia.objects.create(
        cargo=colaborador.cargo,
        competencia=competencia,
        nivel_esperado=Decimal('9.00'),
        peso=Decimal('99.00'),
    )
    nome = colaborador.nome
    notas, comentarios, avaliacoes = _t009_paths(
        tmp_path,
        notas_rows=[
            _nota_row(
                ident='n-auto',
                avaliacao_id='1001',
                avaliador=nome,
                avaliado=nome,
                fator=Decimal('2.50'),
                nota=3,
            ),
            _nota_row(
                ident='n-lider',
                avaliacao_id='1001',
                avaliador='Líder Fixture',
                avaliado=nome,
                fator=Decimal('2.50'),
                nota=4,
            ),
        ],
        header_rows=[
            _header_row('1001', nome_avaliado=nome, nome_avaliador=nome),
        ],
    )

    report = import_notas_comentarios(notas, comentarios, avaliacoes)

    linhas = AvaliacaoCompetencia.objects.filter(
        avaliacao=avaliacao, competencia=competencia
    )
    assert linhas.count() == 1
    linha = linhas.get()
    assert linha.nota_autoavaliacao == Decimal('3.00')
    assert linha.nota_lider == Decimal('4.00')
    assert linha.peso_utilizado == Decimal('2.50')
    assert linha.peso_utilizado != Decimal('1.00')
    assert linha.peso_utilizado != Decimal('99.00')
    assert linha.nivel_esperado_utilizado == Decimal('2.00')
    assert linha.nivel_esperado_utilizado != Decimal('9.00')
    assert report.notas_criadas == 1


@pytest.mark.django_db
def test_t011_c3_id_canonico_colapsado_orfao(colaborador, tmp_path):
    """C3 / SC-006: canônico e colapsado na mesma Avaliacao; órfão não inventa."""
    competencia = _t009_catalogo()
    avaliacao = _t009_avaliacao(colaborador, solides_id='1001')
    nome = colaborador.nome
    notas, comentarios, avaliacoes = _t009_paths(
        tmp_path,
        notas_rows=[
            _nota_row(
                ident='n-can',
                avaliacao_id='1001',
                avaliador=nome,
                avaliado=nome,
                nota=3,
            ),
            _nota_row(
                ident='n-col',
                avaliacao_id='1002',
                avaliador='Líder Fixture',
                avaliado=nome,
                nota=4,
            ),
            _nota_row(
                ident='n-orf',
                avaliacao_id='9999',
                avaliador='Líder Fixture',
                avaliado=nome,
                nota=5,
            ),
        ],
        header_rows=[
            _header_row('1001', nome_avaliado=nome, nome_avaliador=nome),
            _header_row(
                '1002',
                nome_avaliado=nome,
                nome_avaliador='Líder Fixture',
            ),
            _header_row(
                '1003',
                nome_avaliado=nome,
                nome_avaliador='Outro Líder',
            ),
        ],
    )
    before = Avaliacao.objects.count()

    report = import_notas_comentarios(notas, comentarios, avaliacoes)

    assert Avaliacao.objects.count() == before
    assert Avaliacao.objects.filter(solides_id='1002').exists() is False
    assert Avaliacao.objects.filter(solides_id='9999').exists() is False
    assert report.n_orfaos_avaliacao == 1
    assert report.n_ids_colapsados_resolvidos == 1
    linha = AvaliacaoCompetencia.objects.get(
        avaliacao=avaliacao, competencia=competencia
    )
    assert linha.nota_autoavaliacao == Decimal('3.00')
    assert linha.nota_lider == Decimal('4.00')
    assert AvaliacaoCompetencia.objects.filter(avaliacao=avaliacao).count() == 1


@pytest.mark.django_db
def test_t011_c4_dois_lideres_divergentes_e_ciclo_aberto(
    colaborador, ciclo_aberto, tmp_path
):
    """C4: dois líderes → conflito sem média; ciclo aberto → skip (SC-012)."""
    competencia = _t009_catalogo()
    historica = _t009_avaliacao(colaborador)
    operacional = Avaliacao.objects.get(ciclo=ciclo_aberto, usuario=colaborador)
    operacional.solides_id = '8001'
    operacional.save(update_fields=['solides_id'])
    etapa_aberta = operacional.etapa
    concluida_aberta = operacional.concluida
    nome = colaborador.nome
    notas, comentarios, avaliacoes = _t009_paths(
        tmp_path,
        notas_rows=[
            _nota_row(
                ident='l1',
                avaliacao_id='1001',
                avaliador='Líder A',
                avaliado=nome,
                nota=4,
            ),
            _nota_row(
                ident='l2',
                avaliacao_id='1001',
                avaliador='Líder B',
                avaliado=nome,
                nota=5,
            ),
            _nota_row(
                ident='ab',
                avaliacao_id='8001',
                avaliador='Líder Fixture',
                avaliado=nome,
                nota=4,
            ),
        ],
        header_rows=[
            _header_row('1001', nome_avaliado=nome, nome_avaliador=nome),
            _header_row('8001', nome_avaliado=nome, nome_avaliador=nome),
        ],
    )
    before_linhas = AvaliacaoCompetencia.objects.count()

    report = import_notas_comentarios(notas, comentarios, avaliacoes)

    assert report.n_conflitos_lider_divergente == 1
    assert report.n_conflitos_ciclo_aberto == 1
    assert AvaliacaoCompetencia.objects.filter(
        avaliacao=historica, competencia=competencia
    ).exists() is False
    assert AvaliacaoCompetencia.objects.filter(avaliacao=operacional).exists() is False
    assert AvaliacaoCompetencia.objects.count() == before_linhas
    historica.refresh_from_db()
    assert historica.nota_final_lider is None
    operacional.refresh_from_db()
    assert operacional.etapa == etapa_aberta
    assert operacional.concluida == concluida_aberta
    assert operacional.nota_final_lider is None


@pytest.mark.django_db
def test_t011_c5_nota_final_via_formula_spy_sem_create_lines(
    colaborador, tmp_path
):
    """C5: calcular_nota_final_lider é chamado; create_competency_lines não."""
    competencia = _t009_catalogo()
    avaliacao = _t009_avaliacao(colaborador)
    nome = colaborador.nome
    notas, comentarios, avaliacoes = _t009_paths(
        tmp_path,
        notas_rows=[
            _nota_row(
                ident='n-lider',
                avaliacao_id='1001',
                avaliador='Líder Fixture',
                avaliado=nome,
                nota=4,
            ),
        ],
        header_rows=[
            _header_row('1001', nome_avaliado=nome, nome_avaliador=nome),
        ],
    )
    etapa = avaliacao.etapa
    concluida = avaliacao.concluida

    with (
        patch(
            'apps.reviews.services.evaluation.create_competency_lines'
        ) as spy_lines,
        patch(
            'apps.reviews.services.legacy_import.importer.calcular_nota_final_lider',
            wraps=calcular_nota_final_lider,
        ) as spy_calc,
    ):
        import_notas_comentarios(notas, comentarios, avaliacoes)

    spy_lines.assert_not_called()
    assert spy_calc.called
    linha = AvaliacaoCompetencia.objects.get(
        avaliacao=avaliacao, competencia=competencia
    )
    assert linha.nota_lider == Decimal('4.00')
    avaliacao.refresh_from_db()
    assert avaliacao.nota_final_lider is not None
    assert avaliacao.etapa == etapa
    assert avaliacao.concluida == concluida


@pytest.mark.django_db
def test_t011_c5_calculation_error_vira_conflito_sem_media(
    colaborador, tmp_path
):
    """C5: CalculationError → conflito; nota_final_* não é média inventada."""
    _t009_catalogo()
    avaliacao = _t009_avaliacao(colaborador)
    nome = colaborador.nome
    notas, comentarios, avaliacoes = _t009_paths(
        tmp_path,
        notas_rows=[
            _nota_row(
                ident='n-lider',
                avaliacao_id='1001',
                avaliador='Líder Fixture',
                avaliado=nome,
                nota=4,
            ),
        ],
        header_rows=[
            _header_row('1001', nome_avaliado=nome, nome_avaliador=nome),
        ],
    )

    with (
        patch(
            'apps.reviews.services.evaluation.create_competency_lines'
        ) as spy_lines,
        patch(
            'apps.reviews.services.legacy_import.importer.calcular_nota_final_lider',
            side_effect=CalculationError('Soma de peso_utilizado igual a zero'),
        ),
    ):
        report = import_notas_comentarios(notas, comentarios, avaliacoes)

    spy_lines.assert_not_called()
    tipos = [entry.label for entry in report.conflitos]
    assert 'calculo_lider' in tipos
    avaliacao.refresh_from_db()
    assert avaliacao.nota_final_lider is None


@pytest.mark.skipif(
    shutil.which('git') is None,
    reason='git ausente no PATH (ex. container web sem git)',
)
def test_t011_c5_git_diff_evaluation_e_denylist_vazios():
    """C5 / FR-021: evaluation.py e denylist intactos (chamar ≠ editar)."""
    evaluation_diff = _git_diff(
        'HEAD', '--', 'apps/reviews/services/evaluation.py'
    )
    assert evaluation_diff == '', evaluation_diff

    working_tree = _git_diff('HEAD', '--', *_DENYLIST_PATHS)
    assert working_tree == '', working_tree

    for base in ('development', 'origin/development', 'main'):
        if _git_rev_exists(base):
            vs_base = _git_diff(base, '--', *_DENYLIST_PATHS)
            assert vs_base == '', vs_base
            break


