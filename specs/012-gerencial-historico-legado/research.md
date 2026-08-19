# Research: Visualizações Gerenciais e Históricas Pós-Legado

**Branch**: `012-Visualização-pós-legado` · spec dir `012-gerencial-historico-legado`  
**Date**: 2026-08-14  
**Spec**: [spec.md](./spec.md) (Clarifications 2026-08-14 = decisões fechadas)

Pesquisa consolidada a partir da spec (incl. clarifications), Constituição (`.specify/memory/constitution.md`), Freeze v2 em `docs/design-system.md`, contratos 009 (`chart-catalog`, `managerial-panel`, `cycle-managerial-detail`), código de `apps/dashboard/{views,chart_payloads,services}`, `templates/dashboard/_chart_block.html`, `static/js/dashboard_charts.js`, e volume pós-011 (~57 ciclos encerrados + ~700 cabeçalhos sem nota). Todos os itens do Technical Context foram resolvidos (sem `NEEDS CLARIFICATION` remanescente).

Contratos visuais 009 **não se reabrem**: esta fatia acrescenta densidade / default operacional / empty honesto / modo histórico — ver [contracts/density-history-empty.md](./contracts/density-history-empty.md).

---

## R1 — Default operacional = ciclo aberto; matar fallback silencioso

- **Decision**: Em **todas** as superfícies gerenciais desta fatia, o ciclo da visão operacional é `get_open_ciclo()` (já existe em `apps/goals/forms.py` e só retorna `status=aberto`). Se não houver aberto → empty operacional; **MUST NOT** escolher um encerrado. Remover o fallback de `AdminDashboardView`:

  ```python
  ciclo_indicador = ciclo_aberto or (
      Ciclo.objects.filter(status=Ciclo.Status.ENCERRADO)
      .order_by('-data_fim', '-pk').first()
  )
  ```

  `ciclo_indicador` deixa de existir como conceito de default. Query `?ciclo=<pk>` (já usada em estrutura/aderência) permanece **somente** como intenção explícita — nunca como substituto silencioso do aberto.
- **Rationale**: FR-001 / FR-002 / SC-001; clarificação “histórico só por intenção explícita”. Com ~57 encerrados da 011, o `.first()` do arquivo vira a home.
- **Alternatives considered**:
  - Default = último encerrado “mais recente” — rejeitado (é o bug).
  - Default = último ciclo com avaliações — rejeitado (ainda mistura arquivo).
  - Mudar `get_open_ciclo()` — desnecessário; a função já está correta.

---

## R2 — Taxonomia de empty (operacional ≠ dado ≠ nota/gap ≠ escopo)

- **Decision**: Quatro empties distintos, todos via `has_data: false` + `empty_state` (nunca série cinza / zero inventado):

  | Kind | Quando | Copy (direção) |
  |------|--------|----------------|
  | `operacional` | Sem ciclo aberto na home admin/time/estrutura/aderência | “Não há ciclo aberto. O arquivo histórico continua acessível pelo seletor.” |
  | `escopo` | Líder sem subordinados visíveis | Empty de escopo (já existe no time) |
  | `sem_dado` | Ciclo/escopo ok, mas sem avaliações / sem snapshot | Empty local da seção; resto da página intacto |
  | `sem_nota` / `gap` | Cabeçalho legado terminal sem desempenho; série de nota/aderência-snapshot/gap | Empty da **série de desempenho**; pipeline de etapa MAY permanecer |

  FR-009: `percentual_concluidas` de cabeçalhos `concluida` sem nota **não** se apresenta como saúde de desempenho. KPI de conclusão = processo/etapa, copy explícita; doughnut de aderência e gap esperado×nota ficam empty até haver dado.
- **Rationale**: Clarifications US3 + FR-008 / FR-009; precedente `empty_series_payload` / `_chart_block`.
- **Alternatives considered**: Um empty genérico “sem dados” — rejeitado (esconde a diferença aberto vs arquivo vs nota).

---

## R3 — Histórico explícito = modo/query nas superfícies existentes (não página nova)

- **Decision**: Visão de evolução (US3) = GET na **mesma URL** com `visao=historico` (toggle na UI). Superfícies: `dashboard/admin`, `dashboard/team`, `cycles/<pk>/`. **Não** criar rota `/historico/` nem seção nav nova. **Não** reduzir a US3 ao seletor de ciclo (FR-003). Painel pessoal (`dashboard/personal`) **MUST NOT** receber o toggle.

  Seletor de **um** ciclo (`?ciclo=<pk>`) = arquivo pontual (US1/US2). Modo `visao=historico` = tendência entre N ciclos (US3). São mecanismos distintos.

  Navegação do toggle = request GET completo (não HTMX no bloco de chart), para reusar `DOMContentLoaded` → `initAll` em `dashboard_charts.js`. Listas HTMX continuam só `#list-container` (FR-017).
- **Rationale**: Clarification “Onde mora a visão histórica?”; FR-003 / FR-016 / FR-017.
- **Alternatives considered**:
  - Página dedicada — rejeitado pela clarification.
  - Só o seletor de ciclo — rejeitado (não responde “evoluiu?”).
  - HTMX swap do chart — rejeitado nesta fatia (init só em `DOMContentLoaded`; risco FR-017).

---

## R4 — Teto de densidade: Top-N + “Outros”, N = 8

- **Decision**: Constante de apresentação `DENSITY_TOP_N = 8` (faixa spec ~5–10). Helper único em `chart_payloads.py` (ex. `top_n_with_others`) aplicado **antes** de emitir payload:

  | Eixo | Regra de “Outros” |
  |------|-------------------|
  | Contagens / ranking | Soma das categorias restantes |
  | Cobertura % área/cargo | Recalcular % do residual: `sum(com) / sum(total)` — composição dos counts já autorizados, **não** média de percentuais |
  | `bar_grouped` pessoal (esperado×nota) | Top-N por \|gap\| entre competências **com nota**; resto **não** vira média inventada — insight “demais competências omitidas” (sem métrica nova) |
  | Etapas (`Avaliacao.Etapa` + `sem_avaliacao`) | Conjunto fechado (~7) — **sem** Top-N |
  | Status Triad (3 fatias) | Sem Top-N |

  Seletor de ciclos: `<optgroup>` Operacional / Arquivo; arquivo por `-data_inicio`; se arquivo > 20, filtro GET `q` no nome (DTL, sem lib). Lista de ciclos já pagina (`paginate_by=20`) — destacar aberto vs arquivo.
- **Rationale**: FR-006 / SC-004; volume 011 (dezenas de áreas/cargos/ciclos no eixo).
- **Alternatives considered**:
  - N=5 rígido — cedo demais; 8 é leitura gerencial típica, calibrável sem reabrir spec.
  - Paginar o eixo do chart — pior UX que “Outros”.
  - Truncar sem “Outros” em contagens — mente o total.

---

## R5 — US3: métrica = etapa/conclusão no tempo; N = 8; nunca o arquivo completo

- **Decision**: Default da tendência = **pipeline histórico**: para cada ciclo da janela, no escopo já autorizado, contar etapa atual (incl. `sem_avaliacao`) e/ou fração `concluida`. Chart `type: area` (catálogo 009). Pergunta: evoluiu / estável / sem dado.

  - Janela default: `HISTORY_DEFAULT_N = 8` ciclos relevantes no escopo, ordenados por `data_inicio` (depois `pk`), **não** os ~57 crus.
  - Escolha explícita: `?visao=historico&ciclos=<id>,<id>` (cap no mesmo N; rejeitar plotar além do teto).
  - Aderência por snapshot e gap esperado×nota: payloads `has_data: false` + empty `sem_nota` até existir dado (011 não importou notas; snapshot de aderência legado provavelmente ausente).
  - Ponto ausente na série: `null` em `series[].values` (já suportado em `grouped_series_payload`); **nunca** 0 de desempenho.
  - Admin: recorte organização (visible admin). Líder: `get_visible_users` sem o próprio, como o time. **Sem** tendência no pessoal.
- **Rationale**: Clarification US3; FR-007 / FR-012 / SC-003.
- **Alternatives considered**:
  - Aderência como visual principal agora — rejeitado (sem dado 011).
  - Plotar todos os ciclos encerrados — rejeitado (FR-007).
  - Inventar nota final / 9-box temporal — denylist.

---

## R6 — KPIs não misturam arquivo com operação

- **Decision**: `_ciclos_resumo` atual (`total` / `encerrados` / `percentual_encerrados`) **sai** dos KPIs de “saúde da operação”. Com 57 encerrados Sólides, “X% encerrados” é arquivo, não pipeline.

  KPIs operacionais (1–3, Freeze C): totais/gargalo do **ciclo aberto** (avaliações no pipeline, pendências, “sem avaliação”). Arquivo, se aparecer, é copy/seletor (“N ciclos no arquivo”), nunca percentual de governança. Aderência média só com snapshot real do ciclo operacional; senão empty da seção.

  Em ciclo histórico **escolhido explicitamente**, KPIs descrevem **aquele** ciclo (processo/etapa), com empty de desempenho se não houver nota — e a home operacional não herda esses números.
- **Rationale**: FR-004 / FR-009 / FR-013; `templates/dashboard/admin.html` hoje prioriza “ciclos encerrados”.
- **Alternatives considered**: Manter % encerrados como KPI terciário — rejeitado (ainda mistura saúde).

---

## R7 — Pipeline de etapas = visual principal operacional

- **Decision**: Visual principal das homes admin/time (e detalhe de ciclo no modo operacional) = `bar_horizontal` monocromática de etapas + `sem_avaliacao`, amber no gargalo (já existe no time / catálogo 009). Doughnut + valor central permanece **só** para aderência (Status Triad). Tendência = `area`. Ranking/atenção = `bar_horizontal`. Hierarquia Freeze C: 1–3 KPIs → pipeline → drill (tabela). Grid off, pouco ink, sem figcaption duplicando label+valor em barras (já no `_chart_block` para `bar` / `bar_horizontal`).
- **Rationale**: FR-005 / FR-014; DS Charts polish (etapas ≠ rosca arco-íris).
- **Alternatives considered**: Doughnut por etapa — rejeitado no DS 009 (“≥5–7 fatias”). Empilhada temporal como principal operacional — rejeitado (isso é US3).

---

## R8 — Freeze: acrescer densidade/histórico/leveza (FR-019); não reabrir A/B/C

- **Decision**: Formalizar no Freeze v2 uma incrementação **D** em `docs/design-system.md` **na mesma entrega**: teto Top-N+Outros, default operacional vs modo histórico, taxonomia de empty, leveza (grid off, pouco ink, catálogo já existente). Contratos 009 de catálogo/painel/detalhe de ciclo = **referência intacta**. Tokens novos só se o toggle/seletor exigir classe em `input.css` (rebuild Tailwind na mesma entrega). Sem SPA, sem lib, Chart.js **4.5.1**.
- **Rationale**: FR-014 / FR-019 / SC-004 / SC-005.
- **Alternatives considered**: Só código sem DS — rejeitado (FR-019). Reabrir paleta/shell/nav — denylist 009.

---

## R9 — Agregação síncrona; Celery só com evidência (Princípio VI)

- **Decision**: Counts/`annotate` no request sobre querysets já escopados (mesmo padrão 009). Aderência **continua** leitura de `AderenciaSnapshot` (Celery Beat existente); **não** chamar `compute_adherence`. Tendência US3 = `Count` agrupado por `ciclo_id` × etapa, limitado a ≤8 ciclos × escopo — ~700 cabeçalhos é volume irrelevante para sync. Task/snapshot novo **somente** se medição local mostrar peso vs SC-001 (< 3 s percebidos); aí registrar em Complexity Tracking.
- **Rationale**: FR-020; clarificação Celery; 009 R8.
- **Alternatives considered**: Snapshot genérico “painel do ciclo” nesta entrega — prematuro.

---

## R10 — AuthZ só backend; builders recebem `visible`

- **Decision**: Zero mudança em `get_visible_users` / `ScopedObjectMixin` / mixins de papel. Helpers de densidade/tendência **recebem** o QS já resolvido pela view (precedente `build_structure_coverage`). Admin: `RequiresAdminMixin`. Time: `RequiresLeaderMixin` + visible. Detalhe de ciclo: `AdminCyclesMixin` vigente. UI nunca autoriza.
- **Rationale**: Constituição II; FR-010.
- **Alternatives considered**: Filtrar ciclos no template — rejeitado.

---

## R11 — Allowlist / denylist no formato 009

- **Decision**: Contratos [path-allowlist.md](./contracts/path-allowlist.md) + [non-goals-denylist.md](./contracts/non-goals-denylist.md). Denylist explícita do pedido: `stage.py`, `cycle.py` (open/close), `approval.py`, `evaluation.py` (mutators), `adherence.py` (fórmulas), `scope.py`, snapshots write-once, migrations de nota, 6.5.5, PDI. Sem rotas novas. Sem DRF/SPA/lib/plugin npm.
- **Rationale**: FR-018; precedente 008/009.
- **Alternatives considered**: Diff “só UI” sem contrato — rejeitado.

---

## R12 — Painel pessoal: densidade + empty + estética; sem US3

- **Decision**: `dashboard/personal` entra no 100% de charts (Top-N de competências, empty honesto de gap/nota, leveza Freeze D). **MUST NOT** ganhar `visao=historico` nem série entre ciclos. Gap agrupado já preserva `null` ≠ 0.
- **Rationale**: Clarification “painel pessoal”.
- **Alternatives considered**: Tendência pessoal — fora desta fatia.

---

## R13 — HTMX: chart fora do partial (invariante)

- **Decision**: `team_list_partial.html` / `adherence_list_partial.html` / `ciclo_list_partial.html` **não** incluem `_chart_block`. Toggle histórico e troca de ciclo = GET da página. `dashboard_charts.js` permanece init em `DOMContentLoaded` (sem `htmx:afterSwap` nesta fatia, a menos que um partial passe a conter canvas — proibido).
- **Rationale**: FR-017; init atual linha ~587 de `dashboard_charts.js`.
- **Alternatives considered**: Reinit genérico HTMX — complexidade sem ganho se o canvas não está no swap.

---

## R14 — Testes e fixtures

- **Decision**: pytest-django das superfícies dashboard/ciclo (default aberto, empty operacional, Top-N, modo histórico, empty `sem_nota`, escopo). Regressão obrigatória: `tests/test_stage_machine.py`, `tests/test_scope.py`, `tests/test_reject_stage_invariant.py` **sem** alterar asserts de domínio. Fixtures via factories/`conftest` (N de ciclos suficiente para teto, ex. 12–20) — **nunca** `data/legado-solides/raw/`. Reusar/estender `test_chart_payloads.py`, `test_structure_coverage.py`, `test_ciclo_detail.py`.
- **Rationale**: Pedido do plan + SC-007; precedente 011 (samples, não raw).
- **Alternatives considered**: Testar contra dump raw — rejeitado (PII / CI).

---

## R15 — Agent context script

- **Decision**: Script `update-agent-context` **não existe** neste repositório (`.specify/scripts` só PowerShell de feature setup; `pwsh` também ausente no host — setup-plan replicado em bash). Skip documentado; artefatos em `specs/012-gerencial-historico-legado/` são a fonte de verdade (precedente 008/009).
- **Rationale**: Inventário de scripts.
- **Alternatives considered**: Inventar script ad hoc — fora do workflow Speckit neste monólito.

---

## R16 — Stack e reuso (sem NEEDS CLARIFICATION)

| Tópico | Resolução |
|--------|-----------|
| Linguagem | Python 3.x / Django 6.0.7 (desvio 5.x pré-existente) |
| UI | DTL + HTMX + Tailwind CLI |
| Charts | Chart.js **4.5.1** CDN; `dashboard_charts.js`; `_chart_block.html`; `chart_payloads.py`; `.managerial-panel` |
| AuthZ | Mixins + `get_visible_users` intactos |
| Persistência | Zero models/migrations |
| Métrica nova | Proibida; plotar etapa/conclusão, cobertura, aderência-snapshot já existentes |
| Volume | ~57 ciclos encerrados + ~700 cabeçalhos sem nota — densidade e empty, não schema |
