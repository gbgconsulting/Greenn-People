# Contract: Charts — Dashboard Admin (MVP)

**Feature**: `005-dashboard-charts`  
**Rota**: `dashboard:admin` → `/dashboard/admin/`  
**View**: `AdminDashboardView`  
**Auth**: `LoginRequiredMixin` + `RequiresAdminMixin`  
**Tipo**: payload de visualização no contexto Django (sem API REST pública)

## Payloads (contexto → `json_script`)

### `chart_aderencia_distribuicao`

```json
{
  "id": "chart-aderencia-distribuicao",
  "type": "doughnut_or_bar",
  "has_data": true,
  "title": "Distribuição de aderência",
  "labels": ["Alta", "Média", "Baixa"],
  "keys": ["alta", "media", "baixa"],
  "values": [3, 5, 2],
  "colors": ["#059669", "#d97706", "#e11d48"],
  "total": 10,
  "empty_message": "Nenhum snapshot de aderência para este ciclo."
}
```

- **Fonte**: snapshots do ciclo usado em `_aderencia_resumo` / `_snapshots_destaque`.
- **Faixas**: exclusivamente `aderencia_status()` existente.
- `has_data: false` quando `total == 0` ou sem ciclo → UI usa `empty_message`, **não** desenha série fictícia.

### `chart_ciclo_progresso`

```json
{
  "id": "chart-ciclo-progresso",
  "type": "bar",
  "has_data": true,
  "title": "Progresso das avaliações no ciclo",
  "labels": ["Metas", "…", "Feedback"],
  "keys": ["input_metas", "aprovacao_metas", "resultados", "aprovacao_resultados", "avaliacao", "feedback"],
  "values": [2, 4, 1, 0, 3, 5],
  "total": 15,
  "empty_message": "Não há avaliações neste ciclo para exibir progresso."
}
```

- **Fonte**: `Avaliacao` filtrada por `ciclo_indicador`; chaves = `Avaliacao.Etapa`.
- Alternativa contratual aceita no MVP: duas fatias `concluidas` / `pendentes` alinhadas a `avaliacoes_resumo` (mesmos totais dos cards).

## UI obrigatória além do canvas

| Elemento | Contrato |
|---|---|
| Cards KPI | Permanecem (`ciclos_resumo`, `avaliacoes_resumo`, `aderencia_resumo`) |
| Tabela “Líderes com menor aderência” | `snapshots_destaque` continua renderizada quando houver dados |
| Legenda / texto | Labels das faixas/etapas visíveis sem depender só da cor |
| Empty | `empty_state` (ou equivalente) com mensagem PT-BR |

## Fora

- Recalcular aderência no request; endpoints JSON públicos; mudar thresholds.
