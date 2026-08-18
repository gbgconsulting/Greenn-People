"""Orquestração da importação de notas/comentários legado Sólides.

Superfície pública: ``import_notas_comentarios`` (reexportada por ``__init__``).
T009: fase Notas — agrupa por ``(avaliacao_canônica, competencia)`` antes
do persist; upsert ``AvaliacaoCompetencia``; snapshots write-once;
``calcular_nota_final_*`` após o lote de cada avaliação tocada.
T013: fase Comentários (stub). T021: ``--dry-run`` + atomicidade das
duas fases (dry-run já usa ``set_rollback`` no padrão 010/011).

Ordem normativa (``contracts/import-command-contract.md``):
parse notas → parse comentários → mapa ``--avaliacoes`` (011, só memória) →
fase Notas → ``calcular_nota_final_*`` → fase Comentários, na mesma
``transaction.atomic()``.

Denylist intacta — **nunca** chama ``open_cycle`` / ``close_cycle`` /
``advance_stage`` / approval / ``create_competency_lines`` / adherence;
**nunca** edita ``evaluation.py``; **nunca** atribui ``etapa`` / ``concluida``.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from django.core.exceptions import ValidationError
from django.db import transaction

from apps.accounts.services.legacy_import.parse_xlsx import (
    HabilidadeRow,
    LegacyParseError,
    NotaRow,
    parse_comentarios_xlsx,
    parse_habilidades_xlsx,
    parse_notas_xlsx,
    validate_source_paths,
)
from apps.accounts.services.legacy_import.report import (
    ImportReport,
    record_conflito,
    record_conflito_ciclo_aberto,
    record_conflito_lider_divergente,
    record_habilidade_extra_criada,
    record_id_colapsado_resolvido,
    record_nota_atualizada,
    record_nota_criada,
    record_nota_inalterada,
    record_orfao_avaliacao,
    record_orfao_competencia,
)
from apps.reviews.exceptions import CalculationError
from apps.reviews.models import Avaliacao, AvaliacaoCompetencia
from apps.reviews.services.evaluation import (
    calcular_nota_final_autoavaliacao,
    calcular_nota_final_lider,
)
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

_NOTA_QUANT = Decimal('0.01')


class LegacySchemaError(Exception):
    """Pré-condição de schema ausente (003/010/011) — exit 1, zero writes.

    Esta fatia **não** gera migration. Falha de schema (ex. ``solides_id``
    ausente) não entra no ``atomic`` e não deixa escrita parcial.
    """


class LegacyPersistError(Exception):
    """Erro fatal durante persistência — ``atomic`` faz rollback; exit 1.

    Conflitos/órfãos não-fatais NÃO usam esta classe: vão para o relatório
    e exit ``0``.
    """


class _NotaParseError(Exception):
    """Nota ausente / não-numérica — conflito ``nota_invalida`` (R8)."""


@dataclass
class _NotaGroup:
    """Linhas de um par ``(avaliacao canônica, habilidade)`` antes do persist."""

    avaliacao: Avaliacao
    habilidade_id: str
    rows: list[NotaRow] = field(default_factory=list)


def import_notas_comentarios(
    notas_path: str | Path,
    comentarios_path: str | Path,
    avaliacoes_path: str | Path,
    *,
    habilidades_path: str | Path | None = None,
    dry_run: bool = False,
) -> ImportReport:
    """Orquestra parse → mapa → notas → fórmula → comentários (ou dry-run).

    Assinatura alinhada a ``contracts/import-command-contract.md``.

    ``--avaliacoes`` reconstrói o mapa de IDs colapsados em memória
    (IMPORTAR ``aggregate_avaliacao_headers``; **zero** upsert de cabeçalho).
    ``--habilidades`` é opcional (extras só como FK de nota, R11).

    T009: fase Notas + ``calcular_nota_final_*``. T013: fase Comentários.
    T021: dry-run consolidado (aqui: ``set_rollback``).
    """
    notas_file, comentarios_file, avaliacoes_file, hab_file = (
        _validate_required_paths(
            notas_path,
            comentarios_path,
            avaliacoes_path,
            habilidades_path,
        )
    )

    parsed_notas = parse_notas_xlsx(notas_file)
    parsed_comentarios = parse_comentarios_xlsx(comentarios_file)
    mapa = build_collapsed_id_map(avaliacoes_file)

    habilidades_by_id: dict[str, HabilidadeRow] = {}
    habilidades_file = ''
    if hab_file is not None:
        parsed_hab = parse_habilidades_xlsx(hab_file)
        habilidades_file = parsed_hab.path
        for row in parsed_hab.rows:
            habilidades_by_id.setdefault(row.identificador, row)

    report = ImportReport(
        modo='dry-run' if dry_run else 'persist',
        notas_file=parsed_notas.path,
        comentarios_file=parsed_comentarios.path,
        avaliacoes_file=str(avaliacoes_file),
        habilidades_file=habilidades_file,
    )

    with transaction.atomic():
        try:
            _persist_fase_notas(
                parsed_notas.rows,
                mapa,
                habilidades_by_id,
                report,
            )
            _persist_fase_comentarios(parsed_comentarios.rows, mapa, report)
        except LegacyPersistError:
            raise
        except Exception as exc:
            raise LegacyPersistError(str(exc)) from exc
        finally:
            if dry_run:
                transaction.set_rollback(True)

    return report


def _validate_required_paths(
    notas_path: str | Path,
    comentarios_path: str | Path,
    avaliacoes_path: str | Path,
    habilidades_path: str | Path | None,
) -> tuple[Path, Path, Path, Path | None]:
    """Paths obrigatórios existem e são arquivos; habilidades opcional."""
    if not str(notas_path).strip():
        raise LegacyParseError('Arquivo de notas é obrigatório')
    if not str(comentarios_path).strip():
        raise LegacyParseError('Arquivo de comentários é obrigatório')
    if not str(avaliacoes_path).strip():
        raise LegacyParseError('Arquivo de avaliações é obrigatório')

    notas_file, _ = validate_source_paths(notas_path)
    comentarios_file, _ = validate_source_paths(comentarios_path)
    avaliacoes_file, _ = validate_source_paths(avaliacoes_path)

    hab_file: Path | None = None
    if habilidades_path is not None and str(habilidades_path).strip():
        hab_file, _ = validate_source_paths(habilidades_path)
    return notas_file, comentarios_file, avaliacoes_file, hab_file


def _persist_fase_notas(
    rows: Sequence[NotaRow],
    mapa: Mapping[str, str],
    habilidades_by_id: Mapping[str, HabilidadeRow],
    report: ImportReport,
) -> None:
    """Fase Notas (T009 / R4–R9): agrupa → upsert → fórmula.

    **PROIBIDO** ``create_competency_lines``. **PROIBIDO** atribuir
    ``etapa`` / ``concluida``. **PROIBIDO** inventar ``Avaliacao``.
    """
    groups = _group_nota_rows(rows, mapa, report)
    touched: dict[int, Avaliacao] = {}
    for group in groups:
        saved = _upsert_nota_group(group, habilidades_by_id, report)
        if saved:
            touched[group.avaliacao.pk] = group.avaliacao

    for avaliacao in touched.values():
        _calcular_notas_finais(avaliacao, report)


def _persist_fase_comentarios(
    rows: Sequence[Any],
    mapa: Mapping[str, str],
    report: ImportReport,
) -> None:
    """Fase Comentários — corpo em T013. T009: no-op (não aborta o atomic)."""
    _ = (rows, mapa, report)


def _group_nota_rows(
    rows: Sequence[NotaRow],
    mapa: Mapping[str, str],
    report: ImportReport,
) -> list[_NotaGroup]:
    """Resolve avaliação e agrupa por ``(avaliacao.pk, habilidade)``.

    Órfãos / ciclo aberto não entram no persist. IDs colapsados alimentam
    ``ids_colapsados_resolvidos`` uma vez por par colapsado→canônico.
    """
    grouped: dict[tuple[int, str], _NotaGroup] = {}
    seen_orfao: set[str] = set()
    seen_aberto: set[int] = set()
    seen_collapsed: set[tuple[str, str]] = set()
    seen_hab_vazia = False
    av_cache: dict[str, Any] = {}

    for row in rows:
        sid = row.identificador_avaliacao
        if sid not in av_cache:
            av_cache[sid] = resolve_avaliacao(sid, mapa)
        resolved = av_cache[sid]
        avaliacao = resolved.avaliacao
        if avaliacao is None:
            if sid not in seen_orfao:
                seen_orfao.add(sid)
                record_orfao_avaliacao(report, id_legado=sid)
            continue

        if is_ciclo_aberto(avaliacao):
            if avaliacao.pk not in seen_aberto:
                seen_aberto.add(avaliacao.pk)
                record_conflito_ciclo_aberto(
                    report,
                    avaliacao_id=str(avaliacao.solides_id or sid),
                    ciclo='aberto',
                )
            continue

        if resolved.via_collapsed:
            pair = (sid, str(avaliacao.solides_id or ''))
            if pair not in seen_collapsed:
                seen_collapsed.add(pair)
                record_id_colapsado_resolvido(
                    report,
                    colapsado=sid,
                    canonico=str(avaliacao.solides_id or ''),
                )

        if not row.identificador_habilidade:
            if not seen_hab_vazia:
                seen_hab_vazia = True
                record_orfao_competencia(
                    report,
                    habilidade_id='',
                    motivo='kpi_ou_sem_nota',
                )
            continue

        key = (avaliacao.pk, row.identificador_habilidade)
        group = grouped.get(key)
        if group is None:
            group = _NotaGroup(
                avaliacao=avaliacao,
                habilidade_id=row.identificador_habilidade,
            )
            grouped[key] = group
        group.rows.append(row)

    return list(grouped.values())


def _upsert_nota_group(
    group: _NotaGroup,
    habilidades_by_id: Mapping[str, HabilidadeRow],
    report: ImportReport,
) -> bool:
    """Persist um par ``(avaliacao, competencia)``. False se nada foi gravado."""
    avaliacao = group.avaliacao
    hab_meta = habilidades_by_id.get(group.habilidade_id)
    nome = next((r.habilidade for r in group.rows if r.habilidade), '')
    if not nome and hab_meta is not None:
        nome = hab_meta.habilidade
    grupo = hab_meta.grupo if hab_meta is not None else ''

    resolved = resolve_competencia(group.habilidade_id, nome, grupo=grupo)
    competencia = resolved.competencia
    if competencia is None:
        record_orfao_competencia(
            report,
            habilidade_id=group.habilidade_id,
        )
        return False

    if resolved.created:
        record_habilidade_extra_criada(
            report,
            solides_id=str(competencia.solides_id or group.habilidade_id),
            tipo=str(competencia.tipo),
        )

    auto_rows = [
        row for row in group.rows if is_auto(row.nome_avaliador, row.nome_avaliado)
    ]
    lider_rows = [
        row
        for row in group.rows
        if not is_auto(row.nome_avaliador, row.nome_avaliado)
    ]

    av_sid = str(avaliacao.solides_id or '')
    comp_sid = str(competencia.solides_id or group.habilidade_id)

    auto_nota = _nota_univoce(
        auto_rows,
        competencia,
        report,
        av_sid,
        comp_sid,
        lado='auto',
    )
    lider_nota = _nota_univoce(
        lider_rows,
        competencia,
        report,
        av_sid,
        comp_sid,
        lado='lider',
    )

    if auto_nota is None and lider_nota is None:
        return False

    source_rows = []
    if auto_nota is not None:
        source_rows.extend(auto_rows)
    if lider_nota is not None:
        source_rows.extend(lider_rows)

    try:
        peso = _peso_do_grupo(source_rows or group.rows)
        nivel = resolve_nivel_esperado(avaliacao.usuario)
    except SnapshotConflict as exc:
        record_conflito(
            report,
            tipo=exc.code,
            extra=f'avaliacao={av_sid} | competencia={comp_sid}',
            motivo=f'linha={group.rows[0].linha}',
        )
        return False

    return _save_avaliacao_competencia(
        avaliacao=avaliacao,
        competencia=competencia,
        auto_nota=auto_nota,
        lider_nota=lider_nota,
        peso=peso,
        nivel=nivel,
        report=report,
        av_sid=av_sid,
        comp_sid=comp_sid,
    )


def _nota_univoce(
    rows: Sequence[NotaRow],
    competencia: Any,
    report: ImportReport,
    av_sid: str,
    comp_sid: str,
    *,
    lado: str,
) -> Decimal | None:
    """Única nota válida do lado; divergência/fora da escala → None.

    Dois líderes distintos → ``conflitos_lider_divergente`` (sem média).
    Dois autos distintos → ``auto_divergente`` na seção conflitos.
    """
    if not rows:
        return None

    valid: list[Decimal] = []
    for row in rows:
        try:
            nota = _parse_nota(row.nota)
        except _NotaParseError:
            record_conflito(
                report,
                tipo='nota_invalida',
                extra=f'avaliacao={av_sid} | competencia={comp_sid}',
                motivo=f'linha={row.linha}',
            )
            continue
        if not _nota_dentro_da_escala(nota, competencia.escala):
            record_conflito(
                report,
                tipo='nota_fora_da_escala',
                extra=f'avaliacao={av_sid} | competencia={comp_sid}',
                motivo=f'linha={row.linha}',
            )
            continue
        valid.append(nota)

    distinct = set(valid)
    if len(distinct) > 1:
        if lado == 'lider':
            record_conflito_lider_divergente(
                report,
                avaliacao_id=av_sid,
                competencia_id=comp_sid,
            )
        else:
            record_conflito(
                report,
                tipo='auto_divergente',
                extra=f'avaliacao={av_sid} | competencia={comp_sid}',
            )
        return None
    if len(distinct) == 1:
        return valid[0]
    return None


def _peso_do_grupo(rows: Sequence[NotaRow]) -> Decimal:
    """Primeiro Fator válido do grupo; senão ``fator_invalido``."""
    last_error: SnapshotConflict | None = None
    for row in rows:
        try:
            return parse_peso_utilizado(row.fator_no_momento)
        except SnapshotConflict as exc:
            last_error = exc
    if last_error is not None:
        raise last_error
    raise SnapshotConflict('fator_invalido')


def _save_avaliacao_competencia(
    *,
    avaliacao: Avaliacao,
    competencia: Any,
    auto_nota: Decimal | None,
    lider_nota: Decimal | None,
    peso: Decimal,
    nivel: int | Decimal,
    report: ImportReport,
    av_sid: str,
    comp_sid: str,
) -> bool:
    """Create/update unique ``(avaliacao, competencia)`` via ``full_clean``+``save``."""
    lado = _lado_relatorio(auto_nota, lider_nota)
    linha = (
        AvaliacaoCompetencia.objects.filter(
            avaliacao_id=avaliacao.pk,
            competencia_id=competencia.pk,
        ).first()
    )
    created = linha is None
    if created:
        linha = AvaliacaoCompetencia(
            avaliacao=avaliacao,
            competencia=competencia,
            nota_autoavaliacao=auto_nota,
            nota_lider=lider_nota,
        )

    try:
        apply_snapshots(linha, peso, nivel)
    except SnapshotConflict as exc:
        record_conflito(
            report,
            tipo=exc.code,
            extra=f'avaliacao={av_sid} | competencia={comp_sid}',
        )
        return False

    if not created:
        changed = False
        if auto_nota is not None and not _same_nota(
            linha.nota_autoavaliacao, auto_nota
        ):
            linha.nota_autoavaliacao = auto_nota
            changed = True
        if lider_nota is not None and not _same_nota(linha.nota_lider, lider_nota):
            linha.nota_lider = lider_nota
            changed = True
        if not changed:
            record_nota_inalterada(
                report,
                avaliacao_id=av_sid,
                competencia_id=comp_sid,
                lado=lado,
            )
            return True

    try:
        linha.full_clean()
        linha.save()
    except ValidationError as exc:
        snap = conflict_from_write_once(exc)
        if snap is not None:
            record_conflito(
                report,
                tipo=snap.code,
                extra=f'avaliacao={av_sid} | competencia={comp_sid}',
            )
            return False
        raise

    if created:
        record_nota_criada(
            report,
            avaliacao_id=av_sid,
            competencia_id=comp_sid,
            lado=lado,
        )
    else:
        record_nota_atualizada(
            report,
            avaliacao_id=av_sid,
            competencia_id=comp_sid,
            lado=lado,
        )
    return True


def _calcular_notas_finais(avaliacao: Avaliacao, report: ImportReport) -> None:
    """CHAMA a fórmula vigente. ``CalculationError`` → conflito, sem média.

    **NÃO** atribui ``etapa`` / ``concluida``. As funções vigentes só
    persistem ``nota_final_*`` via ``update_fields``.
    """
    av_sid = str(avaliacao.solides_id or '')
    try:
        calcular_nota_final_lider(avaliacao)
    except CalculationError:
        record_conflito(
            report,
            tipo='calculo_lider',
            extra=f'avaliacao={av_sid}',
        )
    try:
        calcular_nota_final_autoavaliacao(avaliacao)
    except CalculationError:
        record_conflito(
            report,
            tipo='calculo_auto',
            extra=f'avaliacao={av_sid}',
        )


def _parse_nota(value: Any) -> Decimal:
    """Converte ``Nota`` em ``Decimal`` finito; senão ``nota_invalida``.

    **Não** recorta pela escala (R8). Booleanos são inválidos.
    """
    if value is None or isinstance(value, bool):
        raise _NotaParseError
    if isinstance(value, str):
        text = value.strip()
        if not text:
            raise _NotaParseError
        if ',' in text and '.' in text:
            raise _NotaParseError
        text = text.replace(',', '.')
        try:
            nota = Decimal(text)
        except InvalidOperation as exc:
            raise _NotaParseError from exc
    elif isinstance(value, Decimal):
        nota = value
    elif isinstance(value, int):
        nota = Decimal(value)
    elif isinstance(value, float):
        nota = Decimal(str(value))
    else:
        raise _NotaParseError
    if not nota.is_finite():
        raise _NotaParseError
    return nota.quantize(_NOTA_QUANT)


def _nota_dentro_da_escala(nota: Decimal, escala: Any) -> bool:
    """Inclusive ``[valor_minimo, valor_maximo]``. Sem clip."""
    if escala is None:
        return False
    minimo = Decimal(escala.valor_minimo)
    maximo = Decimal(escala.valor_maximo)
    return minimo <= nota <= maximo


def _same_nota(stored: Decimal | None, new: Decimal | None) -> bool:
    if stored is None and new is None:
        return True
    if stored is None or new is None:
        return False
    return Decimal(stored).quantize(_NOTA_QUANT) == Decimal(new).quantize(
        _NOTA_QUANT
    )


def _lado_relatorio(auto_nota: Decimal | None, lider_nota: Decimal | None) -> str:
    if auto_nota is not None and lider_nota is not None:
        return 'ambos'
    if auto_nota is not None:
        return 'auto'
    return 'lider'
