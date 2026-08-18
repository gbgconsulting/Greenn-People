"""T006+: importação notas/comentários legado Sólides — relatório mascarado.

T006: ``format_notas_comentarios_report`` (seções estáveis, máx. 5,
sem comentário/nome/e-mail). Sem persistência. **Proibido** ``raw/``.

T007: ``resolve.py`` — mapa colapsado, ``resolve_avaliacao``, ``is_auto``,
``is_ciclo_aberto``, ``resolve_competencia`` (R11). **Proibido** ``raw/``.

T012: ``resolve_autor`` — ``solides_id`` primário; fallback nome canônico
único; inativo permitido; irresolvível → ``None`` (sem inventar User).

T008: ``snapshots.py`` — peso do Fator, nível da tabela 003, write-once.
**Proibido** ``raw/``. **Proibido** ler ``CargoCompetencia``.

T009: fase Notas em ``importer.py`` — agrupa, upsert, fórmula vigente.
**Proibido** ``create_competency_lines`` / mutar ``etapa``/``concluida``.

T013: fase Comentários em ``importer.py`` — ``Feedback`` append-only
(tipo, ``ciente_em`` líder, chave natural, N por avaliação, ciclo aberto).
**Proibido** mutar ``etapa``/``concluida``; **proibido** inventar User.

T010: management command ``importar_notas_comentarios`` (args, relatório,
exit 0/1). T014: fase Comentários integrada no CLI (seções
``comentarios_*`` / ``orfaos_autor``; mesma ``transaction.atomic()``).

T011: validação US1 via quickstart C2–C5 (auto vs líder, snapshots 003,
ID canônico/colapsado/órfão, dois líderes, ciclo aberto, fórmula vigente,
spy ``create_competency_lines``, ``git diff`` denylist).

T015: validação US2 via quickstart C6 (líder com ciência; auto sem
ciência; autor inativo ok; autor irresolvível órfão; N textos;
etapa/concluída intactas; ``git diff`` denylist).

T018: ``--dry-run`` (SC-008), ID canônico/colapsado/órfão (SC-006) e
args/arquivo inválido (exit 1) usando **somente**
``data/legado-solides/samples/``. **Proibido** ``raw/``.

T019: dois líderes (sem média), ciclo ``aberto`` (SC-012), write-once
2ª run (SC-005; ``CargoCompetencia`` vigente divergente não copiada),
habilidade extra vs órfão KPI (SC-014), spy ``create_competency_lines``
**não** chamado, ``calcular_nota_final_lider`` **é** chamado,
``CalculationError`` → conflito sem média. **Proibido** ``raw/``.

T020: comentários (tipo, ``ciente_em`` líder, colaborador null, N textos,
chave natural sem duplicata), mascaramento PII (máx. 5; sem
comentário/nome/e-mail), zero path ``raw/`` na suíte, teste de ouro
denylist (``git diff`` vazio / import não muta ``etapa``/``concluida``)
— SC-007/SC-009/SC-010/SC-013. **Proibido** ``raw/``.

T021–T023 estendem esta suíte (dry-run consolidado, idempotência).

T022: idempotência consolidada (SC-005 / C7) — unique
``(avaliacao, competencia)`` atualiza só ``nota_*``; snapshots
bit-a-bit; ``snapshot_divergente`` sem apagar; Feedback chave natural
sem reescrever ``conteudo``; delta ``Avaliacao`` por
``(ciclo, usuario)`` = 0. **Proibido** ``raw/``.
"""

from __future__ import annotations

import shutil
import subprocess
from datetime import date, datetime
from decimal import Decimal
from io import StringIO
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from django.core.exceptions import ValidationError
from django.core.management import call_command, get_commands
from django.core.management.base import CommandError
from django.utils import timezone
from openpyxl import Workbook

from apps.accounts.models import CustomUser
from apps.accounts.services.legacy_import.dates import parse_legacy_datetime
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
from apps.organization.models import Cargo
from apps.reviews.exceptions import CalculationError
from apps.reviews.models import Avaliacao, AvaliacaoCompetencia, Feedback
from apps.reviews.services.evaluation import calcular_nota_final_lider
from apps.reviews.services.legacy_import import format_notas_comentarios_report as _reexport
from apps.reviews.services.legacy_import.importer import (
    LegacyParseError,
    LegacyPersistError,
    import_notas_comentarios,
)
from apps.reviews.services.legacy_import.resolve import (
    build_collapsed_id_map,
    is_auto,
    is_ciclo_aberto,
    resolve_autor,
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
from tests.conftest import DEFAULT_PASSWORD

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
_NOTAS_MIN = _SAMPLES_DIR / 'notas_min.xlsx'
_COMENTARIOS_MIN = _SAMPLES_DIR / 'comentarios_min.xlsx'
_RAW_PII_DIR = '/'.join(('data', 'legado-solides', 'raw'))
_T018_SEED_USERS = (
    ('gestor.alpha@example.com', 'Gestor Alpha', '100'),
    ('ana.silva@example.com', 'Ana Silva', '101'),
    ('bruno.costa@example.com', 'Bruno Costa', '102'),
    ('carla.dias@example.com', 'Carla Dias', '103'),
)
_T018_PII = (
    'ana.silva@example.com',
    '000.000.000-00',
    'Ana Silva',
    'Gestor Alpha',
    'Bruno Costa',
    'Carla Dias',
    'Ninguem Desconhecido Fixture',
    'Feedback fixture lider A',
    'Feedback fixture autoavaliacao',
)
_T018_NOTAS_CRIADAS = 4
_T018_COMENTARIOS_CRIADOS = 4
_T018_ORFAOS_AVALIACAO = 1
_T018_ORFAOS_AUTOR = 1
_T018_IDS_COLAPSADOS = 2
_T019_LIDER_DIVERGENTE = 1
_T019_ORFAOS_COMPETENCIA = 2
_T019_EXTRAS = 1
_T019_MEDIA_PROIBIDA = Decimal('4.50')
_T019_CARGO_PESO_VIGENTE = Decimal('99.00')
_T019_CARGO_NIVEL_VIGENTE = Decimal('9.00')
_T020_LIDER_A = 'Feedback fixture lider A. Nunca vazar no relatorio.'
_T020_LIDER_B = 'Feedback fixture lider B distinto.'
_T020_AUTO = 'Feedback fixture autoavaliacao.'
_T020_COLAPSADO = 'Feedback fixture colapsado 1002.'
_T020_ORFAO_TEXTO = 'Feedback orfao autor fixture.'
_T020_PII = (
    *_T018_PII,
    _T020_LIDER_A,
    _T020_LIDER_B,
    _T020_AUTO,
    _T020_COLAPSADO,
    _T020_ORFAO_TEXTO,
    'Nunca vazar no relatorio.',
)
_T020_ALLOWLIST_PY = (
    'apps/reviews/services/legacy_import',
    'apps/reviews/management/commands/importar_notas_comentarios.py',
    'apps/accounts/services/legacy_import/parse_xlsx.py',
    'apps/accounts/services/legacy_import/dates.py',
    'apps/accounts/services/legacy_import/report.py',
)
_STAGE_SCOPE_REJECT_TESTS = (
    'tests/test_stage_machine.py',
    'tests/test_scope.py',
    'tests/test_reject_stage_invariant.py',
)
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


# --- T012 resolve_autor ---


def _make_autor(
    *,
    email: str,
    nome: str,
    solides_id: str | None = None,
    is_active: bool = True,
) -> CustomUser:
    return CustomUser.objects.create_user(
        email=email,
        password=DEFAULT_PASSWORD,
        nome=nome,
        solides_id=solides_id,
        is_active=is_active,
        email_confirmado_em=timezone.now(),
    )


@pytest.mark.django_db
def test_t012_resolve_autor_por_solides_id():
    """T012 / R12: primário ``CustomUser.solides_id == Identificador Avaliador``."""
    autor = _make_autor(
        email='autor-id@test.greenn.com.br',
        nome='Ana Silva',
        solides_id='5001',
    )
    before = CustomUser.objects.count()

    found = resolve_autor('5001', 'Nome Distinto')
    assert found == autor
    assert CustomUser.objects.count() == before


@pytest.mark.django_db
def test_t012_resolve_autor_inativo_permitido():
    """T012: usuário inativo (010) ainda resolve — histórico."""
    autor = _make_autor(
        email='ex-colab@test.greenn.com.br',
        nome='Carla Inativa',
        solides_id='5002',
        is_active=False,
    )
    assert autor.is_active is False
    assert resolve_autor('5002', '') == autor

    by_name = resolve_autor('', 'Carla Inativa')
    assert by_name == autor


@pytest.mark.django_db
def test_t012_resolve_autor_fallback_nome_canonico_unico():
    """T012: miss de id → match único ``canonical_key(Nome Avaliador)``."""
    autor = _make_autor(
        email='autor-nome@test.greenn.com.br',
        nome='José Silva',
        solides_id=None,
    )
    found = resolve_autor('9999', 'JOSE SILVA')
    assert found == autor

    vazio_id = resolve_autor('', 'José Silva')
    assert vazio_id == autor


@pytest.mark.django_db
def test_t012_resolve_autor_nome_ambiguo_e_orfao_nao_inventa_user():
    """T012: ambíguo / irresolvível → ``None``; zero User criado (orfaos_autor)."""
    _make_autor(
        email='jose-a@test.greenn.com.br',
        nome='José',
        solides_id='5101',
    )
    _make_autor(
        email='jose-b@test.greenn.com.br',
        nome='Jose',
        solides_id='5102',
    )
    before = CustomUser.objects.count()

    ambiguo = resolve_autor('', 'José')
    assert ambiguo is None

    orfao = resolve_autor('9999', 'Ninguém Desconhecido')
    assert orfao is None

    vazio = resolve_autor('', '')
    assert vazio is None

    assert CustomUser.objects.count() == before
    assert CustomUser.objects.filter(solides_id='9999').exists() is False


@pytest.mark.django_db
def test_t012_comentario_usa_mesmo_resolve_avaliacao_mapa(colaborador):
    """T012: ID colapsado de comentário = mesma resolução canônica da US1."""
    ciclo = _ciclo_encerrado()
    avaliacao = Avaliacao.objects.create(
        ciclo=ciclo,
        usuario=colaborador,
        etapa=Avaliacao.Etapa.FEEDBACK,
        concluida=True,
        solides_id='1001',
    )
    mapa = {'1001': '1001', '1002': '1001'}
    before = Avaliacao.objects.count()

    colapsado = resolve_avaliacao('1002', mapa)
    assert colapsado.avaliacao == avaliacao
    assert colapsado.via_collapsed is True
    assert Avaliacao.objects.count() == before


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
    comentarios_rows: list[list] | None = None,
) -> tuple[Path, Path, Path]:
    notas = _write_xlsx(tmp_path / 'notas.xlsx', _NOTAS_HEADERS, notas_rows)
    comentarios = _write_xlsx(
        tmp_path / 'comentarios.xlsx',
        _COMENTARIOS_HEADERS,
        comentarios_rows or [],
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


def _comentario_row(
    *,
    avaliacao_id: str,
    avaliador_id: str,
    avaliador: str,
    avaliado: str,
    comentario: str,
    criado_em: object = None,
) -> list:
    return [
        avaliacao_id,
        avaliador_id,
        avaliador,
        avaliado,
        comentario,
        criado_em,
    ]


def _t013_solides_ids(colaborador: CustomUser, lider_user: CustomUser) -> None:
    colaborador.solides_id = '101'
    colaborador.save(update_fields=['solides_id'])
    lider_user.solides_id = '201'
    lider_user.save(update_fields=['solides_id'])


@pytest.mark.django_db
def test_t013_lider_ciencia_auto_sem_ciencia_etapa_intacta(
    colaborador, lider, tmp_path
):
    """T013 / R12: líder→ciente_em; auto→null; etapa/concluída intactas."""
    _t013_solides_ids(colaborador, lider)
    avaliacao = _t009_avaliacao(colaborador)
    etapa = avaliacao.etapa
    concluida = avaliacao.concluida
    criado = datetime(2024, 6, 3, 14, 30, 0)
    notas, comentarios, avaliacoes = _t009_paths(
        tmp_path,
        notas_rows=[],
        header_rows=[
            _header_row(
                '1001',
                nome_avaliado=colaborador.nome,
                nome_avaliador=colaborador.nome,
            ),
        ],
        comentarios_rows=[
            _comentario_row(
                avaliacao_id='1001',
                avaliador_id='201',
                avaliador=lider.nome,
                avaliado=colaborador.nome,
                comentario='Desempenho consistente no trimestre.',
                criado_em=criado,
            ),
            _comentario_row(
                avaliacao_id='1001',
                avaliador_id='101',
                avaliador=colaborador.nome,
                avaliado=colaborador.nome,
                comentario='Minha autoavaliação qualitativa.',
                criado_em=criado,
            ),
        ],
    )
    before_users = CustomUser.objects.count()

    report = import_notas_comentarios(notas, comentarios, avaliacoes)

    assert report.comentarios_criados == 2
    assert Feedback.objects.filter(avaliacao=avaliacao).count() == 2
    lider_fb = Feedback.objects.get(avaliacao=avaliacao, tipo=Feedback.Tipo.LIDER)
    auto_fb = Feedback.objects.get(
        avaliacao=avaliacao, tipo=Feedback.Tipo.COLABORADOR
    )
    assert lider_fb.autor_id == lider.pk
    assert lider_fb.conteudo == 'Desempenho consistente no trimestre.'
    assert lider_fb.ciente_em is not None
    expected = timezone.make_aware(criado, timezone.get_current_timezone())
    assert abs((lider_fb.ciente_em - expected).total_seconds()) < 0.001
    lider_fb.refresh_from_db()
    assert abs((lider_fb.created_at - expected).total_seconds()) < 0.001
    assert auto_fb.autor_id == colaborador.pk
    assert auto_fb.ciente_em is None
    avaliacao.refresh_from_db()
    assert avaliacao.etapa == etapa
    assert avaliacao.concluida == concluida
    assert CustomUser.objects.count() == before_users
    assert Avaliacao.objects.filter(solides_id='1001').count() == 1


@pytest.mark.django_db
def test_t013_autor_inativo_n_textos_chave_natural_sem_duplicata(
    colaborador, lider, tmp_path
):
    """T013: inativo ok; N textos; 2ª run não duplica nem reescreve conteúdo."""
    _t013_solides_ids(colaborador, lider)
    autor_inativo = _make_autor(
        email='ex-lider-legado@test.greenn.com.br',
        nome='Carla Inativa Legado',
        solides_id='202',
        is_active=False,
    )
    avaliacao = _t009_avaliacao(colaborador)
    criado = datetime(2024, 6, 4, 9, 0, 0)
    rows = [
        _comentario_row(
            avaliacao_id='1001',
            avaliador_id='202',
            avaliador=autor_inativo.nome,
            avaliado=colaborador.nome,
            comentario='Primeiro texto do líder.',
            criado_em=criado,
        ),
        _comentario_row(
            avaliacao_id='1001',
            avaliador_id='202',
            avaliador=autor_inativo.nome,
            avaliado=colaborador.nome,
            comentario='Segundo texto distinto do líder.',
            criado_em=criado,
        ),
    ]
    notas, comentarios, avaliacoes = _t009_paths(
        tmp_path,
        notas_rows=[],
        header_rows=[
            _header_row(
                '1001',
                nome_avaliado=colaborador.nome,
                nome_avaliador=colaborador.nome,
            ),
        ],
        comentarios_rows=rows,
    )

    first = import_notas_comentarios(notas, comentarios, avaliacoes)
    assert first.comentarios_criados == 2
    assert Feedback.objects.filter(
        avaliacao=avaliacao, autor=autor_inativo
    ).count() == 2

    second = import_notas_comentarios(notas, comentarios, avaliacoes)
    assert second.comentarios_criados == 0
    assert second.comentarios_inalterados == 2
    assert Feedback.objects.filter(
        avaliacao=avaliacao, autor=autor_inativo
    ).count() == 2
    assert set(
        Feedback.objects.filter(avaliacao=avaliacao).values_list(
            'conteudo', flat=True
        )
    ) == {'Primeiro texto do líder.', 'Segundo texto distinto do líder.'}


@pytest.mark.django_db
def test_t013_orfao_autor_ciencia_invalida_ciclo_aberto_id_colapsado(
    colaborador, lider, ciclo_aberto, tmp_path
):
    """T013: órfão de autor; ciência ilegível; ciclo aberto skip; ID colapsado."""
    _t013_solides_ids(colaborador, lider)
    canonica = _t009_avaliacao(colaborador, solides_id='1001')
    operacional = Avaliacao.objects.get(ciclo=ciclo_aberto, usuario=colaborador)
    operacional.solides_id = '8001'
    operacional.save(update_fields=['solides_id'])
    etapa_aberta = operacional.etapa
    criado = datetime(2024, 6, 5, 11, 0, 0)
    notas, comentarios, avaliacoes = _t009_paths(
        tmp_path,
        notas_rows=[],
        header_rows=[
            _header_row(
                '1001',
                nome_avaliado=colaborador.nome,
                nome_avaliador=colaborador.nome,
            ),
            _header_row(
                '1002',
                nome_avaliado=colaborador.nome,
                nome_avaliador=lider.nome,
            ),
            _header_row(
                '8001',
                solicitacao='80',
                avaliado_id='101',
                nome_avaliado=colaborador.nome,
                nome_avaliador=colaborador.nome,
            ),
        ],
        comentarios_rows=[
            _comentario_row(
                avaliacao_id='1002',
                avaliador_id='201',
                avaliador=lider.nome,
                avaliado=colaborador.nome,
                comentario='Comentário no ID colapsado.',
                criado_em=criado,
            ),
            _comentario_row(
                avaliacao_id='1001',
                avaliador_id='9999',
                avaliador='Ninguém Desconhecido',
                avaliado=colaborador.nome,
                comentario='Autor irresolvível.',
                criado_em=criado,
            ),
            _comentario_row(
                avaliacao_id='1001',
                avaliador_id='201',
                avaliador=lider.nome,
                avaliado=colaborador.nome,
                comentario='Líder sem data interpretável.',
                criado_em='data-invalida',
            ),
            _comentario_row(
                avaliacao_id='8001',
                avaliador_id='201',
                avaliador=lider.nome,
                avaliado=colaborador.nome,
                comentario='Ciclo ainda aberto.',
                criado_em=criado,
            ),
        ],
    )
    before_users = CustomUser.objects.count()
    before_av = Avaliacao.objects.count()

    report = import_notas_comentarios(notas, comentarios, avaliacoes)

    assert report.comentarios_criados == 1
    assert Feedback.objects.filter(avaliacao=canonica).count() == 1
    fb = Feedback.objects.get(avaliacao=canonica)
    assert fb.conteudo == 'Comentário no ID colapsado.'
    assert fb.tipo == Feedback.Tipo.LIDER
    assert report.n_orfaos_autor == 1
    assert any(e.label == 'ciencia_data_invalida' for e in report.conflitos)
    assert report.n_conflitos_ciclo_aberto == 1
    assert report.n_ids_colapsados_resolvidos == 1
    assert Feedback.objects.filter(avaliacao=operacional).count() == 0
    operacional.refresh_from_db()
    assert operacional.etapa == etapa_aberta
    assert CustomUser.objects.count() == before_users
    assert CustomUser.objects.filter(solides_id='9999').exists() is False
    assert Avaliacao.objects.count() == before_av
    assert Avaliacao.objects.filter(solides_id='1002').exists() is False


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


def test_t014_command_nao_e_mais_stub_e_emite_secoes():
    """T014: CLI deixa de stubar comentários; contrato cita seções do relatório."""
    text = _IMPORT_NOTAS_COMMAND.read_text(encoding='utf-8')
    assert 'no-op até US2' not in text
    assert 'comentários stub' not in text.lower()
    assert 'Comentários stub' not in text
    assert 'comentarios_criados' in text
    assert 'comentarios_inalterados' in text
    assert 'orfaos_autor' in text
    assert 'transaction.atomic' in text
    assert 'format_notas_comentarios_report' in text
    import_blob = '\n'.join(
        line
        for line in text.splitlines()
        if line.lstrip().startswith(('import ', 'from '))
    )
    for token in _DENYLIST_IMPORT_TOKENS:
        assert token not in import_blob, token


@pytest.mark.django_db
def test_t014_command_fase_comentarios_relatorio_exit_0(
    colaborador, lider, tmp_path
):
    """T014: call_command persiste notas+comentários e emite comentarios_*/orfaos_autor."""
    _t013_solides_ids(colaborador, lider)
    competencia = _t009_catalogo()
    avaliacao = _t009_avaliacao(colaborador)
    etapa = avaliacao.etapa
    concluida = avaliacao.concluida
    nome = colaborador.nome
    lider_nome = lider.nome
    criado = datetime(2024, 6, 3, 14, 30, 0)
    texto_lider = 'Desempenho consistente no trimestre.'
    texto_auto = 'Minha autoavaliação qualitativa.'
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
                avaliador=lider_nome,
                avaliado=nome,
                nota=4,
            ),
        ],
        header_rows=[
            _header_row('1001', nome_avaliado=nome, nome_avaliador=nome),
        ],
        comentarios_rows=[
            _comentario_row(
                avaliacao_id='1001',
                avaliador_id='201',
                avaliador=lider_nome,
                avaliado=nome,
                comentario=texto_lider,
                criado_em=criado,
            ),
            _comentario_row(
                avaliacao_id='1001',
                avaliador_id='101',
                avaliador=nome,
                avaliado=nome,
                comentario=texto_auto,
                criado_em=criado,
            ),
            _comentario_row(
                avaliacao_id='1001',
                avaliador_id='9999',
                avaliador='Ninguém Desconhecido',
                avaliado=nome,
                comentario='Autor irresolvível não deve persistir.',
                criado_em=criado,
            ),
        ],
    )
    report_path = tmp_path / 'relatorio-notas-comentarios.txt'
    stdout = StringIO()
    before_av = Avaliacao.objects.count()
    before_users = CustomUser.objects.count()

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
    assert 'comentarios_criados: 2' in text
    assert 'comentarios_inalterados: 0' in text
    assert 'orfaos_autor: 1' in text
    sections = _amostra_items_by_section(text)
    assert 'comentarios_criados:' in sections
    assert 'comentarios_inalterados:' in sections
    assert 'orfaos_autor:' in sections
    assert len(sections['comentarios_criados:']) == 2
    assert len(sections['orfaos_autor:']) == 1
    assert 'avaliador_id=***999' in sections['orfaos_autor:'][0]
    assert 'motivo=usuario_nao_resolvido' in sections['orfaos_autor:'][0]
    assert texto_lider not in text
    assert texto_auto not in text
    assert 'Autor irresolvível' not in text
    assert 'Ninguém Desconhecido' not in text
    assert nome not in text
    assert lider_nome not in text
    assert colaborador.email not in text
    assert lider.email not in text
    assert _EMAIL not in text
    assert Avaliacao.objects.count() == before_av
    assert CustomUser.objects.count() == before_users
    assert CustomUser.objects.filter(solides_id='9999').exists() is False
    linha = AvaliacaoCompetencia.objects.get(
        avaliacao=avaliacao, competencia=competencia
    )
    assert linha.nota_autoavaliacao == Decimal('3.00')
    assert linha.nota_lider == Decimal('4.00')
    avaliacao.refresh_from_db()
    assert avaliacao.nota_final_lider is not None
    assert avaliacao.etapa == etapa
    assert avaliacao.concluida == concluida
    assert Feedback.objects.filter(avaliacao=avaliacao).count() == 2
    lider_fb = Feedback.objects.get(avaliacao=avaliacao, tipo=Feedback.Tipo.LIDER)
    auto_fb = Feedback.objects.get(
        avaliacao=avaliacao, tipo=Feedback.Tipo.COLABORADOR
    )
    assert lider_fb.autor_id == lider.pk
    assert lider_fb.conteudo == texto_lider
    assert lider_fb.ciente_em is not None
    assert auto_fb.autor_id == colaborador.pk
    assert auto_fb.conteudo == texto_auto
    assert auto_fb.ciente_em is None

    stdout_2 = StringIO()
    result_2 = call_command(
        'importar_notas_comentarios',
        notas=str(notas),
        comentarios=str(comentarios),
        avaliacoes=str(avaliacoes),
        stdout=stdout_2,
    )
    text_2 = stdout_2.getvalue()
    assert result_2 in (0, None)
    assert 'comentarios_criados: 0' in text_2
    assert 'comentarios_inalterados: 2' in text_2
    assert 'orfaos_autor: 1' in text_2
    assert Feedback.objects.filter(avaliacao=avaliacao).count() == 2
    lider_fb.refresh_from_db()
    assert lider_fb.conteudo == texto_lider


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


# --- T015 validação US2 (quickstart C6) ---


@pytest.mark.django_db
def test_t015_c6_comentarios_ciencia_autor_n_textos_etapa_intacta(
    colaborador, lider, tmp_path
):
    """C6: líder com ciência; auto sem ciência; inativo ok; órfão; N textos."""
    _t013_solides_ids(colaborador, lider)
    autor_inativo = _make_autor(
        email='ex-lider-c6@test.greenn.com.br',
        nome='Carla Inativa C6',
        solides_id='202',
        is_active=False,
    )
    avaliacao = _t009_avaliacao(colaborador)
    etapa = avaliacao.etapa
    concluida = avaliacao.concluida
    criado = datetime(2024, 6, 3, 14, 30, 0)
    notas, comentarios, avaliacoes = _t009_paths(
        tmp_path,
        notas_rows=[],
        header_rows=[
            _header_row(
                '1001',
                nome_avaliado=colaborador.nome,
                nome_avaliador=colaborador.nome,
            ),
        ],
        comentarios_rows=[
            _comentario_row(
                avaliacao_id='1001',
                avaliador_id='201',
                avaliador=lider.nome,
                avaliado=colaborador.nome,
                comentario='Primeiro texto do líder.',
                criado_em=criado,
            ),
            _comentario_row(
                avaliacao_id='1001',
                avaliador_id='201',
                avaliador=lider.nome,
                avaliado=colaborador.nome,
                comentario='Segundo texto distinto do líder.',
                criado_em=criado,
            ),
            _comentario_row(
                avaliacao_id='1001',
                avaliador_id='101',
                avaliador=colaborador.nome,
                avaliado=colaborador.nome,
                comentario='Minha autoavaliação qualitativa.',
                criado_em=criado,
            ),
            _comentario_row(
                avaliacao_id='1001',
                avaliador_id='202',
                avaliador=autor_inativo.nome,
                avaliado=colaborador.nome,
                comentario='Comentário de autor inativo.',
                criado_em=criado,
            ),
            _comentario_row(
                avaliacao_id='1001',
                avaliador_id='9999',
                avaliador='Ninguém Desconhecido',
                avaliado=colaborador.nome,
                comentario='Autor irresolvível.',
                criado_em=criado,
            ),
        ],
    )
    before_users = CustomUser.objects.count()
    before_av = Avaliacao.objects.count()

    report = import_notas_comentarios(notas, comentarios, avaliacoes)

    assert report.comentarios_criados == 4
    assert report.n_orfaos_autor == 1
    assert Feedback.objects.filter(avaliacao=avaliacao).count() == 4

    lider_fbs = list(
        Feedback.objects.filter(
            avaliacao=avaliacao, autor=lider, tipo=Feedback.Tipo.LIDER
        ).order_by('pk')
    )
    assert len(lider_fbs) == 2
    expected = timezone.make_aware(criado, timezone.get_current_timezone())
    for fb in lider_fbs:
        assert fb.tipo == Feedback.Tipo.LIDER
        assert fb.ciente_em is not None
        assert abs((fb.ciente_em - expected).total_seconds()) < 0.001

    auto_fb = Feedback.objects.get(
        avaliacao=avaliacao, tipo=Feedback.Tipo.COLABORADOR
    )
    assert auto_fb.autor_id == colaborador.pk
    assert auto_fb.ciente_em is None

    assert autor_inativo.is_active is False
    inativo_fb = Feedback.objects.get(avaliacao=avaliacao, autor=autor_inativo)
    assert inativo_fb.tipo == Feedback.Tipo.LIDER
    assert inativo_fb.ciente_em is not None

    avaliacao.refresh_from_db()
    assert avaliacao.etapa == etapa
    assert avaliacao.concluida == concluida
    assert CustomUser.objects.count() == before_users
    assert CustomUser.objects.filter(solides_id='9999').exists() is False
    assert Avaliacao.objects.count() == before_av
    assert Avaliacao.objects.filter(solides_id='1001').count() == 1


@pytest.mark.skipif(
    shutil.which('git') is None,
    reason='git ausente no PATH (ex. container web sem git)',
)
def test_t015_c6_git_diff_denylist_vazio():
    """C6: denylist intacta (US2 não edita stage/cycle/evaluation/scope/012)."""
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


# --- T018: dry-run + IDs + args inválidos (samples-only / SC-006 / SC-008) ---


def _t018_assert_samples_only() -> None:
    for path in (
        _NOTAS_MIN,
        _COMENTARIOS_MIN,
        _AVALIACOES_HEADERS_MIN,
        _SAMPLES_DIR,
    ):
        assert path.exists(), path
        assert 'raw' not in path.parts
        assert _RAW_PII_DIR not in str(path)


def _t018_write_counts() -> tuple[int, int, int, int]:
    """Linhas, feedbacks e notas finais — SC-008."""
    return (
        AvaliacaoCompetencia.objects.count(),
        Feedback.objects.count(),
        Avaliacao.objects.exclude(nota_final_lider__isnull=True).count(),
        Avaliacao.objects.exclude(
            nota_final_autoavaliacao__isnull=True
        ).count(),
    )


def _t018_nota_final_snapshot() -> set[tuple]:
    return set(
        Avaliacao.objects.values_list(
            'pk', 'nota_final_lider', 'nota_final_autoavaliacao'
        )
    )


def _t018_seed_world() -> dict[str, Avaliacao]:
    """Pré-condição 010/011 alinhada aos samples (canônico 1001 / 3001 / 6001)."""
    cargo = Cargo.objects.create(nome='Analista Sample T018', nivel=1)
    users: dict[str, CustomUser] = {}
    for email, nome, solides_id in _T018_SEED_USERS:
        users[solides_id] = CustomUser.objects.create_user(
            email=email,
            password=DEFAULT_PASSWORD,
            nome=nome,
            solides_id=solides_id,
            cargo=cargo,
            email_confirmado_em=timezone.now(),
        )
    ciclo = _ciclo_encerrado()
    escala = Escala.objects.create(
        nome='Escala T018',
        valor_minimo=1,
        valor_maximo=5,
        is_active=True,
    )
    for sid, nome, tipo in (
        ('HAB10', 'Comunicacao Fixture', Competencia.Tipo.COMPORTAMENTAL),
        ('HAB11', 'Colaboracao Fixture', Competencia.Tipo.COMPORTAMENTAL),
        ('HAB12', 'Lideranca Fixture', Competencia.Tipo.LIDERANCA),
    ):
        Competencia.objects.create(
            nome=nome,
            tipo=tipo,
            escala=escala,
            solides_id=sid,
            is_active=True,
        )
    mapping = (('1001', '101'), ('3001', '100'), ('6001', '103'))
    avaliacoes: dict[str, Avaliacao] = {}
    for av_sid, user_sid in mapping:
        avaliacoes[av_sid] = Avaliacao.objects.create(
            ciclo=ciclo,
            usuario=users[user_sid],
            etapa=Avaliacao.Etapa.FEEDBACK,
            concluida=True,
            solides_id=av_sid,
        )
    return avaliacoes


def _t018_import_samples(**kwargs):
    _t018_assert_samples_only()
    return import_notas_comentarios(
        _NOTAS_MIN,
        _COMENTARIOS_MIN,
        _AVALIACOES_HEADERS_MIN,
        **kwargs,
    )


def test_t018_suite_usa_somente_samples():
    """T018 / OPSEC: fixtures da suíte não apontam para backups PII."""
    _t018_assert_samples_only()
    text = Path(__file__).read_text(encoding='utf-8')
    assert _RAW_PII_DIR not in text


@pytest.mark.django_db
def test_t018_dry_run_zero_writes_totais_projetados():
    """SC-008 / C1: dry-run projeta totais e zero writes em linhas/feedback/nota_final_*."""
    _t018_seed_world()
    before = _t018_write_counts()
    av_before = Avaliacao.objects.count()
    users_before = CustomUser.objects.count()
    notas_finais = _t018_nota_final_snapshot()
    av_ids = set(Avaliacao.objects.values_list('solides_id', flat=True))

    report = _t018_import_samples(dry_run=True)

    assert report.modo == 'dry-run'
    assert report.notas_criadas == _T018_NOTAS_CRIADAS
    assert report.comentarios_criados == _T018_COMENTARIOS_CRIADOS
    assert report.n_orfaos_avaliacao == _T018_ORFAOS_AVALIACAO
    assert report.n_orfaos_autor == _T018_ORFAOS_AUTOR
    assert report.n_ids_colapsados_resolvidos == _T018_IDS_COLAPSADOS
    assert _t018_write_counts() == before
    assert Avaliacao.objects.count() == av_before
    assert CustomUser.objects.count() == users_before
    assert _t018_nota_final_snapshot() == notas_finais
    assert set(Avaliacao.objects.values_list('solides_id', flat=True)) == av_ids
    assert Avaliacao.objects.filter(solides_id='1002').exists() is False
    assert Avaliacao.objects.filter(solides_id='88888').exists() is False
    assert AvaliacaoCompetencia.objects.count() == 0
    assert Feedback.objects.count() == 0


@pytest.mark.django_db
def test_t018_dry_run_via_comando_zero_writes():
    """C1: ``importar_notas_comentarios --dry-run`` com samples → exit 0, zero writes."""
    _t018_seed_world()
    before = _t018_write_counts()
    av_before = Avaliacao.objects.count()
    stdout = StringIO()

    result = call_command(
        'importar_notas_comentarios',
        notas=str(_NOTAS_MIN),
        comentarios=str(_COMENTARIOS_MIN),
        avaliacoes=str(_AVALIACOES_HEADERS_MIN),
        dry_run=True,
        stdout=stdout,
    )

    text = stdout.getvalue()
    assert result in (0, None)
    assert 'modo: dry-run' in text
    assert f'notas_criadas: {_T018_NOTAS_CRIADAS}' in text
    assert f'comentarios_criados: {_T018_COMENTARIOS_CRIADOS}' in text
    assert f'orfaos_avaliacao: {_T018_ORFAOS_AVALIACAO}' in text
    assert f'ids_colapsados_resolvidos: {_T018_IDS_COLAPSADOS}' in text
    for token in _T018_PII:
        assert token not in text, token
    assert _t018_write_counts() == before
    assert Avaliacao.objects.count() == av_before
    assert AvaliacaoCompetencia.objects.count() == 0
    assert Feedback.objects.count() == 0
    assert 'raw' not in _NOTAS_MIN.parts


@pytest.mark.django_db
def test_t018_id_canonico_colapsado_orfao_samples():
    """SC-006 / C3: canônico e colapsado na mesma Avaliacao; órfão não inventa."""
    avaliacoes = _t018_seed_world()
    canonica = avaliacoes['1001']
    before_av = Avaliacao.objects.count()
    before_users = CustomUser.objects.count()
    etapa = canonica.etapa
    concluida = canonica.concluida

    report = _t018_import_samples()

    assert Avaliacao.objects.count() == before_av
    assert CustomUser.objects.count() == before_users
    assert Avaliacao.objects.filter(solides_id='1001').count() == 1
    assert Avaliacao.objects.filter(solides_id='1002').exists() is False
    assert Avaliacao.objects.filter(solides_id='1003').exists() is False
    assert Avaliacao.objects.filter(solides_id='88888').exists() is False
    assert report.n_orfaos_avaliacao == _T018_ORFAOS_AVALIACAO
    assert report.n_ids_colapsados_resolvidos == _T018_IDS_COLAPSADOS
    linha = AvaliacaoCompetencia.objects.get(
        avaliacao=canonica, competencia__solides_id='HAB10'
    )
    assert linha.nota_autoavaliacao == Decimal('3.00')
    assert linha.nota_lider == Decimal('4.00')
    assert AvaliacaoCompetencia.objects.filter(
        avaliacao=canonica, competencia__solides_id='HAB11'
    ).count() == 1
    canonica.refresh_from_db()
    assert canonica.etapa == etapa
    assert canonica.concluida == concluida
    assert canonica.solides_id == '1001'


@pytest.mark.django_db
def test_t018_args_faltando_exit_1_db_inalterado():
    """T018 / contrato: args obrigatórios ausentes → exit 1; DB intacto."""
    _t018_seed_world()
    before = _t018_write_counts()
    av_before = Avaliacao.objects.count()

    with pytest.raises(CommandError) as exc_info:
        call_command('importar_notas_comentarios')
    assert exc_info.value.returncode == 1
    assert _t018_write_counts() == before
    assert Avaliacao.objects.count() == av_before

    with pytest.raises(CommandError) as exc_notas:
        call_command(
            'importar_notas_comentarios',
            comentarios=str(_COMENTARIOS_MIN),
            avaliacoes=str(_AVALIACOES_HEADERS_MIN),
        )
    assert exc_notas.value.returncode == 1

    with pytest.raises(CommandError) as exc_com:
        call_command(
            'importar_notas_comentarios',
            notas=str(_NOTAS_MIN),
            avaliacoes=str(_AVALIACOES_HEADERS_MIN),
        )
    assert exc_com.value.returncode == 1

    with pytest.raises(CommandError) as exc_av:
        call_command(
            'importar_notas_comentarios',
            notas=str(_NOTAS_MIN),
            comentarios=str(_COMENTARIOS_MIN),
        )
    assert exc_av.value.returncode == 1
    assert _t018_write_counts() == before
    assert AvaliacaoCompetencia.objects.count() == 0
    assert Feedback.objects.count() == 0


@pytest.mark.django_db
def test_t018_arquivo_ausente_exit_1_db_inalterado(tmp_path: Path):
    """T018: arquivo inexistente → exit 1; DB inalterado (samples nos paths válidos)."""
    _t018_seed_world()
    before = _t018_write_counts()
    av_before = Avaliacao.objects.count()
    missing = tmp_path / 'notas_inexistente.xlsx'
    assert not missing.exists()
    assert 'raw' not in missing.parts

    with pytest.raises(CommandError) as exc_info:
        call_command(
            'importar_notas_comentarios',
            notas=str(missing),
            comentarios=str(_COMENTARIOS_MIN),
            avaliacoes=str(_AVALIACOES_HEADERS_MIN),
        )
    assert exc_info.value.returncode == 1
    assert 'não encontrado' in str(exc_info.value).lower()
    assert _t018_write_counts() == before
    assert Avaliacao.objects.count() == av_before

    with pytest.raises(LegacyParseError, match='não encontrado'):
        import_notas_comentarios(
            missing, _COMENTARIOS_MIN, _AVALIACOES_HEADERS_MIN
        )
    assert _t018_write_counts() == before
    assert AvaliacaoCompetencia.objects.count() == 0
    assert Feedback.objects.count() == 0


@pytest.mark.django_db
def test_t018_arquivo_ooxml_corrompido_exit_1_db_inalterado(tmp_path: Path):
    """T018: OOXML ilegível → exit 1; nenhuma escrita parcial."""
    _t018_seed_world()
    before = _t018_write_counts()
    av_before = Avaliacao.objects.count()
    corrupted = tmp_path / 'notas_corrompido.xlsx'
    corrupted.write_bytes(b'this is not a valid ooxml workbook')
    assert 'raw' not in corrupted.parts

    with pytest.raises(CommandError) as exc_info:
        call_command(
            'importar_notas_comentarios',
            notas=str(corrupted),
            comentarios=str(_COMENTARIOS_MIN),
            avaliacoes=str(_AVALIACOES_HEADERS_MIN),
        )
    assert exc_info.value.returncode == 1
    assert 'ilegível' in str(exc_info.value).lower()
    assert _t018_write_counts() == before
    assert Avaliacao.objects.count() == av_before

    with pytest.raises(LegacyParseError):
        import_notas_comentarios(
            corrupted, _COMENTARIOS_MIN, _AVALIACOES_HEADERS_MIN
        )
    assert _t018_write_counts() == before
    assert AvaliacaoCompetencia.objects.count() == 0
    assert Feedback.objects.count() == 0


# --- T019: conflitos / write-once / extras / fórmula (samples-only) ---


def _t019_snapshot_linhas() -> set[tuple]:
    """Unique (avaliacao, competencia) + snapshots write-once — SC-005."""
    return set(
        AvaliacaoCompetencia.objects.values_list(
            'avaliacao_id',
            'competencia_id',
            'peso_utilizado',
            'nivel_esperado_utilizado',
        )
    )


def _t019_mover_para_ciclo_aberto(avaliacao: Avaliacao) -> Ciclo:
    """Marca a avaliação em ciclo ``status=aberto`` sem ``open_cycle``."""
    ciclo = Ciclo.objects.create(
        nome='Ciclo Aberto T019',
        data_inicio=date(2024, 1, 1),
        data_fim=date(2024, 12, 31),
        status=Ciclo.Status.ABERTO,
    )
    avaliacao.ciclo = ciclo
    avaliacao.save(update_fields=['ciclo', 'updated_at'])
    return ciclo


@pytest.mark.django_db
def test_t019_dois_lideres_divergentes_sem_media():
    """C4 / R6: HAB12 com dois líderes → conflito; sem média 4.5; sem persistir líder."""
    avaliacoes = _t018_seed_world()
    canonica = avaliacoes['1001']

    report = _t018_import_samples()

    assert report.n_conflitos_lider_divergente == _T019_LIDER_DIVERGENTE
    assert AvaliacaoCompetencia.objects.filter(
        avaliacao=canonica, competencia__solides_id='HAB12'
    ).exists() is False
    hab10 = AvaliacaoCompetencia.objects.get(
        avaliacao=canonica, competencia__solides_id='HAB10'
    )
    assert hab10.nota_autoavaliacao == Decimal('3.00')
    assert hab10.nota_lider == Decimal('4.00')
    assert hab10.nota_lider != _T019_MEDIA_PROIBIDA
    canonica.refresh_from_db()
    assert canonica.nota_final_lider != _T019_MEDIA_PROIBIDA
    assert AvaliacaoCompetencia.objects.filter(
        nota_lider=_T019_MEDIA_PROIBIDA
    ).exists() is False
    assert Avaliacao.objects.filter(solides_id='1001').count() == 1


@pytest.mark.django_db
def test_t019_ciclo_aberto_skip_sc012():
    """C4 / SC-012: avaliação em ciclo ``status=aberto`` → skip; etapa intacta."""
    avaliacoes = _t018_seed_world()
    operacional = avaliacoes['3001']
    etapa = operacional.etapa
    concluida = operacional.concluida
    _t019_mover_para_ciclo_aberto(operacional)
    before_linhas = AvaliacaoCompetencia.objects.filter(
        avaliacao=operacional
    ).count()
    before_av = Avaliacao.objects.count()

    report = _t018_import_samples()

    assert report.n_conflitos_ciclo_aberto == 1
    assert AvaliacaoCompetencia.objects.filter(avaliacao=operacional).count() == (
        before_linhas
    )
    assert AvaliacaoCompetencia.objects.filter(avaliacao=operacional).exists() is False
    assert Avaliacao.objects.count() == before_av
    operacional.refresh_from_db()
    assert operacional.etapa == etapa
    assert operacional.concluida == concluida
    assert operacional.nota_final_lider is None
    assert operacional.ciclo.status == Ciclo.Status.ABERTO
    assert AvaliacaoCompetencia.objects.filter(
        avaliacao=avaliacoes['1001']
    ).exists() is True


@pytest.mark.django_db
def test_t019_write_once_segunda_run_nao_copia_cargo_competencia():
    """SC-005: 2ª run snapshots bit-a-bit; CargoCompetencia vigente divergente ignorada."""
    avaliacoes = _t018_seed_world()
    canonica = avaliacoes['1001']

    _t018_import_samples()
    linha = AvaliacaoCompetencia.objects.get(
        avaliacao=canonica, competencia__solides_id='HAB10'
    )
    peso_historico = linha.peso_utilizado
    nivel_historico = linha.nivel_esperado_utilizado
    assert peso_historico == Decimal('1.00')
    assert nivel_historico == Decimal('2.00')
    pairs_antes = set(
        AvaliacaoCompetencia.objects.values_list('avaliacao_id', 'competencia_id')
    )
    snap_antes = _t019_snapshot_linhas()

    CargoCompetencia.objects.create(
        cargo=canonica.usuario.cargo,
        competencia=linha.competencia,
        nivel_esperado=_T019_CARGO_NIVEL_VIGENTE,
        peso=_T019_CARGO_PESO_VIGENTE,
    )

    report = _t018_import_samples()

    linha.refresh_from_db()
    assert linha.peso_utilizado == peso_historico
    assert linha.nivel_esperado_utilizado == nivel_historico
    assert linha.peso_utilizado != _T019_CARGO_PESO_VIGENTE
    assert linha.nivel_esperado_utilizado != _T019_CARGO_NIVEL_VIGENTE
    assert _t019_snapshot_linhas() == snap_antes
    assert set(
        AvaliacaoCompetencia.objects.values_list('avaliacao_id', 'competencia_id')
    ) == pairs_antes
    assert report.notas_criadas == 0
    tipos = [entry.label for entry in report.conflitos]
    assert 'snapshot_divergente' not in tipos


@pytest.mark.django_db
def test_t019_habilidade_extra_vs_orfao_kpi_zero_cargo_competencia():
    """C8 / SC-014: extra não-KPI criada; SLA/ambíguo órfãos; zero CargoCompetencia."""
    avaliacoes = _t018_seed_world()
    before_cc = CargoCompetencia.objects.count()
    before_kpi = Competencia.objects.filter(solides_id__in=('99002', '99003')).count()
    before_sla = Competencia.objects.filter(nome='SLA').count()
    before_amb = Competencia.objects.filter(nome='Erros de usabilidade').count()

    report = _t018_import_samples()

    extra = Competencia.objects.get(solides_id='99001')
    assert extra.nome == 'Habilidade Extra Fixture'
    assert extra.is_active is True
    assert AvaliacaoCompetencia.objects.filter(
        avaliacao=avaliacoes['1001'], competencia=extra
    ).count() == 1
    assert Competencia.objects.filter(solides_id='99002').exists() is False
    assert Competencia.objects.filter(solides_id='99003').exists() is False
    assert Competencia.objects.filter(nome='SLA').count() == before_sla
    assert Competencia.objects.filter(nome='Erros de usabilidade').count() == before_amb
    assert Competencia.objects.filter(solides_id__in=('99002', '99003')).count() == (
        before_kpi
    )
    assert report.habilidades_extras_criadas == _T019_EXTRAS
    assert report.n_orfaos_competencia == _T019_ORFAOS_COMPETENCIA
    assert CargoCompetencia.objects.count() == before_cc
    assert CargoCompetencia.objects.filter(competencia=extra).count() == 0
    assert CargoCompetencia.objects.count() == 0


@pytest.mark.django_db
def test_t019_formula_chamada_sem_create_competency_lines():
    """C5: ``calcular_nota_final_lider`` é chamado; ``create_competency_lines`` não."""
    avaliacoes = _t018_seed_world()
    canonica = avaliacoes['1001']
    gestor = avaliacoes['3001']
    etapa = canonica.etapa
    concluida = canonica.concluida

    with (
        patch(
            'apps.reviews.services.evaluation.create_competency_lines'
        ) as spy_lines,
        patch(
            'apps.reviews.services.legacy_import.importer.calcular_nota_final_lider',
            wraps=calcular_nota_final_lider,
        ) as spy_calc,
    ):
        report = _t018_import_samples()

    spy_lines.assert_not_called()
    assert spy_calc.called
    tipos = [entry.label for entry in report.conflitos]
    assert 'calculo_lider' in tipos
    canonica.refresh_from_db()
    gestor.refresh_from_db()
    assert canonica.nota_final_lider is None
    assert canonica.nota_final_lider != _T019_MEDIA_PROIBIDA
    assert gestor.nota_final_lider is not None
    assert gestor.nota_final_lider != _T019_MEDIA_PROIBIDA
    assert canonica.etapa == etapa
    assert canonica.concluida == concluida
    assert AvaliacaoCompetencia.objects.filter(avaliacao=canonica).exists() is True


@pytest.mark.django_db
def test_t019_calculation_error_vira_conflito_sem_media():
    """C5: CalculationError → conflito; ``nota_final_*`` não é média inventada."""
    avaliacoes = _t018_seed_world()
    gestor = avaliacoes['3001']
    canonica = avaliacoes['1001']

    with (
        patch(
            'apps.reviews.services.evaluation.create_competency_lines'
        ) as spy_lines,
        patch(
            'apps.reviews.services.legacy_import.importer.calcular_nota_final_lider',
            side_effect=CalculationError('Soma de peso_utilizado igual a zero'),
        ) as spy_calc,
    ):
        report = _t018_import_samples()

    spy_lines.assert_not_called()
    assert spy_calc.called
    tipos = [entry.label for entry in report.conflitos]
    assert 'calculo_lider' in tipos
    assert AvaliacaoCompetencia.objects.count() == _T018_NOTAS_CRIADAS
    gestor.refresh_from_db()
    canonica.refresh_from_db()
    assert gestor.nota_final_lider is None
    assert canonica.nota_final_lider is None
    assert gestor.nota_final_lider != _T019_MEDIA_PROIBIDA
    assert canonica.nota_final_lider != _T019_MEDIA_PROIBIDA
    assert Avaliacao.objects.exclude(nota_final_lider__isnull=True).count() == 0
    assert AvaliacaoCompetencia.objects.filter(
        nota_lider=_T019_MEDIA_PROIBIDA
    ).exists() is False


# --- T020: comentários / PII / raw/ / teste de ouro (samples-only) ---


def _t020_etapa_snapshot() -> dict[int, tuple[str, bool, int, str]]:
    """``(etapa, concluida, ciclo_id, ciclo.status)`` por avaliação — SC-013."""
    return {
        av.pk: (av.etapa, av.concluida, av.ciclo_id, av.ciclo.status)
        for av in Avaliacao.objects.select_related('ciclo')
    }


def _t020_iter_allowlist_py() -> list[Path]:
    files: list[Path] = []
    for rel in _T020_ALLOWLIST_PY:
        path = _REPO_ROOT / rel
        if path.is_file():
            files.append(path)
            continue
        files.extend(sorted(path.rglob('*.py')))
    return files


def _t020_assert_report_sem_pii(text: str) -> None:
    """SC-010 / C10: amostra ≤ 5; zero comentário/nome/e-mail completos."""
    for token in _T020_PII:
        assert token not in text, token
        assert token.lower() not in text.lower(), token
    sections = _amostra_items_by_section(text)
    assert sections
    for header, items in sections.items():
        assert len(items) <= _SAMPLE_MAX, header
        for item in items:
            for token in _T020_PII:
                assert token not in item, (header, token)


@pytest.mark.django_db
def test_t020_comentarios_tipo_ciencia_n_textos_chave_natural():
    """SC-007 / C6: tipo, ciente_em líder, auto null, N textos, sem duplicata."""
    avaliacoes = _t018_seed_world()
    canonica = avaliacoes['1001']
    ana = CustomUser.objects.get(solides_id='101')
    gestor = CustomUser.objects.get(solides_id='100')
    bruno = CustomUser.objects.get(solides_id='102')
    etapa = canonica.etapa
    concluida = canonica.concluida
    before_users = CustomUser.objects.count()
    before_av = Avaliacao.objects.count()

    report = _t018_import_samples()

    assert report.comentarios_criados == _T018_COMENTARIOS_CRIADOS
    assert report.n_orfaos_autor == _T018_ORFAOS_AUTOR
    assert Feedback.objects.filter(avaliacao=canonica).count() == 4
    assert Feedback.objects.count() == 4
    assert set(
        Feedback.objects.filter(avaliacao=canonica).values_list(
            'conteudo', flat=True
        )
    ) == {_T020_LIDER_A, _T020_LIDER_B, _T020_AUTO, _T020_COLAPSADO}
    assert Feedback.objects.filter(conteudo=_T020_ORFAO_TEXTO).exists() is False

    lider_gestor = list(
        Feedback.objects.filter(
            avaliacao=canonica, autor=gestor, tipo=Feedback.Tipo.LIDER
        ).order_by('pk')
    )
    assert len(lider_gestor) == 2
    expected_a = parse_legacy_datetime(45446.5)
    expected_b = parse_legacy_datetime(45447)
    by_conteudo = {fb.conteudo: fb for fb in lider_gestor}
    assert abs(
        (by_conteudo[_T020_LIDER_A].ciente_em - expected_a).total_seconds()
    ) < 0.001
    assert abs(
        (by_conteudo[_T020_LIDER_B].ciente_em - expected_b).total_seconds()
    ) < 0.001
    for fb in lider_gestor:
        assert fb.tipo == Feedback.Tipo.LIDER
        assert fb.ciente_em is not None

    auto_fb = Feedback.objects.get(
        avaliacao=canonica, tipo=Feedback.Tipo.COLABORADOR
    )
    assert auto_fb.autor_id == ana.pk
    assert auto_fb.conteudo == _T020_AUTO
    assert auto_fb.ciente_em is None

    colapsado_fb = Feedback.objects.get(conteudo=_T020_COLAPSADO)
    assert colapsado_fb.avaliacao_id == canonica.pk
    assert colapsado_fb.autor_id == bruno.pk
    assert colapsado_fb.tipo == Feedback.Tipo.LIDER
    expected_c = parse_legacy_datetime(45323.25)
    assert abs((colapsado_fb.ciente_em - expected_c).total_seconds()) < 0.001
    assert Avaliacao.objects.filter(solides_id='1002').exists() is False

    pks_antes = set(Feedback.objects.values_list('pk', flat=True))
    conteudos_antes = set(
        Feedback.objects.values_list('pk', 'conteudo', 'tipo')
    )
    second = _t018_import_samples()
    assert second.comentarios_criados == 0
    assert second.comentarios_inalterados == _T018_COMENTARIOS_CRIADOS
    assert Feedback.objects.count() == 4
    assert set(Feedback.objects.values_list('pk', flat=True)) == pks_antes
    assert set(Feedback.objects.values_list('pk', 'conteudo', 'tipo')) == (
        conteudos_antes
    )
    by_conteudo[_T020_LIDER_A].refresh_from_db()
    assert by_conteudo[_T020_LIDER_A].conteudo == _T020_LIDER_A

    canonica.refresh_from_db()
    assert canonica.etapa == etapa
    assert canonica.concluida == concluida
    assert CustomUser.objects.count() == before_users
    assert CustomUser.objects.filter(solides_id='88888').exists() is False
    assert Avaliacao.objects.count() == before_av
    assert Avaliacao.objects.filter(solides_id='1001').count() == 1


@pytest.mark.django_db
def test_t020_relatorio_mascara_pii_max_5(tmp_path: Path):
    """SC-010 / C10: stdout == --report-file; amostra ≤ 5; zero PII completa."""
    _t018_seed_world()
    report_path = tmp_path / 'relatorio-notas-comentarios.txt'
    stdout = StringIO()
    assert 'raw' not in report_path.parts

    result = call_command(
        'importar_notas_comentarios',
        notas=str(_NOTAS_MIN),
        comentarios=str(_COMENTARIOS_MIN),
        avaliacoes=str(_AVALIACOES_HEADERS_MIN),
        report_file=str(report_path),
        stdout=stdout,
    )

    text = stdout.getvalue()
    file_text = report_path.read_text(encoding='utf-8')
    assert result in (0, None)
    assert file_text == text
    assert '=== Importação notas/comentários legado Sólides ===' in text
    assert 'modo: persist' in text
    assert f'comentarios_criados: {_T018_COMENTARIOS_CRIADOS}' in text
    assert f'orfaos_autor: {_T018_ORFAOS_AUTOR}' in text
    assert '--- Amostra (mascarada, max 5 por seção) ---' in text
    assert mask_solides_id('1001') in text
    _t020_assert_report_sem_pii(text)
    sections = _amostra_items_by_section(text)
    assert 'comentarios_criados:' in sections
    assert len(sections['comentarios_criados:']) == _T018_COMENTARIOS_CRIADOS
    assert len(sections['orfaos_autor:']) == _T018_ORFAOS_AUTOR
    for item in sections['comentarios_criados:']:
        assert 'avaliacao=' in item
        assert 'autor=' in item
        assert 'tipo=' in item
        assert 'conteudo=' not in item
        assert 'Comentário' not in item


def test_t020_suite_nao_referencia_raw():
    """SC-009 / C9: suíte e allowlist não apontam para backups PII ``raw/``."""
    _t018_assert_samples_only()
    suite = Path(__file__).read_text(encoding='utf-8')
    assert _RAW_PII_DIR not in suite
    for rel in _t020_iter_allowlist_py():
        blob = rel.read_text(encoding='utf-8')
        assert _RAW_PII_DIR not in blob, rel
        assert 'legado-solides/raw' not in blob, rel
        assert 'raw' not in rel.parts
    for path in (_NOTAS_MIN, _COMENTARIOS_MIN, _AVALIACOES_HEADERS_MIN):
        resolved = path.resolve()
        assert 'raw' not in resolved.parts
        assert _RAW_PII_DIR not in str(resolved)


@pytest.mark.django_db
def test_t020_ouro_import_nao_muta_etapa_concluida():
    """SC-013: executar o import não altera ``etapa``/``concluida`` nem ciclo."""
    avaliacoes = _t018_seed_world()
    canonica = avaliacoes['1001']
    before = _t020_etapa_snapshot()
    before_status = {
        ciclo.pk: ciclo.status for ciclo in Ciclo.objects.all()
    }

    _t018_import_samples()

    assert _t020_etapa_snapshot() == before
    assert {
        ciclo.pk: ciclo.status for ciclo in Ciclo.objects.all()
    } == before_status
    canonica.refresh_from_db()
    assert canonica.etapa == Avaliacao.Etapa.FEEDBACK
    assert canonica.concluida is True
    importer = (
        _REPO_ROOT / 'apps/reviews/services/legacy_import/importer.py'
    ).read_text(encoding='utf-8')
    command = _IMPORT_NOTAS_COMMAND.read_text(encoding='utf-8')
    assert '.etapa =' not in importer
    assert '.concluida =' not in importer
    assert '.etapa =' not in command
    assert '.concluida =' not in command


@pytest.mark.skipif(
    shutil.which('git') is None,
    reason='git ausente no PATH (ex. container web sem git)',
)
def test_t020_ouro_git_diff_denylist_vazio():
    """SC-013: denylist + asserts de stage/scope/reject intactos."""
    evaluation_diff = _git_diff(
        'HEAD', '--', 'apps/reviews/services/evaluation.py'
    )
    assert evaluation_diff == '', evaluation_diff

    working_tree = _git_diff('HEAD', '--', *_DENYLIST_PATHS)
    assert working_tree == '', working_tree

    stage_scope = _git_diff('HEAD', '--', *_STAGE_SCOPE_REJECT_TESTS)
    assert stage_scope == '', stage_scope

    for base in ('development', 'origin/development', 'main'):
        if _git_rev_exists(base):
            vs_base = _git_diff(base, '--', *_DENYLIST_PATHS)
            assert vs_base == '', vs_base
            vs_tests = _git_diff(base, '--', *_STAGE_SCOPE_REJECT_TESTS)
            assert vs_tests == '', vs_tests
            break


# --- T021: dry-run consolidado + falha pré-persistência + rollback atômico ---


def test_t021_command_nao_e_mais_stub_dry_run():
    """T021: CLI/importer deixam o stub ``set_rollback``; dry-run é zero write."""
    command = _IMPORT_NOTAS_COMMAND.read_text(encoding='utf-8')
    importer = (
        _REPO_ROOT / 'apps/reviews/services/legacy_import/importer.py'
    ).read_text(encoding='utf-8')
    assert 'stub até US3' not in command
    assert 'set_rollback' not in command
    assert 'set_rollback' not in importer
    assert 'transaction.atomic' in command
    assert 'transaction.atomic' in importer
    assert 'zero save/create/update' in command


@pytest.mark.django_db
def test_t021_dry_run_zero_save_create_update_e_formula():
    """T021 / SC-008: dry-run não chama save/create/update nem a fórmula."""
    _t018_seed_world()
    before_comp = Competencia.objects.count()
    before_extra = Competencia.objects.filter(solides_id='99001').count()

    with (
        patch.object(AvaliacaoCompetencia, 'save') as ac_save,
        patch.object(Feedback, 'save') as fb_save,
        patch.object(Competencia, 'save') as comp_save,
        patch.object(Avaliacao, 'save') as av_save,
        patch.object(CustomUser, 'save') as user_save,
        patch.object(Ciclo, 'save') as ciclo_save,
        patch(
            'apps.reviews.services.legacy_import.importer.calcular_nota_final_lider'
        ) as spy_lider,
        patch(
            'apps.reviews.services.legacy_import.importer.'
            'calcular_nota_final_autoavaliacao'
        ) as spy_auto,
    ):
        report = _t018_import_samples(dry_run=True)

    ac_save.assert_not_called()
    fb_save.assert_not_called()
    comp_save.assert_not_called()
    av_save.assert_not_called()
    user_save.assert_not_called()
    ciclo_save.assert_not_called()
    spy_lider.assert_not_called()
    spy_auto.assert_not_called()
    assert report.modo == 'dry-run'
    assert report.notas_criadas == _T018_NOTAS_CRIADAS
    assert report.comentarios_criados == _T018_COMENTARIOS_CRIADOS
    assert report.habilidades_extras_criadas == _T019_EXTRAS
    assert Competencia.objects.count() == before_comp
    assert Competencia.objects.filter(solides_id='99001').count() == before_extra
    assert AvaliacaoCompetencia.objects.count() == 0
    assert Feedback.objects.count() == 0


@pytest.mark.django_db
def test_t021_colunas_obrigatorias_ausentes_exit_1_db_inalterado(tmp_path: Path):
    """T021: colunas obrigatórias ausentes → exit 1; nenhuma escrita."""
    _t018_seed_world()
    before = _t018_write_counts()
    av_before = Avaliacao.objects.count()
    notas_sem_nota = _write_xlsx(
        tmp_path / 'notas_sem_coluna.xlsx',
        [h for h in _NOTAS_HEADERS if h != 'Nota'],
        [
            _nota_row(
                ident='n1',
                avaliacao_id='1001',
                avaliador='Ana Silva',
                avaliado='Ana Silva',
                nota=3,
            )[:-1],
        ],
    )
    comentarios = _write_xlsx(
        tmp_path / 'comentarios.xlsx',
        _COMENTARIOS_HEADERS,
        [],
    )
    avaliacoes = _write_xlsx(
        tmp_path / 'avaliacoes.xlsx',
        _AVALIACOES_HEADERS,
        [_header_row('1001', nome_avaliado='Ana Silva', nome_avaliador='Ana Silva')],
    )
    assert 'raw' not in notas_sem_nota.parts

    with pytest.raises(CommandError) as exc_info:
        call_command(
            'importar_notas_comentarios',
            notas=str(notas_sem_nota),
            comentarios=str(comentarios),
            avaliacoes=str(avaliacoes),
        )
    assert exc_info.value.returncode == 1
    assert 'obrigat' in str(exc_info.value).lower()
    assert _t018_write_counts() == before
    assert Avaliacao.objects.count() == av_before
    assert AvaliacaoCompetencia.objects.count() == 0
    assert Feedback.objects.count() == 0

    with pytest.raises(LegacyParseError, match='obrigat'):
        import_notas_comentarios(notas_sem_nota, comentarios, avaliacoes)
    assert _t018_write_counts() == before


@pytest.mark.django_db
def test_t021_rollback_atomico_das_duas_fases():
    """T021: exceção na fase comentários desfaz notas da mesma atomic."""
    _t018_seed_world()
    before = _t018_write_counts()
    notas_finais = _t018_nota_final_snapshot()
    extras_antes = Competencia.objects.filter(solides_id='99001').count()

    with patch(
        'apps.reviews.services.legacy_import.importer._upsert_feedback',
        side_effect=RuntimeError('falha na fase comentarios'),
    ):
        with pytest.raises(LegacyPersistError, match='fase comentarios'):
            _t018_import_samples()

    assert _t018_write_counts() == before
    assert _t018_nota_final_snapshot() == notas_finais
    assert AvaliacaoCompetencia.objects.count() == 0
    assert Feedback.objects.count() == 0
    assert Competencia.objects.filter(solides_id='99001').count() == extras_antes
    assert Avaliacao.objects.filter(solides_id='1002').exists() is False


# --- T022: idempotência consolidada (SC-005 / C7) ---


def _t022_avaliacao_ciclo_usuario_keys() -> set[tuple[int, int]]:
    """Delta ``Avaliacao`` por ``(ciclo, usuario)`` — SC-005 / T022."""
    return set(Avaliacao.objects.values_list('ciclo_id', 'usuario_id'))


def _t022_competencia_pairs() -> set[tuple[int, int]]:
    return set(
        AvaliacaoCompetencia.objects.values_list('avaliacao_id', 'competencia_id')
    )


def _t022_feedback_fingerprint() -> set[tuple]:
    return set(
        Feedback.objects.values_list(
            'pk', 'avaliacao_id', 'autor_id', 'tipo', 'conteudo'
        )
    )


def test_t022_importer_nao_inventa_nem_apaga_avaliacao():
    """T022: importer não cria/apaga ``Avaliacao``; update só ``nota_*``."""
    importer = (
        _REPO_ROOT / 'apps/reviews/services/legacy_import/importer.py'
    ).read_text(encoding='utf-8')
    assert 'Avaliacao.objects.create' not in importer
    assert 'get_or_create' not in importer
    assert '.delete()' not in importer
    assert '_NOTA_UPDATE_FIELDS' in importer
    assert "('nota_autoavaliacao', 'nota_lider', 'updated_at')" in importer
    assert 'delta Avaliacao por (ciclo, usuario)' in importer


@pytest.mark.django_db
def test_t022_segunda_run_samples_delta_zero_sc005():
    """C7 / SC-005: 2ª run idêntica → delta linhas/feedback/Avaliacao = 0."""
    _t018_seed_world()
    first = _t018_import_samples()
    assert first.notas_criadas == _T018_NOTAS_CRIADAS
    assert first.comentarios_criados == _T018_COMENTARIOS_CRIADOS

    pairs = _t022_competencia_pairs()
    snaps = _t019_snapshot_linhas()
    feedbacks = _t022_feedback_fingerprint()
    av_keys = _t022_avaliacao_ciclo_usuario_keys()
    av_count = Avaliacao.objects.count()
    av_ids = set(Avaliacao.objects.values_list('pk', 'solides_id'))
    linha_count = AvaliacaoCompetencia.objects.count()
    fb_count = Feedback.objects.count()
    extra_pk = Competencia.objects.get(solides_id='99001').pk

    second = _t018_import_samples()

    assert second.notas_criadas == 0
    assert second.notas_atualizadas == 0
    assert second.notas_inalteradas == _T018_NOTAS_CRIADAS
    assert second.comentarios_criados == 0
    assert second.comentarios_inalterados == _T018_COMENTARIOS_CRIADOS
    assert second.habilidades_extras_criadas == 0
    assert _t022_competencia_pairs() == pairs
    assert _t019_snapshot_linhas() == snaps
    assert _t022_feedback_fingerprint() == feedbacks
    assert _t022_avaliacao_ciclo_usuario_keys() == av_keys
    assert Avaliacao.objects.count() == av_count
    assert set(Avaliacao.objects.values_list('pk', 'solides_id')) == av_ids
    assert AvaliacaoCompetencia.objects.count() == linha_count
    assert Feedback.objects.count() == fb_count
    assert Avaliacao.objects.filter(solides_id='1002').exists() is False
    assert Competencia.objects.get(solides_id='99001').pk == extra_pk
    tipos = [entry.label for entry in second.conflitos]
    assert 'snapshot_divergente' not in tipos


@pytest.mark.django_db
def test_t022_update_so_nota_snapshots_bit_a_bit(colaborador, tmp_path):
    """T022: 2ª run com Nota diferente atualiza só ``nota_*``; snapshots estáveis."""
    competencia = _t009_catalogo()
    avaliacao = _t009_avaliacao(colaborador)
    nome = colaborador.nome
    header = [
        _header_row(
            '1001',
            nome_avaliado=nome,
            nome_avaliador=nome,
        )
    ]
    notas_v1, comentarios_path, avaliacoes = _t009_paths(
        tmp_path,
        notas_rows=[
            _nota_row(
                ident='n1',
                avaliacao_id='1001',
                avaliador=nome,
                avaliado=nome,
                fator=1,
                nota=3,
            )
        ],
        header_rows=header,
    )
    before_av = Avaliacao.objects.count()
    av_keys = _t022_avaliacao_ciclo_usuario_keys()

    import_notas_comentarios(notas_v1, comentarios_path, avaliacoes)
    linha = AvaliacaoCompetencia.objects.get(
        avaliacao=avaliacao, competencia=competencia
    )
    peso = linha.peso_utilizado
    nivel = linha.nivel_esperado_utilizado
    pk = linha.pk
    assert linha.nota_autoavaliacao == Decimal('3.00')

    notas_v2 = _write_xlsx(
        tmp_path / 'notas_v2.xlsx',
        _NOTAS_HEADERS,
        [
            _nota_row(
                ident='n1',
                avaliacao_id='1001',
                avaliador=nome,
                avaliado=nome,
                fator=1,
                nota=4,
            )
        ],
    )
    saves: list[dict] = []
    orig_save = AvaliacaoCompetencia.save

    def _spy_save(self, *args, **kwargs):
        saves.append(dict(kwargs))
        return orig_save(self, *args, **kwargs)

    with (
        patch.object(AvaliacaoCompetencia, 'save', _spy_save),
        patch.object(AvaliacaoCompetencia, 'delete') as ac_del,
        patch.object(Avaliacao, 'delete') as av_del,
    ):
        report = import_notas_comentarios(notas_v2, comentarios_path, avaliacoes)

    ac_del.assert_not_called()
    av_del.assert_not_called()
    assert report.notas_criadas == 0
    assert report.notas_atualizadas == 1
    assert report.notas_inalteradas == 0
    linha.refresh_from_db()
    assert linha.pk == pk
    assert linha.nota_autoavaliacao == Decimal('4.00')
    assert linha.peso_utilizado == peso
    assert linha.nivel_esperado_utilizado == nivel
    assert Avaliacao.objects.count() == before_av
    assert _t022_avaliacao_ciclo_usuario_keys() == av_keys
    assert AvaliacaoCompetencia.objects.count() == 1
    assert saves
    for kwargs in saves:
        fields = kwargs.get('update_fields')
        assert fields is not None
        assert 'peso_utilizado' not in fields
        assert 'nivel_esperado_utilizado' not in fields
        assert 'nota_autoavaliacao' in fields


@pytest.mark.django_db
def test_t022_snapshot_divergente_nao_apaga_linha_nem_avaliacao(
    colaborador, tmp_path
):
    """T022: Fator diverge → ``snapshot_divergente``; linha e Avaliacao ficam."""
    competencia = _t009_catalogo()
    avaliacao = _t009_avaliacao(colaborador)
    nome = colaborador.nome
    header = [
        _header_row(
            '1001',
            nome_avaliado=nome,
            nome_avaliador=nome,
        )
    ]
    notas_v1, comentarios, avaliacoes = _t009_paths(
        tmp_path,
        notas_rows=[
            _nota_row(
                ident='n1',
                avaliacao_id='1001',
                avaliador=nome,
                avaliado=nome,
                fator=1,
                nota=4,
            )
        ],
        header_rows=header,
    )
    import_notas_comentarios(notas_v1, comentarios, avaliacoes)
    linha = AvaliacaoCompetencia.objects.get(
        avaliacao=avaliacao, competencia=competencia
    )
    pk = linha.pk
    peso = linha.peso_utilizado
    nivel = linha.nivel_esperado_utilizado
    av_pk = avaliacao.pk
    av_keys = _t022_avaliacao_ciclo_usuario_keys()

    notas_v2 = _write_xlsx(
        tmp_path / 'notas_fator_diverge.xlsx',
        _NOTAS_HEADERS,
        [
            _nota_row(
                ident='n1',
                avaliacao_id='1001',
                avaliador=nome,
                avaliado=nome,
                fator=2,
                nota=4,
            )
        ],
    )
    with (
        patch.object(AvaliacaoCompetencia, 'delete') as ac_del,
        patch.object(Avaliacao, 'delete') as av_del,
    ):
        report = import_notas_comentarios(notas_v2, comentarios, avaliacoes)

    ac_del.assert_not_called()
    av_del.assert_not_called()
    tipos = [entry.label for entry in report.conflitos]
    assert 'snapshot_divergente' in tipos
    assert report.notas_criadas == 0
    assert AvaliacaoCompetencia.objects.filter(pk=pk).exists() is True
    linha.refresh_from_db()
    assert linha.peso_utilizado == peso == Decimal('1.00')
    assert linha.nivel_esperado_utilizado == nivel
    assert linha.nota_autoavaliacao == Decimal('4.00')
    assert Avaliacao.objects.filter(pk=av_pk).exists() is True
    assert Avaliacao.objects.count() == 1
    assert _t022_avaliacao_ciclo_usuario_keys() == av_keys
    avaliacao.refresh_from_db()
    assert avaliacao.etapa == Avaliacao.Etapa.FEEDBACK
    assert avaliacao.concluida is True


@pytest.mark.django_db
def test_t022_feedback_chave_natural_nao_reescreve_conteudo(
    colaborador, lider, tmp_path
):
    """T022: match da chave natural não duplica nem reescreve ``conteudo``."""
    _t013_solides_ids(colaborador, lider)
    avaliacao = _t009_avaliacao(colaborador)
    criado = datetime(2024, 6, 3, 14, 30, 0)
    original = 'Desempenho consistente no trimestre.'
    notas, comentarios, avaliacoes = _t009_paths(
        tmp_path,
        notas_rows=[],
        header_rows=[
            _header_row(
                '1001',
                nome_avaliado=colaborador.nome,
                nome_avaliador=colaborador.nome,
            )
        ],
        comentarios_rows=[
            _comentario_row(
                avaliacao_id='1001',
                avaliador_id='201',
                avaliador=lider.nome,
                avaliado=colaborador.nome,
                comentario=original,
                criado_em=criado,
            )
        ],
    )
    av_keys = _t022_avaliacao_ciclo_usuario_keys()
    first = import_notas_comentarios(notas, comentarios, avaliacoes)
    assert first.comentarios_criados == 1
    fb = Feedback.objects.get(avaliacao=avaliacao)
    fb_pk = fb.pk
    grafia = '  Desempenho   consistente no trimestre.  '
    Feedback.objects.filter(pk=fb_pk).update(conteudo=grafia)
    fb.refresh_from_db()
    assert fb.conteudo == grafia

    saves: list = []
    orig_save = Feedback.save

    def _spy_save(self, *args, **kwargs):
        saves.append(self.pk)
        return orig_save(self, *args, **kwargs)

    with patch.object(Feedback, 'save', _spy_save):
        second = import_notas_comentarios(notas, comentarios, avaliacoes)

    assert second.comentarios_criados == 0
    assert second.comentarios_inalterados == 1
    assert Feedback.objects.count() == 1
    assert set(Feedback.objects.values_list('pk', flat=True)) == {fb_pk}
    fb.refresh_from_db()
    assert fb.conteudo == grafia
    assert fb.conteudo != original
    assert saves == []
    assert _t022_avaliacao_ciclo_usuario_keys() == av_keys
    assert Avaliacao.objects.count() == 1


