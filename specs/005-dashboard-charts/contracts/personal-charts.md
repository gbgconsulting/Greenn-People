# Contract: Charts — Painel Pessoal (slice 3)

**Feature**: `005-dashboard-charts`  
**Rota**: `dashboard:personal` → `/`  
**View**: `PersonalDashboardView`  
**Auth**: `LoginRequiredMixin`  
**Tipo**: payload de visualização no contexto Django (sem API REST pública)

## Payload `chart_gaps_competencia`

```json
{
  "id": "chart-gaps-competencia",
  "type": "bar_grouped",
  "has_data": true,
  "title": "Esperado × nota por competência",
  "labels": ["Comunicação", "Liderança"],
  "series": [
    { "key": "nivel_esperado", "label": "Nível esperado", "values": [4, 3] },
    { "key": "nota_atual", "label": "Nota atual", "values": [3, null] }
  ],
  "empty_message": "Ainda não há notas por competência para exibir gaps."
}
```

- **Fonte**: `competencias_resumo` de `build_fr005_context` (mesmos pares da UI textual).
- `null` em `nota_atual`: competência sem nota — chart pode omitir ponto ou mostrar só esperado; **não** inventar nota.
- `has_data: false` se vínculo pendente, lista vazia ou nenhuma nota disponível para comparar.

## 9-box (inalterada)

- Continua apenas `{% if classificacao %}` com resultado de `get_visible_classification_for_collaborator`.
- Este contrato **proíbe** drag, drawer, edição in-matrix ou mudança de `visivel_ao_colaborador`.

## Fora

- Novas competências/notas; endpoints; alterar regra de origem da nota (`nota_atual_origem`).
