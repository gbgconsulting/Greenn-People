# Quickstart: Validação — Importação Notas e Comentários do Legado

**Branch**: `013-import-notas-comentarios-legado` | **Date**: 2026-08-18

Guia de validação end-to-end conforme [spec.md](./spec.md). Modelo: [data-model.md](./data-model.md). Contratos: [contracts/](./contracts/).

**Não** inclui corpos de implementação, migrations ou suíte completa — isso fica em `/speckit-tasks`.

---

## Ordem segura completa

```text
003 catálogo
  → 010 colaboradores
  → 011 ciclos + cabeçalhos (ids_colapsados reconstruíveis)
  → **esta feature (013)** notas + comentários
  → (leitura) 012 painéis — não alterar aqui
```

Pré-condição dura: 003 + 010 + 011 no ambiente alvo. **Zero** `migrate` desta fatia.

---

## §0 — Gate de regressão (obrigatório antes de merge)

```bash
export DJANGO_SETTINGS_MODULE=config.settings.dev

git diff main -- \
  apps/cycles/services/stage.py \
  apps/cycles/services/cycle.py \
  apps/goals/services/approval.py \
  apps/accounts/services/scope.py \
  apps/reviews/services/evaluation.py \
  apps/dashboard/services/adherence.py \
  apps/dashboard/urls.py \
  apps/cycles/urls.py \
  apps/pdi \
  apps/talent

pytest tests/test_stage_machine tests/test_scope tests/test_reject_stage_invariant -q
pytest tests/test_import_notas_comentarios_legado.py -q
```

**Esperado**: diff denylist **vazio**; testes verdes; **asserts** de stage/scope/reject **não** alterados.

Allowlist: [contracts/model-allowlist.md](./contracts/model-allowlist.md).  
Denylist: [contracts/non-goals-denylist.md](./contracts/non-goals-denylist.md).

**CI nunca lê `data/legado-solides/raw/`.** Homologação com backups brutos é **manual**, em staging/banco descartável.

---

## Pré-requisitos

- Python 3.x, `pip install -r requirements.txt` (openpyxl já via 010 — sem nova lib)
- Specs **003**, **010**, **011** aplicadas
- Fontes CI / local (anonimizadas):
  - `data/legado-solides/samples/` — notas, comentários, cabeçalhos 011 (reusar sample de avaliações da 011)
- Fontes staging (PII — **manual**, nunca CI):
  - `data/legado-solides/raw/backup_notas_avaliacoes_20260624.xlsx`
  - `data/legado-solides/raw/backup_comentarios_avaliacoes_20260624.xlsx`
  - `data/legado-solides/raw/backup_avaliacoes_20260624.xlsx`

---

## Comando

```bash
# Preview sem gravar (samples)
python manage.py importar_notas_comentarios \
  --notas data/legado-solides/samples/notas_min.xlsx \
  --comentarios data/legado-solides/samples/comentarios_min.xlsx \
  --avaliacoes data/legado-solides/samples/avaliacoes_headers_min.xlsx \
  --dry-run

# Carga real (staging — paths raw; MANUAL)
python manage.py importar_notas_comentarios \
  --notas data/legado-solides/raw/backup_notas_avaliacoes_20260624.xlsx \
  --comentarios data/legado-solides/raw/backup_comentarios_avaliacoes_20260624.xlsx \
  --avaliacoes data/legado-solides/raw/backup_avaliacoes_20260624.xlsx \
  --report-file /tmp/relatorio-notas-comentarios-legado.txt
```

`--habilidades` só se a run precisar criar competência extra (FK).  
Contrato CLI: [contracts/import-command-contract.md](./contracts/import-command-contract.md).

---

## Cenários de validação

### C1 — Dry-run (US3 / SC-008)

| Passo | Ação | Esperado |
|---|---|---|
| 1 | Contar `AvaliacaoCompetencia` / `Feedback` / `nota_final_*` não-nulas | N0, M0, F0 |
| 2 | `--dry-run` com samples | exit 0; totais projetados; seções do contrato |
| 3 | Contar depois | N0, M0, F0 inalterados |

### C2 — Persist notas + snapshots (US1)

| Passo | Ação | Esperado |
|---|---|---|
| 1 | Sample com auto (`Nome Avaliador`=`Nome Avaliado`) e líder | auto só em `nota_autoavaliacao`; líder só em `nota_lider` |
| 2 | `peso_utilizado` | = `Fator no Momento` (não 1 inventado) |
| 3 | `nivel_esperado_utilizado` | = `nivel_esperado_for(cargo.nivel)` da 003; **não** `CargoCompetencia` vigente |
| 4 | Unique `(avaliacao, competencia)` | uma linha |

Ver [contracts/snapshot-and-formula.md](./contracts/snapshot-and-formula.md).

### C3 — ID canônico / colapsado / órfão (US1 / SC-006)

| Passo | Ação | Esperado |
|---|---|---|
| 1 | Nota com ID = `Avaliacao.solides_id` canônico | persiste nessa avaliação |
| 2 | Nota com ID colapsado do sample de cabeçalhos 011 | mesma avaliação canônica; **zero** 2ª `Avaliacao` |
| 3 | ID sem canônico nem mapa | `orfaos_avaliacao`; zero avaliação inventada |

Ver [contracts/collapsed-id-resolution.md](./contracts/collapsed-id-resolution.md).

### C4 — Dois líderes divergentes + ciclo aberto

| Passo | Ação | Esperado |
|---|---|---|
| 1 | Duas notas líder distintas no mesmo `(avaliacao, competencia)` | `conflitos_lider_divergente`; sem média |
| 2 | Avaliação em ciclo `status=aberto` | `conflitos_ciclo_aberto`; skip (SC-012) |

### C5 — Nota final via fórmula vigente

| Passo | Ação | Esperado |
|---|---|---|
| 1 | Avaliação com linhas de líder válidas | `nota_final_lider` preenchida por `calcular_nota_final_lider` |
| 2 | `git diff` `evaluation.py` | vazio |
| 3 | Spy: `create_competency_lines` | **não** chamado |
| 4 | Peso total zero / linha sem líder | conflito de cálculo; sem média inventada |

### C6 — Comentários (US2)

| Passo | Ação | Esperado |
|---|---|---|
| 1 | Comentário líder com `Criado em` parseável | `tipo=lider`; `ciente_em` preenchido; `etapa`/`concluida` inalterados |
| 2 | Comentário auto | `tipo=colaborador`; `ciente_em` null |
| 3 | Autor inativo (010) | permitido |
| 4 | Autor irresolvível | `orfaos_autor`; zero User inventado |
| 5 | N textos na mesma avaliação | todos persistidos |

### C7 — Idempotência / 2ª run (SC-005)

| Passo | Ação | Esperado |
|---|---|---|
| 1 | Persist duas vezes com as mesmas fontes | exit 0 |
| 2 | Delta unique `(avaliacao, competencia)` | 0 |
| 3 | Snapshots | 100% bit-a-bit estáveis |
| 4 | Feedback chave natural | sem duplicata |

### C8 — Habilidade extra vs órfão (SC-014)

| Passo | Ação | Esperado |
|---|---|---|
| 1 | Nota referencia extra não-KPI | `Competencia` mínima criada; **zero** `CargoCompetencia` |
| 2 | Nome KPI/ambíguo 003 | `orfaos_competencia`; competência **não** criada |
| 3 | Matriz 2.720 | **não** carregada |

### C9 — Pytest samples-only (CI / SC-009)

```bash
pytest tests/test_import_notas_comentarios_legado.py -q
# Assert: nenhum teste abre data/legado-solides/raw/
```

Cobre: dry-run, ID colapsado, órfão, dois líderes, write-once 2ª run, extra vs órfão, ciclo aberto, mascaramento PII, denylist gate.

### C10 — Relatório mascarado (SC-010)

Amostra ≤ 5/seção; zero comentário completo / nome / e-mail no stdout; totais completos.

---

## Homologação dump real (staging — MANUAL)

**Nunca** instruir o CI a ler `raw/`.

| Check | Esperado (dump 2026-06-24) |
|---|---|
| Notas processadas | ~7.360 (persistidas / atualizadas / inalteradas / conflito / órfão) — SC-001 |
| Auto vs líder | recorte ~2.213 / ~5.147 **não invertido** — SC-002 |
| Comentários | ~1.494 processados; líderes com ciência — SC-007 |
| Tempo operador | < 10 min carga humana + < 3 min revisão relatório — SC-010/SC-011 |
| 2ª run | snapshots estáveis — SC-005 |

Simulação (`--dry-run`) **obrigatória** antes do persist em staging.

---

## Referências rápidas

| Artefato | Conteúdo |
|---|---|
| [research.md](./research.md) | Decisões R1–R15 (clarifications implementadas) |
| [contracts/column-mapping-contract.md](./contracts/column-mapping-contract.md) | Colunas notas/comentários + serial Excel |
| [contracts/collapsed-id-resolution.md](./contracts/collapsed-id-resolution.md) | Consome aggregation-contract 011 |
| [contracts/snapshot-and-formula.md](./contracts/snapshot-and-formula.md) | Write-once; MUST call `calcular_*` |
| [contracts/import-command-contract.md](./contracts/import-command-contract.md) | CLI / atomicidade / exit / relatório |
| [data/legado-solides/README.md](../../data/legado-solides/README.md) | Inventário, PII, ordem segura |
