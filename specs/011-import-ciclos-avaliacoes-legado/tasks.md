# Tasks: Importação One-Shot do Legado Sólides — Ciclos Históricos e Cabeçalhos de Avaliação

**Input**: Design documents from `/specs/011-import-ciclos-avaliacoes-legado/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: Incluídos conforme FR-019, US3, research R14 e `contracts/migration-safety.md` §4 (`tests/test_import_ciclos_avaliacoes_legado.py` + fixtures em `data/legado-solides/samples/`). **Regressão obrigatória** stage/scope/`reject_stage_invariant` + diff denylist vazio (inclui `cycle.py` open/close). Nenhum teste referencia `data/legado-solides/raw/`.

**Organization**: Tasks por user story. **MVP = US1 + US2** (+ gate MVP). Depois **US3 (P2)**; Polish + gate final.

## Escopo inválido (REJEITAR task/PR)

Qualquer task que proponha alterar denylist ([contracts/non-goals-denylist.md](./contracts/non-goals-denylist.md)) é **INVÁLIDA**:

| Zona | Exemplos proibidos |
|------|--------------------|
| Máquina de estados | `apps/cycles/services/stage.py` — `advance_stage` / `can_advance` |
| Ciclos (serviços) | `apps/cycles/services/cycle.py` — `open_cycle` / `close_cycle` |
| Aprovação / reprovação | `apps/goals/services/approval.py` |
| AuthZ / escopo | `apps/accounts/services/scope.py`, `get_visible_users`, `ScopedObjectMixin` |
| Fórmulas / notas | `apps/reviews/services/evaluation.py`, preencher `nota_final_*` |
| Aderência | `apps/dashboard/services/adherence.py` |
| Conteúdo 6.5.5+ | `AvaliacaoCompetencia`, `Feedback`, PDI, comentários |
| Snapshots | Mutar `peso_utilizado` / `nivel_esperado_utilizado` |
| Schema existente | Alterar tipo/nullable/unique de campos existentes (exceto **ADICIONAR** `Ciclo.solides_id`) |
| Migrations extras | Qualquer migration em `reviews`/`accounts` nesta fatia; RunPython de domínio |
| Integridade | Alterar `on_delete` / remover constraints |
| Stack / UX | UI de upload, DRF, Celery, abrir ciclo ativo |
| Dependências | Nova lib em `requirements.txt` (openpyxl já na 010) |
| CI / OPSEC | Usar `data/legado-solides/raw/` em testes CI |

**Permitido apenas** (allowlist completa em [contracts/model-allowlist.md](./contracts/model-allowlist.md)): `Ciclo.solides_id` + migration em `apps/cycles`; `apps/cycles/services/legacy_import/**`; comando `importar_ciclos_avaliacoes`; extensão de `apps/accounts/services/legacy_import/{parse_xlsx,dates,report}.py`; `data/legado-solides/samples/**`; `tests/test_import_ciclos_avaliacoes_legado.py`; reuso read-only de `crosswalk`/`canonical_key`/`display_name` e ORM `reviews.Avaliacao` **sem** alteração de schema.

**Teste de ouro**: executar `importar_ciclos_avaliacoes` **não** chama stage/open/close/approval/evaluation/adherence/scope; grava só ciclos `encerrado` + cabeçalhos `etapa=feedback`/`concluida=True`; **não** inventa User/Ciclo; **não** preenche notas.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Pode rodar em paralelo (arquivos diferentes, sem dependência de task incompleta)
- **[Story]**: US1…US3 conforme spec.md
- Paths relativos à raiz do repositório; cada task cita path **allowlist** e reforça **denylist intacta**

## Path Conventions

Monólito Django na raiz. Parse XLSX (openpyxl) **somente** em `apps/accounts/services/legacy_import/parse_xlsx.py`. Domínio Ciclo/Avaliação histórica em `apps/cycles/services/legacy_import/`.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Congelar allowlist/denylist e criar esqueleto do pacote de domínio + management command  
**Pré-requisito**: imediato — antes de migrations ou import. Specs 003 + 010 já aplicadas no ambiente alvo.

- [X] T001 Confirmar allowlist/denylist em `specs/011-import-ciclos-avaliacoes-legado/contracts/model-allowlist.md` e `contracts/non-goals-denylist.md` (só `Ciclo.solides_id` + `cycles/services/legacy_import` + comando + extensão parse/dates/report; denylist inclui `stage.py` **e** `cycle.py`; sem nova lib)
- [X] T002 Criar pacote `apps/cycles/services/legacy_import/` com `__init__.py` (API pública: tipos de relatório / entrypoint do importer) conforme plan.md Project Structure (allowlist; denylist intacta)
- [X] T003 [P] Criar `apps/cycles/management/__init__.py` e `apps/cycles/management/commands/__init__.py` para registrar management command Django (allowlist; denylist intacta)

**Checkpoint**: Pacote `cycles.services.legacy_import` importável; diretório de commands pronto; denylist congelada

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Estender parse/dates/report da 010 para solicitações + avaliações-cabeçalho — **BLOQUEIA** todas as user stories  
**⚠️ CRITICAL**: Nenhuma user story começa antes desta fase. **Zero** alteração em denylist. **Zero** persistência de Ciclo/Avaliação ainda.

- [X] T004 [P] Estender leitura OOXML de `backup_solicitacoes_*` (colunas obrigatórias `Identificador`, `Nome`, `Iniciada em`, `Terminada em`; `Status` opcional) e `canonicalize_id` em `apps/accounts/services/legacy_import/parse_xlsx.py` conforme `contracts/column-mapping-contract.md` §solicitações e research R1 (openpyxl **somente** aqui; denylist intacta)
- [X] T005 [P] Estender leitura OOXML de `backup_avaliacoes_*` (colunas `Identificador`, `Identificador Solicitação`, `Identificador Avaliado`, `Nome Avaliado`, `Nome Avaliador`) em `apps/accounts/services/legacy_import/parse_xlsx.py` conforme `contracts/column-mapping-contract.md` §avaliações (openpyxl só no parser; denylist intacta)
- [X] T006 [P] Implementar/estender helper de rótulo de nome serial Excel (`normalize_ciclo_nome` → ISO `YYYY-MM-DD` via `parse_legacy_date`, senão `display_name`) em `apps/accounts/services/legacy_import/dates.py` conforme research R6 e `contracts/column-mapping-contract.md` §Normalização de nome (allowlist; denylist intacta)
- [X] T007 [P] Estender contadores/seções do relatório (`ciclos_*`, `avaliacoes_*`, `grupos_agregados`, `orfaos_ciclo`, `orfaos_usuario`, amostra mascarada `ids_colapsados`) em `apps/accounts/services/legacy_import/report.py` conforme `contracts/import-command-contract.md` §Formato do relatório e research R12 (sem dump PII; denylist intacta)

**Checkpoint**: Parse de fixtures XLSX mínimas retorna rows normalizados; nome serial unit-testável; relatório formatável sem persistência

---

## Phase 3: User Story 1 — Importar solicitações como ciclos históricos encerrados (Priority: P1) 🎯 MVP (parte 1)

**Goal**: `Ciclo.solides_id` aditivo + upsert de solicitações como ciclos **sempre** `status=encerrado`, com nome/datas normalizados e idempotência por `solides_id`  
**Independent Test**: Após migrate + fixtures de solicitações, importar fase ciclos e verificar contagem, 100% encerrado, nome serial legível, reexecução sem duplicar (quickstart C1 + C3)  
**Allowlist**: `apps/cycles/models.py` (+field only), `apps/cycles/migrations/*.py` (AddField), `legacy_import/{resolve,importer}.py` (fase ciclos), `importar_ciclos_avaliacoes.py`

### Implementation for User Story 1

- [X] T008 [US1] Adicionar `solides_id` (`CharField(max_length=50, blank=True, null=True, unique=True, db_index=True)`) em `Ciclo` em `apps/cycles/models.py` — **ADITIVA somente solides_id; sem alterar campos existentes**; denylist intacta
- [X] T009 [US1] Gerar e revisar migration aditiva (`AddField solides_id`) em `apps/cycles/migrations/` conforme `contracts/migration-safety.md` — `sqlmigrate` MUST mostrar somente `ADD COLUMN`; sem RunPython mutando domínio; **nenhuma** migration em `reviews`/`accounts`; denylist intacta
- [X] T010 [P] [US1] Implementar resolução/upsert de ciclo por `solides_id` (lookup, create/update `nome`/`data_inicio`/`data_fim`/`status=encerrado`) em `apps/cycles/services/legacy_import/resolve.py` conforme research R5/R7/R11 e `contracts/column-mapping-contract.md` §solicitações — datas ambas obrigatórias; conflito se inválidas; **nunca** `aberto`; denylist intacta
- [X] T011 [US1] Implementar fase 1 do pipeline (parse solicitações → upsert Ciclo via `full_clean()`+`save()`, contadores `ciclos_criados`/`atualizados`/`inalterados`/`conflitos`) em `apps/cycles/services/legacy_import/importer.py` — `transaction.atomic()` no modo persist; **proibido** chamar `open_cycle`/`close_cycle`; denylist intacta
- [X] T012 [US1] Criar management command fino `apps/cycles/management/commands/importar_ciclos_avaliacoes.py` com args obrigatórios `--solicitacoes` e `--avaliacoes`, opcionais `--report-file` / `--dry-run`, impressão de relatório e exit 0/1 conforme `contracts/import-command-contract.md` (fase 1 ciclos funcional; fase 2 pode stub até US2; sem UI/DRF/Celery; denylist intacta)
- [X] T013 [US1] Validar US1 via `specs/011-import-ciclos-avaliacoes-legado/quickstart.md` C1 + C3 (migrate, null/unique `solides_id`, todos status → encerrado, nome serial, datas inválidas → conflito, ciclo aberto vigente intacto); confirmar diff denylist vazio (`stage.py`/`cycle.py`/approval/scope/evaluation/adherence)

**Checkpoint**: US1 independentemente testável; ciclos históricos encerrados com `solides_id` (SC-001/SC-002 parciais)

---

## Phase 4: User Story 2 — Importar cabeçalhos de avaliação agregados 1:1 (Priority: P1) 🎯 MVP (parte 2)

**Goal**: Agregar N linhas Sólides → 1 `Avaliacao` por `(ciclo, usuario)` em estado terminal (`etapa=feedback`, `concluida=True`) com `solides_id` canônico determinístico — sem máquina de estados  
**Independent Test**: Após US1, importar cabeçalhos com multi-avaliador → 1 Avaliacao; órfãos no relatório; zero notas; zero chamada a stage (quickstart C4 + C5)  
**Allowlist**: `apps/cycles/services/legacy_import/{aggregate,resolve,importer}.py`, comando, `report.py` — **proibido** mutar `stage.py`/`cycle.py`/preencher `nota_final_*`

### Implementation for User Story 2

- [X] T014 [P] [US2] Implementar agregação `group_key=(solicitacao_id, avaliado_id)`, linha canônica (autoavaliação via `canonical_key` se existir; senão `min_id`) e lista `collapsed_ids` em `apps/cycles/services/legacy_import/aggregate.py` conforme `contracts/aggregation-contract.md` e research R8 (allowlist; denylist intacta)
- [X] T015 [P] [US2] Estender `apps/cycles/services/legacy_import/resolve.py` com `resolve_ciclo(solicitacao_id)` e `resolve_usuario(avaliado_id, nome)` (primário `CustomUser.solides_id`; fallback match único `canonical_key(nome)`; inativo permitido; **nunca** inventar User/Ciclo) conforme research R9 e `contracts/column-mapping-contract.md` §Resolução de FKs (denylist intacta)
- [X] T016 [US2] Implementar fase 2 do pipeline em `apps/cycles/services/legacy_import/importer.py`: agregar → resolve FK → upsert `Avaliacao` (`etapa=feedback`, `concluida=True`, `solides_id` canônico) via `full_clean()`+`save()`; conflitos `solides_id_divergente` / `solides_id_avaliacao_em_uso`; **não** tocar `nota_final_*` / `AvaliacaoCompetencia`; **proibido** `advance_stage`/open/close/approval; denylist intacta
- [X] T017 [US2] Integrar fase 2 no comando `apps/cycles/management/commands/importar_ciclos_avaliacoes.py` (ordem fixa: ciclos → cabeçalhos na mesma `transaction.atomic()`) e emitir seções `grupos_agregados` / `ids_colapsados` / `orfaos_*` via `report.py` conforme `contracts/import-command-contract.md` (denylist intacta)
- [X] T018 [US2] Validar US2 via `specs/011-import-ciclos-avaliacoes-legado/quickstart.md` C4 + C5 (1 Avaliacao por multi-avaliador, canônico, `feedback`+`concluida`, órfão usuário/ciclo, `nota_final_*` null); confirmar denylist diff vazio

**Checkpoint**: US1+US2 entregáveis — ciclos + cabeçalhos agregados (SC-003/SC-004); handoff `ids_colapsados` para 6.5.5

---

## Phase 5: Gate MVP (US1 + US2) — verificação obrigatória 🎯

**Purpose**: Fechar o **mínimo indispensável** (Sprint 6.5.4 + pré-requisito ciclos) antes de P2  
**Pré-requisito**: **obrigatório** antes de demo MVP / seguir para US3

- [X] T019 Gate MVP / regressão denylist: `git diff` vs base da feature nos paths denylist = **vazio** (`apps/cycles/services/stage.py`, `apps/cycles/services/cycle.py`, `apps/goals/services/approval.py`, `apps/accounts/services/scope.py`, `apps/reviews/services/evaluation.py`, `apps/dashboard/services/adherence.py`) **e** suíte stage/scope verde: `pytest tests/test_stage_machine tests/test_scope tests/test_reject_stage_invariant -q`. Diff allowlist MUST restringir-se a `Ciclo.solides_id`, `cycles/services/legacy_import/**`, comando, extensão `parse_xlsx`/`dates`/`report`, `samples/**`. Migration: **somente** AddField `Ciclo.solides_id`.

**Checkpoint MVP**: US1+US2 entregáveis; denylist intacta; stage/scope PASS — **release mínimo viável**

---

## Phase 6: User Story 3 — Simular, reexecutar e testar com samples anonimizados (Priority: P2)

**Goal**: `--dry-run` (zero writes), idempotência, rollback atômico, fixtures anonimizadas + suite pytest CI sem `raw/`  
**Independent Test**: Dry-run sem writes; duas execuções sem duplicar; `pytest tests/test_import_ciclos_avaliacoes_legado.py -q` verde só com samples (quickstart C2 + C6 + C7)  
**Allowlist**: `importer.py`, comando, `data/legado-solides/samples/**`, `tests/test_import_ciclos_avaliacoes_legado.py`

### Tests for User Story 3 ⚠️

> **NOTE**: Escrever testes com fixtures samples; garantir falha até implementação completa de dry-run/idempotência quando aplicável.

- [X] T020 [P] [US3] Criar fixtures XLSX anonimizadas `data/legado-solides/samples/solicitacoes_min.xlsx` e `avaliacoes_headers_min.xlsx` — subset: finished/draft/active/canceled, nome serial Excel, datas serial+ISO, multi-avaliador (com e sem autoavaliação), órfão sem usuário, solicitação órfã; **sem PII real**; **proibido** `raw/`; denylist intacta
- [X] T021 [P] [US3] Criar `tests/test_import_ciclos_avaliacoes_legado.py` com testes de dry-run (zero writes em Ciclo/Avaliacao) e status sempre encerrado usando **somente** `data/legado-solides/samples/` (SC-005/SC-007; **proibido** `raw/`; denylist intacta)
- [X] T022 [P] [US3] Adicionar testes de agregação multi-avaliador (1 Avaliacao, canônico auto/`min_id`, `ids_colapsados`), órfãos (usuário/ciclo) e `etapa=feedback`/`concluida=True` sem notes em `tests/test_import_ciclos_avaliacoes_legado.py` conforme `contracts/aggregation-contract.md` (denylist intacta)
- [X] T023 [P] [US3] Adicionar testes de idempotência (2ª execução delta Ciclo/`Avaliacao` = 0), arquivo inválido/args faltando (exit 1, DB inalterado) e assert nenhum path `raw/` na suíte em `tests/test_import_ciclos_avaliacoes_legado.py` (SC-006; denylist intacta)
- [X] T024 [US3] Adicionar teste migration reversível `Ciclo.solides_id` (forward/backward preserva seed; unique non-null → IntegrityError) em `tests/test_import_ciclos_avaliacoes_legado.py` conforme `contracts/migration-safety.md` §4 (denylist intacta)

### Implementation for User Story 3

- [X] T025 [US3] Consolidar `--dry-run` (parse + agregação + totais projetados, zero commit), falha fatal pré-persistência (arquivo ausente/OOXML ilegível/colunas ausentes/migration pré-requisito) e rollback em exceção (`transaction.atomic()`) em `apps/cycles/services/legacy_import/importer.py` e `apps/cycles/management/commands/importar_ciclos_avaliacoes.py` conforme research R12 e `contracts/import-command-contract.md` §Códigos de saída (denylist intacta)
- [X] T026 [US3] Consolidar idempotência Ciclo por `solides_id` e Avaliacao por `(ciclo, usuario)` / canônico (update campos permitidos; conflitos sem sobrescrever silenciosamente) em `apps/cycles/services/legacy_import/importer.py` conforme research R11 (denylist intacta)
- [X] T027 [US3] Validar US3 via `specs/011-import-ciclos-avaliacoes-legado/quickstart.md` C2 + C6 + C7 (`pytest tests/test_import_ciclos_avaliacoes_legado.py -q` verde; CI não lê `raw/`); confirmar denylist diff vazio

**Checkpoint**: SC-005…SC-008 atendidos; suite CI segura

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Validação quickstart end-to-end, relatório mascarado e **gate final** de regressão  
**Pré-requisito**: após stories desejadas; gate final **sempre** antes de declarar feature done

- [ ] T028 [P] Percorrer `specs/011-import-ciclos-avaliacoes-legado/quickstart.md` completo (C0–C7) e verificar SC-001…SC-010 aplicáveis com samples; smoke opcional com `raw/` **somente** manual em staging (fora do CI)
- [ ] T029 [P] Confirmar relatório stdout/`--report-file` usa **amostra mascarada** exclusivamente (máx. 5 por seção; sem nomes/e-mails em massa) em `apps/accounts/services/legacy_import/report.py` (SC-010); inspecionar ausência de dump PII
- [ ] T030 [P] Atualizar `data/legado-solides/README.md` (se necessário) com ponteiro ao comando `importar_ciclos_avaliacoes` e ordem segura passo 4→5 — sem expor PII; denylist intacta
- [ ] T031 Gate final regressão denylist: `git diff` vs base da feature nos paths denylist = **vazio** (mesmos paths da T019, **incluindo** `cycle.py`) **e** suíte completa verde: `pytest tests/test_stage_machine tests/test_scope tests/test_reject_stage_invariant tests/test_import_ciclos_avaliacoes_legado.py -q`. Migration: **ADITIVA somente Ciclo.solides_id**. Allowlist-only no diff restante. Sem chamada a stage/open/close/approval/calcular no código novo.

**Checkpoint**: Feature done; denylist intacta; pytest stage/scope + import verdes

---

## Dependencies & Execution Order

### Phase Dependencies

| Fase | Depende de | Notas |
|------|------------|-------|
| Setup (1) | — | Imediato |
| Foundational (2) | Setup | **Bloqueia** todas as stories |
| US1 (3) | Foundational | Schema + ciclos antes de cabeçalhos |
| US2 (4) | US1 | FK ciclo via `solides_id`; agregação |
| Gate MVP T019 (5) | US1+US2 | **Mínimo indispensável** |
| US3 (6) | T019 | Dry-run/idempotência/testes sobre pipeline core |
| Polish (7) | US3 (ou MVP se adiar testes) | Gate final **sempre** |

### User Story Dependencies

- **User Story 1 (P1)**: Após Foundational — schema + ciclos encerrados; sem dependência de US2
- **User Story 2 (P1)**: Após US1 — precisa `Ciclo.solides_id` populado para resolver FK
- **User Story 3 (P2)**: Após Gate MVP — dry-run/idempotência/samples cobrem US1+US2

### Within Each User Story

- Schema/migration antes de persistência (US1)
- Aggregate/resolve antes de upsert Avaliacao (US2)
- Fixtures samples antes ou em paralelo com testes (US3)
- Validação quickstart + denylist no fim de cada story

### Parallel Opportunities

- T003 ∥ após T001/T002
- T004 ∥ T005 ∥ T006 ∥ T007 (Foundational — arquivos distintos)
- T010 ∥ após T008/T009 (resolve ciclos enquanto migration revisada)
- T014 ∥ T015 (aggregate ∥ resolve usuario — arquivos distintos)
- T020 ∥ T021 ∥ T022 ∥ T023 (fixtures + testes em paralelo após pipeline)
- T028 ∥ T029 ∥ T030 (Polish)

---

## Parallel Example: User Story 1

```bash
# Após T008/T009 (model + migration):
Task: "Implementar resolução/upsert de ciclo em apps/cycles/services/legacy_import/resolve.py"
# Sequencial depois:
Task: "Implementar fase 1 importer + command importar_ciclos_avaliacoes"
```

## Parallel Example: User Story 2

```bash
# Launch em paralelo (arquivos distintos):
Task: "Implementar agregação em apps/cycles/services/legacy_import/aggregate.py"
Task: "Estender resolve_ciclo/resolve_usuario em apps/cycles/services/legacy_import/resolve.py"
# Depois integrar no importer + command
```

## Parallel Example: User Story 3

```bash
# Launch fixtures + testes em paralelo:
Task: "Criar solicitacoes_min.xlsx e avaliacoes_headers_min.xlsx em data/legado-solides/samples/"
Task: "Criar testes dry-run + status encerrado em tests/test_import_ciclos_avaliacoes_legado.py"
Task: "Adicionar testes agregação/órfãos em tests/test_import_ciclos_avaliacoes_legado.py"
Task: "Adicionar testes idempotência/arquivo inválido em tests/test_import_ciclos_avaliacoes_legado.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 + User Story 2)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL — blocks all stories)
3. Complete Phase 3: US1 (schema + ciclos encerrados)
4. Complete Phase 4: US2 (cabeçalhos agregados)
5. **STOP and VALIDATE**: Gate MVP T019 (denylist + stage/scope)
6. Deploy/demo staging se pronto

### Incremental Delivery

1. Setup + Foundational → parsers/report prontos
2. US1 → ciclos históricos com `solides_id`
3. US2 → cabeçalhos 1:1 → **MVP Sprint 6.5.4**
4. US3 → dry-run, idempotência, CI samples-only
5. Polish → quickstart + gate final

### Parallel Team Strategy

1. Time completa Setup + Foundational juntos
2. Após Foundational:
   - Dev A: US1 (model/migration/fase ciclos)
   - Dev B: pode preparar `aggregate.py` stubs (integra após US1)
3. Após US1: Dev B fecha US2; Dev A inicia fixtures US3
4. Após Gate MVP: US3 + Polish

---

## Notes

- [P] = arquivos diferentes, sem dependência de task incompleta
- [Story] mapeia US1/US2/US3 para rastreabilidade
- Clarifications 2026-08-13 são **fechadas** — não reabrir (sempre encerrado; agregação 1:1; canônico auto/`min_id`; persistência direta `feedback`+`concluida`)
- Commit após cada task ou grupo lógico
- Parar em qualquer checkpoint para validar story
- Evitar: mutar denylist, segunda lib XLSX, inventar User/Ciclo, preencher notas, abrir ciclo
