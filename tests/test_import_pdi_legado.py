"""T005/T006: datas reusadas e relatório mascarado da importação PDI legado.

T005: ``parse_legacy_date`` / ``parse_legacy_datetime`` cobrem
``Data de Entrega`` e ``Criado em`` (serial Excel + ISO). Sem openpyxl
em ``dates.py``. **Proibido** ``raw/``.

T006: ``format_pdi_report`` (seções estáveis, máx. 5, sem nome/e-mail/
título/objetivo/situação completos). Sem persistência. **Proibido** ``raw/``.

T010: validação US1 via quickstart C2 + C5 + C6 (1+1, concat ``\\n\\n``,
responsável = dono, de-para + atraso, digest, spy overdue, denylist).
T013: validação US2 via C3 + C4 (órfão, ambíguo, ``id_vs_nome``, inativo
ok, zero User inventado; denylist + asserts de ``test_scope.py`` intactos).
XLSX em ``tmp_path`` — **proibido** ``raw/``. Samples oficiais ficam na T015.

T016: ``--dry-run`` (SC-006), persist 1+1 / concat / responsável = dono
(SC-002/SC-003) e args/arquivo inválido (exit 1) **somente** com
``data/legado-solides/samples/``. **Proibido** ``raw/``.

T017: órfão / ambíguo / ``id_vs_nome`` / inativo (SC-001), de-para
FR-010/FR-011 (SC-011/SC-012), spy ``mark_overdue_pdi_actions`` e
``git diff`` ``overdue.py`` — **somente** samples. **Proibido** ``raw/``.

T018: digest SC-007, 2ª run delta 0 SC-005, mascaramento SC-008
(stdout == ``--report-file``), suíte sem backups brutos, teste de ouro
denylist SC-010. **Não** altera asserts de stage/scope/reject.

T020: idempotência conservadora — upsert por digest; chave de ação
divergente sem 2ª ação e sem delete; ``pdis_atualizados`` /
``acoes_atualizadas`` = 0. **Proibido** ``raw/``.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from datetime import date, datetime, timedelta, timezone as dt_timezone
from io import StringIO
from pathlib import Path
from unittest.mock import patch

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db.models import Count
from django.utils import timezone
from openpyxl import Workbook

from apps.accounts.models import CustomUser
from apps.accounts.services.legacy_import.dates import (
    parse_legacy_date,
    parse_legacy_datetime,
)
from apps.accounts.services.legacy_import.parse_xlsx import parse_pdi_xlsx
from apps.accounts.services.legacy_import.report import (
    ImportReport,
    format_pdi_report,
    mask_solides_id,
    record_acao_criada,
    record_acao_inalterada,
    record_conflito,
    record_orfao_solicitacao,
    record_pdi_criado,
    record_pdi_inalterado,
    record_pdi_orfao_usuario,
)
from apps.accounts.services.scope import get_visible_users, user_in_scope
from apps.cycles.models import Ciclo
from apps.pdi.models import AcaoPDI, PDI
from apps.pdi.services.legacy_import import (
    LegacyParseError,
    format_pdi_report as _reexport,
    import_pdi,
)
from apps.pdi.services.legacy_import.resolve import (
    ResolveConflict,
    acao_natural_key,
    build_pdi_digest,
    normalize_pdi_titulo,
    resolve_usuario,
)
from apps.reviews.models import Avaliacao
from tests.conftest import DEFAULT_PASSWORD

_DATES_PY = (
    Path(__file__).resolve().parents[1]
    / 'apps'
    / 'accounts'
    / 'services'
    / 'legacy_import'
    / 'dates.py'
)
_SAMPLE_MAX = 5
_DIGEST = 'pdi_' + 'a' * 40
_DIGEST_B = 'pdi_' + 'b' * 40
_EMAIL = 'ana.souza@example.com'
_NOME = 'Ana Souza'
_TITULO = 'PDI confidencial de liderança'
_OBJETIVO = 'Objetivo completo que não pode vazar'
_SITUACAO = 'Situação atual completa que não pode vazar'


def _amostra_items_by_section(text: str) -> dict[str, list[str]]:
    marker = '--- Amostra (mascarada, max 5 por seção) ---'
    _, _, rest = text.partition(marker)
    sample, _, _ = rest.partition('=== Fim ===')
    sections: dict[str, list[str]] = {}
    current: str | None = None
    for raw in sample.splitlines():
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


def test_dates_py_nao_importa_openpyxl():
    """T005 / R8: datas só stdlib + Django; openpyxl permanece em parse_xlsx."""
    source = _DATES_PY.read_text(encoding='utf-8')
    assert 'import openpyxl' not in source
    assert 'from openpyxl' not in source
    assert 'parse_legacy_date' in source
    assert 'parse_legacy_datetime' in source


def test_parse_legacy_date_cobre_data_de_entrega():
    """T005: ``Data de Entrega`` → ``date`` (serial, ISO, sentinela, tipado)."""
    assert parse_legacy_date(45446.0) == date(2024, 6, 3)
    assert parse_legacy_date('2024-06-01') == date(2024, 6, 1)
    assert parse_legacy_date(0) is None
    assert parse_legacy_date('') is None
    assert parse_legacy_date(None) is None
    assert parse_legacy_date(datetime(2025, 1, 15, 12, 0)) == date(2025, 1, 15)
    assert parse_legacy_date(date(2025, 3, 1)) == date(2025, 3, 1)


def test_parse_legacy_date_prazo_ilegivel_levanta_valueerror():
    """T005 / R8: prazo não interpretável → ``ValueError`` (conflito da linha)."""
    try:
        parse_legacy_date('prazo-nao-e-data')
    except ValueError:
        return
    raise AssertionError('esperado ValueError para prazo ilegível')


def test_parse_legacy_datetime_cobre_criado_em():
    """T005: ``Criado em`` → instante (serial com fração + ISO)."""
    serial = parse_legacy_datetime(45446.5)
    assert serial is not None
    assert serial.date() == date(2024, 6, 3)
    iso = parse_legacy_datetime('2024-06-01T15:30:00Z')
    assert iso is not None
    assert iso.astimezone(dt_timezone.utc).replace(tzinfo=None) == datetime(
        2024, 6, 1, 15, 30
    )
    assert parse_legacy_datetime(0) is None
    assert parse_legacy_datetime(None) is None
    assert parse_legacy_datetime('') is None


def test_format_pdi_report_reexportado_na_api_publica():
    assert _reexport is format_pdi_report


def test_format_pdi_report_mascara_e_trunca_max_5():
    """T006 / SC-008: amostra ≤ 5; sem nome, e-mail, título, objetivo ou digest completo."""
    report = ImportReport(
        modo='persist',
        pdi_file='samples/pdi_min.xlsx',
    )
    record_pdi_criado(report, solides_id=_DIGEST)
    record_pdi_inalterado(report, solides_id=_DIGEST_B)
    record_acao_criada(
        report, pdi_solides_id=_DIGEST, status_acao='atrasada'
    )
    record_acao_inalterada(
        report, pdi_solides_id=_DIGEST_B, status_acao='pendente'
    )
    record_pdi_orfao_usuario(report, linha=12, motivo='nome_ambiguo')
    record_orfao_solicitacao(report, id_legado='sol-99999')
    record_conflito(
        report,
        tipo='prazo_invalido',
        motivo=f'linha=4 | email={_EMAIL} | nome={_NOME}',
    )
    record_conflito(
        report,
        tipo='status_desconhecido',
        motivo='linha=9',
    )
    record_conflito(
        report,
        tipo='descricao_vazia',
        motivo='linha=11',
    )
    record_conflito(
        report,
        tipo='titulo_ausente',
        motivo='linha=3',
        extra=f'titulo={_TITULO} | objetivo={_OBJETIVO} | situacao={_SITUACAO}',
    )
    record_conflito(
        report,
        tipo='acao_chave_divergente',
        extra=f'pdi={_DIGEST}',
    )
    record_conflito(
        report,
        tipo='id_vs_nome',
        motivo=f'linha=20 | nome={_NOME} | email={_EMAIL}',
    )
    for i in range(8):
        record_pdi_orfao_usuario(report, linha=100 + i, motivo='usuario_nao_resolvido')
        record_orfao_solicitacao(report, id_legado=f'sol{i:04d}')
        if i == 0:
            continue
        record_pdi_criado(report, solides_id=f'pdi_{"c" * 39}{i}')
        record_acao_criada(
            report,
            pdi_solides_id=f'pdi_{"c" * 39}{i}',
            status_acao='concluida',
        )
        record_conflito(report, tipo='prazo_invalido', motivo=f'linha={i}')

    text = format_pdi_report(report)

    assert text.startswith('=== Importação PDI/ações legado Sólides ===')
    assert 'modo: persist' in text
    assert 'pdi_file: samples/pdi_min.xlsx' in text
    assert 'pdis_criados: 8' in text
    assert 'pdis_atualizados: 0' in text
    assert 'pdis_inalterados: 1' in text
    assert 'acoes_criadas: 8' in text
    assert 'acoes_atualizadas: 0' in text
    assert 'acoes_inalteradas: 1' in text
    assert 'orfaos_usuario: 9' in text
    assert 'orfaos_solicitacao: 9' in text
    assert report.n_conflitos == 13
    assert 'conflitos: 13' in text

    assert _EMAIL not in text
    assert _EMAIL.lower() not in text.lower()
    assert _NOME not in text
    assert _TITULO not in text
    assert _OBJETIVO not in text
    assert _SITUACAO not in text
    assert _DIGEST not in text
    assert _DIGEST_B not in text
    assert mask_solides_id(_DIGEST) in text
    assert 'status_acao=atrasada' in text
    assert 'tipo=prazo_invalido' in text
    assert 'tipo=acao_chave_divergente' in text
    assert 'a***@example.com' in text
    assert 'email=' in text.lower()

    sections = _amostra_items_by_section(text)
    for header in (
        'pdis_criados:',
        'acoes_criadas:',
        'orfaos_usuario:',
        'orfaos_solicitacao:',
        'conflitos:',
    ):
        assert len(sections[header]) == _SAMPLE_MAX, header
    for header, items in sections.items():
        assert len(items) <= _SAMPLE_MAX, header
        for item in items:
            assert _TITULO not in item
            assert _EMAIL not in item
            assert _NOME not in item
            assert _OBJETIVO not in item
            assert _SITUACAO not in item


# --- T010 validação US1 (quickstart C2 + C5 + C6) ---

_REPO_ROOT = Path(__file__).resolve().parents[1]
_IMPORTER_PY = (
    _REPO_ROOT / 'apps' / 'pdi' / 'services' / 'legacy_import' / 'importer.py'
)
_COMMAND_PY = (
    _REPO_ROOT / 'apps' / 'pdi' / 'management' / 'commands' / 'importar_pdi.py'
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
    'apps/pdi/models.py',
    'apps/pdi/views.py',
    'apps/pdi/urls.py',
    'apps/pdi/forms.py',
    'apps/pdi/services/overdue.py',
    'apps/pdi/services/progress.py',
    'apps/pdi/tasks.py',
    'apps/talent',
)
_PDI_HEADERS = (
    'Nome',
    'Título do PDI',
    'Status',
    'Objetivo',
    'Situação Atual',
    'Situação Desejada',
    'Data de Entrega',
    'Criado em',
)


def _write_pdi_xlsx(
    path: Path,
    rows: list[list[object]],
    headers: tuple[str, ...] | None = None,
) -> Path:
    """Fixture OOXML em tmp — testes T010/T012 não leem ``raw/`` nem samples oficiais."""
    wb = Workbook()
    ws = wb.active
    ws.append(list(headers or _PDI_HEADERS))
    for row in rows:
        ws.append(row)
    wb.save(path)
    return path


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
def test_t010_c2_persist_1_pdi_1_acao_concat_responsavel_sem_fk(
    colaborador, tmp_path
):
    """C2: 1 PDI + 1 ação; concat ``\\n\\n``; responsável = dono; zero FK ciclo."""
    titulo = 'PDI concatenacao T010 C2'
    path = _write_pdi_xlsx(
        tmp_path / 'pdi_c2.xlsx',
        [
            [
                colaborador.nome,
                titulo,
                'em_andamento',
                ' Objetivo  um ',
                '',
                'Situação   desejada',
                timezone.localdate() + timedelta(days=10),
                None,
            ]
        ],
    )
    ciclos_antes = Ciclo.objects.count()
    avaliacoes_antes = Avaliacao.objects.count()
    pdis_antes = PDI.objects.count()
    acoes_antes = AcaoPDI.objects.count()

    report = import_pdi(path)

    assert report.pdis_criados == 1
    assert report.acoes_criadas == 1
    assert PDI.objects.count() == pdis_antes + 1
    assert AcaoPDI.objects.count() == acoes_antes + 1

    pdi = PDI.objects.get(usuario=colaborador, titulo=titulo)
    acoes = list(pdi.acoes.all())
    assert len(acoes) == 1
    acao = acoes[0]
    assert acao.descricao == 'Objetivo um\n\nSituação desejada'
    assert acao.descricao.count('\n\n') == 1
    assert acao.responsavel_id == pdi.usuario_id == colaborador.id
    assert Ciclo.objects.count() == ciclos_antes
    assert Avaliacao.objects.count() == avaliacoes_antes
    field_names = {f.name for f in PDI._meta.get_fields()} | {
        f.name for f in AcaoPDI._meta.get_fields()
    }
    assert 'ciclo' not in field_names
    assert 'avaliacao' not in field_names
    assert AcaoPDI.objects.filter(pdi=pdi).count() != 3
    assert pdi.acoes.exists()


@pytest.mark.django_db
def test_t010_c2_tres_trechos_nao_viram_tres_acoes(colaborador, tmp_path):
    """C2: três trechos na mesma linha → uma descrição, uma ação; PDI sem ação = 0."""
    titulo = 'PDI tres trechos T010 C2'
    path = _write_pdi_xlsx(
        tmp_path / 'pdi_c2_tres.xlsx',
        [
            [
                colaborador.nome,
                titulo,
                'finalizado',
                'Objetivo',
                'Situação atual',
                'Situação desejada',
                timezone.localdate() - timedelta(days=3),
                None,
            ]
        ],
    )

    import_pdi(path)

    pdi = PDI.objects.get(usuario=colaborador, titulo=titulo)
    acoes = list(pdi.acoes.all())
    assert len(acoes) == 1
    assert acoes[0].descricao == 'Objetivo\n\nSituação atual\n\nSituação desejada'
    assert PDI.objects.filter(usuario=colaborador, acoes__isnull=True).count() == 0


@pytest.mark.django_db
def test_t010_c5_de_para_atraso_conflitos_spy_mark_overdue(colaborador, tmp_path):
    """C5: FR-010/FR-011; conflitos sem persistir; spy ``mark_overdue_pdi_actions``."""
    hoje = timezone.localdate()
    path = _write_pdi_xlsx(
        tmp_path / 'pdi_c5.xlsx',
        [
            [
                colaborador.nome,
                'PDI finalizado T010 C5',
                'finalizado',
                'Concluir curso',
                '',
                '',
                hoje - timedelta(days=30),
                None,
            ],
            [
                colaborador.nome,
                'PDI atrasado T010 C5',
                'em_andamento',
                'Prazo vencido',
                '',
                '',
                hoje - timedelta(days=1),
                None,
            ],
            [
                colaborador.nome,
                'PDI pendente T010 C5',
                'em_andamento',
                'Prazo futuro',
                '',
                '',
                hoje + timedelta(days=5),
                None,
            ],
            [
                colaborador.nome,
                'PDI status desconhecido T010 C5',
                'rascunho',
                'Texto',
                '',
                '',
                hoje,
                None,
            ],
            [
                colaborador.nome,
                'PDI prazo ilegivel T010 C5',
                'em_andamento',
                'Texto',
                '',
                '',
                'prazo-nao-e-data',
                None,
            ],
            [
                colaborador.nome,
                'PDI descricao vazia T010 C5',
                'em_andamento',
                '',
                '  ',
                None,
                hoje + timedelta(days=2),
                None,
            ],
        ],
    )
    pdis_antes = PDI.objects.count()

    with patch('apps.pdi.tasks.mark_overdue_pdi_actions') as spy_overdue:
        report = import_pdi(path)

    spy_overdue.assert_not_called()
    importer_src = _IMPORTER_PY.read_text(encoding='utf-8')
    command_src = _COMMAND_PY.read_text(encoding='utf-8')
    assert 'mark_overdue_pdi_actions(' not in importer_src
    assert 'mark_overdue_pdi_actions(' not in command_src
    assert 'recalculate_overdue_status(' not in importer_src

    tipos = {c.label for c in report.conflitos}
    assert 'status_desconhecido' in tipos
    assert 'prazo_invalido' in tipos
    assert 'descricao_vazia' in tipos
    assert report.pdis_criados == 3
    assert report.acoes_criadas == 3
    assert PDI.objects.count() == pdis_antes + 3
    assert PDI.objects.filter(status=PDI.Status.ARQUIVADO).count() == 0

    pdi_ok = PDI.objects.get(titulo='PDI finalizado T010 C5')
    acao_ok = pdi_ok.acoes.get()
    assert pdi_ok.status == PDI.Status.CONCLUIDO
    assert acao_ok.status == AcaoPDI.Status.CONCLUIDA
    assert acao_ok.status != AcaoPDI.Status.ATRASADA

    pdi_atrasado = PDI.objects.get(titulo='PDI atrasado T010 C5')
    acao_atrasada = pdi_atrasado.acoes.get()
    assert pdi_atrasado.status == PDI.Status.ATIVO
    assert acao_atrasada.status == AcaoPDI.Status.ATRASADA

    pdi_pendente = PDI.objects.get(titulo='PDI pendente T010 C5')
    acao_pendente = pdi_pendente.acoes.get()
    assert pdi_pendente.status == PDI.Status.ATIVO
    assert acao_pendente.status == AcaoPDI.Status.PENDENTE
    assert acao_pendente.status != AcaoPDI.Status.EM_ANDAMENTO

    assert not PDI.objects.filter(titulo='PDI status desconhecido T010 C5').exists()
    assert not PDI.objects.filter(titulo='PDI prazo ilegivel T010 C5').exists()
    assert not PDI.objects.filter(titulo='PDI descricao vazia T010 C5').exists()


@pytest.mark.django_db
def test_t010_c6_digest_prefixo_len_estavel_diferente_da_concatenacao(
    colaborador, tmp_path
):
    """C6 / SC-007: ``pdi_`` + 40 hex; len 44; ≠ Nome+Título; estável entre runs."""
    titulo = 'PDI digest T010 C6'
    criado = '2024-06-03T15:30:00Z'
    path = _write_pdi_xlsx(
        tmp_path / 'pdi_c6.xlsx',
        [
            [
                colaborador.nome,
                titulo,
                'em_andamento',
                'Objetivo digest',
                '',
                '',
                timezone.localdate() + timedelta(days=8),
                criado,
            ]
        ],
    )

    import_pdi(path)
    pdi = PDI.objects.get(usuario=colaborador, titulo=titulo)
    digest = pdi.solides_id
    assert digest is not None
    assert digest.startswith('pdi_')
    assert len(digest) == 44
    assert len(digest) <= 50
    hex_part = digest.removeprefix('pdi_')
    assert len(hex_part) == 40
    assert re.fullmatch(r'[0-9a-f]{40}', hex_part)
    claro = f'{colaborador.nome}{titulo}'
    assert digest != claro
    assert colaborador.nome not in digest
    assert titulo not in digest
    esperado = build_pdi_digest(colaborador.nome, titulo, criado)
    assert digest == esperado

    report2 = import_pdi(path)
    pdi.refresh_from_db()
    assert pdi.solides_id == digest
    assert report2.pdis_criados == 0
    assert report2.pdis_inalterados == 1
    assert report2.acoes_criadas == 0
    assert report2.acoes_inalteradas == 1
    assert PDI.objects.filter(usuario=colaborador, titulo=titulo).count() == 1
    assert AcaoPDI.objects.filter(pdi=pdi).count() == 1


@pytest.mark.skipif(
    shutil.which('git') is None,
    reason='git ausente no PATH (ex. container web sem git)',
)
def test_t010_c5_git_diff_overdue_models_denylist_vazios():
    """C5 / FR-021: ``overdue.py`` / ``models.py`` e denylist intactos."""
    overdue_diff = _git_diff('HEAD', '--', 'apps/pdi/services/overdue.py')
    models_diff = _git_diff('HEAD', '--', 'apps/pdi/models.py')
    assert overdue_diff == '', overdue_diff
    assert models_diff == '', models_diff

    migrations_diff = _git_diff('HEAD', '--', '**/migrations/**')
    assert migrations_diff == '', migrations_diff

    working_tree = _git_diff('HEAD', '--', *_DENYLIST_PATHS)
    assert working_tree == '', working_tree

    for base in ('development', 'origin/development', 'main'):
        if _git_rev_exists(base):
            vs_base = _git_diff(base, '--', *_DENYLIST_PATHS)
            assert vs_base == '', vs_base
            migrations_vs_base = _git_diff(base, '--', '**/migrations/**')
            assert migrations_vs_base == '', migrations_vs_base
            break


# --- T011 resolução R5 (ID / id_vs_nome / órfão) — persistência no importer é T012 ---


@pytest.mark.django_db
def test_t011_nome_unico_resolve_incluindo_inativo(colaborador, lider):
    """C3/C4: match único por nome; inativo não bloqueia; zero User inventado."""
    users_antes = CustomUser.objects.count()
    assert resolve_usuario(nome=colaborador.nome) == colaborador

    colaborador.is_active = False
    colaborador.save(update_fields=['is_active'])
    assert resolve_usuario(nome=colaborador.nome) == colaborador
    assert CustomUser.objects.count() == users_antes
    assert resolve_usuario(nome=lider.nome) == lider


@pytest.mark.django_db
def test_t011_zero_ou_ambiguo_e_orfao_nunca_escolhe_o_primeiro(
    colaborador, area, cargo_colab, lider
):
    """Zero ou 2+ nomes → None; nunca o primeiro em silêncio."""
    users_antes = CustomUser.objects.count()
    assert resolve_usuario(nome='Pessoa Inexistente XyZ') is None
    assert resolve_usuario(nome='') is None
    assert resolve_usuario(nome='   ') is None

    CustomUser.objects.create_user(
        email='dup-a@test.greenn.com.br',
        password='TestPass123!',
        nome=colaborador.nome,
        cargo=cargo_colab,
        area=area,
        line_manager=lider,
        email_confirmado_em=timezone.now(),
    )
    assert resolve_usuario(nome=colaborador.nome) is None
    assert CustomUser.objects.count() == users_antes + 1


@pytest.mark.django_db
def test_t011_id_unico_prevalece_e_id_vs_nome_quando_nome_unico_diverge(
    colaborador, lider
):
    """ID unique hit prevalece se coerente; Nome unique de outra pessoa → id_vs_nome."""
    colaborador.solides_id = '441'
    colaborador.save(update_fields=['solides_id'])
    lider.solides_id = '442'
    lider.save(update_fields=['solides_id'])

    assert (
        resolve_usuario(nome=colaborador.nome, solides_id='441') == colaborador
    )
    assert (
        resolve_usuario(nome=colaborador.nome, solides_id=441.0) == colaborador
    )

    with pytest.raises(ResolveConflict) as excinfo:
        resolve_usuario(nome=lider.nome, solides_id='441')
    assert excinfo.value.tipo == 'id_vs_nome'

    assert resolve_usuario(nome=colaborador.nome, solides_id='99999') == colaborador
    assert resolve_usuario(nome='Inexistente', solides_id='441') == colaborador


# --- T012 integração US2 no importer + comando (órfãos / id_vs_nome / inativo) ---

_SCOPE_DENY = (
    'get_visible_users',
    'user_in_scope',
    'ScopedObjectMixin',
)


def _pdi_row(
    nome: str,
    titulo: str,
    *,
    status: str = 'em_andamento',
    identificador: object | None = None,
) -> list[object]:
    row: list[object] = [
        nome,
        titulo,
        status,
        'Objetivo T012',
        '',
        '',
        timezone.localdate() + timedelta(days=7),
        None,
    ]
    if identificador is not None:
        row.append(identificador)
    return row


@pytest.mark.django_db
def test_t012_orfaos_e_id_vs_nome_nao_fatais_lote_continua(
    colaborador, lider, tmp_path
):
    """C3: órfão/ambíguo/id_vs_nome skip da linha; lote segue; zero User inventado."""
    colaborador.solides_id = '441'
    colaborador.save(update_fields=['solides_id'])
    lider.solides_id = '442'
    lider.save(update_fields=['solides_id'])

    titulo_ok = 'PDI T012 match unico'
    titulo_orfao = 'PDI T012 orfao'
    titulo_id_vs_nome = 'PDI T012 id vs nome'
    headers = _PDI_HEADERS + ('Identificador',)
    path = _write_pdi_xlsx(
        tmp_path / 'pdi_t012_c3.xlsx',
        [
            _pdi_row('Pessoa Inexistente XyZ', titulo_orfao, identificador=''),
            _pdi_row(
                colaborador.nome, titulo_ok, identificador=colaborador.solides_id
            ),
            _pdi_row(
                lider.nome,
                titulo_id_vs_nome,
                identificador=colaborador.solides_id,
            ),
        ],
        headers=headers,
    )
    users_antes = CustomUser.objects.count()
    pdis_antes = PDI.objects.count()

    report = import_pdi(path)

    assert CustomUser.objects.count() == users_antes
    assert report.pdis_criados == 1
    assert report.acoes_criadas == 1
    assert report.n_orfaos_usuario == 1
    assert report.orfaos_usuario[0].motivo == 'usuario_nao_resolvido'
    tipos = {c.label for c in report.conflitos}
    assert 'id_vs_nome' in tipos
    assert PDI.objects.count() == pdis_antes + 1
    assert PDI.objects.filter(titulo=titulo_ok, usuario=colaborador).exists()
    assert not PDI.objects.filter(titulo=titulo_orfao).exists()
    assert not PDI.objects.filter(titulo=titulo_id_vs_nome).exists()


@pytest.mark.django_db
def test_t012_nome_ambiguo_nunca_escolhe_o_primeiro(
    colaborador, area, cargo_colab, lider, tmp_path
):
    """C3: 2+ canonical_key → orfaos_usuario nome_ambiguo; não persiste no 'primeiro'."""
    CustomUser.objects.create_user(
        email='dup-t012@test.greenn.com.br',
        password='TestPass123!',
        nome=colaborador.nome,
        cargo=cargo_colab,
        area=area,
        line_manager=lider,
        email_confirmado_em=timezone.now(),
    )
    titulo = 'PDI T012 ambiguo'
    path = _write_pdi_xlsx(
        tmp_path / 'pdi_t012_ambiguo.xlsx',
        [_pdi_row(colaborador.nome, titulo)],
    )
    pdis_antes = PDI.objects.filter(titulo=titulo).count()

    report = import_pdi(path)

    assert report.pdis_criados == 0
    assert report.n_orfaos_usuario == 1
    assert report.orfaos_usuario[0].motivo == 'nome_ambiguo'
    assert PDI.objects.filter(titulo=titulo).count() == pdis_antes


@pytest.mark.django_db
def test_t012_inativo_persiste_sem_atalho_de_escopo(colaborador, tmp_path):
    """C4: is_active=False com match único persiste; comando sem mixins de escopo."""
    colaborador.is_active = False
    colaborador.save(update_fields=['is_active'])
    titulo = 'PDI T012 inativo'
    path = _write_pdi_xlsx(
        tmp_path / 'pdi_t012_inativo.xlsx',
        [_pdi_row(colaborador.nome, titulo)],
    )

    report = import_pdi(path)

    assert report.pdis_criados == 1
    pdi = PDI.objects.get(titulo=titulo)
    assert pdi.usuario_id == colaborador.id
    acao = pdi.acoes.get()
    assert acao.responsavel_id == colaborador.id

    importer_src = _IMPORTER_PY.read_text(encoding='utf-8')
    command_src = _COMMAND_PY.read_text(encoding='utf-8')
    for token in _SCOPE_DENY:
        assert f'{token}(' not in importer_src
        assert f'{token}(' not in command_src
        if token != 'ScopedObjectMixin':
            continue
        assert 'class Command(ScopedObjectMixin' not in command_src
        assert 'class Command(BaseCommand)' in command_src


@pytest.mark.django_db
def test_t012_comando_orfaos_nao_fatais_exit_0(colaborador, tmp_path):
    """CLI: órfão no lote → relatório com orfaos_usuario; handle retorna 0."""
    path = _write_pdi_xlsx(
        tmp_path / 'pdi_t012_cmd.xlsx',
        [
            _pdi_row('Pessoa Inexistente XyZ', 'PDI T012 cmd orfao'),
            _pdi_row(colaborador.nome, 'PDI T012 cmd ok'),
        ],
    )
    stdout = StringIO()

    result = call_command('importar_pdi', pdi=str(path), stdout=stdout)

    assert result in (0, None)
    text = stdout.getvalue()
    assert 'orfaos_usuario: 1' in text
    assert 'pdis_criados: 1' in text
    assert PDI.objects.filter(titulo='PDI T012 cmd ok', usuario=colaborador).exists()
    assert not PDI.objects.filter(titulo='PDI T012 cmd orfao').exists()


# --- T013 validação US2 (quickstart C3 + C4) ---

_SCOPE_TEST_PY = _REPO_ROOT / 'tests' / 'test_scope.py'
_SCOPE_ASSERT_MARKERS = (
    "assert get_scope_level(admin) == 'admin'",
    "assert get_scope_level(lider) == 'leader'",
    "assert get_scope_level(colaborador) == 'collaborator'",
    'assert {admin.pk, lider.pk, colaborador.pk, outsider.pk}.issubset(visible)',
    'assert visible == {lider.pk, colaborador.pk}',
    'assert outsider.pk not in visible',
    'assert user_in_scope(lider, outsider.pk) is False',
    'assert visible == {colaborador.pk}',
    'assert resp.status_code == 404',
    'assert after == before + 1',
)


@pytest.mark.django_db
def test_t013_c3_orfao_ambiguo_id_vs_nome_zero_user_inventado(
    colaborador, lider, area, cargo_colab, tmp_path
):
    """C3: órfão, ambíguo e ``id_vs_nome``; nunca o primeiro; zero User inventado."""
    colaborador.solides_id = '441'
    colaborador.save(update_fields=['solides_id'])
    lider.solides_id = '442'
    lider.save(update_fields=['solides_id'])
    CustomUser.objects.create_user(
        email='dup-t013@test.greenn.com.br',
        password='TestPass123!',
        nome=colaborador.nome,
        cargo=cargo_colab,
        area=area,
        line_manager=lider,
        email_confirmado_em=timezone.now(),
    )

    titulo_orfao = 'PDI T013 C3 orfao'
    titulo_ambiguo = 'PDI T013 C3 ambiguo'
    titulo_id_vs_nome = 'PDI T013 C3 id vs nome'
    titulo_lider = 'PDI T013 C3 lider unico'
    headers = _PDI_HEADERS + ('Identificador',)
    path = _write_pdi_xlsx(
        tmp_path / 'pdi_t013_c3.xlsx',
        [
            _pdi_row('Pessoa Inexistente XyZ', titulo_orfao, identificador=''),
            _pdi_row(colaborador.nome, titulo_ambiguo, identificador=''),
            _pdi_row(
                lider.nome,
                titulo_id_vs_nome,
                identificador=colaborador.solides_id,
            ),
            _pdi_row(lider.nome, titulo_lider, identificador=lider.solides_id),
        ],
        headers=headers,
    )
    users_antes = CustomUser.objects.count()
    pdis_antes = PDI.objects.count()

    report = import_pdi(path)

    assert CustomUser.objects.count() == users_antes
    assert not CustomUser.objects.filter(nome='Pessoa Inexistente XyZ').exists()
    assert report.pdis_criados == 1
    assert report.acoes_criadas == 1
    assert report.n_orfaos_usuario == 2
    motivos = {item.motivo for item in report.orfaos_usuario}
    assert motivos == {'usuario_nao_resolvido', 'nome_ambiguo'}
    tipos = {c.label for c in report.conflitos}
    assert 'id_vs_nome' in tipos
    assert PDI.objects.count() == pdis_antes + 1
    assert PDI.objects.filter(titulo=titulo_lider, usuario=lider).exists()
    assert not PDI.objects.filter(titulo=titulo_orfao).exists()
    assert not PDI.objects.filter(titulo=titulo_ambiguo).exists()
    assert not PDI.objects.filter(titulo=titulo_id_vs_nome).exists()
    assert not PDI.objects.filter(titulo=titulo_ambiguo, usuario=colaborador).exists()


@pytest.mark.django_db
def test_t013_c4_inativo_persiste_escopo_vigente_sem_atalho(
    colaborador, lider, area, cargo_colab, tmp_path
):
    """C4 / FR-020: inativo com match único persiste; escopo vigente sem atalho."""
    colaborador.is_active = False
    colaborador.save(update_fields=['is_active'])
    outsider = CustomUser.objects.create_user(
        email='outsider-t013@test.greenn.com.br',
        password='TestPass123!',
        nome='Outsider T013',
        cargo=cargo_colab,
        area=area,
        line_manager=None,
        email_confirmado_em=timezone.now(),
    )
    visivel_lider_antes = set(
        get_visible_users(lider).values_list('pk', flat=True)
    )
    visivel_colab_antes = set(
        get_visible_users(colaborador).values_list('pk', flat=True)
    )
    visivel_outsider_antes = set(
        get_visible_users(outsider).values_list('pk', flat=True)
    )
    titulo = 'PDI T013 C4 inativo'
    path = _write_pdi_xlsx(
        tmp_path / 'pdi_t013_c4.xlsx',
        [_pdi_row(colaborador.nome, titulo)],
    )
    users_antes = CustomUser.objects.count()

    report = import_pdi(path)

    assert CustomUser.objects.count() == users_antes
    assert report.pdis_criados == 1
    pdi = PDI.objects.get(titulo=titulo)
    assert pdi.usuario_id == colaborador.id
    assert pdi.usuario.is_active is False
    assert pdi.acoes.get().responsavel_id == colaborador.id

    visivel_lider = set(get_visible_users(lider).values_list('pk', flat=True))
    visivel_colab = set(
        get_visible_users(colaborador).values_list('pk', flat=True)
    )
    visivel_outsider = set(
        get_visible_users(outsider).values_list('pk', flat=True)
    )
    assert visivel_lider == visivel_lider_antes == {lider.pk, colaborador.pk}
    assert visivel_colab == visivel_colab_antes == {colaborador.pk}
    assert visivel_outsider == visivel_outsider_antes == {outsider.pk}
    assert colaborador.pk not in visivel_outsider
    assert user_in_scope(lider, colaborador.pk) is True
    assert user_in_scope(outsider, colaborador.pk) is False


@pytest.mark.skipif(
    shutil.which('git') is None,
    reason='git ausente no PATH (ex. container web sem git)',
)
def test_t013_c4_git_diff_denylist_e_test_scope_intactos():
    """C4 / SC-010: denylist vazia; asserts de ``tests/test_scope.py`` intactos."""
    scope_src = _SCOPE_TEST_PY.read_text(encoding='utf-8')
    for marker in _SCOPE_ASSERT_MARKERS:
        assert marker in scope_src, marker

    working_tree = _git_diff('HEAD', '--', *_DENYLIST_PATHS)
    assert working_tree == '', working_tree
    scope_working = _git_diff('HEAD', '--', 'tests/test_scope.py')
    assert scope_working == '', scope_working
    migrations_diff = _git_diff('HEAD', '--', '**/migrations/**')
    assert migrations_diff == '', migrations_diff

    for base in ('development', 'origin/development', 'main'):
        if _git_rev_exists(base):
            vs_base = _git_diff(base, '--', *_DENYLIST_PATHS)
            assert vs_base == '', vs_base
            scope_vs_base = _git_diff(base, '--', 'tests/test_scope.py')
            assert scope_vs_base == '', scope_vs_base
            migrations_vs_base = _git_diff(base, '--', '**/migrations/**')
            assert migrations_vs_base == '', migrations_vs_base
            break


# --- T016: dry-run / 1+1 samples / args inválidos (quickstart C1 + C2; SC-002/003/006) ---

_SAMPLES_DIR = _REPO_ROOT / 'data' / 'legado-solides' / 'samples'
_PDI_MIN = _SAMPLES_DIR / 'pdi_min.xlsx'
_RAW_PII_DIR = '/'.join(('data', 'legado-solides', 'raw'))
_T016_PDIS_CRIADOS = 4
_T016_ACOES_CRIADAS = 4
_T016_ORFAOS_USUARIO = 2
_T016_ORFAOS_SOLICITACAO = 3
_T016_CONFLITOS = 5
_T016_TITULO_ANA = (
    'PDI Comunicacao Fixture com titulo longo que nao pode vazar no relatorio'
)
_T016_DESC_ANA = (
    'Objetivo completo que nao pode vazar no relatorio mascarado de PDI Fixture'
    '\n\n'
    'Situacao atual completa que nao pode vazar no relatorio mascarado Fixture'
    '\n\n'
    'Situacao desejada completa que nao pode vazar no relatorio mascarado Fixture'
)
_T016_TITULO_BRUNO = 'PDI Colaboracao Fixture'
_T016_DESC_BRUNO = (
    'Objetivo colaboracao Fixture\n\nSituacao desejada colaboracao Fixture'
)
_T016_TITULO_GESTOR = 'PDI Lideranca Fixture'
_T016_TITULO_CARLA = 'PDI Inativo Fixture'
_T016_TITULOS_OK = (
    _T016_TITULO_ANA,
    _T016_TITULO_BRUNO,
    _T016_TITULO_GESTOR,
    _T016_TITULO_CARLA,
)
_T016_SEED_UNIQUE = (
    ('gestor.alpha@example.com', 'Gestor Alpha', '100', True),
    ('ana.silva@example.com', 'Ana Silva', '101', True),
    ('bruno.costa@example.com', 'Bruno Costa', '102', True),
    ('carla.dias@example.com', 'Carla Dias', '103', False),
    ('diego.alves@example.com', 'Diego Alves', '104', True),
    ('fernanda.lima@example.com', 'Fernanda Lima', None, True),
)
_T016_PII = (
    'ana.silva@example.com',
    '000.000.000-00',
    'Ana Silva',
    'Usuario Orfao Fixture',
    _T016_TITULO_ANA,
)


def _t016_assert_samples_only() -> None:
    assert _PDI_MIN.exists(), _PDI_MIN
    assert 'raw' not in _PDI_MIN.parts
    assert _RAW_PII_DIR not in str(_PDI_MIN)


def _t016_write_counts() -> tuple[int, int, int]:
    """PDI / AcaoPDI / User — SC-006 e args inválidos."""
    return (
        PDI.objects.count(),
        AcaoPDI.objects.count(),
        CustomUser.objects.count(),
    )


def _t016_seed_world() -> dict[str, CustomUser]:
    """Pré-condição 010 alinhada a ``pdi_min.xlsx`` (match único + inativo + ambíguo)."""
    _t016_assert_samples_only()
    users: dict[str, CustomUser] = {}
    gestor: CustomUser | None = None
    for email, nome, solides_id, is_active in _T016_SEED_UNIQUE:
        user = CustomUser.objects.create_user(
            email=email,
            password=DEFAULT_PASSWORD,
            nome=nome,
            solides_id=solides_id,
            email_confirmado_em=timezone.now(),
            is_active=is_active,
        )
        users[nome] = user
        if solides_id == '100':
            gestor = user
    CustomUser.objects.create_user(
        email='nome.ambiguo.a@example.com',
        password=DEFAULT_PASSWORD,
        nome='Nome Ambiguo',
        email_confirmado_em=timezone.now(),
    )
    CustomUser.objects.create_user(
        email='nome.ambiguo.b@example.com',
        password=DEFAULT_PASSWORD,
        nome='Nome Ambiguo',
        email_confirmado_em=timezone.now(),
    )
    if gestor is not None:
        for nome in ('Ana Silva', 'Bruno Costa', 'Diego Alves'):
            colab = users[nome]
            colab.line_manager = gestor
            colab.save(update_fields=['line_manager'])
    return users


def _t016_import_sample(**kwargs):
    _t016_assert_samples_only()
    return import_pdi(_PDI_MIN, **kwargs)


def test_t016_suite_usa_somente_samples():
    """T016 / OPSEC: suíte aponta para samples; zero path ``raw/`` neste módulo."""
    _t016_assert_samples_only()
    text = Path(__file__).read_text(encoding='utf-8')
    assert _RAW_PII_DIR not in text
    assert 'pdi_min.xlsx' in text


@pytest.mark.django_db
def test_t016_dry_run_zero_writes_totais_projetados():
    """SC-006 / C1: dry-run projeta totais e zero writes em ``PDI``/``AcaoPDI``."""
    _t016_seed_world()
    before = _t016_write_counts()

    report = _t016_import_sample(dry_run=True)

    assert report.modo == 'dry-run'
    assert report.pdis_criados == _T016_PDIS_CRIADOS
    assert report.acoes_criadas == _T016_ACOES_CRIADAS
    assert report.n_orfaos_usuario == _T016_ORFAOS_USUARIO
    assert report.n_orfaos_solicitacao == _T016_ORFAOS_SOLICITACAO
    assert report.n_conflitos == _T016_CONFLITOS
    assert _t016_write_counts() == before
    assert PDI.objects.count() == 0
    assert AcaoPDI.objects.count() == 0
    assert not CustomUser.objects.filter(nome='Usuario Orfao Fixture').exists()


@pytest.mark.django_db
def test_t016_dry_run_via_comando_zero_writes():
    """C1: ``importar_pdi --dry-run`` com samples → exit 0, zero writes."""
    _t016_seed_world()
    before = _t016_write_counts()
    stdout = StringIO()

    result = call_command(
        'importar_pdi',
        pdi=str(_PDI_MIN),
        dry_run=True,
        stdout=stdout,
    )

    text = stdout.getvalue()
    assert result in (0, None)
    assert 'modo: dry-run' in text
    assert f'pdis_criados: {_T016_PDIS_CRIADOS}' in text
    assert f'acoes_criadas: {_T016_ACOES_CRIADAS}' in text
    assert f'orfaos_usuario: {_T016_ORFAOS_USUARIO}' in text
    assert f'orfaos_solicitacao: {_T016_ORFAOS_SOLICITACAO}' in text
    assert f'conflitos: {_T016_CONFLITOS}' in text
    for token in _T016_PII:
        assert token not in text, token
    assert _t016_write_counts() == before
    assert PDI.objects.count() == 0
    assert AcaoPDI.objects.count() == 0
    assert 'raw' not in _PDI_MIN.parts


@pytest.mark.django_db
def test_t016_persist_1_pdi_1_acao_concat_responsavel_samples():
    """SC-002/SC-003 / C2: 1+1; concat ``\\n\\n``; responsável = dono; zero três ações."""
    users = _t016_seed_world()
    ana = users['Ana Silva']
    bruno = users['Bruno Costa']
    gestor = users['Gestor Alpha']
    carla = users['Carla Dias']
    users_antes = CustomUser.objects.count()
    pdis_antes = PDI.objects.count()
    acoes_antes = AcaoPDI.objects.count()

    report = _t016_import_sample()

    assert CustomUser.objects.count() == users_antes
    assert not CustomUser.objects.filter(nome='Usuario Orfao Fixture').exists()
    assert report.pdis_criados == _T016_PDIS_CRIADOS
    assert report.acoes_criadas == _T016_ACOES_CRIADAS
    assert PDI.objects.count() == pdis_antes + _T016_PDIS_CRIADOS
    assert AcaoPDI.objects.count() == acoes_antes + _T016_ACOES_CRIADAS

    for titulo in _T016_TITULOS_OK:
        pdi = PDI.objects.get(titulo=titulo)
        acoes = list(pdi.acoes.all())
        assert len(acoes) == 1
        assert acoes[0].responsavel_id == pdi.usuario_id
        assert pdi.acoes.exists()

    pdi_ana = PDI.objects.get(titulo=_T016_TITULO_ANA, usuario=ana)
    acao_ana = pdi_ana.acoes.get()
    assert acao_ana.descricao == _T016_DESC_ANA
    assert acao_ana.descricao.count('\n\n') == 2
    assert acao_ana.responsavel_id == ana.id
    assert acao_ana.responsavel_id != gestor.id
    assert ana.line_manager_id == gestor.id

    pdi_bruno = PDI.objects.get(titulo=_T016_TITULO_BRUNO, usuario=bruno)
    acao_bruno = pdi_bruno.acoes.get()
    assert acao_bruno.descricao == _T016_DESC_BRUNO
    assert acao_bruno.descricao.count('\n\n') == 1
    assert acao_bruno.responsavel_id == bruno.id

    pdi_gestor = PDI.objects.get(titulo=_T016_TITULO_GESTOR, usuario=gestor)
    assert pdi_gestor.acoes.get().responsavel_id == gestor.id

    pdi_carla = PDI.objects.get(titulo=_T016_TITULO_CARLA, usuario=carla)
    assert carla.is_active is False
    assert pdi_carla.acoes.get().responsavel_id == carla.id

    assert PDI.objects.filter(acoes__isnull=True).count() == 0
    assert not (
        AcaoPDI.objects.values('pdi_id')
        .annotate(n=Count('id'))
        .filter(n__gte=3)
        .exists()
    )
    assert not PDI.objects.filter(titulo='PDI Orfao Fixture').exists()
    assert not PDI.objects.filter(titulo='PDI Ambiguo Fixture').exists()
    assert not PDI.objects.filter(titulo='PDI IdVsNome Fixture').exists()
    assert not PDI.objects.filter(titulo='PDI Status Desconhecido Fixture').exists()
    assert not PDI.objects.filter(titulo='PDI Prazo Ilegivel Fixture').exists()
    assert not PDI.objects.filter(titulo='PDI Descricao Vazia Fixture').exists()
    assert not PDI.objects.filter(usuario=users['Diego Alves']).exists()


@pytest.mark.django_db
def test_t016_args_faltando_exit_1_db_inalterado():
    """T016 / contrato: ``--pdi`` ausente → exit 1; DB intacto."""
    _t016_seed_world()
    before = _t016_write_counts()

    with pytest.raises(CommandError) as exc_info:
        call_command('importar_pdi')
    assert exc_info.value.returncode == 1
    assert _t016_write_counts() == before
    assert PDI.objects.count() == 0
    assert AcaoPDI.objects.count() == 0


@pytest.mark.django_db
def test_t016_arquivo_ausente_exit_1_db_inalterado(tmp_path: Path):
    """T016: arquivo inexistente → exit 1; DB inalterado (samples no path válido)."""
    _t016_seed_world()
    before = _t016_write_counts()
    missing = tmp_path / 'pdi_inexistente.xlsx'
    assert not missing.exists()
    assert 'raw' not in missing.parts

    with pytest.raises(CommandError) as exc_info:
        call_command('importar_pdi', pdi=str(missing))
    assert exc_info.value.returncode == 1
    assert 'não encontrado' in str(exc_info.value).lower()
    assert _t016_write_counts() == before

    with pytest.raises(LegacyParseError, match='não encontrado'):
        import_pdi(missing)
    assert _t016_write_counts() == before
    assert PDI.objects.count() == 0
    assert AcaoPDI.objects.count() == 0


@pytest.mark.django_db
def test_t016_arquivo_ooxml_corrompido_exit_1_db_inalterado(tmp_path: Path):
    """T016: OOXML ilegível → exit 1; nenhuma escrita parcial."""
    _t016_seed_world()
    before = _t016_write_counts()
    corrupted = tmp_path / 'pdi_corrompido.xlsx'
    corrupted.write_bytes(b'this is not a valid ooxml workbook')
    assert 'raw' not in corrupted.parts

    with pytest.raises(CommandError) as exc_info:
        call_command('importar_pdi', pdi=str(corrupted))
    assert exc_info.value.returncode == 1
    assert 'ilegível' in str(exc_info.value).lower()
    assert _t016_write_counts() == before

    with pytest.raises(LegacyParseError):
        import_pdi(corrupted)
    assert _t016_write_counts() == before
    assert PDI.objects.count() == 0
    assert AcaoPDI.objects.count() == 0


@pytest.mark.django_db
def test_t016_colunas_obrigatorias_ausentes_exit_1_db_inalterado(tmp_path: Path):
    """T016: header sem colunas obrigatórias → exit 1; DB inalterado."""
    _t016_seed_world()
    before = _t016_write_counts()
    path = tmp_path / 'pdi_sem_colunas.xlsx'
    _write_pdi_xlsx(path, [['Ana Silva']], headers=('Nome',))
    assert 'raw' not in path.parts

    with pytest.raises(CommandError) as exc_info:
        call_command('importar_pdi', pdi=str(path))
    assert exc_info.value.returncode == 1
    assert 'obrigatór' in str(exc_info.value).lower()
    assert _t016_write_counts() == before

    with pytest.raises(LegacyParseError):
        import_pdi(path)
    assert _t016_write_counts() == before
    assert PDI.objects.count() == 0
    assert AcaoPDI.objects.count() == 0


# --- T017: SC-001 / FR-010 / FR-011 / spy overdue / denylist (samples) ---

_T017_TITULO_ORFAO = 'PDI Orfao Fixture'
_T017_TITULO_AMBIGUO = 'PDI Ambiguo Fixture'
_T017_TITULO_ID_VS_NOME = 'PDI IdVsNome Fixture'
_T017_TITULO_STATUS = 'PDI Status Desconhecido Fixture'
_T017_TITULO_PRAZO = 'PDI Prazo Ilegivel Fixture'
_T017_TITULO_DESC = 'PDI Descricao Vazia Fixture'
_T017_CONFLITO_TIPOS = {
    'id_vs_nome',
    'status_desconhecido',
    'prazo_invalido',
    'descricao_vazia',
    'titulo_excede_limite',
}
_OVERDUE_PY = _REPO_ROOT / 'apps' / 'pdi' / 'services' / 'overdue.py'
_TASKS_PY = _REPO_ROOT / 'apps' / 'pdi' / 'tasks.py'


@pytest.mark.django_db
def test_t017_sc001_orfao_ambiguo_id_vs_nome_inativo_zero_user():
    """SC-001 / C3+C4: órfão, ambíguo, ``id_vs_nome``; inativo persiste; zero User."""
    users = _t016_seed_world()
    carla = users['Carla Dias']
    users_antes = CustomUser.objects.count()

    report = _t016_import_sample()

    assert CustomUser.objects.count() == users_antes
    assert not CustomUser.objects.filter(nome='Usuario Orfao Fixture').exists()
    assert report.n_orfaos_usuario == _T016_ORFAOS_USUARIO
    motivos = {item.motivo for item in report.orfaos_usuario}
    assert motivos == {'usuario_nao_resolvido', 'nome_ambiguo'}
    tipos = {c.label for c in report.conflitos}
    assert 'id_vs_nome' in tipos
    assert report.pdis_criados == _T016_PDIS_CRIADOS
    assert PDI.objects.filter(titulo=_T016_TITULO_CARLA, usuario=carla).exists()
    assert carla.is_active is False
    assert PDI.objects.get(titulo=_T016_TITULO_CARLA).usuario_id == carla.id
    assert not PDI.objects.filter(titulo=_T017_TITULO_ORFAO).exists()
    assert not PDI.objects.filter(titulo=_T017_TITULO_AMBIGUO).exists()
    assert not PDI.objects.filter(titulo=_T017_TITULO_ID_VS_NOME).exists()
    assert not PDI.objects.filter(titulo=_T017_TITULO_AMBIGUO, usuario=users['Ana Silva']).exists()


@pytest.mark.django_db
def test_t017_c5_de_para_fr010_fr011_zero_arquivado_spy_overdue():
    """SC-011/SC-012 / C5: FR-010/FR-011; conflitos skip; spy overdue; zero arquivado."""
    users = _t016_seed_world()
    ana = users['Ana Silva']
    bruno = users['Bruno Costa']
    gestor = users['Gestor Alpha']
    pdis_antes = PDI.objects.count()

    with patch('apps.pdi.tasks.mark_overdue_pdi_actions') as spy_overdue:
        report = _t016_import_sample()

    spy_overdue.assert_not_called()
    importer_src = _IMPORTER_PY.read_text(encoding='utf-8')
    command_src = _COMMAND_PY.read_text(encoding='utf-8')
    assert 'mark_overdue_pdi_actions(' not in importer_src
    assert 'mark_overdue_pdi_actions(' not in command_src
    assert 'recalculate_overdue_status(' not in importer_src
    tasks_src = _TASKS_PY.read_text(encoding='utf-8')
    overdue_src = _OVERDUE_PY.read_text(encoding='utf-8')
    assert 'mark_overdue_pdi_actions' in tasks_src
    assert 'def recalculate_overdue_status' in overdue_src

    tipos = {c.label for c in report.conflitos}
    assert tipos == _T017_CONFLITO_TIPOS
    assert report.n_conflitos == _T016_CONFLITOS
    assert report.pdis_criados == _T016_PDIS_CRIADOS
    assert report.acoes_criadas == _T016_ACOES_CRIADAS
    assert PDI.objects.count() == pdis_antes + _T016_PDIS_CRIADOS
    assert PDI.objects.filter(status=PDI.Status.ARQUIVADO).count() == 0
    assert not PDI.objects.filter(titulo=_T017_TITULO_STATUS).exists()
    assert not PDI.objects.filter(titulo=_T017_TITULO_PRAZO).exists()
    assert not PDI.objects.filter(titulo=_T017_TITULO_DESC).exists()
    assert not PDI.objects.filter(usuario=users['Diego Alves']).exists()
    assert not PDI.objects.filter(usuario=users['Fernanda Lima']).exists()

    pdi_ana = PDI.objects.get(titulo=_T016_TITULO_ANA, usuario=ana)
    acao_ana = pdi_ana.acoes.get()
    assert pdi_ana.status == PDI.Status.CONCLUIDO
    assert acao_ana.status == AcaoPDI.Status.CONCLUIDA
    assert acao_ana.status != AcaoPDI.Status.ATRASADA

    pdi_bruno = PDI.objects.get(titulo=_T016_TITULO_BRUNO, usuario=bruno)
    acao_bruno = pdi_bruno.acoes.get()
    assert pdi_bruno.status == PDI.Status.ATIVO
    assert acao_bruno.status == AcaoPDI.Status.PENDENTE
    assert acao_bruno.status != AcaoPDI.Status.EM_ANDAMENTO
    assert acao_bruno.prazo == date(2027, 12, 31)

    pdi_gestor = PDI.objects.get(titulo=_T016_TITULO_GESTOR, usuario=gestor)
    acao_gestor = pdi_gestor.acoes.get()
    assert pdi_gestor.status == PDI.Status.ATIVO
    assert acao_gestor.status == AcaoPDI.Status.ATRASADA
    assert acao_gestor.prazo == date(2024, 6, 3)
    assert acao_gestor.prazo < timezone.localdate()

    pdi_carla = PDI.objects.get(titulo=_T016_TITULO_CARLA)
    acao_carla = pdi_carla.acoes.get()
    assert pdi_carla.status == PDI.Status.CONCLUIDO
    assert acao_carla.status == AcaoPDI.Status.CONCLUIDA
    assert acao_carla.status != AcaoPDI.Status.ATRASADA
    assert acao_carla.prazo == date(2024, 1, 15)


@pytest.mark.skipif(
    shutil.which('git') is None,
    reason='git ausente no PATH (ex. container web sem git)',
)
def test_t017_git_diff_overdue_denylist_vazio():
    """C5 / FR-021: ``overdue.py`` e denylist intactos; zero migrations."""
    overdue_diff = _git_diff('HEAD', '--', 'apps/pdi/services/overdue.py')
    assert overdue_diff == '', overdue_diff

    working_tree = _git_diff('HEAD', '--', *_DENYLIST_PATHS)
    assert working_tree == '', working_tree
    migrations_diff = _git_diff('HEAD', '--', '**/migrations/**')
    assert migrations_diff == '', migrations_diff

    for base in ('development', 'origin/development', 'main'):
        if _git_rev_exists(base):
            vs_base = _git_diff(base, '--', *_DENYLIST_PATHS)
            assert vs_base == '', vs_base
            overdue_vs_base = _git_diff(base, '--', 'apps/pdi/services/overdue.py')
            assert overdue_vs_base == '', overdue_vs_base
            migrations_vs_base = _git_diff(base, '--', '**/migrations/**')
            assert migrations_vs_base == '', migrations_vs_base
            break


# --- T018: digest / idempotência / PII / raw/ / teste de ouro (samples) ---

_STAGE_SCOPE_REJECT_TESTS = (
    'tests/test_stage_machine.py',
    'tests/test_scope.py',
    'tests/test_reject_stage_invariant.py',
)
_STAGE_TEST_PY = _REPO_ROOT / 'tests' / 'test_stage_machine.py'
_REJECT_TEST_PY = _REPO_ROOT / 'tests' / 'test_reject_stage_invariant.py'
_STAGE_ASSERT_MARKERS = (
    'assert advanced.etapa == Avaliacao.Etapa.APROVACAO_METAS',
    'assert avaliacao.etapa == Avaliacao.Etapa.APROVACAO_METAS',
    'assert result.etapa == Avaliacao.Etapa.FEEDBACK',
)
_REJECT_ASSERT_MARKERS = (
    'assert avaliacao.etapa == etapa_antes',
    'assert resultado.status == Meta.Status.REPROVADA',
    'advance_mock.assert_not_called()',
)
_T018_ALLOWLIST_PY = (
    'apps/pdi/services/legacy_import',
    'apps/pdi/management/commands/importar_pdi.py',
    'apps/accounts/services/legacy_import/parse_xlsx.py',
    'apps/accounts/services/legacy_import/dates.py',
    'apps/accounts/services/legacy_import/report.py',
)
_T018_DENY_IMPORT_TOKENS = (
    'apps.cycles.services.stage',
    'apps.cycles.services.cycle',
    'apps.goals.services.approval',
    'apps.accounts.services.scope',
    'calcular_aderencia',
    'rest_framework',
    'import openpyxl',
    'from openpyxl',
)
_T018_DENY_CALLS = (
    'advance_stage(',
    'open_cycle(',
    'close_cycle(',
    'get_visible_users(',
    'user_in_scope(',
    'mark_overdue_pdi_actions(',
    'calculate_pdi_progress(',
    'calcular_aderencia(',
)
_T018_PII = (
    *_T016_PII,
    _T016_DESC_ANA,
    _T016_DESC_BRUNO,
    _T016_TITULO_BRUNO,
    _T016_TITULO_GESTOR,
    _T016_TITULO_CARLA,
    'gestor.alpha@example.com',
    'bruno.costa@example.com',
    'carla.dias@example.com',
    'Nome Ambiguo',
    _T017_TITULO_ORFAO,
    _T017_TITULO_AMBIGUO,
    _T017_TITULO_ID_VS_NOME,
    'Objetivo completo que nao pode vazar no relatorio mascarado de PDI Fixture',
    'Situacao atual completa que nao pode vazar no relatorio mascarado Fixture',
)


def _t018_iter_allowlist_py() -> list[Path]:
    files: list[Path] = []
    for rel in _T018_ALLOWLIST_PY:
        path = _REPO_ROOT / rel
        if path.is_file():
            files.append(path)
            continue
        files.extend(sorted(path.rglob('*.py')))
    return files


def _t018_assert_report_sem_pii(text: str) -> None:
    """SC-008 / C8: amostra ≤ 5; zero título/objetivo/nome/e-mail completos."""
    for token in _T018_PII:
        assert token not in text, token
        assert token.lower() not in text.lower(), token
    sections = _amostra_items_by_section(text)
    assert sections
    for header, items in sections.items():
        assert len(items) <= _SAMPLE_MAX, header
        for item in items:
            for token in _T018_PII:
                assert token not in item, (header, token)


def _t018_parsed_rows_by_titulo() -> dict[str, object]:
    """Primeira linha do sample cujo título normalizado persiste (C6)."""
    _t016_assert_samples_only()
    by_titulo: dict[str, object] = {}
    for row in parse_pdi_xlsx(_PDI_MIN).rows:
        try:
            titulo = normalize_pdi_titulo(row.titulo)
        except ResolveConflict:
            continue
        if titulo in _T016_TITULOS_OK:
            by_titulo.setdefault(titulo, row)
    return by_titulo


def _t018_etapa_snapshot() -> dict[int, tuple[str, bool, int, str]]:
    return {
        av.pk: (av.etapa, av.concluida, av.ciclo_id, av.ciclo.status)
        for av in Avaliacao.objects.select_related('ciclo')
    }


def _t018_acao_keys() -> set[tuple[str, str, date]]:
    """Chaves naturais (digest PDI, descrição normalizada, prazo)."""
    keys: set[tuple[str, str, date]] = set()
    for pdi in PDI.objects.prefetch_related('acoes'):
        digest = pdi.solides_id or ''
        for acao in pdi.acoes.all():
            descricao, prazo = acao_natural_key(acao.descricao, acao.prazo)
            keys.add((digest, descricao, prazo))
    return keys


def _t018_pdi_snapshot() -> dict[int, tuple[str | None, str, str]]:
    return {
        pdi.pk: (pdi.solides_id, pdi.titulo, pdi.status)
        for pdi in PDI.objects.all()
    }


@pytest.mark.django_db
def test_t018_c6_digest_prefixo_hex_estavel_diferente_da_concatenacao():
    """SC-007 / C6: ``pdi_`` + 40 hex; len ≤ 50; ≠ Nome+Título; estável."""
    users = _t016_seed_world()
    rows = _t018_parsed_rows_by_titulo()
    assert set(rows) == set(_T016_TITULOS_OK)

    _t016_import_sample()

    for titulo, row in rows.items():
        pdi = PDI.objects.get(titulo=titulo)
        digest = pdi.solides_id
        assert digest is not None
        assert digest.startswith('pdi_')
        assert len(digest) == 44
        assert len(digest) <= 50
        hex_part = digest.removeprefix('pdi_')
        assert len(hex_part) == 40
        assert re.fullmatch(r'[0-9a-f]{40}', hex_part)
        nome = str(row.nome)
        claro = f'{nome}{titulo}'
        assert digest != claro
        assert nome not in digest
        assert titulo not in digest
        esperado = build_pdi_digest(row.nome, row.titulo, row.criado_em)
        assert digest == esperado
        assert users[nome].id == pdi.usuario_id

    report2 = _t016_import_sample()
    for titulo in _T016_TITULOS_OK:
        pdi = PDI.objects.get(titulo=titulo)
        row = rows[titulo]
        assert pdi.solides_id == build_pdi_digest(
            row.nome, row.titulo, row.criado_em
        )
    assert report2.pdis_criados == 0
    assert report2.pdis_inalterados == _T016_PDIS_CRIADOS
    assert PDI.objects.filter(titulo__in=_T016_TITULOS_OK).count() == (
        _T016_PDIS_CRIADOS
    )


@pytest.mark.django_db
def test_t018_c7_segunda_run_delta_0_chaves_naturais_titulo_status():
    """SC-005 / C7: 2ª run delta 0; título/status inalterados; atualizados = 0."""
    _t016_seed_world()
    report1 = _t016_import_sample()
    assert report1.pdis_criados == _T016_PDIS_CRIADOS
    assert report1.acoes_criadas == _T016_ACOES_CRIADAS
    assert report1.pdis_atualizados == 0
    assert report1.acoes_atualizadas == 0

    pdis_antes = _t018_pdi_snapshot()
    keys_antes = _t018_acao_keys()
    acoes_antes = {
        acao.pk: (acao.descricao, acao.prazo, acao.status, acao.pdi_id)
        for acao in AcaoPDI.objects.all()
    }
    n_pdi = PDI.objects.count()
    n_acao = AcaoPDI.objects.count()
    assert n_pdi == _T016_PDIS_CRIADOS
    assert n_acao == _T016_ACOES_CRIADAS
    assert len(keys_antes) == _T016_ACOES_CRIADAS

    report2 = _t016_import_sample()

    assert report2.pdis_criados == 0
    assert report2.acoes_criadas == 0
    assert report2.pdis_inalterados == _T016_PDIS_CRIADOS
    assert report2.acoes_inalteradas == _T016_ACOES_CRIADAS
    assert report2.pdis_atualizados == 0
    assert report2.acoes_atualizadas == 0
    assert PDI.objects.count() == n_pdi
    assert AcaoPDI.objects.count() == n_acao
    assert _t018_pdi_snapshot() == pdis_antes
    assert _t018_acao_keys() == keys_antes
    acoes_depois = {
        acao.pk: (acao.descricao, acao.prazo, acao.status, acao.pdi_id)
        for acao in AcaoPDI.objects.all()
    }
    assert acoes_depois == acoes_antes
    tipos = {c.label for c in report2.conflitos}
    assert 'acao_chave_divergente' not in tipos


@pytest.mark.django_db
def test_t020_chave_acao_divergente_sem_segunda_acao_sem_delete():
    """T020 / SC-005: chave divergente → conflito; zero 2ª ação; zero rewrite."""
    _t016_seed_world()
    report1 = _t016_import_sample()
    assert report1.pdis_atualizados == 0
    assert report1.acoes_atualizadas == 0

    pdi = PDI.objects.get(titulo=_T016_TITULO_ANA)
    acao = pdi.acoes.get()
    pk = acao.pk
    descricao_mutada = 'Descricao divergente fixture T020'
    prazo_original = acao.prazo
    titulo = pdi.titulo
    status = pdi.status
    digest = pdi.solides_id
    n_pdi = PDI.objects.count()
    n_acao = AcaoPDI.objects.count()
    AcaoPDI.objects.filter(pk=pk).update(descricao=descricao_mutada)

    report2 = _t016_import_sample()

    tipos = {c.label for c in report2.conflitos}
    assert 'acao_chave_divergente' in tipos
    assert report2.pdis_criados == 0
    assert report2.acoes_criadas == 0
    assert report2.pdis_atualizados == 0
    assert report2.acoes_atualizadas == 0
    assert report2.pdis_inalterados == _T016_PDIS_CRIADOS - 1
    assert report2.acoes_inalteradas == _T016_ACOES_CRIADAS - 1
    assert PDI.objects.count() == n_pdi
    assert AcaoPDI.objects.count() == n_acao
    acao.refresh_from_db()
    pdi.refresh_from_db()
    assert acao.pk == pk
    assert acao.descricao == descricao_mutada
    assert acao.prazo == prazo_original
    assert pdi.titulo == titulo
    assert pdi.status == status
    assert pdi.solides_id == digest
    assert pdi.acoes.count() == 1


@pytest.mark.django_db
def test_t020_pdi_sem_acao_nao_cria_segunda_nem_atualiza():
    """T020: digest existente sem ação → conflito; não recria ação nem apaga PDI."""
    _t016_seed_world()
    _t016_import_sample()
    pdi = PDI.objects.get(titulo=_T016_TITULO_ANA)
    pdi.acoes.all().delete()
    n_pdi = PDI.objects.count()
    n_acao = AcaoPDI.objects.count()
    assert n_acao == _T016_ACOES_CRIADAS - 1

    report = _t016_import_sample()

    tipos = {c.label for c in report.conflitos}
    assert 'acao_chave_divergente' in tipos
    assert report.pdis_criados == 0
    assert report.acoes_criadas == 0
    assert report.pdis_atualizados == 0
    assert report.acoes_atualizadas == 0
    assert PDI.objects.count() == n_pdi
    assert AcaoPDI.objects.count() == n_acao
    assert PDI.objects.filter(pk=pdi.pk).exists()
    assert pdi.acoes.count() == 0


def test_t020_importer_nao_usa_atualizado_nem_delete():
    """T020: política conservadora — sem update silencioso / delete no importer."""
    src = (
        _REPO_ROOT / 'apps' / 'pdi' / 'services' / 'legacy_import' / 'importer.py'
    ).read_text(encoding='utf-8')
    assert 'record_pdi_atualizado(' not in src
    assert 'record_acao_atualizada(' not in src
    assert '.delete(' not in src
    assert 'bulk_create(' not in src
    assert 'objects.update(' not in src


@pytest.mark.django_db
def test_t018_c8_relatorio_mascarado_stdout_igual_report_file(tmp_path: Path):
    """SC-008 / C8: amostra ≤ 5; sem PII completa; stdout == ``--report-file``."""
    users = _t016_seed_world()
    stdout = StringIO()
    report_path = tmp_path / 'relatorio-pdi-legado.txt'
    assert 'raw' not in report_path.parts

    result = call_command(
        'importar_pdi',
        pdi=str(_PDI_MIN),
        report_file=str(report_path),
        stdout=stdout,
    )

    text = stdout.getvalue()
    file_text = report_path.read_text(encoding='utf-8')
    assert result in (0, None)
    assert file_text == text
    assert text.startswith('=== Importação PDI/ações legado Sólides ===')
    assert 'modo: persist' in text
    assert f'pdis_criados: {_T016_PDIS_CRIADOS}' in text
    assert f'acoes_criadas: {_T016_ACOES_CRIADAS}' in text
    assert f'orfaos_usuario: {_T016_ORFAOS_USUARIO}' in text
    assert f'conflitos: {_T016_CONFLITOS}' in text
    assert '--- Amostra (mascarada, max 5 por seção) ---' in text
    _t018_assert_report_sem_pii(text)

    pdi_ana = PDI.objects.get(titulo=_T016_TITULO_ANA, usuario=users['Ana Silva'])
    assert pdi_ana.solides_id is not None
    assert pdi_ana.solides_id not in text
    assert mask_solides_id(pdi_ana.solides_id) in text
    assert pdi_ana.titulo == _T016_TITULO_ANA
    assert pdi_ana.acoes.get().descricao == _T016_DESC_ANA

    sections = _amostra_items_by_section(text)
    for header in (
        'pdis_criados:',
        'acoes_criadas:',
        'orfaos_usuario:',
        'orfaos_solicitacao:',
        'conflitos:',
    ):
        assert header in sections
        assert len(sections[header]) <= _SAMPLE_MAX, header
    assert len(sections['conflitos:']) == _SAMPLE_MAX
    assert len(sections['orfaos_usuario:']) == _T016_ORFAOS_USUARIO


def test_t018_c9_suite_nao_referencia_raw():
    """SC-007 / C9: suíte e allowlist não apontam para backups PII ``raw/``."""
    _t016_assert_samples_only()
    suite = Path(__file__).read_text(encoding='utf-8')
    assert _RAW_PII_DIR not in suite
    assert 'pdi_min.xlsx' in suite
    for rel in _t018_iter_allowlist_py():
        blob = rel.read_text(encoding='utf-8')
        assert _RAW_PII_DIR not in blob, rel
        assert 'legado-solides/raw' not in blob, rel
        assert 'raw' not in rel.parts
    resolved = _PDI_MIN.resolve()
    assert 'raw' not in resolved.parts
    assert _RAW_PII_DIR not in str(resolved)
    tests_dir = _REPO_ROOT / 'tests'
    this_file = Path(__file__).resolve()
    for path in tests_dir.glob('test_import_pdi*.py'):
        blob = path.read_text(encoding='utf-8')
        assert _RAW_PII_DIR not in blob, path
        if path.resolve() == this_file:
            continue
        assert 'legado-solides/raw' not in blob, path


@pytest.mark.django_db
def test_t018_c10_import_nao_muta_etapa_escopo(colaborador, lider, avaliacao):
    """SC-010 / C10: import não altera etapa, ciclo nem quem vê quem."""
    _t016_seed_world()
    etapa_antes = avaliacao.etapa
    concluida_antes = avaliacao.concluida
    before_av = _t018_etapa_snapshot()
    before_ciclo = {ciclo.pk: ciclo.status for ciclo in Ciclo.objects.all()}
    visivel_lider = set(get_visible_users(lider).values_list('pk', flat=True))
    visivel_colab = set(
        get_visible_users(colaborador).values_list('pk', flat=True)
    )
    n_ciclo = Ciclo.objects.count()
    n_av = Avaliacao.objects.count()

    with (
        patch('apps.cycles.services.stage.advance_stage') as spy_stage,
        patch('apps.cycles.services.cycle.open_cycle') as spy_open,
        patch('apps.cycles.services.cycle.close_cycle') as spy_close,
    ):
        report = _t016_import_sample()

    spy_stage.assert_not_called()
    spy_open.assert_not_called()
    spy_close.assert_not_called()
    assert report.pdis_criados == _T016_PDIS_CRIADOS

    avaliacao.refresh_from_db()
    assert avaliacao.etapa == etapa_antes
    assert avaliacao.concluida == concluida_antes
    assert _t018_etapa_snapshot() == before_av
    assert {ciclo.pk: ciclo.status for ciclo in Ciclo.objects.all()} == (
        before_ciclo
    )
    assert Ciclo.objects.count() == n_ciclo
    assert Avaliacao.objects.count() == n_av
    assert set(get_visible_users(lider).values_list('pk', flat=True)) == (
        visivel_lider
    )
    assert set(get_visible_users(colaborador).values_list('pk', flat=True)) == (
        visivel_colab
    )
    assert user_in_scope(lider, colaborador.pk) is True

    importer_src = _IMPORTER_PY.read_text(encoding='utf-8')
    command_src = _COMMAND_PY.read_text(encoding='utf-8')
    assert '.etapa =' not in importer_src
    assert '.concluida =' not in importer_src
    assert '.etapa =' not in command_src
    assert '.concluida =' not in command_src
    for src in (importer_src, command_src):
        for token in _T018_DENY_IMPORT_TOKENS:
            assert token not in src, token
        for call in _T018_DENY_CALLS:
            assert call not in src, call


@pytest.mark.skipif(
    shutil.which('git') is None,
    reason='git ausente no PATH (ex. container web sem git)',
)
def test_t018_ouro_git_diff_denylist_e_asserts_stage_scope_reject():
    """SC-010: denylist vazia; asserts de stage/scope/reject intactos."""
    stage_src = _STAGE_TEST_PY.read_text(encoding='utf-8')
    for marker in _STAGE_ASSERT_MARKERS:
        assert marker in stage_src, marker
    reject_src = _REJECT_TEST_PY.read_text(encoding='utf-8')
    for marker in _REJECT_ASSERT_MARKERS:
        assert marker in reject_src, marker
    scope_src = _SCOPE_TEST_PY.read_text(encoding='utf-8')
    for marker in _SCOPE_ASSERT_MARKERS:
        assert marker in scope_src, marker

    working_tree = _git_diff('HEAD', '--', *_DENYLIST_PATHS)
    assert working_tree == '', working_tree
    stage_scope = _git_diff('HEAD', '--', *_STAGE_SCOPE_REJECT_TESTS)
    assert stage_scope == '', stage_scope
    migrations_diff = _git_diff('HEAD', '--', '**/migrations/**')
    assert migrations_diff == '', migrations_diff

    for base in ('development', 'origin/development', 'main'):
        if _git_rev_exists(base):
            vs_base = _git_diff(base, '--', *_DENYLIST_PATHS)
            assert vs_base == '', vs_base
            vs_tests = _git_diff(base, '--', *_STAGE_SCOPE_REJECT_TESTS)
            assert vs_tests == '', vs_tests
            migrations_vs_base = _git_diff(base, '--', '**/migrations/**')
            assert migrations_vs_base == '', migrations_vs_base
            break

