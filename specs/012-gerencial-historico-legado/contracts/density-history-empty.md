# Contract: Densidade, histórico e empty vs operacional

**Feature**: `012-gerencial-historico-legado`  
**Alinha a**: [spec.md](../spec.md) FR-001–009, FR-012–016, FR-019 · [plan.md](../plan.md) · [research.md](../research.md) R1–R8 · Freeze D (atualizar `docs/design-system.md` na mesma entrega)  
**Reusa (não reabre)**: `specs/009-persona-visual-redesign/contracts/{chart-catalog,managerial-panel,cycle-managerial-detail}.md`

Shape JSON de chart permanece o canônico 009 (`has_data`, `type`, `labels`, `values` / `series`, `colors`, `legend_items`, `empty_message`, `total?`). Types: `doughnut` + centro, `bar_horizontal`, `area`, `bar_grouped` só para duas séries já existentes.

---

## 1. Default operacional vs arquivo

| Regra | MUST / MUST NOT |
|-------|-----------------|
| Default das homes admin, time, estrutura, aderência | MUST ser o ciclo **aberto** (`get_open_ciclo()`) |
| Sem ciclo aberto | MUST empty `operacional`; MUST NOT selecionar encerrado em silêncio |
| `?ciclo=<pk>` | MUST carregar aquele ciclo **só** com intenção explícita (seletor) |
| KPIs de operação | MUST refletir o ciclo aberto (ou o explicitamente escolhido); MUST NOT usar `percentual_encerrados` / total do arquivo como saúde |
| `ciclo_detail` | O `pk` já é escolha explícita — permitido mostrar pipeline **daquele** ciclo |

Seletor: operacional em destaque (`<optgroup>`); arquivo agrupado, ordenado por data, buscável se > 20 (`q`). Lista de ciclos: aberto destacado; paginação vigente.

---

## 2. Modo histórico (US3) ≠ seletor

| Aspecto | Contrato |
|---------|----------|
| Ativação | GET `visao=historico` na mesma URL (toggle). Sem rota nova, sem item de nav “Histórico” |
| Superfícies | `dashboard/admin`, `dashboard/team`, `cycles/<pk>/` |
| Fora | `dashboard/personal`, e nesta fatia **não** estrutura/aderência |
| Visual | `area` de **etapa/conclusão** nos últimos `HISTORY_DEFAULT_N = 8` ciclos do escopo |
| Cap | MUST NOT plotar o arquivo completo; `?ciclos=` honra o mesmo teto |
| Aderência / gap | `has_data: false` + empty `sem_nota` até existir dado — MUST NOT ser o visual principal agora |
| Lacuna na série | `null` no ponto; MUST NOT 0 de desempenho |
| Home | Permanece operacional até o toggle |

O seletor de um ciclo **não** substitui esta superfície de tendência (FR-003).

---

## 3. Densidade (100% dos charts da fatia)

`DENSITY_TOP_N = 8`.

| Chart | Corte |
|-------|-------|
| Cobertura área/cargo, rankings, eixos longos | Top-N + rótulo `"Outros"` (soma ou cobertura ponderada por totais) |
| Gap pessoal `bar_grouped` | Top-N por \|gap\| com nota; resto omitido (sem média inventada) |
| Pipeline de etapas | Conjunto fechado — sem Top-N |
| Doughnut aderência | 3 fatias Status Triad — sem Top-N |

MUST NOT renderizar dezenas de rótulos crus. Viewport ~375px: sem scroll horizontal do canvas (pilha KPI → visual → drill).

---

## 4. Empty honesto

| Kind | Trigger | Série |
|------|---------|-------|
| `operacional` | Sem aberto na home gerencial | Nenhuma (não plotar arquivo) |
| `escopo` | Visible vazio | Nenhuma |
| `sem_dado` | Sem avaliações / sem snapshot na seção | Só aquela seção |
| `sem_nota` | Desempenho/gap/aderência sem dado (legado 011) | Só a série de desempenho; pipeline de etapa MAY permanecer |

`has_data !== true` → `_chart_block` usa `empty_state`; MUST NOT gráfico cinza fantasma nem série fictícia.

Cabeçalho `etapa=feedback` + `concluida=True` **sem nota** ≠ “ciclo 100% saudável de desempenho”.

---

## 5. Leveza (Freeze D — estética)

Alinhado ao catálogo 009 / Charts polish; esta fatia **exige** cumprimento em 100% das superfícies com chart:

- Grid de valor / eixos ruidosos **off** (já em `dashboard_charts.js`)
- Pouco ink; sem sombra extra no frame
- Datalabel só com N baixo; barras longas → tooltip + Top-N
- Doughnut: valor central + legenda texto
- Ranking/atenção: `bar_horizontal`
- Tendência: `area` suave
- Grouped só para duas séries já existentes (esperado × nota)
- Status Triad intacta; informação não depende só da cor
- Sem figcaption que repita label+valor em `bar` / `bar_horizontal`
- Pipeline = visual principal operacional (não a tabela)

Documentar estas regras em `docs/design-system.md` na mesma entrega (FR-019).

---

## 6. HTMX

Partials de lista (`team_list_partial`, `adherence_list_partial`, `ciclo_list_partial`) MUST NOT incluir `_chart_block`. Swap de lista MUST deixar o canvas da página íntegro. Toggle histórico / troca de ciclo = GET completo.

---

## Non-goals deste contrato

Trocar Chart.js; plugin npm; página de histórico; métrica nova; importar notas; relaxar AuthZ; reabrir Freeze A/B/C de paleta/shell; tendência no painel pessoal.
