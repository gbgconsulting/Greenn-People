# Contract: Charts — Dashboard Time (slice 2)

**Feature**: `005-dashboard-charts`  
**Rota**: `dashboard:team` → `/dashboard/team/`  
**View**: `TeamDashboardView`  
**Auth**: `LoginRequiredMixin` + `RequiresLeaderMixin`  
**Tipo**: payload de visualização no contexto Django (sem API REST pública)

## Payload `chart_escopo_status`

```json
{
  "id": "chart-escopo-status",
  "type": "bar",
  "has_data": true,
  "title": "Status do escopo no ciclo",
  "labels": ["Metas", "…", "Feedback", "Sem avaliação"],
  "keys": ["input_metas", "aprovacao_metas", "resultados", "aprovacao_resultados", "avaliacao", "feedback", "sem_avaliacao"],
  "values": [1, 2, 0, 1, 3, 0, 2],
  "total": 9,
  "empty_message": "Não há dados de ciclo no seu escopo para exibir."
}
```

## Regras de escopo (não negociáveis)

1. Universo de pessoas = mesmo critério de `get_queryset()` (`get_visible_users`, exclude self, `is_active=True`).
2. Agregação **não** usa apenas `object_list` da página HTMX.
3. UI MUST NOT filtrar IDs no cliente para “esconder” pessoas.
4. Sem ciclo aberto: `has_data: false` (ou só `sem_avaliacao` se membros existem mas sem avaliações — empty honesto se nada útil a mostrar).

## Colocação no template

- Chart na seção do template pai `team.html`, **fora** de `#list-container` / `team_list_partial.html`.
- Lista HTMX permanece com contrato equivalente ao atual.

## Correlatos

- `dashboard:structure` **não** faz parte deste contrato (métrica diferente).

## Fora

- Ampliar escopo além de `get_visible_users`; inventar status que não sejam `Avaliacao.etapa` / ausência de avaliação.
