"""T005/T006: datas reusadas e relatório mascarado da importação PDI legado.

T005: ``parse_legacy_date`` / ``parse_legacy_datetime`` cobrem
``Data de Entrega`` e ``Criado em`` (serial Excel + ISO). Sem openpyxl
em ``dates.py``. **Proibido** ``raw/``.

T006: ``format_pdi_report`` (seções estáveis, máx. 5, sem nome/e-mail/
título/objetivo/situação completos). Sem persistência. **Proibido** ``raw/``.
"""

from __future__ import annotations

from datetime import date, datetime, timezone as dt_timezone
from pathlib import Path

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
from apps.pdi.services.legacy_import import format_pdi_report as _reexport

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
