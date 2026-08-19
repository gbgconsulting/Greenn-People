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
from django.utils import timezone
from openpyxl import Workbook

from apps.accounts.models import CustomUser
from apps.accounts.services.legacy_import.dates import (
    parse_legacy_date,
    parse_legacy_datetime,
)
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
from apps.pdi.services.legacy_import import format_pdi_report as _reexport
from apps.pdi.services.legacy_import import import_pdi
from apps.pdi.services.legacy_import.resolve import (
    ResolveConflict,
    build_pdi_digest,
    resolve_usuario,
)
from apps.reviews.models import Avaliacao

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
