# Quickstart: Validação — Importação Ciclos Históricos e Cabeçalhos de Avaliação

**Branch**: `011-import-ciclos-avaliacoes-legado` | **Date**: 2026-08-13

Guia de validação end-to-end conforme [spec.md](./spec.md). Modelo: [data-model.md](./data-model.md). Contratos: [contracts/](./contracts/).

---

## Ordem segura completa

```text
003 catálogo
  → 010 colaboradores (+ schema solides_id users/Avaliação)
  → **esta feature** (Ciclo.solides_id + import ciclos/cabeçalhos)
  → (futuro) notas/comentários 6.5.5
```

---

## §0 — Gate de regressão (C0 — obrigatório antes de merge)

```bash
export DJANGO_SETTINGS_MODULE=config.settings.dev

# Denylist diff MUST be empty (inclui cycle.py open/close e stage.py)
git diff main -- \
  apps/cycles/services/stage.py \
  apps/cycles/services/cycle.py \
  apps/goals/services/approval.py \
  apps/accounts/services/scope.py \
  apps/reviews/services/evaluation.py \
  apps/dashboard/services/adherence.py

pytest tests/test_stage_machine tests/test_scope tests/test_reject_stage_invariant -q
pytest tests/test_import_ciclos_avaliacoes_legado.py -q
```

**Esperado**: diff denylist vazio; todos os testes verdes.

Allowlist: [contracts/model-allowlist.md](./contracts/model-allowlist.md).  
Denylist: [contracts/non-goals-denylist.md](./contracts/non-goals-denylist.md).

---

## Pré-requisitos

- Python 3.x, `pip install -r requirements.txt` (openpyxl já via 010 — sem nova lib)
- Specs **003** e **010** aplicadas no ambiente alvo
- Migration desta feature (`Ciclo.solides_id`) — ver C1
- Fontes operacionais (staging — PII):
  - `data/legado-solides/raw/backup_solicitacoes_avalicaoes_20260624.xlsx`
  - `data/legado-solides/raw/backup_avaliacoes_20260624.xlsx`

**CI / dev local**: usar apenas `data/legado-solides/samples/*.xlsx` (anonimizadas).

---

## Comando

```bash
# Preview sem gravar
python manage.py importar_ciclos_avaliacoes \
  --solicitacoes data/legado-solides/samples/solicitacoes_min.xlsx \
  --avaliacoes data/legado-solides/samples/avaliacoes_headers_min.xlsx \
  --dry-run

# Carga real (staging — paths raw)
python manage.py importar_ciclos_avaliacoes \
  --solicitacoes data/legado-solides/raw/backup_solicitacoes_avalicaoes_20260624.xlsx \
  --avaliacoes data/legado-solides/raw/backup_avaliacoes_20260624.xlsx \
  --report-file /tmp/relatorio-ciclos-avaliacoes-legado.txt
```

Contrato CLI: [contracts/import-command-contract.md](./contracts/import-command-contract.md).

---

## Cenários de validação

### C1 — Schema `Ciclo.solides_id`

| Passo | Ação | Esperado |
|---|---|---|
| 1 | `python manage.py migrate cycles` | Migration aditiva ok |
| 2 | Shell: criar Ciclo sem `solides_id` | Aceito (null) |
| 3 | Dois ciclos com mesmo `solides_id` non-null | IntegrityError |
| 4 | Fluxo manual abrir/encerrar ciclo existente | Intact (SC-001) |

Ver [contracts/migration-safety.md](./contracts/migration-safety.md).

### C2 — Dry-run (US3)

| Passo | Ação | Esperado |
|---|---|---|
| 1 | Contar `Ciclo` / `Avaliacao` antes | N0, M0 |
| 2 | `--dry-run` com samples | exit 0; totais projetados; relatório com seções |
| 3 | Contar depois | N0, M0 inalterados (SC-005) |

### C3 — Import ciclos (todos encerrados) (US1)

| Passo | Ação | Esperado |
|---|---|---|
| 1 | Persist com fixture contendo finished/draft/active/canceled | exit 0 |
| 2 | Query ciclos importados | 100% `status=encerrado` |
| 3 | Zero `status=aberto` criado pela importação | SC-002 |
| 4 | Nome serial Excel (ex. fixture `46113.0`) | Rótulo legível ISO, não bruto |
| 5 | Linha sem datas | Conflito; ciclo não criado |

### C4 — Import cabeçalhos + agregação multi-avaliador (US2)

| Passo | Ação | Esperado |
|---|---|---|
| 1 | Fixture com N linhas mesmo (solicitação, avaliado), avaliadores distintos | 1 Avaliacao |
| 2 | `solides_id` | Canônico (auto se existir; senão min ID) |
| 3 | Relatório | `grupos_agregados` ≥ 1; `ids_colapsados` amostra |
| 4 | `etapa` / `concluida` | `feedback` / `True` |
| 5 | `nota_final_*` | null / intocado |

Ver [contracts/aggregation-contract.md](./contracts/aggregation-contract.md).

### C5 — Órfão sem usuário

| Passo | Ação | Esperado |
|---|---|---|
| 1 | Avaliado com ID sem `CustomUser` correspondente e nome sem match | `orfaos_usuario` no relatório |
| 2 | Contagem users | Inalterada (zero inventado) |
| 3 | Ciclo referenciado ausente | `orfaos_ciclo`; zero Ciclo inventado |

### C6 — Idempotência

| Passo | Ação | Esperado |
|---|---|---|
| 1 | Executar persist duas vezes com mesmas fontes | exit 0 |
| 2 | Contagem Ciclo por `solides_id` | Delta = 0 (SC-006) |
| 3 | Contagem Avaliacao por `(ciclo, usuario)` | Delta = 0 |

### C7 — Pytest samples-only (CI)

```bash
pytest tests/test_import_ciclos_avaliacoes_legado.py -q
# Assert: nenhum teste abre data/legado-solides/raw/
```

**Esperado**: dry-run, agregação, órfãos, idempotência, status sempre encerrado, denylist gate cobertos (SC-007).

---

## Dump real (staging — opcional pós-samples)

| Check | Esperado (dump 2026-06-24) |
|---|---|
| Solicitações elegíveis | ~57 ciclos encerrados |
| Status mix legado | 50 finished + 1 active + 3 draft + 3 canceled → todos encerrados |
| Cabeçalhos | Grupos agregados ≤ 1925; zero duplicata `(ciclo, usuario)` |
| Cobertura usuários | ≥95% grupos com avaliado resolvido → Avaliacao (SC-004) |
| Tempo operador | < 10 min carga + < 3 min revisão relatório (SC-009) |

---

## Referências rápidas

| Artefato | Conteúdo |
|---|---|
| [research.md](./research.md) | Decisões R1–R14 (clarifications implementadas) |
| [contracts/column-mapping-contract.md](./contracts/column-mapping-contract.md) | Colunas solicitações/avaliações |
| [contracts/aggregation-contract.md](./contracts/aggregation-contract.md) | 1:1 + canônico + colapsados |
| [contracts/import-command-contract.md](./contracts/import-command-contract.md) | CLI / exit / relatório |
| [data/legado-solides/README.md](../../data/legado-solides/README.md) | Inventário e ordem segura |
