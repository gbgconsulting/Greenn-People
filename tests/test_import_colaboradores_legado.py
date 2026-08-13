"""T030+: importação de colaboradores legado Sólides — fixtures samples.

T030: dry-run (zero writes / SC-006) e idempotência (2ª execução, delta
duplicatas e-mail = 0 / SC-007). Usa **somente**
``data/legado-solides/samples/`` (SC-008; **proibido** ``raw/``).
Denylist de domínio intacta.

T031: demitidos inativos (serial Excel + ISO), ordem preferência e-mail,
Area/Cargo resolve e crosswalk parcial/ambíguo.
T032: hierarquia (``line_manager`` resolvível), ciclo reportado (vínculo
não aplicado) e arquivo inválido (exit 1, DB inalterado).
T033: migration ``solides_id`` reversível (seed preservado) e diff
denylist vazio pós-import.
T034: C5 PII/OPSEC (relatório sem CPF, model sem PII, CI sem ``raw/``)
e C6 senha unusable (login bloqueado até reset).
"""

from __future__ import annotations

import subprocess
from datetime import date
from io import StringIO
from pathlib import Path

import pytest
from django.contrib.auth import authenticate
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import IntegrityError, connection, transaction
from django.test import Client
from django.urls import reverse

from apps.accounts.models import CustomUser
from apps.accounts.services.legacy_import import (
    LegacyParseError,
    import_colaboradores,
)
from apps.accounts.services.legacy_import.dates import (
    is_active_from_dismissal,
    parse_legacy_date,
)
from apps.accounts.services.legacy_import.hierarchy import apply_hierarchy
from apps.accounts.services.legacy_import.parse_xlsx import ColaboradorRow
from apps.accounts.services.legacy_import.report import ImportReport
from apps.accounts.services.legacy_import.resolve import resolve_email
from apps.competencies.models import Competencia, Escala
from apps.cycles.models import Ciclo
from apps.organization.models import Area, Cargo
from apps.pdi.models import PDI
from apps.reviews.models import Avaliacao
from tests.conftest import DEFAULT_PASSWORD

REPO_ROOT = Path(__file__).resolve().parents[1]
SAMPLES_DIR = REPO_ROOT / 'data' / 'legado-solides' / 'samples'
COLABORADORES_MIN = SAMPLES_DIR / 'colaboradores_min.xlsx'
AVALIACOES_MIN = SAMPLES_DIR / 'avaliacoes_crosswalk_min.xlsx'

# 8 linhas na fixture; Elena Sem Email → nao_importavel (sem e-mail).
_IMPORTAVEIS = 7
_NAO_IMPORTAVEIS = 1
_AREAS_FIXTURE = 3  # Engenharia / Produto / RH Fixture
_CARGOS_FIXTURE = 4  # Elena (Estagiario) não entra no resolve
_DEMITIDOS = 2  # Carla (serial 45446) + Diego (ISO 2024-06-01)
_SOLIDES_UNICOS = 5  # Fernanda sem match; Nome Ambiguo ambíguo
_GESTORES_VINCULADOS = 3  # Ana, Bruno, Diego → Gestor Alpha (100)
_SEM_GESTOR = 4  # Gestor Alpha, Carla, Fernanda, Nome Ambiguo

_EMAIL_GESTOR = 'gestor.alpha@example.com'
_EMAIL_ANA = 'ana.silva@example.com'
_EMAIL_BRUNO = 'bruno.costa@example.com'
_EMAIL_CARLA = 'carla.dias@example.com'
_EMAIL_DIEGO = 'diego.alves@example.com'
_EMAIL_FERNANDA = 'fernanda.lima@example.com'
_EMAIL_AMBIGUO = 'nome.ambiguo@example.com'

_AREAS_ESPERADAS = frozenset(
    {'Engenharia Fixture', 'Produto Fixture', 'RH Fixture'}
)
_CARGOS_ESPERADOS = {
    'Tech Lead Fixture': '9004',
    'Desenvolvedor Fixture': '9001',
    'Analista Fixture': '9002',
    'People Partner Fixture': '9003',
}
_USER_AREA_CARGO = {
    _EMAIL_GESTOR: ('Engenharia Fixture', 'Tech Lead Fixture'),
    _EMAIL_ANA: ('Engenharia Fixture', 'Desenvolvedor Fixture'),
    _EMAIL_BRUNO: ('Produto Fixture', 'Analista Fixture'),
    _EMAIL_CARLA: ('Engenharia Fixture', 'Desenvolvedor Fixture'),
    _EMAIL_DIEGO: ('Produto Fixture', 'Analista Fixture'),
    _EMAIL_FERNANDA: ('RH Fixture', 'People Partner Fixture'),
    _EMAIL_AMBIGUO: ('Produto Fixture', 'Analista Fixture'),
}
_SOLIDES_POR_EMAIL = {
    _EMAIL_GESTOR: '100',
    _EMAIL_ANA: '101',
    _EMAIL_BRUNO: '102',
    _EMAIL_CARLA: '103',
    _EMAIL_DIEGO: '104',
    _EMAIL_FERNANDA: None,
    _EMAIL_AMBIGUO: None,
}
_LINE_MANAGER_POR_EMAIL = {
    _EMAIL_GESTOR: None,
    _EMAIL_ANA: _EMAIL_GESTOR,
    _EMAIL_BRUNO: _EMAIL_GESTOR,
    _EMAIL_CARLA: None,
    _EMAIL_DIEGO: _EMAIL_GESTOR,
    _EMAIL_FERNANDA: None,
    _EMAIL_AMBIGUO: None,
}

# (app, migration solides_id, previous) — contracts/migration-safety.md §1/§2.
_SOLIDES_ID_MIGRATIONS = (
    ('accounts', '0002_add_solides_id', '0001_initial'),
    ('organization', '0004_add_solides_id', '0003_area_cargo_unique_nome_ativo'),
    ('competencies', '0003_add_solides_id', '0002_escala_competencia_is_active_unique'),
    ('reviews', '0007_add_solides_id', '0006_alter_etapa_input_metas_label'),
    ('pdi', '0002_add_solides_id', '0001_pdi_acaopdi'),
)
_SOLIDES_ID_TABLES = (
    'accounts_customuser',
    'organization_cargo',
    'competencies_competencia',
    'reviews_avaliacao',
    'pdi_pdi',
)
_DENYLIST_PATHS = (
    'apps/cycles/services/stage.py',
    'apps/cycles/services/cycle.py',
    'apps/goals/services/approval.py',
    'apps/accounts/services/scope.py',
    'apps/reviews/services/evaluation.py',
    'apps/dashboard/services/adherence.py',
)
# Base efetiva da feature (merge 009) — T024; ``git diff main`` é ruidoso.
_FEATURE_BASE = '2967bf9'

_EMAILS_IMPORTAVEIS = (
    _EMAIL_GESTOR,
    _EMAIL_ANA,
    _EMAIL_BRUNO,
    _EMAIL_CARLA,
    _EMAIL_DIEGO,
    _EMAIL_FERNANDA,
    _EMAIL_AMBIGUO,
)
_PII_FIELD_NAMES = frozenset(
    {'cpf', 'rg', 'ctps', 'pis', 'endereco', 'telefone', 'banco'},
)
_CPF_SENTINELA = '000.000.000-00'
_RAW_PII_DIR = '/'.join(('data', 'legado-solides', 'raw'))
_BACKUP_COLABORADORES = '_'.join(('backup', 'colaboradores', '20260624'))
_BACKUP_AVALIACOES = '_'.join(('backup', 'avaliacoes', '20260624'))


def _db_counts() -> tuple[int, int, int]:
    """Snapshot User / Area / Cargo — dry-run e delta de duplicatas."""
    return (
        CustomUser.objects.count(),
        Area.objects.count(),
        Cargo.objects.count(),
    )


def _user_emails() -> set[str]:
    return set(CustomUser.objects.values_list('email', flat=True))


def _import_samples(**kwargs):
    """Carga persist das fixtures samples (T031+)."""
    return import_colaboradores(
        COLABORADORES_MIN,
        avaliacoes_path=AVALIACOES_MIN,
        **kwargs,
    )


def _table_columns(table: str) -> set[str]:
    """Colunas reais do schema (introspection; SQLite e PostgreSQL)."""
    with connection.cursor() as cursor:
        description = connection.introspection.get_table_description(
            cursor,
            table,
        )
    return {col.name for col in description}


def _migrate_to(app: str, name: str) -> None:
    call_command('migrate', app, name, verbosity=0, interactive=False)
    connection.close()
    connection.connect()


def _forward_solides_id() -> None:
    for app, current, _previous in _SOLIDES_ID_MIGRATIONS:
        _migrate_to(app, current)


def _backward_solides_id() -> None:
    for app, _current, previous in reversed(_SOLIDES_ID_MIGRATIONS):
        _migrate_to(app, previous)


def _git_diff(*args: str) -> str:
    result = subprocess.run(
        ['git', 'diff', *args],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout


def _git_commit_exists(rev: str) -> bool:
    result = subprocess.run(
        ['git', 'cat-file', '-t', rev],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    return result.returncode == 0 and result.stdout.strip() == 'commit'


def _denylist_payloads() -> dict[str, bytes]:
    return {rel: (REPO_ROOT / rel).read_bytes() for rel in _DENYLIST_PATHS}


def _colaborador_row(**overrides) -> ColaboradorRow:
    """Linha mínima para testes de ``resolve_email`` (sem persistência)."""
    fields = {
        'linha': 2,
        'nome': 'Fulano Fixture',
        'email_empresarial': '',
        'email': '',
        'email_pessoal': '',
        'data_demissao': None,
        'cargo': '',
        'cargo_id': '',
        'departamento': '',
        'superior_direto_id': '',
    }
    fields.update(overrides)
    return ColaboradorRow(**fields)


# --- T030: Dry-run (zero writes) + idempotência (SC-006 / SC-007 / SC-008) ---


def test_suite_usa_somente_samples():
    """SC-008: fixtures da suíte resolvem em ``samples/``, nunca em backups PII."""
    assert COLABORADORES_MIN.is_file()
    assert AVALIACOES_MIN.is_file()
    assert SAMPLES_DIR.name == 'samples'
    assert SAMPLES_DIR.parent.name == 'legado-solides'
    for path in (COLABORADORES_MIN, AVALIACOES_MIN, SAMPLES_DIR):
        assert 'raw' not in path.parts


@pytest.mark.django_db
def test_dry_run_zero_writes_totais_projetados():
    """SC-006 / C2 / C4: ``dry_run`` projeta totais e não persiste nada."""
    before = _db_counts()
    emails_before = _user_emails()

    report = import_colaboradores(
        COLABORADORES_MIN,
        avaliacoes_path=AVALIACOES_MIN,
        dry_run=True,
    )

    assert report.modo == 'dry-run'
    assert report.usuarios_criados == _IMPORTAVEIS
    assert report.usuarios_atualizados == 0
    assert report.usuarios_inalterados == 0
    assert report.n_nao_importaveis == _NAO_IMPORTAVEIS
    assert report.areas_criadas == _AREAS_FIXTURE
    assert report.cargos_criados == _CARGOS_FIXTURE

    assert _db_counts() == before
    assert _user_emails() == emails_before
    assert CustomUser.objects.count() == 0
    assert Area.objects.count() == 0
    assert Cargo.objects.count() == 0


@pytest.mark.django_db
def test_dry_run_via_comando_zero_writes():
    """C2 / C4: ``manage.py importar_colaboradores --dry-run`` → exit 0, zero writes."""
    before = _db_counts()
    stdout = StringIO()

    result = call_command(
        'importar_colaboradores',
        colaboradores=str(COLABORADORES_MIN),
        avaliacoes=str(AVALIACOES_MIN),
        dry_run=True,
        stdout=stdout,
    )

    text = stdout.getvalue()
    assert result in (0, None)
    assert 'modo: dry-run' in text
    assert 'usuarios_criados: 7' in text
    assert _db_counts() == before


@pytest.mark.django_db
def test_import_segunda_execucao_sem_duplicatas():
    """SC-007 / C4: 2ª execução idêntica → delta de e-mails duplicados = 0."""
    first = import_colaboradores(
        COLABORADORES_MIN,
        avaliacoes_path=AVALIACOES_MIN,
    )
    assert first.modo == 'persist'
    assert first.usuarios_criados == _IMPORTAVEIS
    assert first.usuarios_atualizados == 0
    assert first.usuarios_inalterados == 0
    assert first.n_nao_importaveis == _NAO_IMPORTAVEIS

    emails_after_first = _user_emails()
    counts_after_first = _db_counts()
    assert len(emails_after_first) == _IMPORTAVEIS
    assert CustomUser.objects.count() == _IMPORTAVEIS

    second = import_colaboradores(
        COLABORADORES_MIN,
        avaliacoes_path=AVALIACOES_MIN,
    )

    assert second.usuarios_criados == 0
    assert second.usuarios_atualizados == 0
    assert second.usuarios_inalterados == _IMPORTAVEIS
    assert second.areas_criadas == 0
    assert second.cargos_criados == 0

    assert _user_emails() == emails_after_first
    assert _db_counts() == counts_after_first
    assert CustomUser.objects.count() == _IMPORTAVEIS
    assert len(_user_emails()) == _IMPORTAVEIS


@pytest.mark.django_db
def test_dry_run_apos_persist_projeta_inalterados_sem_writes():
    """SC-006 + SC-007: dry-run após carga real projeta inalterados e não grava."""
    import_colaboradores(
        COLABORADORES_MIN,
        avaliacoes_path=AVALIACOES_MIN,
    )
    before = _db_counts()
    emails_before = _user_emails()

    report = import_colaboradores(
        COLABORADORES_MIN,
        avaliacoes_path=AVALIACOES_MIN,
        dry_run=True,
    )

    assert report.modo == 'dry-run'
    assert report.usuarios_criados == 0
    assert report.usuarios_atualizados == 0
    assert report.usuarios_inalterados == _IMPORTAVEIS
    assert _db_counts() == before
    assert _user_emails() == emails_before


# --- T031: demitidos, preferência e-mail, Area/Cargo, crosswalk ---


def test_parse_demissao_serial_excel_e_iso():
    """Contrato §is_active: serial ``45446.0`` e ISO ``2024-06-01`` → demissão."""
    assert parse_legacy_date(45446.0) == date(2024, 6, 3)
    assert parse_legacy_date('2024-06-01') == date(2024, 6, 1)
    assert is_active_from_dismissal(45446.0) is False
    assert is_active_from_dismissal('2024-06-01') is False
    assert is_active_from_dismissal(None) is True
    assert is_active_from_dismissal('') is True
    assert is_active_from_dismissal(0) is True


@pytest.mark.django_db
def test_demitidos_inativos_serial_e_iso():
    """SC-003 / C2: data demissão preenchida → ``is_active=False``; demais ativos."""
    report = _import_samples()

    assert report.demitidos_inativos == _DEMITIDOS
    carla = CustomUser.objects.get(email=_EMAIL_CARLA)
    diego = CustomUser.objects.get(email=_EMAIL_DIEGO)
    assert carla.is_active is False
    assert diego.is_active is False

    ativos = CustomUser.objects.filter(is_active=True)
    assert ativos.count() == _IMPORTAVEIS - _DEMITIDOS
    assert set(ativos.values_list('email', flat=True)) == {
        _EMAIL_GESTOR,
        _EMAIL_ANA,
        _EMAIL_BRUNO,
        _EMAIL_FERNANDA,
        _EMAIL_AMBIGUO,
    }


def test_resolve_email_ordem_preferencia_tres_colunas():
    """FR-004: empresarial → corporativo (``E-mail``) → pessoal; vazio → None."""
    assert (
        resolve_email(
            _colaborador_row(
                email_empresarial=' emp@example.com ',
                email='corp@example.com',
                email_pessoal='pessoal@example.com',
            )
        )
        == 'emp@example.com'
    )
    assert (
        resolve_email(
            _colaborador_row(
                email=' corp@example.com ',
                email_pessoal='pessoal@example.com',
            )
        )
        == 'corp@example.com'
    )
    assert (
        resolve_email(_colaborador_row(email_pessoal=' pessoal@example.com '))
        == 'pessoal@example.com'
    )
    assert resolve_email(_colaborador_row()) is None


@pytest.mark.django_db
def test_import_aplica_ordem_preferencia_email():
    """C2 / FR-004: fixture cobre 1ª, 2ª e 3ª preferência; sem e-mail → skip."""
    report = _import_samples()

    assert CustomUser.objects.get(nome='Ana Silva').email == _EMAIL_ANA
    assert CustomUser.objects.get(nome='Bruno Costa').email == _EMAIL_BRUNO
    assert CustomUser.objects.get(nome='Diego Alves').email == _EMAIL_DIEGO
    assert not CustomUser.objects.filter(nome='Elena Sem Email').exists()
    assert report.n_nao_importaveis == _NAO_IMPORTAVEIS
    assert {entry.motivo for entry in report.nao_importaveis} == {'sem_email'}


@pytest.mark.django_db
def test_area_cargo_resolve_cria_e_vincula():
    """C2: Departamento → Area; Cargo ID/nome → Cargo; linha sem e-mail não cria cargo."""
    report = _import_samples()

    assert report.areas_criadas == _AREAS_FIXTURE
    assert report.cargos_criados == _CARGOS_FIXTURE
    assert set(Area.objects.values_list('nome', flat=True)) == _AREAS_ESPERADAS
    assert Area.objects.filter(parent__isnull=True, is_active=True).count() == 3

    cargos = {c.nome: c for c in Cargo.objects.all()}
    assert set(cargos) == set(_CARGOS_ESPERADOS)
    for nome, solides_id in _CARGOS_ESPERADOS.items():
        assert cargos[nome].solides_id == solides_id
        assert cargos[nome].is_active is True
    assert cargos['Tech Lead Fixture'].nivel == 5
    assert not Cargo.objects.filter(nome='Estagiario Fixture').exists()

    # Ana e Carla compartilham Cargo ID 9001 — um único Cargo.
    assert Cargo.objects.filter(solides_id='9001').count() == 1
    ana = CustomUser.objects.get(email=_EMAIL_ANA)
    carla = CustomUser.objects.get(email=_EMAIL_CARLA)
    assert ana.cargo_id == carla.cargo_id == cargos['Desenvolvedor Fixture'].pk

    for email, (area_nome, cargo_nome) in _USER_AREA_CARGO.items():
        user = CustomUser.objects.get(email=email)
        assert user.area.nome == area_nome
        assert user.cargo.nome == cargo_nome


@pytest.mark.django_db
def test_area_reutiliza_departamento_existente():
    """Resolve Area: departamento já cadastrado → reutiliza, não duplica."""
    Area.objects.create(nome='Engenharia Fixture', is_active=True)
    report = _import_samples()

    assert report.areas_reutilizadas == 1
    assert report.areas_criadas == _AREAS_FIXTURE - 1
    assert Area.objects.filter(nome='Engenharia Fixture', is_active=True).count() == 1
    assert set(Area.objects.values_list('nome', flat=True)) == _AREAS_ESPERADAS


@pytest.mark.django_db
def test_crosswalk_parcial_e_ambiguo():
    """SC-005 / C3: match único preenche ``solides_id``; parcial e ambíguo ficam null."""
    report = _import_samples()

    assert report.solides_id_preenchidos == _SOLIDES_UNICOS
    for email, solides_id in _SOLIDES_POR_EMAIL.items():
        assert CustomUser.objects.get(email=email).solides_id == solides_id

    ambiguos = [c for c in report.conflitos if c.label == 'crosswalk_ambiguo']
    assert len(ambiguos) == 1
    assert 'Nome Ambiguo' in ambiguos[0].extra
    assert '900' in ambiguos[0].motivo
    assert '901' in ambiguos[0].motivo
    # Fernanda não gera conflito — só fica sem identificador (dedupe por e-mail).
    assert CustomUser.objects.get(email=_EMAIL_FERNANDA).email == _EMAIL_FERNANDA


# --- T032: hierarquia, ciclo reportado, arquivo inválido (C3 / C4.3) ---


@pytest.mark.django_db
def test_hierarquia_line_manager_resolvivel():
    """C3: ``Superior direto id`` → ``solides_id`` aplica ``line_manager``."""
    report = _import_samples()

    assert report.gestores_vinculados == _GESTORES_VINCULADOS
    assert report.sem_gestor == _SEM_GESTOR
    assert report.n_ciclos_hierarquia == 0
    assert not any(c.label == 'gestor_nao_resolvido' for c in report.conflitos)

    gestor = CustomUser.objects.get(email=_EMAIL_GESTOR)
    assert gestor.line_manager_id is None
    assert gestor.solides_id == '100'

    for email, manager_email in _LINE_MANAGER_POR_EMAIL.items():
        user = CustomUser.objects.get(email=email)
        if manager_email is None:
            assert user.line_manager_id is None
        else:
            assert user.line_manager is not None
            assert user.line_manager.email == manager_email
            assert user.line_manager.solides_id == '100'

    # Diego demitido ainda recebe gestor (fase B não filtra is_active).
    diego = CustomUser.objects.get(email=_EMAIL_DIEGO)
    assert diego.is_active is False
    assert diego.line_manager_id == gestor.pk


@pytest.mark.django_db
def test_hierarquia_superior_inexistente_nao_aplica_vinculo():
    """C3: superior sem ``solides_id`` → ``gestor_nao_resolvido``; vínculo intacto."""
    _import_samples()
    ana = CustomUser.objects.get(email=_EMAIL_ANA)
    gestor_pk = ana.line_manager_id
    assert gestor_pk is not None

    follow_up = ImportReport()
    apply_hierarchy(
        [
            _colaborador_row(
                nome='Ana Silva',
                email_empresarial=_EMAIL_ANA,
                superior_direto_id='99999',
            )
        ],
        follow_up,
    )

    ana.refresh_from_db()
    assert ana.line_manager_id == gestor_pk
    nao_resolvidos = [
        c for c in follow_up.conflitos if c.label == 'gestor_nao_resolvido'
    ]
    assert len(nao_resolvidos) == 1
    assert '99999' in nao_resolvidos[0].extra
    assert _EMAIL_ANA in nao_resolvidos[0].motivo
    assert follow_up.gestores_vinculados == 0
    assert follow_up.n_ciclos_hierarquia == 0


@pytest.mark.django_db
def test_hierarquia_ciclo_reportado_vinculo_nao_aplicado():
    """C3: ciclo artificial → ``ciclos_hierarquia``; ``line_manager`` anterior intacto."""
    _import_samples()
    ana = CustomUser.objects.get(email=_EMAIL_ANA)
    gestor = CustomUser.objects.get(email=_EMAIL_GESTOR)
    assert ana.line_manager_id == gestor.pk
    assert gestor.line_manager_id is None

    # Gestor Alpha (100) tenta reportar a Ana (101) → ciclo Alpha → Ana → Alpha.
    ciclo_report = ImportReport()
    apply_hierarchy(
        [
            _colaborador_row(
                nome='Gestor Alpha',
                email_empresarial=_EMAIL_GESTOR,
                superior_direto_id='101',
            )
        ],
        ciclo_report,
    )

    gestor.refresh_from_db()
    ana.refresh_from_db()
    assert ciclo_report.n_ciclos_hierarquia == 1
    assert ciclo_report.gestores_vinculados == 0
    assert gestor.line_manager_id is None
    assert ana.line_manager_id == gestor.pk

    ciclo = ciclo_report.ciclos_hierarquia[0]
    assert ciclo.motivo == 'ciclo_detectado'
    assert _EMAIL_GESTOR in ciclo.label
    assert _EMAIL_ANA in ciclo.label


@pytest.mark.django_db
def test_arquivo_ausente_exit_1_db_inalterado(tmp_path: Path):
    """C4.3: path inexistente → ``CommandError`` exit 1; DB inalterado."""
    _import_samples()
    before = _db_counts()
    emails_before = _user_emails()
    missing = tmp_path / 'colaboradores_inexistente.xlsx'
    assert not missing.exists()
    assert 'raw' not in missing.parts

    with pytest.raises(CommandError) as exc_info:
        call_command('importar_colaboradores', colaboradores=str(missing))
    assert exc_info.value.returncode == 1
    assert 'não encontrado' in str(exc_info.value).lower()
    assert _db_counts() == before
    assert _user_emails() == emails_before

    with pytest.raises(LegacyParseError, match='não encontrado'):
        import_colaboradores(missing)
    assert _db_counts() == before
    assert _user_emails() == emails_before
    assert CustomUser.objects.count() == _IMPORTAVEIS


@pytest.mark.django_db
def test_arquivo_ooxml_corrompido_exit_1_db_inalterado(tmp_path: Path):
    """C4.3: OOXML ilegível → exit 1; nenhuma escrita parcial."""
    _import_samples()
    before = _db_counts()
    emails_before = _user_emails()
    corrupted = tmp_path / 'colaboradores_corrompido.xlsx'
    corrupted.write_bytes(b'this is not a valid ooxml workbook')
    assert 'raw' not in corrupted.parts

    with pytest.raises(CommandError) as exc_info:
        call_command('importar_colaboradores', colaboradores=str(corrupted))
    assert exc_info.value.returncode == 1
    assert 'ilegível' in str(exc_info.value).lower()
    assert _db_counts() == before
    assert _user_emails() == emails_before

    with pytest.raises(LegacyParseError):
        import_colaboradores(corrupted)
    assert _db_counts() == before
    assert _user_emails() == emails_before
    assert CustomUser.objects.count() == _IMPORTAVEIS


# --- T033: migration reversível + denylist diff vazio (C1 / R17) ---


@pytest.mark.django_db(transaction=True)
def test_solides_id_migration_reversible_and_preserves_existing():
    """Forward migrate adds nullable field; reverse removes it; seed data intact."""
    cargo = Cargo.objects.create(nome='Cargo Seed T033', nivel=1)
    user = CustomUser.objects.create_user(
        email='seed.migration@example.com',
        password=DEFAULT_PASSWORD,
        nome='Seed Migration',
        cargo=cargo,
    )
    escala = Escala.objects.create(
        nome='Escala Seed T033',
        valor_minimo=1,
        valor_maximo=5,
    )
    competencia = Competencia.objects.create(
        nome='Competencia Seed T033',
        tipo=Competencia.Tipo.TECNICA,
        escala=escala,
    )
    ciclo = Ciclo.objects.create(
        nome='Ciclo Seed T033',
        data_inicio=date(2024, 1, 1),
        data_fim=date(2024, 12, 31),
        status=Ciclo.Status.ENCERRADO,
    )
    avaliacao = Avaliacao.objects.create(ciclo=ciclo, usuario=user)
    pdi = PDI.objects.create(usuario=user, titulo='PDI Seed T033')

    assert user.solides_id is None
    assert cargo.solides_id is None
    assert competencia.solides_id is None
    assert avaliacao.solides_id is None
    assert pdi.solides_id is None

    user.solides_id = 't033-dup'
    user.save(update_fields=['solides_id'])
    other = CustomUser.objects.create_user(
        email='seed.migration.dup@example.com',
        password=DEFAULT_PASSWORD,
        nome='Seed Dup',
    )
    other.solides_id = 't033-dup'
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            other.save(update_fields=['solides_id'])
    other.refresh_from_db()
    assert other.solides_id is None

    seed = {
        'user_pk': user.pk,
        'user_email': user.email,
        'user_nome': user.nome,
        'cargo_pk': cargo.pk,
        'cargo_nome': cargo.nome,
        'competencia_pk': competencia.pk,
        'competencia_nome': competencia.nome,
        'avaliacao_pk': avaliacao.pk,
        'avaliacao_etapa': avaliacao.etapa,
        'avaliacao_concluida': avaliacao.concluida,
        'pdi_pk': pdi.pk,
        'pdi_titulo': pdi.titulo,
        'counts': (
            CustomUser.objects.count(),
            Cargo.objects.count(),
            Competencia.objects.count(),
            Avaliacao.objects.count(),
            PDI.objects.count(),
        ),
    }

    try:
        _backward_solides_id()
        for table in _SOLIDES_ID_TABLES:
            assert 'solides_id' not in _table_columns(table)

        with connection.cursor() as cursor:
            cursor.execute(
                'SELECT email, nome FROM accounts_customuser WHERE id = %s',
                [seed['user_pk']],
            )
            row = cursor.fetchone()
        assert row is not None
        assert row[0] == seed['user_email']
        assert row[1] == seed['user_nome']

        with connection.cursor() as cursor:
            cursor.execute(
                'SELECT nome FROM organization_cargo WHERE id = %s',
                [seed['cargo_pk']],
            )
            assert cursor.fetchone()[0] == seed['cargo_nome']
            cursor.execute(
                'SELECT etapa, concluida FROM reviews_avaliacao WHERE id = %s',
                [seed['avaliacao_pk']],
            )
            etapa, concluida = cursor.fetchone()
            assert etapa == seed['avaliacao_etapa']
            assert bool(concluida) is seed['avaliacao_concluida']

        _forward_solides_id()
        for table in _SOLIDES_ID_TABLES:
            assert 'solides_id' in _table_columns(table)

        user.refresh_from_db()
        cargo.refresh_from_db()
        competencia.refresh_from_db()
        avaliacao.refresh_from_db()
        pdi.refresh_from_db()
        assert user.email == seed['user_email']
        assert user.nome == seed['user_nome']
        assert user.solides_id is None
        assert cargo.nome == seed['cargo_nome']
        assert cargo.solides_id is None
        assert competencia.nome == seed['competencia_nome']
        assert competencia.solides_id is None
        assert avaliacao.etapa == seed['avaliacao_etapa']
        assert avaliacao.concluida is seed['avaliacao_concluida']
        assert avaliacao.solides_id is None
        assert pdi.titulo == seed['pdi_titulo']
        assert pdi.solides_id is None
        assert (
            CustomUser.objects.count(),
            Cargo.objects.count(),
            Competencia.objects.count(),
            Avaliacao.objects.count(),
            PDI.objects.count(),
        ) == seed['counts']

        user.solides_id = 't033-dup'
        user.save(update_fields=['solides_id'])
        other.solides_id = 't033-dup'
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                other.save(update_fields=['solides_id'])
    finally:
        _forward_solides_id()


@pytest.mark.django_db
def test_denylist_diff_vazio_pos_import():
    """R17 / FR-016: após import, diff da denylist permanece vazio."""
    before = _denylist_payloads()
    _import_samples()
    assert _denylist_payloads() == before

    working_tree = _git_diff('HEAD', '--', *_DENYLIST_PATHS)
    assert working_tree == '', working_tree

    if _git_commit_exists(_FEATURE_BASE):
        vs_base = _git_diff(_FEATURE_BASE, 'HEAD', '--', *_DENYLIST_PATHS)
        assert vs_base == '', vs_base


# --- T034: C5 PII/OPSEC + C6 senha unusable (SC-008 / SC-009) ---


def test_suite_nao_referencia_raw_pii():
    """SC-008 / C5.1: a suíte pytest não aponta para backups PII."""
    tests_dir = Path(__file__).parent
    for rel in sorted(tests_dir.glob('test_*.py')):
        text = rel.read_text(encoding='utf-8')
        assert _RAW_PII_DIR not in text, rel.name
        assert _BACKUP_COLABORADORES not in text, rel.name
        assert _BACKUP_AVALIACOES not in text, rel.name


@pytest.mark.django_db
def test_relatorio_stdout_mascara_email_sem_cpf():
    """C5.2 / SC-009: stdout mascara e-mails e não emite CPF sentinela."""
    stdout = StringIO()
    result = call_command(
        'importar_colaboradores',
        colaboradores=str(COLABORADORES_MIN),
        avaliacoes=str(AVALIACOES_MIN),
        stdout=stdout,
    )
    text = stdout.getvalue()

    assert result in (0, None)
    assert 'Amostra (mascarada' in text
    assert '***@example.com' in text
    for email in _EMAILS_IMPORTAVEIS:
        assert email not in text
        assert email.lower() not in text.lower()
    assert _CPF_SENTINELA not in text
    assert '00000000000' not in text


@pytest.mark.django_db
def test_usuario_importado_sem_campos_pii():
    """C5.3 / FR-015: CustomUser importado não tem CPF/RG/endereço."""
    _import_samples()

    field_names = {f.name.lower() for f in CustomUser._meta.get_fields()}
    assert _PII_FIELD_NAMES.isdisjoint(field_names)
    columns = {col.lower() for col in _table_columns('accounts_customuser')}
    assert _PII_FIELD_NAMES.isdisjoint(columns)
    for name in _PII_FIELD_NAMES:
        assert not hasattr(CustomUser, name)

    user = CustomUser.objects.get(email=_EMAIL_ANA)
    for name in _PII_FIELD_NAMES:
        assert not hasattr(user, name)


@pytest.mark.django_db
def test_login_bloqueado_sem_reset_ok_apos_set_password():
    """C6: senha unusable bloqueia login; reset administrativo libera."""
    _import_samples()
    user = CustomUser.objects.get(email=_EMAIL_ANA)
    assert user.is_active
    assert user.email_confirmado_em is not None
    assert not user.has_usable_password()

    assert authenticate(username=_EMAIL_ANA, password=DEFAULT_PASSWORD) is None
    client = Client()
    assert client.login(username=_EMAIL_ANA, password=DEFAULT_PASSWORD) is False
    resp = client.post(
        reverse('accounts:login'),
        {'username': _EMAIL_ANA, 'password': DEFAULT_PASSWORD},
    )
    assert resp.status_code == 200
    assert '_auth_user_id' not in client.session

    user.set_password(DEFAULT_PASSWORD)
    user.save(update_fields=['password'])
    user.refresh_from_db()
    assert user.has_usable_password()

    authenticated = authenticate(
        username=_EMAIL_ANA,
        password=DEFAULT_PASSWORD,
    )
    assert authenticated is not None
    assert authenticated.pk == user.pk

    client = Client()
    assert client.login(username=_EMAIL_ANA, password=DEFAULT_PASSWORD) is True
    assert client.session.get('_auth_user_id') == str(user.pk)
