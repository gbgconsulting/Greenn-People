# Data Model: Visualizações Gerenciais e Históricas Pós-Legado

**Branch**: `012-Visualização-pós-legado` · spec dir `012-gerencial-historico-legado`  
**Date**: 2026-08-14

## Declaração

Esta feature **não introduz models Django novos**, **não cria migrations** e **não altera** campos, FKs, `on_delete`, snapshots write-once, máquina de estados nem schema de nota.

As Key Entities da [spec.md](./spec.md) são **conceitos de apresentação / query** mapeados para contexto de views, helpers de payload e templates. Persistência continua `Ciclo`, `Avaliacao`, `AderenciaSnapshot` (leitura).

Contratos: [contracts/](./contracts/). Catálogo visual reusado (não reaberto): `specs/009-persona-visual-redesign/contracts/{chart-catalog,managerial-panel,cycle-managerial-detail}.md`.

---

## Entidades de apresentação

### Ciclo operacional (aberto)

| Campo lógico | Origem |
|---|---|
| Identidade | `Ciclo` com `status=aberto` via `get_open_ciclo()` |
| Cardinalidade | No máximo um |
| Papel | Âncora **default** de admin, time, estrutura, aderência e correlatos |

**Validação**: ausência ⇒ empty `operacional`; nunca fallback para encerrado.

### Ciclo histórico / arquivo

| Campo lógico | Origem |
|---|---|
| Identidade | `Ciclo` com `status=encerrado` (legado 011 + operacionais anteriores) |
| Acesso | Intenção explícita: `?ciclo=<pk>` no seletor agrupado, ou URL `cycles/<pk>/` |
| Papel | Não alimenta KPIs de “saúde da operação” por default |

### Modo de visão

| Valor | Query | Superfícies |
|---|---|---|
| `operacional` (default) | ausente / outro | admin, time, estrutura, aderência, ciclo detalhe |
| `historico` | `visao=historico` | **somente** admin, time, `ciclo_detail` |

Painel pessoal **não** possui este modo.

Query opcional da janela US3: `ciclos=<id>,<id>` (cap `HISTORY_DEFAULT_N`).

### Fatia de densidade (Top-N + Outros)

| Campo | Valor |
|---|---|
| `DENSITY_TOP_N` | `8` |
| Label residual | `"Outros"` |
| Contagem | soma das categorias além do N |
| Cobertura % | `sum(com_avaliacao) / sum(total)` do residual |
| Gap agrupado pessoal | Top-N por \|gap\|; resto omitido (sem média inventada) |
| Implementação | helper em `apps/dashboard/chart_payloads.py` |

Etapas de avaliação e Status Triad **não** passam por este corte.

### Indicador já existente (plotável)

| Indicador | Fonte | US3 nesta fatia |
|---|---|---|
| Etapa / `sem_avaliacao` | `Avaliacao.etapa` + ausência de cabeçalho no escopo | **Default da tendência** (`area`) |
| Conclusão de processo | `Avaliacao.concluida` | Composição da mesma série / KPI de processo |
| Cobertura área/cargo | `build_structure_coverage` (counts) | Não é tendência; densidade Top-N no operacional |
| Aderência | `AderenciaSnapshot.percentual` | Empty até haver snapshot |
| Gap esperado × nota | `competencias_resumo` / notas | Empty até haver nota; pessoal sem tendência |

**Proibido**: nota final derivada, 9-box temporal, “saúde do ciclo”, média de percentuais como métrica nova.

### Série histórica de etapa (US3)

| Campo lógico | Origem |
|---|---|
| `labels` | nomes/datas dos ≤ N ciclos da janela |
| `series` | buckets de etapa (e/ou concluída vs em fluxo vs sem avaliação) já existentes |
| `values` com lacuna | `null` — não `0` de desempenho |
| `has_data` | falso se a janela no escopo não tem cabeçalhos úteis |
| Escopo | QS `visible` já resolvido pela view |
| Builder | módulo de apresentação em `apps/dashboard` (ex. `services/history.py`) — **recebe** `visible` + lista de ciclos |

### Empty (kind)

| Kind | `has_data` | Onde |
|---|---|---|
| `operacional` | false | Home gerencial sem ciclo aberto |
| `escopo` | false | Time/estrutura/aderência sem pessoas visíveis |
| `sem_dado` | false | Seção sem avaliações/snapshots |
| `sem_nota` | false | Série de desempenho/gap/aderência sem dado; pipeline MAY seguir visível |

Render: `templates/components/empty_state.html` via `_chart_block`.

### Painel gerencial

Inalterado em composição (Freeze C / contrato 009): 1–3 KPIs → visual principal → drill. Esta fatia só troca **qual** ciclo/modo alimenta os slots e aplica densidade/leveza.

| Slot | Operacional (default) | Histórico (`visao=historico`) |
|---|---|---|
| KPI | Pipeline do ciclo **aberto** (não % de encerrados do arquivo) | Resumo da janela N (evoluiu / estável / sem dado) — 1–3 |
| Visual | `bar_horizontal` etapas | `area` etapa/conclusão |
| Drill | tabela/ranking já existente | opcional lista dos ciclos da janela (links `ciclo_detail`) |

---

## Mapeamento por superfície

| Superfície | Default | Seletor `?ciclo=` | `visao=historico` | Densidade | AuthZ |
|---|---|---|---|---|---|
| Admin | Aberto; senão empty operacional | Sim (arquivo agrupado) | Sim (tendência org) | Top-N cobertura se plotada; seletor | `RequiresAdminMixin` |
| Time | Aberto; senão empty | Sim (explícito) | Sim (tendência do escopo) | Ranking Top-N | `RequiresLeaderMixin` + `get_visible_users` |
| Estrutura | Aberto; senão empty | Já existe — agrupar | **Não** (fora da clarification US3) | Top-N área/cargo | `RequiresManagerOrAdminMixin` + visible |
| Aderência | Aberto; senão empty | Já existe — agrupar | **Não** | Doughnut 3 fatias (sem Top-N) | visible se não admin |
| `ciclo_detail` | O `pk` (já explícito) | N/A | Sim (tendência org, cap N) | Top-N cobertura | `AdminCyclesMixin` |
| `ciclo_list` | Lista; aberto em destaque; arquivo paginado | N/A | Não | Paginação 20 + agrupamento visual | admin |
| Pessoal | Ciclo aberto do colaborador (FR-005 vigente) | Não | **Não** | Top-N competências com nota | `LoginRequired` (próprio) |

---

## Relacionamentos (leitura)

```text
CustomUser ──get_visible_users──► QS visível
                    │
Ciclo(aberto) ──default──► painel operacional (KPIs + pipeline)
Ciclo(encerrado) ──só se ?ciclo= ou detalhe──► mesmo painel, copy de arquivo
Ciclo[] (≤ N) ──visao=historico──► série area (etapa/conclusão)
Avaliacao ──etapa/concluida──► pipeline e tendência (pode existir sem nota)
AderenciaSnapshot ──leitura──► doughnut; empty se não houver
```

Nenhuma FK nova. `on_delete=PROTECT` intacto.

---

## State transitions

**Nenhuma.** Não altera `Ciclo.status` nem `Avaliacao.etapa` / `concluida`.

---

## Validation rules (apresentação)

1. Sem ciclo aberto na home gerencial → empty `operacional`; zero payload com labels do arquivo.
2. `has_data !== true` → não instancia Chart; sem zero de desempenho.
3. Eixo categórico longo → ≤ `DENSITY_TOP_N` rótulos + no máximo um “Outros”.
4. Série US3 → ≤ `HISTORY_DEFAULT_N` ciclos; `null` ≠ 0.
5. Cabeçalho `concluida` sem nota → não copy de desempenho saudável.
6. Cobertura ≠ aderência (labels/seções).
7. Diff em denylist de domínio = falha de aceite.
8. Builder de tendência/densidade nunca chama `get_visible_users` com outro usuário.
