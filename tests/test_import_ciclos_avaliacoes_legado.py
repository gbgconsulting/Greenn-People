"""T021–T026: importação ciclos/avaliações legado Sólides — fixtures samples.

T021: dry-run (zero writes em Ciclo/Avaliacao / SC-005) e status sempre
``encerrado`` (SC-007 parcial). Usa **somente**
``data/legado-solides/samples/`` (**proibido** ``raw/``). Denylist intacta.

T022: agregação multi-avaliador (1 Avaliacao, canônico auto/`min_id`,
``ids_colapsados``), órfãos usuário/ciclo e ``etapa=feedback`` /
``concluida=True`` sem ``nota_final_*`` (aggregation-contract).

T023: idempotência (2ª execução delta Ciclo/Avaliacao = 0 / SC-006),
arquivo inválido/args faltando (exit 1, DB inalterado) e assert nenhum
path ``raw/`` na suíte.

T024: migration reversível ``Ciclo.solides_id`` (forward/backward preserva
seed; unique non-null → IntegrityError) — ``contracts/migration-safety.md`` §4.

T025: consolidar dry-run pós-persist (inalterados, zero writes), colunas
ausentes / schema pré-requisito (exit 1) e rollback atômico em
``LegacyPersistError`` (R12 / contrato §Códigos de saída).

T026: consolidar idempotência R11 — update campos permitidos (Ciclo /
Avaliacao) e conflitos ``solides_id_divergente`` /
``solides_id_avaliacao_em_uso`` sem sobrescrita silenciosa.
"""

from __future__ import annotations

from datetime import date, timedelta
from io import StringIO
from pathlib import Path
from unittest.mock import patch

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connection, transaction
from django.db.utils import IntegrityError
from django.utils import timezone
from openpyxl import Workbook

from apps.accounts.models import CustomUser
from apps.cycles.models import Ciclo
from apps.cycles.services.legacy_import import (
    LegacyParseError,
    LegacyPersistError,
    LegacySchemaError,
    import_ciclos_avaliacoes,
)
from apps.reviews.models import Avaliacao
from tests.conftest import DEFAULT_PASSWORD

REPO_ROOT = Path(__file__).resolve().parents[1]
SAMPLES_DIR = REPO_ROOT / 'data' / 'legado-solides' / 'samples'
SOLICITACOES_MIN = SAMPLES_DIR / 'solicitacoes_min.xlsx'
AVALIACOES_HEADERS_MIN = SAMPLES_DIR / 'avaliacoes_headers_min.xlsx'

_RAW_PII_DIR = '/'.join(('data', 'legado-solides', 'raw'))

# Ciclo.solides_id — contracts/migration-safety.md §1/§2/§4.
_CICLO_SOLIDES_MIGRATION = '0002_add_solides_id'
_CICLO_PREVIOUS_MIGRATION = '0001_ciclo'
_CICLO_TABLE = 'cycles_ciclo'

# Fixture solicitacoes_min: 6 linhas; ID 60 sem datas → conflito.
_CICLOS_OK = 5
_CICLOS_CONFLITO = 1
_SOLIDES_CICLOS = ('10', '20', '30', '40', '50')

# Com seed 100–103: 4 Avaliacao; 1 órfão usuário (99999); 1 órfão ciclo (999).
_AVALIACOES_OK = 4
_ORFAOS_USUARIO = 1
_ORFAOS_CICLO = 1
_GRUPOS_COM_COLAPSADOS = 2  # Ana (auto→1001) e Bruno (min_id→2001)

_EMAIL_GESTOR = 'gestor.alpha@example.com'
_EMAIL_ANA = 'ana.silva@example.com'
_EMAIL_BRUNO = 'bruno.costa@example.com'
_EMAIL_CARLA = 'carla.dias@example.com'

_SEED_USERS = (
    (_EMAIL_GESTOR, 'Gestor Alpha', '100'),
    (_EMAIL_ANA, 'Ana Silva', '101'),
    (_EMAIL_BRUNO, 'Bruno Costa', '102'),
    (_EMAIL_CARLA, 'Carla Dias', '103'),
)


def _db_counts() -> tuple[int, int]:
    """Snapshot Ciclo / Avaliacao — dry-run e delta de idempotência."""
    return Ciclo.objects.count(), Avaliacao.objects.count()


def _ciclo_solides_ids() -> set[str]:
    return set(
        Ciclo.objects.exclude(solides_id__isnull=True)
        .exclude(solides_id='')
        .values_list('solides_id', flat=True)
    )


def _avaliacao_solides_ids() -> set[str]:
    return set(
        Avaliacao.objects.exclude(solides_id__isnull=True)
        .exclude(solides_id='')
        .values_list('solides_id', flat=True)
    )


def _seed_avaliados() -> dict[str, CustomUser]:
    """Usuários com ``solides_id`` alinhados ao sample (100–103)."""
    users: dict[str, CustomUser] = {}
    for email, nome, solides_id in _SEED_USERS:
        user = CustomUser.objects.create_user(
            email=email,
            password=DEFAULT_PASSWORD,
            nome=nome,
            solides_id=solides_id,
            email_confirmado_em=timezone.now(),
        )
        users[solides_id] = user
    return users


def _seed_ciclo_aberto_manual() -> Ciclo:
    """Ciclo aberto vigente (sem solides_id) — deve permanecer intacto."""
    today = date.today()
    return Ciclo.objects.create(
        nome='Ciclo Aberto Vigente Seed',
        data_inicio=today - timedelta(days=10),
        data_fim=today + timedelta(days=20),
        status=Ciclo.Status.ABERTO,
    )


def _import_samples(**kwargs):
    """Carga das fixtures samples (T021+)."""
    return import_ciclos_avaliacoes(
        SOLICITACOES_MIN,
        AVALIACOES_HEADERS_MIN,
        **kwargs,
    )


def _assert_samples_only_paths() -> None:
    for path in (SOLICITACOES_MIN, AVALIACOES_HEADERS_MIN, SAMPLES_DIR):
        assert path.exists()
        assert 'raw' not in path.parts
        assert _RAW_PII_DIR not in str(path)


def _table_columns(table: str) -> set[str]:
    """Colunas reais do schema (introspection; SQLite e PostgreSQL)."""
    with connection.cursor() as cursor:
        description = connection.introspection.get_table_description(
            cursor,
            table,
        )
    return {col.name for col in description}


def _migrate_cycles_to(name: str) -> None:
    call_command('migrate', 'cycles', name, verbosity=0, interactive=False)
    connection.close()
    connection.connect()


# --- T021: dry-run + status sempre encerrado (samples-only) ---


def test_suite_nao_referencia_raw_pii():
    """SC-007 / OPSEC: a suíte pytest não aponta para backups PII ``raw/``."""
    _assert_samples_only_paths()
    tests_dir = Path(__file__).parent
    for rel in sorted(tests_dir.glob('test_*.py')):
        text = rel.read_text(encoding='utf-8')
        assert _RAW_PII_DIR not in text, rel.name



@pytest.mark.django_db
def test_dry_run_zero_writes_totais_projetados():
    """SC-005 / C2: ``dry_run`` projeta totais e não persiste Ciclo/Avaliacao."""
    _seed_avaliados()
    before = _db_counts()
    solides_before = _ciclo_solides_ids()
    aval_before = _avaliacao_solides_ids()

    report = _import_samples(dry_run=True)

    assert report.modo == 'dry-run'
    assert report.ciclos_criados == _CICLOS_OK
    assert report.ciclos_atualizados == 0
    assert report.ciclos_inalterados == 0
    assert report.ciclos_conflitos == _CICLOS_CONFLITO
    assert report.avaliacoes_criadas == _AVALIACOES_OK
    assert report.avaliacoes_atualizadas == 0
    assert report.grupos_agregados == _AVALIACOES_OK
    assert report.n_orfaos_usuario == _ORFAOS_USUARIO
    assert report.n_orfaos_ciclo == _ORFAOS_CICLO

    assert _db_counts() == before
    assert _ciclo_solides_ids() == solides_before
    assert _avaliacao_solides_ids() == aval_before
    assert Ciclo.objects.filter(solides_id__in=_SOLIDES_CICLOS).count() == 0
    assert Avaliacao.objects.count() == 0


@pytest.mark.django_db
def test_dry_run_via_comando_zero_writes():
    """C2: ``manage.py importar_ciclos_avaliacoes --dry-run`` → exit 0, zero writes."""
    _seed_avaliados()
    before = _db_counts()
    stdout = StringIO()

    result = call_command(
        'importar_ciclos_avaliacoes',
        solicitacoes=str(SOLICITACOES_MIN),
        avaliacoes=str(AVALIACOES_HEADERS_MIN),
        dry_run=True,
        stdout=stdout,
    )

    text = stdout.getvalue()
    assert result in (0, None)
    assert 'modo: dry-run' in text
    assert f'ciclos_criados: {_CICLOS_OK}' in text
    assert f'avaliacoes_criadas: {_AVALIACOES_OK}' in text
    assert _db_counts() == before
    assert 'raw' not in SOLICITACOES_MIN.parts


@pytest.mark.django_db
def test_persist_status_sempre_encerrado_e_ciclo_aberto_intacto():
    """SC-002 / SC-007: finished/draft/active/canceled → ``encerrado``; aberto intacto."""
    _seed_avaliados()
    aberto = _seed_ciclo_aberto_manual()
    aberto_pk = aberto.pk

    report = _import_samples()

    assert report.modo == 'persist'
    assert report.ciclos_criados == _CICLOS_OK
    assert report.ciclos_conflitos == _CICLOS_CONFLITO

    importados = Ciclo.objects.filter(solides_id__in=_SOLIDES_CICLOS)
    assert importados.count() == _CICLOS_OK
    assert set(importados.values_list('status', flat=True)) == {
        Ciclo.Status.ENCERRADO,
    }
    assert Ciclo.objects.filter(
        solides_id__isnull=False,
        status=Ciclo.Status.ABERTO,
    ).count() == 0

    aberto.refresh_from_db()
    assert aberto.pk == aberto_pk
    assert aberto.status == Ciclo.Status.ABERTO
    assert aberto.solides_id is None
    assert aberto.nome == 'Ciclo Aberto Vigente Seed'

    serial = Ciclo.objects.get(solides_id='50')
    assert serial.nome == '2026-04-01'
    assert serial.status == Ciclo.Status.ENCERRADO


# --- T022: agregação, órfãos, feedback sem notas ---


@pytest.mark.django_db
def test_agregacao_multi_avaliador_canonico_e_ids_colapsados():
    """Aggregation-contract: N→1; auto→1001; sem auto→min_id 2001; ids_colapsados."""
    users = _seed_avaliados()
    report = _import_samples()

    assert report.avaliacoes_criadas == _AVALIACOES_OK
    assert report.grupos_agregados == _AVALIACOES_OK
    assert len(report.ids_colapsados) == _GRUPOS_COM_COLAPSADOS

    ciclo10 = Ciclo.objects.get(solides_id='10')
    ana = Avaliacao.objects.get(ciclo=ciclo10, usuario=users['101'])
    assert ana.solides_id == '1001'
    assert Avaliacao.objects.filter(ciclo=ciclo10, usuario=users['101']).count() == 1

    bruno = Avaliacao.objects.get(ciclo=ciclo10, usuario=users['102'])
    assert bruno.solides_id == '2001'
    assert Avaliacao.objects.filter(ciclo=ciclo10, usuario=users['102']).count() == 1

    colapsados_por_canonico = {
        entry.extra: entry.motivo for entry in report.ids_colapsados
    }
    assert '1001' in colapsados_por_canonico
    assert '2001' in colapsados_por_canonico
    assert '1002' in colapsados_por_canonico['1001']
    assert '1003' in colapsados_por_canonico['1001']
    assert '2003' in colapsados_por_canonico['2001']
    assert '2005' in colapsados_por_canonico['2001']


@pytest.mark.django_db
def test_orfaos_usuario_e_ciclo_sem_inventar():
    """Órfão usuário (99999) e solicitação órfã (999) no relatório; sem inventar."""
    _seed_avaliados()
    users_before = CustomUser.objects.count()
    report = _import_samples()

    assert report.n_orfaos_usuario == _ORFAOS_USUARIO
    assert report.n_orfaos_ciclo == _ORFAOS_CICLO
    assert any('99999' in (e.label + e.extra) for e in report.orfaos_usuario)
    assert any('999' in (e.label + e.extra) for e in report.orfaos_ciclo)

    assert CustomUser.objects.count() == users_before
    assert CustomUser.objects.filter(solides_id='99999').count() == 0
    assert Ciclo.objects.filter(solides_id='999').count() == 0
    assert Avaliacao.objects.filter(solides_id='4001').count() == 0
    assert Avaliacao.objects.filter(solides_id='5001').count() == 0


@pytest.mark.django_db
def test_avaliacao_feedback_concluida_sem_notas():
    """Cabeçalhos terminais: ``feedback`` + ``concluida``; ``nota_final_*`` null."""
    users = _seed_avaliados()
    report = _import_samples()

    assert report.avaliacoes_criadas == _AVALIACOES_OK
    assert Avaliacao.objects.count() == _AVALIACOES_OK

    for aval in Avaliacao.objects.select_related('ciclo', 'usuario'):
        assert aval.etapa == Avaliacao.Etapa.FEEDBACK
        assert aval.concluida is True
        assert aval.nota_final_lider is None
        assert aval.nota_final_autoavaliacao is None
        assert aval.solides_id in {'1001', '2001', '3001', '6001'}

    ciclo20 = Ciclo.objects.get(solides_id='20')
    gestor = Avaliacao.objects.get(ciclo=ciclo20, usuario=users['100'])
    assert gestor.solides_id == '3001'

    ciclo40 = Ciclo.objects.get(solides_id='40')
    carla = Avaliacao.objects.get(ciclo=ciclo40, usuario=users['103'])
    assert carla.solides_id == '6001'
    assert carla.etapa == Avaliacao.Etapa.FEEDBACK
    assert carla.concluida is True


# --- T023: idempotência, arquivo inválido/args, sem raw/ ---


@pytest.mark.django_db
def test_idempotencia_segunda_execucao_delta_zero():
    """SC-006 / C6: 2ª execução idêntica → delta Ciclo/Avaliacao = 0."""
    _seed_avaliados()
    first = _import_samples()
    assert first.ciclos_criados == _CICLOS_OK
    assert first.avaliacoes_criadas == _AVALIACOES_OK

    counts_after_first = _db_counts()
    ciclo_ids = _ciclo_solides_ids()
    aval_ids = _avaliacao_solides_ids()
    assert len(ciclo_ids) == _CICLOS_OK
    assert len(aval_ids) == _AVALIACOES_OK

    second = _import_samples()
    assert second.ciclos_criados == 0
    assert second.ciclos_atualizados == 0
    assert second.ciclos_inalterados == _CICLOS_OK
    assert second.ciclos_conflitos == _CICLOS_CONFLITO
    assert second.avaliacoes_criadas == 0
    assert second.avaliacoes_atualizadas == 0
    assert second.avaliacoes_inalteradas == _AVALIACOES_OK

    assert _db_counts() == counts_after_first
    assert _ciclo_solides_ids() == ciclo_ids
    assert _avaliacao_solides_ids() == aval_ids
    assert Ciclo.objects.filter(solides_id__in=_SOLIDES_CICLOS).count() == _CICLOS_OK
    assert Avaliacao.objects.count() == _AVALIACOES_OK


@pytest.mark.django_db
def test_arquivo_ausente_exit_1_db_inalterado(tmp_path: Path):
    """Args/arquivo ausente → ``CommandError`` exit 1; DB inalterado."""
    _seed_avaliados()
    _import_samples()
    before = _db_counts()
    ciclo_ids = _ciclo_solides_ids()
    missing = tmp_path / 'solicitacoes_inexistente.xlsx'
    assert not missing.exists()
    assert 'raw' not in missing.parts

    with pytest.raises(CommandError) as exc_info:
        call_command(
            'importar_ciclos_avaliacoes',
            solicitacoes=str(missing),
            avaliacoes=str(AVALIACOES_HEADERS_MIN),
        )
    assert exc_info.value.returncode == 1
    assert 'não encontrado' in str(exc_info.value).lower()
    assert _db_counts() == before
    assert _ciclo_solides_ids() == ciclo_ids

    with pytest.raises(LegacyParseError, match='não encontrado'):
        import_ciclos_avaliacoes(missing, AVALIACOES_HEADERS_MIN)
    assert _db_counts() == before


@pytest.mark.django_db
def test_arquivo_ooxml_corrompido_exit_1_db_inalterado(tmp_path: Path):
    """OOXML ilegível → exit 1; nenhuma escrita parcial."""
    _seed_avaliados()
    _import_samples()
    before = _db_counts()
    corrupted = tmp_path / 'avaliacoes_corrompido.xlsx'
    corrupted.write_bytes(b'this is not a valid ooxml workbook')
    assert 'raw' not in corrupted.parts

    with pytest.raises(CommandError) as exc_info:
        call_command(
            'importar_ciclos_avaliacoes',
            solicitacoes=str(SOLICITACOES_MIN),
            avaliacoes=str(corrupted),
        )
    assert exc_info.value.returncode == 1
    assert 'ilegível' in str(exc_info.value).lower()
    assert _db_counts() == before

    with pytest.raises(LegacyParseError):
        import_ciclos_avaliacoes(SOLICITACOES_MIN, corrupted)
    assert _db_counts() == before
    assert Avaliacao.objects.count() == _AVALIACOES_OK


@pytest.mark.django_db
def test_args_faltando_exit_1_db_inalterado():
    """Args obrigatórios ausentes → ``CommandError`` returncode 1; DB intacto."""
    _seed_avaliados()
    before = _db_counts()

    with pytest.raises(CommandError) as exc_info:
        call_command('importar_ciclos_avaliacoes')
    assert exc_info.value.returncode == 1
    assert _db_counts() == before

    with pytest.raises(CommandError) as exc_sol:
        call_command(
            'importar_ciclos_avaliacoes',
            avaliacoes=str(AVALIACOES_HEADERS_MIN),
        )
    assert exc_sol.value.returncode == 1

    with pytest.raises(CommandError) as exc_aval:
        call_command(
            'importar_ciclos_avaliacoes',
            solicitacoes=str(SOLICITACOES_MIN),
        )
    assert exc_aval.value.returncode == 1
    assert _db_counts() == before
    assert Ciclo.objects.count() == 0
    assert Avaliacao.objects.count() == 0


# --- T024: migration Ciclo.solides_id reversível (migration-safety §4) ---


@pytest.mark.django_db(transaction=True)
def test_ciclo_solides_id_migration_reversible_and_preserves_existing():
    """Forward adds nullable field; reverse removes it; seed data intact."""
    assert 'solides_id' in _table_columns(_CICLO_TABLE)

    seed = Ciclo.objects.create(
        nome='Ciclo Seed T024',
        data_inicio=date(2024, 1, 1),
        data_fim=date(2024, 12, 31),
        status=Ciclo.Status.ENCERRADO,
    )
    assert seed.solides_id is None
    seed_pk = seed.pk
    seed_nome = seed.nome
    seed_status = seed.status
    seed_inicio = seed.data_inicio
    seed_fim = seed.data_fim
    count_before = Ciclo.objects.count()

    seed.solides_id = 't024-dup'
    seed.save(update_fields=['solides_id'])
    other = Ciclo.objects.create(
        nome='Ciclo Dup T024',
        data_inicio=date(2025, 1, 1),
        data_fim=date(2025, 6, 30),
        status=Ciclo.Status.ENCERRADO,
    )
    other.solides_id = 't024-dup'
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            other.save(update_fields=['solides_id'])
    other.refresh_from_db()
    assert other.solides_id is None

    try:
        _migrate_cycles_to(_CICLO_PREVIOUS_MIGRATION)
        assert 'solides_id' not in _table_columns(_CICLO_TABLE)

        with connection.cursor() as cursor:
            cursor.execute(
                'SELECT nome, status, data_inicio, data_fim '
                'FROM cycles_ciclo WHERE id = %s',
                [seed_pk],
            )
            row = cursor.fetchone()
        assert row is not None
        assert row[0] == seed_nome
        assert row[1] == seed_status
        assert row[2] == seed_inicio
        assert row[3] == seed_fim

        with connection.cursor() as cursor:
            cursor.execute('SELECT COUNT(*) FROM cycles_ciclo')
            assert cursor.fetchone()[0] == count_before + 1  # seed + other

        _migrate_cycles_to(_CICLO_SOLIDES_MIGRATION)
        assert 'solides_id' in _table_columns(_CICLO_TABLE)

        seed.refresh_from_db()
        assert seed.nome == seed_nome
        assert seed.status == seed_status
        assert seed.data_inicio == seed_inicio
        assert seed.data_fim == seed_fim
        assert seed.solides_id is None
        assert Ciclo.objects.count() == count_before + 1

        seed.solides_id = 't024-dup'
        seed.save(update_fields=['solides_id'])
        other.refresh_from_db()
        other.solides_id = 't024-dup'
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                other.save(update_fields=['solides_id'])
    finally:
        _migrate_cycles_to(_CICLO_SOLIDES_MIGRATION)


# --- T025: dry-run consolidado, falhas pré-persistência, rollback atomic ---


@pytest.mark.django_db
def test_dry_run_apos_persist_projeta_inalterados_sem_writes():
    """T025 / SC-005: dry-run após persist projeta inalterados e zero writes."""
    _seed_avaliados()
    first = _import_samples()
    assert first.ciclos_criados == _CICLOS_OK
    assert first.avaliacoes_criadas == _AVALIACOES_OK
    before = _db_counts()
    ciclo_ids = _ciclo_solides_ids()
    aval_ids = _avaliacao_solides_ids()

    dry = _import_samples(dry_run=True)

    assert dry.modo == 'dry-run'
    assert dry.ciclos_criados == 0
    assert dry.ciclos_inalterados == _CICLOS_OK
    assert dry.avaliacoes_criadas == 0
    assert dry.avaliacoes_inalteradas == _AVALIACOES_OK
    assert dry.grupos_agregados == _AVALIACOES_OK
    assert _db_counts() == before
    assert _ciclo_solides_ids() == ciclo_ids
    assert _avaliacao_solides_ids() == aval_ids


@pytest.mark.django_db
def test_colunas_ausentes_exit_1_db_inalterado(tmp_path: Path):
    """T025: colunas obrigatórias ausentes → exit 1; DB inalterado."""
    _seed_avaliados()
    _import_samples()
    before = _db_counts()
    ciclo_ids = _ciclo_solides_ids()

    bad = tmp_path / 'solicitacoes_sem_colunas.xlsx'
    wb = Workbook()
    ws = wb.active
    ws.append(['Nome', 'Status'])  # faltam Identificador / datas
    ws.append(['Ciclo incompleto', 'finished'])
    wb.save(bad)
    assert 'raw' not in bad.parts

    with pytest.raises(CommandError) as exc_info:
        call_command(
            'importar_ciclos_avaliacoes',
            solicitacoes=str(bad),
            avaliacoes=str(AVALIACOES_HEADERS_MIN),
        )
    assert exc_info.value.returncode == 1
    assert 'colunas obrigatórias ausentes' in str(exc_info.value).lower()
    assert _db_counts() == before
    assert _ciclo_solides_ids() == ciclo_ids

    with pytest.raises(LegacyParseError, match='Colunas obrigatórias ausentes'):
        import_ciclos_avaliacoes(bad, AVALIACOES_HEADERS_MIN)
    assert _db_counts() == before


@pytest.mark.django_db(transaction=True)
def test_schema_solides_id_ausente_exit_1_zero_writes():
    """T025: migration Ciclo.solides_id ausente → LegacySchemaError; zero writes."""
    _seed_avaliados()
    before = _db_counts()
    assert 'solides_id' in _table_columns(_CICLO_TABLE)

    try:
        _migrate_cycles_to(_CICLO_PREVIOUS_MIGRATION)
        assert 'solides_id' not in _table_columns(_CICLO_TABLE)

        with pytest.raises(LegacySchemaError, match='solides_id'):
            import_ciclos_avaliacoes(SOLICITACOES_MIN, AVALIACOES_HEADERS_MIN)

        with pytest.raises(CommandError) as exc_info:
            call_command(
                'importar_ciclos_avaliacoes',
                solicitacoes=str(SOLICITACOES_MIN),
                avaliacoes=str(AVALIACOES_HEADERS_MIN),
            )
        assert exc_info.value.returncode == 1
        assert 'solides_id' in str(exc_info.value).lower()

        with connection.cursor() as cursor:
            cursor.execute('SELECT COUNT(*) FROM cycles_ciclo')
            assert cursor.fetchone()[0] == before[0]
    finally:
        _migrate_cycles_to(_CICLO_SOLIDES_MIGRATION)

    assert 'solides_id' in _table_columns(_CICLO_TABLE)
    assert _db_counts() == before


@pytest.mark.django_db
def test_persist_exception_rollback_atomico():
    """T025 / R12: exceção na fase 2 → LegacyPersistError + rollback ciclos."""
    _seed_avaliados()
    before = _db_counts()
    assert Ciclo.objects.filter(solides_id__in=_SOLIDES_CICLOS).count() == 0

    with patch(
        'apps.cycles.services.legacy_import.importer._persist_fase_avaliacoes',
        side_effect=RuntimeError('falha simulada fase 2'),
    ):
        with pytest.raises(LegacyPersistError, match='falha simulada'):
            _import_samples()

    assert _db_counts() == before
    assert Ciclo.objects.filter(solides_id__in=_SOLIDES_CICLOS).count() == 0
    assert Avaliacao.objects.count() == 0

    with patch(
        'apps.cycles.services.legacy_import.importer._persist_fase_avaliacoes',
        side_effect=RuntimeError('falha simulada fase 2'),
    ):
        with pytest.raises(CommandError) as exc_info:
            call_command(
                'importar_ciclos_avaliacoes',
                solicitacoes=str(SOLICITACOES_MIN),
                avaliacoes=str(AVALIACOES_HEADERS_MIN),
            )
    assert exc_info.value.returncode == 1
    assert 'falha na persistência' in str(exc_info.value).lower()
    assert _db_counts() == before


# --- T026: update campos permitidos + conflitos sem sobrescrita (R11) ---


@pytest.mark.django_db
def test_idempotencia_atualiza_campos_permitidos_ciclo_e_avaliacao():
    """T026 / R11: reexecução com divergência → atualiza; não duplica; não reabre."""
    users = _seed_avaliados()
    first = _import_samples()
    assert first.ciclos_criados == _CICLOS_OK
    assert first.avaliacoes_criadas == _AVALIACOES_OK

    ciclo = Ciclo.objects.get(solides_id='10')
    original_nome = ciclo.nome
    original_inicio = ciclo.data_inicio
    original_fim = ciclo.data_fim
    ciclo.nome = 'Nome Mutado Temporario'
    ciclo.data_inicio = original_inicio - timedelta(days=7)
    ciclo.data_fim = original_fim + timedelta(days=7)
    ciclo.save(update_fields=['nome', 'data_inicio', 'data_fim'])

    ana = Avaliacao.objects.get(ciclo=ciclo, usuario=users['101'])
    nota_lider_antes = ana.nota_final_lider
    ana.etapa = Avaliacao.Etapa.INPUT_METAS
    ana.concluida = False
    ana.save(update_fields=['etapa', 'concluida'])

    counts_before = _db_counts()
    second = _import_samples()

    assert second.ciclos_criados == 0
    assert second.ciclos_atualizados >= 1
    assert second.avaliacoes_criadas == 0
    assert second.avaliacoes_atualizadas >= 1
    assert _db_counts() == counts_before

    ciclo.refresh_from_db()
    assert ciclo.nome == original_nome
    assert ciclo.data_inicio == original_inicio
    assert ciclo.data_fim == original_fim
    assert ciclo.status == Ciclo.Status.ENCERRADO

    ana.refresh_from_db()
    assert ana.etapa == Avaliacao.Etapa.FEEDBACK
    assert ana.concluida is True
    assert ana.solides_id == '1001'
    assert ana.nota_final_lider == nota_lider_antes
    assert Avaliacao.objects.filter(ciclo=ciclo, usuario=users['101']).count() == 1


@pytest.mark.django_db
def test_conflito_solides_id_divergente_nao_sobrescreve():
    """T026: par com outro ``solides_id`` non-null → conflito; valor intacto."""
    users = _seed_avaliados()
    _import_samples()
    ciclo = Ciclo.objects.get(solides_id='10')
    ana = Avaliacao.objects.get(ciclo=ciclo, usuario=users['101'])
    ana.solides_id = '9999'
    ana.save(update_fields=['solides_id'])
    before_count = Avaliacao.objects.count()

    report = _import_samples()

    ana.refresh_from_db()
    assert ana.solides_id == '9999'
    assert Avaliacao.objects.filter(ciclo=ciclo, usuario=users['101']).count() == 1
    assert Avaliacao.objects.count() == before_count
    assert report.avaliacoes_criadas == 0
    assert any(
        e.label == 'solides_id_divergente' for e in report.conflitos
    )


@pytest.mark.django_db
def test_conflito_solides_id_avaliacao_em_uso_nao_sobrescreve():
    """T026: canônico já em outra Avaliacao → conflito; nenhum overwrite."""
    users = _seed_avaliados()
    _import_samples()
    ciclo10 = Ciclo.objects.get(solides_id='10')
    ciclo40 = Ciclo.objects.get(solides_id='40')
    ana = Avaliacao.objects.get(ciclo=ciclo10, usuario=users['101'])
    carla = Avaliacao.objects.get(ciclo=ciclo40, usuario=users['103'])

    ana.solides_id = None
    ana.save(update_fields=['solides_id'])
    carla.solides_id = '1001'
    carla.save(update_fields=['solides_id'])
    before_count = Avaliacao.objects.count()
    carla_pk = carla.pk

    report = _import_samples()

    ana.refresh_from_db()
    carla.refresh_from_db()
    assert ana.solides_id in (None, '')
    assert carla.solides_id == '1001'
    assert carla.pk == carla_pk
    assert Avaliacao.objects.count() == before_count
    assert Avaliacao.objects.filter(solides_id='1001').count() == 1
    assert report.avaliacoes_criadas == 0
    assert any(
        e.label == 'solides_id_avaliacao_em_uso' for e in report.conflitos
    )
    # Conflito não conta grupo/handoff (T026 consolidação no importer).
    assert all(
        entry.extra != '1001' for entry in report.ids_colapsados
    )
