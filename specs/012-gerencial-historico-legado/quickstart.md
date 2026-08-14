# Quickstart: Validação 012 — Visualizações gerenciais e históricas pós-legado

**Branch**: `012-Visualização-pós-legado`  
**Pré-requisitos**: ambiente Django local com spec **011 aplicada** (ciclos encerrados + cabeçalhos sem nota no banco) **ou** fixtures de teste equivalentes; um usuário admin (Marina) e um líder com escopo (Bruno); Tailwind rebuild se `input.css` mudar.

Contratos: [contracts/](./contracts/). Modelo lógico: [data-model.md](./data-model.md). Catálogo visual 009 (não reabrir): `chart-catalog` / `managerial-panel` / `cycle-managerial-detail`.

## Setup

```bash
# na raiz do repo
source .venv/bin/activate  # se aplicável
python manage.py migrate
python manage.py runserver
# se input.css alterado:
# npx --yes @tailwindcss/cli -i static/src/input.css -o static/css/tailwind.css
```

Não apontar testes para `data/legado-solides/raw/`.

---

## Sequência de validação (espelha prioridade)

### 0) Gate de escopo inválido

- Diff **não** toca denylist ([path-allowlist.md](./contracts/path-allowlist.md) / [non-goals-denylist.md](./contracts/non-goals-denylist.md)).
- Regressão de domínio verde, **sem** asserts de etapa/escopo/rejeição alterados:

```bash
pytest tests/test_stage_machine.py tests/test_scope.py \
  tests/test_reject_stage_invariant.py
```

### 1) US1 — Operação RH sem o arquivo explodir (P1)

Pré-condição A: **zero** ciclo aberto + dezenas de encerrados.

| # | Ação | Esperado |
|---|------|----------|
| 1.1 | GET `/dashboard/admin/` | Empty operacional honesto e leve; **nenhum** ciclo encerrado selecionado em silêncio; sem gráfico fantasma |
| 1.2 | KPIs | Não mostram “saúde” como % de ciclos encerrados do arquivo Sólides |
| 1.3 | Lista `/cycles/` | Aberto (nenhum) vs arquivo agrupado/paginado; sem parede de rótulos |
| 1.4 | Seletor/arquivo explícito → um ciclo legado | Acessa aquele ciclo; home operacional **não** passa a defaultar nele |
| 1.5 | Detalhe `cycles/<pk>/` de cabeçalho `concluida` sem nota | Pipeline de etapa MAY aparecer; desempenho/gap/aderência empty ou “sem nota” — não “100% saudável” |
| 1.6 | Pessoal `/` | Densidade (Top-N competências) + empty honesto + estética; **sem** toggle de tendência |

Pré-condição B: **um** ciclo aberto operacional.

| # | Ação | Esperado |
|---|------|----------|
| 1.7 | Admin | Pipeline de etapas = visual principal; KPIs só desse ciclo; arquivo fora dos eixos |
| 1.8 | Categorias longas (área/cargo) | Top-N + “Outros”; nenhum eixo com 50+ rótulos |
| 1.9 | Viewport ~375px | KPI → visual → drill sem scroll horizontal do canvas |

### 2) US2 — Time / estrutura / aderência (P1)

| # | Ação | Esperado |
|---|------|----------|
| 2.1 | Líder, ciclo aberto → `/dashboard/team/` | 1–3 KPIs → pipeline do escopo (incl. sem avaliação) → drill; só `get_visible_users` |
| 2.2 | Líder, sem ciclo aberto | Empty operacional; sem série inventada |
| 2.3 | Estrutura | Cobertura ≠ aderência; Top-N + Outros; empty se sem aberto |
| 2.4 | Aderência | Doughnut só com snapshot; senão empty; seletor agrupado |
| 2.5 | HTMX paginação da tabela | Canvas da página intacto (partial sem `_chart_block`) |
| 2.6 | ~375px | Pilha consultável |

### 3) US3 — Tendência explícita (P2)

| # | Ação | Esperado |
|---|------|----------|
| 3.1 | Admin ou time **sem** `visao=` | Home continua operacional (não tendência) |
| 3.2 | `?visao=historico` | `area` de etapa/conclusão dos últimos **8** ciclos do escopo; evoluiu / estável / sem dado |
| 3.3 | `?visao=historico&ciclos=` | Só os ids pedidos, ainda cap 8; nunca ~57 séries |
| 3.4 | Série de nota/gap/aderência | Empty `sem_nota` até haver dado; `null` ≠ 0 |
| 3.5 | Pessoal | MUST NOT expor `visao=historico` |
| 3.6 | Sem página `/historico/` | Toggle/query nas URLs já existentes |

### 4) 100% charts + Freeze D

- Todas as superfícies com chart (admin, time, estrutura, aderência, detalhe/lista ciclo, pessoal) passam densidade + empty + leveza (grid off, pouco ink, doughnut+centro, `bar_horizontal` ranking, `area` tendência).
- `docs/design-system.md` contém Freeze D (FR-019) se o contrato entrou no Freeze — esperado: **sim**.
- Network: Chart.js **4.5.1**; sem lib adicional; `base.html` sem Chart.js.

---

## Comandos de teste (orientação)

```bash
pytest tests/test_dashboard_operational_default.py \
  tests/test_dashboard_history_mode.py \
  tests/test_chart_payloads.py tests/test_structure_coverage.py \
  tests/test_ciclo_detail.py \
  tests/test_stage_machine.py tests/test_scope.py \
  tests/test_reject_stage_invariant.py
```

---

## Evidências sugeridas

- Admin sem ciclo aberto: screenshot empty operacional (SC-001).
- Admin com ciclo aberto: pipeline + KPIs só desse ciclo (SC-002).
- Time `?visao=historico`: área N≤8 (SC-003).
- Side-by-side vs 009: hierarquia KPI → visual → drill preservada, mais arejada (SC-005).
- ~375px sem overflow de canvas (SC-006).
- Diff denylist vazio + regressão verde (SC-007).
