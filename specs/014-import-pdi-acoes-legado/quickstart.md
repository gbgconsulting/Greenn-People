# Quickstart: Validação — Importação PDI e Ações do Legado

**Branch**: `014-import-pdi-legado` | **Date**: 2026-08-19

Guia de validação end-to-end conforme [spec.md](./spec.md). Modelo: [data-model.md](./data-model.md). Contratos: [contracts/](./contracts/).

**Não** inclui corpos de implementação, migrations ou suíte completa — isso fica em `/speckit-tasks`.

---

## Ordem segura

```text
003 catálogo
  → 010 colaboradores (incl. inativos; PDI.solides_id no schema)
  → (opcional) 011 ciclos + 013 notas — NÃO bloqueiam esta fatia
  → **esta feature (014 / README passo 7)** PDI + 1 ação
  → (leitura) telas PDI vigentes + 012 painéis — não alterar aqui
```

Pré-condição dura: **003 + 010**. **Zero** `migrate` desta fatia. Staging: `--dry-run` **primeiro**.

---

## C0 — Gate denylist / git diff (obrigatório antes de merge)

```bash
export DJANGO_SETTINGS_MODULE=config.settings.dev

# Base da feature: ajustar se o merge-base não for `development`.
git diff development -- \
  apps/cycles/services/stage.py \
  apps/cycles/services/cycle.py \
  apps/goals/services/approval.py \
  apps/accounts/services/scope.py \
  apps/reviews/services/evaluation.py \
  apps/dashboard/services/adherence.py \
  apps/dashboard/urls.py \
  apps/cycles/urls.py \
  apps/pdi/models.py \
  apps/pdi/views.py \
  apps/pdi/urls.py \
  apps/pdi/forms.py \
  apps/pdi/services/overdue.py \
  apps/pdi/services/progress.py \
  apps/pdi/tasks.py \
  apps/talent

git diff development -- '**/migrations/**'
```

**Esperado**: diffs **vazios**. Allowlist: [contracts/model-allowlist.md](./contracts/model-allowlist.md). Denylist: [contracts/non-goals-denylist.md](./contracts/non-goals-denylist.md).

**CI nunca lê `data/legado-solides/raw/`.** Homologação com backups brutos é **manual**, em staging/banco descartável.

---

## Pré-requisitos

- Python 3.x, `pip install -r requirements.txt` (openpyxl já via 010 — sem nova lib)
- Specs **003** e **010** aplicadas
- Fonte CI / local: `data/legado-solides/samples/pdi_min.xlsx`
- Fonte staging (PII — **manual**, nunca CI): `data/legado-solides/raw/backup_pdi_*.xlsx`

---

## Comando

```bash
# Preview sem gravar (samples)
python manage.py importar_pdi \
  --pdi data/legado-solides/samples/pdi_min.xlsx \
  --dry-run

# Persist local / CI fixture
python manage.py importar_pdi \
  --pdi data/legado-solides/samples/pdi_min.xlsx \
  --report-file /tmp/relatorio-pdi-legado.txt

# Carga real (staging — path raw; MANUAL)
python manage.py importar_pdi \
  --pdi data/legado-solides/raw/backup_pdi_20260624.xlsx \
  --dry-run
python manage.py importar_pdi \
  --pdi data/legado-solides/raw/backup_pdi_20260624.xlsx \
  --report-file /tmp/relatorio-pdi-legado.txt
```

Contrato CLI: [contracts/import-command-contract.md](./contracts/import-command-contract.md).  
Stdout **MUST** coincidir com `--report-file`.

---

## Cenários de validação

### C1 — Dry-run samples (US3 / SC-006)

| Passo | Ação | Esperado |
|---|---|---|
| 1 | Contar `PDI` / `AcaoPDI` | N0, M0 |
| 2 | `--dry-run` com `pdi_min.xlsx` | exit 0; totais projetados; seções do contrato |
| 3 | Contar depois | N0, M0 inalterados |

### C2 — Persist 1 PDI + 1 ação (US1)

| Passo | Ação | Esperado |
|---|---|---|
| 1 | Linha resolvível (pessoa única, título, status conhecido, prazo, ≥1 trecho) | 1 `PDI` + 1 `AcaoPDI` |
| 2 | Concatenação | só trechos não vazios, ordem Objetivo → Situação Atual → Situação Desejada, separador `\n\n` |
| 3 | Responsável | `acao.responsavel_id == pdi.usuario_id` |
| 4 | Ciclo/avaliação | zero FK |

### C3 — Órfão / ambíguo (US2)

| Passo | Ação | Esperado |
|---|---|---|
| 1 | Nome sem User | `orfaos_usuario`; zero User inventado |
| 2 | Duas pessoas mesma `canonical_key` | órfão; nunca o “primeiro” |
| 3 | ID pessoa vs nome único divergente | conflito `id_vs_nome` |

### C4 — Inativo ok (US2 / FR-020)

| Passo | Ação | Esperado |
|---|---|---|
| 1 | Match único em User `is_active=False` | PDI persiste |
| 2 | Leitura posterior | escopo vigente; inativo **não** cria atalho; `test_scope` intacto |

### C5 — Status de-para + atraso (FR-010/FR-011)

| Passo | Ação | Esperado |
|---|---|---|
| 1 | `finalizado` | PDI `concluido`; ação `concluida` (**nunca** atrasada) |
| 2 | `em_andamento` + prazo < hoje | PDI `ativo`; ação `atrasada` |
| 3 | `em_andamento` + prazo ≥ hoje | PDI `ativo`; ação `pendente` |
| 4 | Status desconhecido / prazo ilegível / descrição vazia | conflito; zero `arquivado`; zero prazo inventado |
| 5 | Spy | `mark_overdue_pdi_actions` **não** chamado; `overdue.py` diff vazio |

### C6 — Digest ≠ nome concatenado (FR-008 / SC-007)

| Passo | Ação | Esperado |
|---|---|---|
| 1 | Ler `PDI.solides_id` | prefixo `pdi_` + 40 hex; len ≤ 50 |
| 2 | Comparar com `Nome+Título` em claro | **diferente** |
| 3 | Duas runs | mesmo digest |

### C7 — 2ª run delta 0 (SC-005)

| Passo | Ação | Esperado |
|---|---|---|
| 1 | Persist duas vezes a mesma fonte | exit 0 |
| 2 | Delta digest PDI | 0 |
| 3 | Delta chave ação `(pdi, display_name(descricao), prazo)` | 0 |
| 4 | Título/status | inalterados (sem rewrite silencioso) |

### C8 — PII mascarada (FR-018 / SC-008)

| Passo | Ação | Esperado |
|---|---|---|
| 1 | Sample com título/objetivo longos | persistem no DB |
| 2 | stdout e `--report-file` | idênticos; amostra ≤ 5; **sem** texto completo / nome / e-mail / linha bruta |

### C9 — Pytest samples-only (CI / SC-007)

```bash
pytest tests/test_import_pdi_legado.py -q
# Assert: nenhum teste abre data/legado-solides/raw/
```

Cobre: dry-run, 1+1, órfão, ambíguo, inativo, status, atraso, digest, idempotência, mascaramento, denylist gate.

### C10 — Gate stage / scope (SC-010)

```bash
pytest tests/test_stage_machine.py tests/test_scope.py tests/test_reject_stage_invariant.py -q
```

**Esperado**: verde **sem** alterar asserts. Após import, IDOR fora da hierarquia → 404 (comportamento vigente das views — **não** editadas).

---

## Homologação dump real (staging — MANUAL)

**Nunca** instruir o CI a ler `raw/`.

| Check | Esperado (dump 2026-06-24) |
|---|---|
| Linhas processadas | ~86 (persistidas / inalteradas / conflito / órfão) — SC-001 |
| Recorte status | 67 `finalizado` / 19 `em_andamento` **não invertido** — SC-011 |
| 1+1 | 100% resolvíveis = 1 PDI + 1 ação — SC-002 |
| Tempo operador | < 10 min carga humana + < 3 min revisão relatório — SC-008/SC-009 |
| 2ª run | delta 0 — SC-005 |

Simulação (`--dry-run`) **obrigatória** antes do persist em staging.

---

## Referências rápidas

| Artefato | Conteúdo |
|---|---|
| [research.md](./research.md) | Decisões R1…R10 + R-digest / R-atraso / R-idempotência / R-ordem / R-PII |
| [contracts/column-mapping-contract.md](./contracts/column-mapping-contract.md) | Colunas README, `\n\n`, datas, digest |
| [contracts/import-command-contract.md](./contracts/import-command-contract.md) | CLI / atomicidade / exit / relatório |
| [contracts/model-allowlist.md](./contracts/model-allowlist.md) | Único diff de código permitido |
| [contracts/non-goals-denylist.md](./contracts/non-goals-denylist.md) | Teste de ouro FR-021 |
| [contracts/migration-safety.md](./contracts/migration-safety.md) | Zero migrations |
| [data/legado-solides/README.md](../../data/legado-solides/README.md) | Inventário, PII, ordem segura passo 7 |
