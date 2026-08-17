"""Builder de tendência etapa/conclusão (US3).

Recebe o QS ``visible`` já resolvido pela view e a janela de ciclos (≤ N).
Este módulo **MUST NOT** chamar ``get_visible_users`` nem ``compute_adherence``.

O gráfico histórico agrupa as etapas do pipeline em 3 status mutuamente
exclusivos (``sem_avaliacao`` / ``em_andamento`` / ``concluida``) e emite
percentuais 0–100 por ciclo — barra categórica empilhada, não área contínua.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING, Any

from django.db.models import Count, Q

from apps.cycles.models import Ciclo
from apps.dashboard.chart_payloads import (
    CHART_TYPE_BAR,
    EMPTY_KIND_ESCOPO,
    EMPTY_KIND_SEM_DADO,
    FINISH_SLATE,
    HISTORY_DEFAULT_N,
    SEM_AVALIACAO_KEY,
    SEM_AVALIACAO_LABEL,
    STATUS_TRIAD_ALTA,
    STATUS_TRIAD_MEDIA,
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
_CHART_TITLE = 'Andamento ao longo dos ciclos'
_CHART_INSIGHT = (
    'Quem ainda não começou, quem está no meio e quem já concluiu. '
    'A linha mostra se mais gente está terminando.'
)

_STATUS_SEM = SEM_AVALIACAO_KEY
_STATUS_ANDAMENTO = 'em_andamento'
_STATUS_CONCLUIDA = 'concluida'
# Empilhamento de baixo → cima: conclusão cresce a partir do 0, alinhada à linha.
_STATUS_STACK_ORDER: tuple[str, str, str] = (
    _STATUS_CONCLUIDA,
    _STATUS_ANDAMENTO,
    _STATUS_SEM,
)
_STATUS_LABELS: dict[str, str] = {
    _STATUS_SEM: SEM_AVALIACAO_LABEL,
    _STATUS_ANDAMENTO: 'Em andamento',
    _STATUS_CONCLUIDA: 'Concluídas',
}
# Tokens já usados em badge_status (concluida / em_andamento / neutro).
_STATUS_COLORS: dict[str, str] = {
    _STATUS_SEM: FINISH_SLATE,
    _STATUS_ANDAMENTO: STATUS_TRIAD_MEDIA,
    _STATUS_CONCLUIDA: STATUS_TRIAD_ALTA,
}
_LINE_KEY = 'taxa_conclusao'
_LINE_LABEL = 'Quem concluiu'

# Etapa do domínio → status de visão. ``concluida`` não é etapa: vem do flag.
# ``input_metas`` é o valor real de ``Avaliacao.Etapa`` (proposta usava "metas").
STATUS_MAP: dict[str, str] = {
    Avaliacao.Etapa.INPUT_METAS: _STATUS_ANDAMENTO,
    Avaliacao.Etapa.APROVACAO_METAS: _STATUS_ANDAMENTO,
    Avaliacao.Etapa.RESULTADOS: _STATUS_ANDAMENTO,
    Avaliacao.Etapa.APROVACAO_RESULTADOS: _STATUS_ANDAMENTO,
    Avaliacao.Etapa.AVALIACAO: _STATUS_ANDAMENTO,
    Avaliacao.Etapa.FEEDBACK: _STATUS_ANDAMENTO,
    SEM_AVALIACAO_KEY: _STATUS_SEM,
}

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
    if raw is None or str(raw).strip() == '':
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


def _distribute_int_percents(counts: dict[str, int], total: int) -> dict[str, int]:
    """Percentuais inteiros 0–100 cuja soma é 100 (resto para as maiores frações)."""
    keys = list(counts)
    if total <= 0 or not keys:
        return dict.fromkeys(keys, 0)

    scaled = {key: counts[key] * 100 for key in keys}
    floors = {key: scaled[key] // total for key in keys}
    remainder = 100 - sum(floors.values())
    ranked = sorted(
        keys,
        key=lambda key: (scaled[key] % total, counts[key]),
        reverse=True,
    )
    for key in ranked:
        if remainder <= 0:
            break
        floors[key] += 1
        remainder -= 1
    return floors


def build_stage_history(
    visible: QuerySet[CustomUser],
    ciclos: Sequence[Ciclo],
) -> dict:
    """Monta o payload de tendência empilhada 100% no escopo.

    ``visible``
        QuerySet já autorizado pela view. Este builder **nunca** chama
        ``get_visible_users`` — o caller resolve o escopo (admin = visible
        admin; líder = ``get_visible_users`` sem o próprio, como o time).

    ``ciclos``
        Janela já recortada: lista ≤ ``HISTORY_DEFAULT_N`` (default 8),
        ordenada pelo caller (default ``data_inicio`` / ``pk``; ou ordem de
        ``?ciclos=``). Cap defensivo aplicado aqui; **não** plota o arquivo.

    Retorno
        Payload canônico 009 via ``grouped_series_payload`` com ``type: bar``
        empilhado. Três séries de status (percentual do escopo) + overlay de
        linha com ``concluida_pct``. Ciclo sem cabeçalho no escopo = 100%
        ``sem_avaliacao`` (pessoas paradas), não 0 de nota. ``has_data=false``
        se a janela no escopo não tem cabeçalhos úteis.
        **MUST NOT** chamar ``compute_adherence`` nem inventar nota.
    """
    window = list(ciclos)[:HISTORY_DEFAULT_N]
    membro_ids = list(visible.values_list('pk', flat=True))
    visible_total = len(membro_ids)

    if visible_total == 0:
        return empty_kind_payload(
            kind=EMPTY_KIND_ESCOPO,
            chart_id=_CHART_ID,
            chart_type=CHART_TYPE_BAR,
            title=_CHART_TITLE,
        )

    if not window:
        return empty_kind_payload(
            kind=EMPTY_KIND_SEM_DADO,
            chart_id=_CHART_ID,
            chart_type=CHART_TYPE_BAR,
            title=_CHART_TITLE,
        )

    etapa_keys = [choice.value for choice in Avaliacao.Etapa]
    for etapa in etapa_keys:
        if STATUS_MAP.get(etapa) != _STATUS_ANDAMENTO:
            raise ValueError(f'etapa sem mapeamento em_andamento: {etapa!r}')
    etapa_labels = dict(Avaliacao.Etapa.choices)
    ciclo_ids = [c.pk for c in window]
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

    labels: list[str] = []
    values_by_status: dict[str, list[int]] = {
        key: [] for key in _STATUS_STACK_ORDER
    }
    points: list[dict[str, Any]] = []
    any_header = False

    for ciclo in window:
        cid = ciclo.pk
        headers = int(by_ciclo_headers.get(cid, 0))
        if headers > 0:
            any_header = True
        concluida_count = int(by_ciclo_concluidas.get(cid, 0))
        andamento_count = max(0, headers - concluida_count)
        sem_count = max(0, visible_total - headers)
        totais = {
            _STATUS_SEM: sem_count,
            _STATUS_ANDAMENTO: andamento_count,
            _STATUS_CONCLUIDA: concluida_count,
        }
        pcts = _distribute_int_percents(totais, visible_total)
        etapa_counts = {
            etapa: int(by_ciclo_etapa.get(cid, {}).get(etapa, 0))
            for etapa in etapa_keys
        }
        labels.append(ciclo.nome)
        for key in _STATUS_STACK_ORDER:
            values_by_status[key].append(int(pcts[key]))
        points.append(
            {
                'ciclo': ciclo.nome,
                'data': ciclo.data_inicio.isoformat(),
                'sem_avaliacao_pct': pcts[_STATUS_SEM],
                'em_andamento_pct': pcts[_STATUS_ANDAMENTO],
                'concluida_pct': pcts[_STATUS_CONCLUIDA],
                'totais': totais,
                'detalhe_etapas': etapa_counts,
            },
        )

    if not any_header:
        return empty_kind_payload(
            kind=EMPTY_KIND_SEM_DADO,
            chart_id=_CHART_ID,
            chart_type=CHART_TYPE_BAR,
            title=_CHART_TITLE,
        )

    series: list[dict[str, Any]] = [
        {
            'key': key,
            'label': _STATUS_LABELS[key],
            'values': values_by_status[key],
            'color': _STATUS_COLORS[key],
            'kind': 'bar',
        }
        for key in _STATUS_STACK_ORDER
    ]
    series.append(
        {
            'key': _LINE_KEY,
            'label': _LINE_LABEL,
            'values': list(values_by_status[_STATUS_CONCLUIDA]),
            'color': _STATUS_COLORS[_STATUS_CONCLUIDA],
            'kind': 'line',
        },
    )

    payload = grouped_series_payload(
        chart_id=_CHART_ID,
        title=_CHART_TITLE,
        labels=labels,
        series=series,
        empty_message=empty_kind_message(EMPTY_KIND_SEM_DADO),
        has_data=True,
        chart_type=CHART_TYPE_BAR,
    )
    latest = points[-1]
    payload['stacked'] = True
    payload['html_legend'] = True
    payload['value_unit'] = '%'
    payload['insight'] = _CHART_INSIGHT
    payload['points'] = points
    payload['x_meta'] = [
        {'ciclo': point['ciclo'], 'data': point['data']} for point in points
    ]
    payload['detalhe_labels'] = etapa_labels
    payload['legend_items'] = [
        {
            'label': _STATUS_LABELS[key],
            'value': f'{latest[_pct_key(key)]}%',
            'color': _STATUS_COLORS[key],
        }
        for key in (_STATUS_SEM, _STATUS_ANDAMENTO, _STATUS_CONCLUIDA)
    ]
    payload['legend_caption'] = (
        f'No ciclo mais recente ({latest["ciclo"]})'
    )
    return payload


def _pct_key(status: str) -> str:
    return {
        _STATUS_SEM: 'sem_avaliacao_pct',
        _STATUS_ANDAMENTO: 'em_andamento_pct',
        _STATUS_CONCLUIDA: 'concluida_pct',
    }[status]


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
