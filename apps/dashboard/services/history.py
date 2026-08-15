"""Builder de tendência etapa/conclusão (US3).

Recebe o QS ``visible`` já resolvido pela view e a janela de ciclos (≤ N).
Este módulo **MUST NOT** chamar ``get_visible_users`` nem ``compute_adherence``.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING

from django.db.models import Count, Q

from apps.cycles.models import Ciclo
from apps.dashboard.chart_payloads import (
    CHART_TYPE_AREA,
    EMPTY_KIND_ESCOPO,
    EMPTY_KIND_SEM_DADO,
    HISTORY_DEFAULT_N,
    SEM_AVALIACAO_KEY,
    SEM_AVALIACAO_LABEL,
    empty_kind_message,
    empty_kind_payload,
    grouped_series_payload,
)
from apps.reviews.models import Avaliacao

if TYPE_CHECKING:
    from django.db.models import QuerySet
    from django.http import HttpRequest

    from apps.accounts.models import CustomUser

_CHART_ID = 'chart-stage-history'
_CHART_TITLE = 'Tendência de etapa e conclusão'
_CONCLUIDA_KEY = 'concluida'
_CONCLUIDA_LABEL = 'Concluídas'

# Ordem de pipeline para comparar “evoluiu” entre ciclos da janela.
_ETAPA_RANK: dict[str, int] = {
    choice.value: index for index, choice in enumerate(Avaliacao.Etapa)
}


def default_history_ciclos(
    *,
    limit: int = HISTORY_DEFAULT_N,
) -> list[Ciclo]:
    """Últimos ``limit`` ciclos por ``data_inicio`` / ``pk`` (ordem cronológica).

    Nunca devolve mais que ``HISTORY_DEFAULT_N`` (teto defensivo).
    """
    n = max(0, min(int(limit), HISTORY_DEFAULT_N))
    if n == 0:
        return []
    recent = list(
        Ciclo.objects.order_by('-data_inicio', '-pk')[:n],
    )
    recent.reverse()
    return recent


def parse_history_ciclos(
    raw: str | None,
    *,
    limit: int = HISTORY_DEFAULT_N,
) -> list[Ciclo] | None:
    """Parseia ``?ciclos=<id>,<id>`` preservando ordem; cap no teto N.

    Retorna ``None`` se ``raw`` estiver vazio (caller usa
    ``default_history_ciclos``). Ids inválidos / inexistentes são ignorados.
    """
    if raw is None or not str(raw).strip():
        return None
    n = max(0, min(int(limit), HISTORY_DEFAULT_N))
    if n == 0:
        return []

    pks: list[int] = []
    seen: set[int] = set()
    for part in str(raw).split(','):
        part = part.strip()
        if not part:
            continue
        try:
            pk = int(part)
        except (TypeError, ValueError):
            continue
        if pk in seen:
            continue
        seen.add(pk)
        pks.append(pk)
        if len(pks) >= n:
            break

    if not pks:
        return []

    by_pk = Ciclo.objects.in_bulk(pks)
    return [by_pk[pk] for pk in pks if pk in by_pk]


def resolve_history_ciclos(
    request: HttpRequest,
    *,
    limit: int = HISTORY_DEFAULT_N,
) -> list[Ciclo]:
    """Janela US3: ``?ciclos=`` explícito (cap N) ou default últimos N."""
    parsed = parse_history_ciclos(request.GET.get('ciclos'), limit=limit)
    if parsed is not None:
        return parsed
    return default_history_ciclos(limit=limit)


def is_history_mode(request: HttpRequest) -> bool:
    """True somente com intenção explícita ``?visao=historico``."""
    return request.GET.get('visao') == 'historico'


def build_stage_history(
    visible: QuerySet[CustomUser],
    ciclos: Sequence[Ciclo],
) -> dict:
    """Monta o payload de tendência ``area`` de etapa/conclusão no escopo.

    ``visible``
        QuerySet já autorizado pela view. Este builder **nunca** chama
        ``get_visible_users`` — o caller resolve o escopo (admin = visible
        admin; líder = ``get_visible_users`` sem o próprio, como o time).

    ``ciclos``
        Janela já recortada: lista ≤ ``HISTORY_DEFAULT_N`` (default 8),
        ordenada pelo caller (default ``data_inicio`` / ``pk``; ou ordem de
        ``?ciclos=``). Cap defensivo aplicado aqui; **não** plota o arquivo.

    Retorno
        Payload canônico 009 via ``grouped_series_payload`` com ``type: area``.
        Contagens de ``Avaliacao.etapa`` (+ ``sem_avaliacao``) e série
        ``concluida`` por ciclo. Lacuna (ciclo sem cabeçalho útil no escopo) =
        ``null`` em todas as séries (nunca 0 de desempenho).
        ``has_data=false`` se a janela no escopo não tem cabeçalhos úteis.
        **MUST NOT** chamar ``compute_adherence`` nem inventar nota.
    """
    window = list(ciclos)[:HISTORY_DEFAULT_N]
    membro_ids = list(visible.values_list('pk', flat=True))
    visible_total = len(membro_ids)

    if visible_total == 0:
        return empty_kind_payload(
            kind=EMPTY_KIND_ESCOPO,
            chart_id=_CHART_ID,
            chart_type=CHART_TYPE_AREA,
            title=_CHART_TITLE,
        )

    if not window:
        return empty_kind_payload(
            kind=EMPTY_KIND_SEM_DADO,
            chart_id=_CHART_ID,
            chart_type=CHART_TYPE_AREA,
            title=_CHART_TITLE,
        )

    etapa_keys = [choice.value for choice in Avaliacao.Etapa]
    labels_by_key = dict(Avaliacao.Etapa.choices)
    series_keys = [*etapa_keys, SEM_AVALIACAO_KEY, _CONCLUIDA_KEY]
    series_labels = {
        **labels_by_key,
        SEM_AVALIACAO_KEY: SEM_AVALIACAO_LABEL,
        _CONCLUIDA_KEY: _CONCLUIDA_LABEL,
    }

    ciclo_ids = [c.pk for c in window]
    # Contagens por ciclo × etapa e concluídas — só no escopo já autorizado.
    rows = (
        Avaliacao.objects.filter(
            ciclo_id__in=ciclo_ids,
            usuario_id__in=membro_ids,
        )
        .values('ciclo_id', 'etapa')
        .annotate(
            total=Count('pk'),
            concluidas=Count('pk', filter=Q(concluida=True)),
        )
    )

    # ciclo_id → {etapa: count}; ciclo_id → concluídas
    by_ciclo_etapa: dict[int, dict[str, int]] = {cid: {} for cid in ciclo_ids}
    by_ciclo_concluidas: dict[int, int] = dict.fromkeys(ciclo_ids, 0)
    by_ciclo_headers: dict[int, int] = dict.fromkeys(ciclo_ids, 0)

    for row in rows:
        cid = int(row['ciclo_id'])
        etapa = row['etapa']
        total = int(row['total'] or 0)
        by_ciclo_etapa[cid][etapa] = total
        by_ciclo_headers[cid] += total
        by_ciclo_concluidas[cid] += int(row['concluidas'] or 0)

    labels = [c.nome for c in window]
    values_by_key: dict[str, list[int | None]] = {
        key: [] for key in series_keys
    }
    any_header = False

    for ciclo in window:
        cid = ciclo.pk
        headers = by_ciclo_headers.get(cid, 0)
        if headers <= 0:
            # Lacuna: sem cabeçalho útil no escopo → null em todas as séries.
            for key in series_keys:
                values_by_key[key].append(None)
            continue

        any_header = True
        etapa_counts = by_ciclo_etapa.get(cid, {})
        covered = 0
        for etapa in etapa_keys:
            count = int(etapa_counts.get(etapa, 0))
            values_by_key[etapa].append(count)
            covered += count
        values_by_key[SEM_AVALIACAO_KEY].append(
            max(0, visible_total - covered),
        )
        values_by_key[_CONCLUIDA_KEY].append(
            int(by_ciclo_concluidas.get(cid, 0)),
        )

    if not any_header:
        return empty_kind_payload(
            kind=EMPTY_KIND_SEM_DADO,
            chart_id=_CHART_ID,
            chart_type=CHART_TYPE_AREA,
            title=_CHART_TITLE,
        )

    series = [
        {
            'key': key,
            'label': series_labels[key],
            'values': values_by_key[key],
        }
        for key in series_keys
    ]

    return grouped_series_payload(
        chart_id=_CHART_ID,
        title=_CHART_TITLE,
        labels=labels,
        series=series,
        empty_message=empty_kind_message(EMPTY_KIND_SEM_DADO),
        has_data=True,
        chart_type=CHART_TYPE_AREA,
    )


def _progress_score(etapa: str | None, concluida: bool) -> tuple[int, int]:
    """Score ordinal (etapa, concluída) — maior = mais avançado no pipeline."""
    rank = _ETAPA_RANK.get(etapa or '', -1)
    return (rank, 1 if concluida else 0)


def build_history_kpis(
    visible: QuerySet[CustomUser],
    ciclos: Sequence[Ciclo],
) -> dict[str, int | bool]:
    """Resumo 1–3 da janela: evoluiu / estável / sem dado (US3 / SC-003).

    Por pessoa no escopo ``visible``, compara o primeiro e o último ponto
    útil na janela (etapa + ``concluida``). Sem cabeçalho → ``sem_dado``;
    score final > inicial → ``evoluiu``; caso contrário → ``estavel``.
    **MUST NOT** inventar nota nem chamar ``compute_adherence``.
    """
    window = list(ciclos)[:HISTORY_DEFAULT_N]
    membro_ids = list(visible.values_list('pk', flat=True))
    empty = {
        'evoluiu': 0,
        'estavel': 0,
        'sem_dado': 0,
        'has_janela': bool(window) and bool(membro_ids),
    }
    if not membro_ids or not window:
        empty['sem_dado'] = len(membro_ids)
        return empty

    ciclo_order = {c.pk: index for index, c in enumerate(window)}
    rows = Avaliacao.objects.filter(
        ciclo_id__in=ciclo_order,
        usuario_id__in=membro_ids,
    ).values_list('usuario_id', 'ciclo_id', 'etapa', 'concluida')

    by_user: dict[int, list[tuple[int, tuple[int, int]]]] = {}
    for usuario_id, ciclo_id, etapa, concluida in rows:
        order = ciclo_order.get(ciclo_id)
        if order is None:
            continue
        by_user.setdefault(usuario_id, []).append(
            (order, _progress_score(etapa, bool(concluida))),
        )

    evoluiu = 0
    estavel = 0
    sem_dado = 0
    for uid in membro_ids:
        points = by_user.get(uid)
        if not points:
            sem_dado += 1
            continue
        points.sort(key=lambda item: item[0])
        first_score = points[0][1]
        last_score = points[-1][1]
        if last_score > first_score:
            evoluiu += 1
        else:
            estavel += 1

    return {
        'evoluiu': evoluiu,
        'estavel': estavel,
        'sem_dado': sem_dado,
        'has_janela': True,
    }
