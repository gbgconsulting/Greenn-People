"""T024 [US4]: backfill operacional de ``data_entrada`` (dry-run / persist).

Contrato: ``specs/015-cycle-admission-cutoff/contracts/admission-backfill-command-contract.md``
+ SC-007 / FR-016 / FR-017.

Cobre:
- dry-run → 0 writes; totais coerentes
- persist → só preenche ``data_entrada`` NULL; datas já preenchidas intactas
- 2ª execução → delta preenchimento = 0 (idempotência)
- spies → ``open_cycle`` / ``close_cycle`` / ``ensure_avaliacao_for_user`` /
  ``advance_stage`` **não** chamados
- relatório → amostra mascarada (``mask_email``; e-mail completo ausente)
- demais campos (nome/email/área/cargo/gestor/``is_active``) intactos
- residual sem data no Excel → permanece NULL
"""

from __future__ import annotations

from datetime import date
from io import StringIO
from pathlib import Path
from unittest.mock import patch

import pytest
from django.core.management import call_command
from django.utils import timezone
from openpyxl import Workbook

from apps.accounts.models import CustomUser
from apps.accounts.services.admission_backfill import backfill_data_entrada
from apps.accounts.services.legacy_import.report import mask_email
from apps.cycles.models import Ciclo
from apps.reviews.models import Avaliacao

DEFAULT_PASSWORD = 'TestPass123!'
REPO_ROOT = Path(__file__).resolve().parents[1]

# Datas canônicas do cenário (ISO + serial Excel equivalentes).
_ADMISSAO_VAZIA = date(2023, 3, 15)
_ADMISSAO_SERIAL = (_ADMISSAO_VAZIA - date(1899, 12, 30)).days  # 45000
_ADMISSAO_JA_PREENCHIDA = date(2021, 6, 1)
_ADMISSAO_EXCEL_DIVERGENTE = date(2019, 1, 1)

_EMAIL_VAZIA = 'entrada.vazia@test.greenn.com.br'
_EMAIL_PREENCHIDA = 'entrada.ok@test.greenn.com.br'
_EMAIL_SEM_DATA_XLSX = 'sem.data.xlsx@test.greenn.com.br'
_EMAIL_ORFAO = 'orfa.inexistente@test.greenn.com.br'
_EMAIL_SOLIDES = 'so.solides@test.greenn.com.br'

_SOLIDES_ID = '9001'

_HEADERS = (
    'Nome',
    'E-mail empresarial',
    'Identificador',
    'Data admissão',
)


def _write_admission_xlsx(path: Path, rows: list[list[object]]) -> Path:
    """Gera OOXML mínimo com coluna “Data admissão” (samples; nunca ``raw/``)."""
    assert 'raw' not in path.parts
    wb = Workbook()
    ws = wb.active
    assert ws is not None
    ws.title = 'sheet1'
    ws.append(list(_HEADERS))
    for row in rows:
        ws.append(row)
    wb.save(path)
    return path


def _fixture_xlsx(tmp_path: Path) -> Path:
    """Backup sintético: vazia (serial), já preenchida (ISO), sem data, órfão."""
    return _write_admission_xlsx(
        tmp_path / 'backup_colaboradores_admission_min.xlsx',
        [
            ['Entrada Vazia', _EMAIL_VAZIA, '', _ADMISSAO_SERIAL],
            [
                'Entrada Ok',
                _EMAIL_PREENCHIDA,
                '',
                _ADMISSAO_EXCEL_DIVERGENTE.isoformat(),
            ],
            ['Sem Data Xlsx', _EMAIL_SEM_DATA_XLSX, '', None],
            ['Órfão Backup', _EMAIL_ORFAO, '', '2022-01-10'],
            ['Só Solides', '', _SOLIDES_ID, '2023-08-20'],
        ],
    )


def _make_user(
    *,
    email: str,
    nome: str,
    lider,
    area,
    cargo_colab,
    data_entrada: date | None,
    solides_id: str | None = None,
    is_active: bool = True,
) -> CustomUser:
    return CustomUser.objects.create_user(
        email=email,
        password=DEFAULT_PASSWORD,
        nome=nome,
        cargo=cargo_colab,
        area=area,
        line_manager=lider,
        data_entrada=data_entrada,
        solides_id=solides_id,
        is_active=is_active,
        email_confirmado_em=timezone.now(),
    )


def _identity_snapshot(user: CustomUser) -> tuple:
    """Campos que o backfill MUST NOT mutar (FR-017)."""
    return (
        user.nome,
        user.email,
        user.area_id,
        user.cargo_id,
        user.line_manager_id,
        user.is_active,
        user.solides_id,
    )


def _seed_world(lider, area, cargo_colab) -> dict[str, CustomUser]:
    """Usuários de cenário alinhados ao xlsx sintético."""
    vazia = _make_user(
        email=_EMAIL_VAZIA,
        nome='Entrada Vazia',
        lider=lider,
        area=area,
        cargo_colab=cargo_colab,
        data_entrada=None,
    )
    preenchida = _make_user(
        email=_EMAIL_PREENCHIDA,
        nome='Entrada Ok',
        lider=lider,
        area=area,
        cargo_colab=cargo_colab,
        data_entrada=_ADMISSAO_JA_PREENCHIDA,
    )
    sem_xlsx = _make_user(
        email=_EMAIL_SEM_DATA_XLSX,
        nome='Sem Data Xlsx',
        lider=lider,
        area=area,
        cargo_colab=cargo_colab,
        data_entrada=None,
    )
    solides = _make_user(
        email=_EMAIL_SOLIDES,
        nome='Só Solides',
        lider=lider,
        area=area,
        cargo_colab=cargo_colab,
        data_entrada=None,
        solides_id=_SOLIDES_ID,
    )
    return {
        'vazia': vazia,
        'preenchida': preenchida,
        'sem_xlsx': sem_xlsx,
        'solides': solides,
    }


def _report_get(report, key: str):
    """Acesso uniforme a TypedDict / dataclass / objeto."""
    if isinstance(report, dict):
        return report[key]
    return getattr(report, key)


def _format_report_text(report) -> str:
    """Texto UTF-8 do relatório (T028: ``format_admission_backfill_report``)."""
    from apps.accounts.services.legacy_import.report import (
        format_admission_backfill_report,
    )

    return format_admission_backfill_report(report)


# ---------------------------------------------------------------------------
# Dry-run
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_dry_run_zero_writes_totais_projetados(tmp_path, lider, area, cargo_colab):
    """SC-007: dry-run → 0 writes; totais projetados coerentes."""
    users = _seed_world(lider, area, cargo_colab)
    path = _fixture_xlsx(tmp_path)

    before_entrada = {
        u.pk: u.data_entrada for u in CustomUser.objects.all()
    }
    before_count = CustomUser.objects.count()
    before_av = Avaliacao.objects.count()

    report = backfill_data_entrada(path, dry_run=True)

    assert _report_get(report, 'dry_run') is True
    assert _report_get(report, 'lidos') >= 4
    # vazia (email) + solides (id) projetados a preencher; preenchida = skip
    assert _report_get(report, 'preenchidos') == 2
    assert _report_get(report, 'ja_preenchidos') == 1
    assert _report_get(report, 'orfaos') >= 1

    assert CustomUser.objects.count() == before_count
    assert Avaliacao.objects.count() == before_av
    for user in CustomUser.objects.all():
        assert user.data_entrada == before_entrada[user.pk]

    users['vazia'].refresh_from_db()
    assert users['vazia'].data_entrada is None


@pytest.mark.django_db
def test_dry_run_via_comando_zero_writes(tmp_path, lider, area, cargo_colab):
    """CLI ``--dry-run``: exit 0 e zero mutações em ``data_entrada``."""
    _seed_world(lider, area, cargo_colab)
    path = _fixture_xlsx(tmp_path)
    before = {
        u.pk: u.data_entrada for u in CustomUser.objects.all()
    }
    stdout = StringIO()

    result = call_command(
        'backfill_data_entrada',
        colaboradores=str(path),
        dry_run=True,
        stdout=stdout,
    )

    assert result in (0, None)
    for user in CustomUser.objects.all():
        assert user.data_entrada == before[user.pk]


# ---------------------------------------------------------------------------
# Persist + campos intactos + residual NULL
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_persist_preenche_so_null_demais_campos_intactos(
    tmp_path, lider, area, cargo_colab
):
    """FR-017 / SC-007: só NULL; nome/email/área/cargo/gestor/ativo intactos."""
    users = _seed_world(lider, area, cargo_colab)
    path = _fixture_xlsx(tmp_path)

    snap_vazia = _identity_snapshot(users['vazia'])
    snap_preenchida = _identity_snapshot(users['preenchida'])
    snap_sem = _identity_snapshot(users['sem_xlsx'])
    snap_solides = _identity_snapshot(users['solides'])
    entrada_preenchida = users['preenchida'].data_entrada

    report = backfill_data_entrada(path, dry_run=False)

    assert _report_get(report, 'dry_run') is False
    assert _report_get(report, 'preenchidos') == 2
    assert _report_get(report, 'ja_preenchidos') == 1

    users['vazia'].refresh_from_db()
    users['preenchida'].refresh_from_db()
    users['sem_xlsx'].refresh_from_db()
    users['solides'].refresh_from_db()

    assert users['vazia'].data_entrada == _ADMISSAO_VAZIA
    assert users['solides'].data_entrada == date(2023, 8, 20)
    assert users['preenchida'].data_entrada == entrada_preenchida
    assert users['preenchida'].data_entrada != _ADMISSAO_EXCEL_DIVERGENTE
    # Sem data no Excel / só auto-cadastro residual → permanece NULL
    assert users['sem_xlsx'].data_entrada is None

    assert _identity_snapshot(users['vazia']) == snap_vazia
    assert _identity_snapshot(users['preenchida']) == snap_preenchida
    assert _identity_snapshot(users['sem_xlsx']) == snap_sem
    assert _identity_snapshot(users['solides']) == snap_solides

    assert not CustomUser.objects.filter(email__iexact=_EMAIL_ORFAO).exists()


@pytest.mark.django_db
def test_persist_nao_inventa_user_orfao(tmp_path, lider, area, cargo_colab):
    """Match órfão → relatório; NÃO cria ``User``."""
    _seed_world(lider, area, cargo_colab)
    path = _fixture_xlsx(tmp_path)
    before = CustomUser.objects.count()

    report = backfill_data_entrada(path)

    assert _report_get(report, 'orfaos') >= 1
    assert CustomUser.objects.count() == before
    assert not CustomUser.objects.filter(email__iexact=_EMAIL_ORFAO).exists()


# ---------------------------------------------------------------------------
# Idempotência
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_segunda_execucao_delta_preenchimento_zero(
    tmp_path, lider, area, cargo_colab
):
    """SC-007: 2ª run → ``preenchidos`` delta = 0; datas intactas."""
    users = _seed_world(lider, area, cargo_colab)
    path = _fixture_xlsx(tmp_path)

    first = backfill_data_entrada(path)
    assert _report_get(first, 'preenchidos') == 2

    after_first = {
        u.pk: u.data_entrada for u in CustomUser.objects.all()
    }

    second = backfill_data_entrada(path)
    assert _report_get(second, 'preenchidos') == 0
    assert _report_get(second, 'ja_preenchidos') >= 2

    for user in CustomUser.objects.all():
        assert user.data_entrada == after_first[user.pk]

    users['vazia'].refresh_from_db()
    assert users['vazia'].data_entrada == _ADMISSAO_VAZIA


# ---------------------------------------------------------------------------
# Denylist spies (MUST NOT chamar open/close/ensure/advance)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_backfill_nao_chama_open_close_ensure_advance(
    tmp_path, lider, area, cargo_colab
):
    """Contrato denylist: backfill não abre/fecha ciclo nem matricula/avança."""
    _seed_world(lider, area, cargo_colab)
    path = _fixture_xlsx(tmp_path)

    n_av_before = Avaliacao.objects.count()
    ciclo_status_before = {
        c.pk: c.status for c in Ciclo.objects.all()
    }

    with (
        patch('apps.cycles.services.cycle.open_cycle') as spy_open,
        patch('apps.cycles.services.cycle.close_cycle') as spy_close,
        patch(
            'apps.reviews.services.enrollment.ensure_avaliacao_for_user'
        ) as spy_ensure,
        patch('apps.cycles.services.stage.advance_stage') as spy_advance,
    ):
        report = backfill_data_entrada(path)

    spy_open.assert_not_called()
    spy_close.assert_not_called()
    spy_ensure.assert_not_called()
    spy_advance.assert_not_called()

    assert _report_get(report, 'preenchidos') == 2
    assert Avaliacao.objects.count() == n_av_before
    assert {
        c.pk: c.status for c in Ciclo.objects.all()
    } == ciclo_status_before

    importer_src = (
        REPO_ROOT
        / 'apps/accounts/services/admission_backfill/importer.py'
    ).read_text(encoding='utf-8')
    command_src = (
        REPO_ROOT
        / 'apps/accounts/management/commands/backfill_data_entrada.py'
    ).read_text(encoding='utf-8')
    for src in (importer_src, command_src):
        for token in (
            'open_cycle',
            'close_cycle',
            'ensure_avaliacao_for_user',
            'advance_stage',
        ):
            assert token not in src, token


# ---------------------------------------------------------------------------
# Relatório — amostra mascarada
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_relatorio_amostra_mascarada(tmp_path, lider, area, cargo_colab):
    """Contrato relatório: amostra via ``mask_email``; e-mail completo ausente."""
    _seed_world(lider, area, cargo_colab)
    path = _fixture_xlsx(tmp_path)

    report = backfill_data_entrada(path, dry_run=True)
    text = _format_report_text(report)

    assert _EMAIL_VAZIA not in text
    assert _EMAIL_PREENCHIDA not in text
    assert _EMAIL_ORFAO not in text
    assert _EMAIL_VAZIA.lower() not in text.lower()

    masked = mask_email(_EMAIL_VAZIA)
    assert masked == 'e***@test.greenn.com.br'
    assert masked in text

    # Totais presentes no texto (contrato §Relatório)
    lower = text.lower()
    assert 'lidos' in lower or 'preenchidos' in lower
    assert 'dry' in lower


@pytest.mark.django_db
def test_comando_report_file_amostra_mascarada(
    tmp_path, lider, area, cargo_colab
):
    """``--report-file`` grava o mesmo UTF-8 mascarado (sem PII completa)."""
    _seed_world(lider, area, cargo_colab)
    path = _fixture_xlsx(tmp_path)
    report_path = tmp_path / 'backfill_report.txt'
    stdout = StringIO()

    result = call_command(
        'backfill_data_entrada',
        colaboradores=str(path),
        dry_run=True,
        report_file=str(report_path),
        stdout=stdout,
    )

    assert result in (0, None)
    assert report_path.is_file()
    file_text = report_path.read_text(encoding='utf-8')
    out_text = stdout.getvalue()

    for blob in (file_text, out_text):
        assert _EMAIL_VAZIA not in blob
        assert mask_email(_EMAIL_VAZIA) in blob
