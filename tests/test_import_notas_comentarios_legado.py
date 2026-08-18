"""T006+: importação notas/comentários legado Sólides — relatório mascarado.

T006: ``format_notas_comentarios_report`` (seções estáveis, máx. 5,
sem comentário/nome/e-mail). Sem persistência. **Proibido** ``raw/``.

T018–T023 estendem esta suíte (dry-run, IDs, conflitos, comentários).
"""

from __future__ import annotations

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
from apps.reviews.services.legacy_import import format_notas_comentarios_report as _reexport

_SAMPLE_MAX = 5
_EMAIL = 'ana.silva@example.com'
_NOME = 'Ana Silva'
_COMENTARIO = 'Texto completo de feedback que NUNCA pode ir ao relatório.'
_CPF = '000.000.000-00'
_AVALIACAO_ID = 'SOLIDES-AV1001'
_COMPETENCIA_ID = 'HAB12'
_AUTOR_ID = 'USR88'


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
