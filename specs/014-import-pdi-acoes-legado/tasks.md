---
description: "Task list for feature implementation"
---

# Tasks: Importação One-Shot do Legado Sólides — PDIs e Ações

**Input**: Design documents from `/specs/014-import-pdi-acoes-legado/`

**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/, quickstart.md

**Tests**: Incluídos conforme FR-022, SC-007, US3 e quickstart C9 (`tests/test_import_pdi_legado.py` + fixtures em `data/legado-solides/samples/`). **MUST NOT** ler `data/legado-solides/raw/`. Regressão `test_stage_machine` / `test_scope` / `test_reject_stage_invariant` **sem** alterar asserts. Gate: `git diff` vazio na denylist (inclui `apps/pdi/models.py` / `views.py` / `urls.py` / `forms.py` / `overdue.py` / `progress.py` / `tasks.py` — **chamar `AcaoPDI.save()` ≠ editar `overdue.py`**).

**Organization**: Tasks por user story. Sequência: Fundação → US1 P1 (persistir 1 PDI + 1 ação) → US2 P1 (resolver pessoa) → Gate MVP → US3 P2. **MVP = Fundação + US1 + US2**. US2 estende `resolve.py` da US1 (match único já necessário para persistir). US3 **não** começa antes do gate MVP.

## Escopo inválido (REJEITAR task/PR)

Qualquer task que proponha alterar denylist ([contracts/non-goals-denylist.md](./contracts/non-goals-denylist.md) / [contracts/model-allowlist.md](./contracts/model-allowlist.md)) é **INVÁLIDA**:

| Zona | Exemplos proibidos |
|------|--------------------|
| Máquina de estados | `apps/cycles/services/stage.py`; mutar `Avaliacao.etapa` / `concluida` |
| Abrir / fechar ciclo | `apps/cycles/services/cycle.py` (`open_cycle` / `close_cycle`) |
| Aprovação | `apps/goals/services/approval.py` |
| Fórmula / notas | Editar `apps/reviews/services/evaluation.py`; mutar nota/feedback |
| Aderência / 9-box | `apps/dashboard/services/adherence.py`; `ClassificacaoTalento` |
| AuthZ / escopo | `apps/accounts/services/scope.py`; `get_visible_users`; mixins **no comando** |
| PDI produto | Editar `apps/pdi/models.py`, `views.py`, `urls.py`, `forms.py`; simular POST CreateView |
| Atraso / progresso | Editar `overdue.py` / `progress.py` / `tasks.py`; chamar `mark_overdue_pdi_actions` / `calculate_pdi_progress` |
| Schema | Qualquer `*/migrations/*`; `AddField`; `solides_id` em `AcaoPDI`; FK Ciclo/Avaliação |
| UI 012 | `apps/dashboard/urls.py`; `apps/cycles/urls.py`; templates 012; rota `/historico/` |
| Talent | Mutators `apps/talent/**` |
| Stack | SPA, DRF, Celery, lib nova, UI de upload |
| Persistência | Raw SQL; `bulk_create` bypass `save`; apagar PDI/ação para refazer |
| CI / OPSEC | Ler `data/legado-solides/raw/` em testes |

**Permitido apenas** a allowlist em [contracts/model-allowlist.md](./contracts/model-allowlist.md): estender `parse_xlsx.py` / `dates.py` (só se faltar formato) / `report.py`; pacote **novo** `apps/pdi/services/legacy_import/**`; comando `importar_pdi`; samples + `tests/test_import_pdi_legado.py`. Reuso **read-only**: `canonical_key`/`display_name` (003); ORM `PDI`/`AcaoPDI`/`CustomUser`; hook de atraso **via** `AcaoPDI.save()`. **Zero** migrations ([contracts/migration-safety.md](./contracts/migration-safety.md)).

**Teste de ouro**: executar `importar_pdi` **não** avança etapa, não abre/fecha ciclo, não aprova, não muda quem vê quem, **não edita** fórmula/`overdue.py`/`views.py`, não cria 9-box, não dispara aderência, não toca telas/rotas 012. Diff dessas regras = **vazio**. Permitido persistir `PDI`/`AcaoPDI` e preencher `PDI.solides_id` **já existente** com digest curto.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Pode rodar em paralelo (arquivos diferentes, sem dependência de task incompleta)
- **[Story]**: US1…US3 conforme spec.md
- Paths relativos à raiz; cada task cita path **allowlist** e reforça **denylist intacta**

## Path Conventions

Monólito Django na raiz. Parse XLSX (openpyxl) **somente** em `apps/accounts/services/legacy_import/parse_xlsx.py`. Domínio PDI/ação em `apps/pdi/services/legacy_import/`. Sem UI. Nenhum módulo em `pdi/` importa openpyxl.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Congelar contratos e criar esqueleto do pacote de domínio + management command  
**Pré-requisito**: imediato — specs 003 + 010 aplicadas no ambiente alvo. **Zero** `makemigrations`. 011/013 **não** bloqueiam.

- [X] T001 Confirmar allowlist/denylist congeladas em `specs/014-import-pdi-acoes-legado/contracts/model-allowlist.md` e `contracts/non-goals-denylist.md` (comando `importar_pdi`; parse só em `parse_xlsx.py`; domínio em `pdi/services/legacy_import/`; denylist inclui `stage.py` / `cycle.py` / `evaluation.py` / `scope.py` / urls 012 / `overdue.py` / `progress.py` / `tasks.py` / `views.py` / `models.py` / `talent`; **zero** migrations; sem nova lib)
- [X] T002 Criar pacote `apps/pdi/services/legacy_import/` com `__init__.py` expondo a API pública do importer (entrypoint + tipos de relatório) conforme plan.md Project Structure — stubs `NotImplementedError` em `resolve.py` / `importer.py` (allowlist; denylist intacta)
- [X] T003 [P] Criar `apps/pdi/management/__init__.py` e `apps/pdi/management/commands/__init__.py` para registrar management command Django (allowlist; denylist intacta)

**Checkpoint**: Pacote `pdi.services.legacy_import` importável; diretório de commands pronto; denylist congelada; zero migration

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Estender parse/report da 010/011/013 para PDI — **BLOQUEIA** todas as user stories  
**⚠️ CRITICAL**: Nenhuma user story começa antes desta fase. **Zero** alteração em denylist. **Zero** persistência de `PDI`/`AcaoPDI` ainda. **Zero** `openpyxl` fora de `parse_xlsx.py`.

- [X] T004 Estender `apps/accounts/services/legacy_import/parse_xlsx.py` com `parse_pdi_xlsx` conforme [contracts/column-mapping-contract.md](./contracts/column-mapping-contract.md) e research R1 — reusar `_load_sheet_rows` / `canonicalize_id` / `_require_columns`; colunas obrigatórias: `Nome`, `Título do PDI`, `Status`, `Objetivo`, `Situação Atual`, `Situação Desejada`, `Data de Entrega`; opcionais se header existir: `Criado em`, `Identificador Solicitação`, ID da pessoa (`Identificador` / `Identificador Avaliado`); células de data/texto **crus** no dataclass; arquivo ausente/OOXML inválido/colunas obrigatórias ausentes → `LegacyParseError`; openpyxl **somente** aqui; denylist intacta
- [X] T005 [P] Confirmar reuso de `parse_legacy_date` e `parse_legacy_datetime` em `apps/accounts/services/legacy_import/dates.py` para `Data de Entrega` (prazo) e `Criado em` (material do digest) conforme column-mapping §Datas e research R8 — **estender só se** o dump 6.5.6 trouxer formato não coberto; **sem** importar openpyxl; denylist intacta
- [X] T006 [P] Estender `apps/accounts/services/legacy_import/report.py` com seções estáveis `pdis_criados`/`atualizados`/`inalterados`, `acoes_criadas`/`atualizadas`/`inalteradas`, `orfaos_usuario`/`orfaos_solicitacao`, `conflitos` (`status_desconhecido`, `prazo_invalido`, `descricao_vazia`, `titulo_ausente`, `id_vs_nome`, `acao_chave_divergente`, …) e `format_pdi_report` conforme [contracts/import-command-contract.md](./contracts/import-command-contract.md) §Formato — amostra mascarada máx. 5/seção via `mask_solides_id`/`mask_pii`; **sem** nome, e-mail, linha bruta, título/objetivo/situação completos; denylist intacta

**Checkpoint**: Parse de fixtures XLSX mínimas retorna rows normalizados; datas unit-testáveis via helpers vigentes; relatório formatável sem persistência

---

## Phase 3: User Story 1 — Persistir PDIs e uma ação por linha (Priority: P1) 🎯 MVP (parte 1)

**Goal**: Cada linha resolvível gera exatamente 1 `PDI` + 1 `AcaoPDI`; concatenação `\n\n`; responsável = dono; digest curto em `PDI.solides_id`; de-para FR-010/FR-011 **antes** do `save`; zero FK ciclo/avaliação  
**Independent Test**: Com 003/010 carregados — **sem** exigir 011/013 — importar amostra (quickstart C2 + C5 + C6): 1+1; dono = responsável; concat só trechos não vazios; digest `pdi_`+40 hex ≠ nome concatenado; `finalizado`→concluído/concluída; `em_andamento`+prazo vs `timezone.localdate()`; zero `arquivado`; spy `mark_overdue_pdi_actions` **não** chamado; `git diff overdue.py` / `models.py` vazio  
**Allowlist**: `apps/pdi/services/legacy_import/{resolve,importer}.py`, `importar_pdi.py` — **proibido** editar `overdue.py` / inventar User / `bulk_create` bypass `save`

### Implementation for User Story 1

- [X] T007 [P] [US1] Implementar em `apps/pdi/services/legacy_import/resolve.py`: concatenação FR-005 (`display_name` dos trechos Objetivo → Situação Atual → Situação Desejada, join `\n\n`, três vazios → `descricao_vazia`); digest R-digest (`pdi_` + sha256 hex[:40] de `canonical_key(Nome)` + `\n` + `display_name(título)` [+ `\n` + ISO UTC de `Criado em` se parseável] — **nunca** nome/título em claro em `solides_id`); de-para PDI FR-010 (`finalizado`→`concluido`, `em_andamento`→`ativo`, senão `status_desconhecido`; **nunca** `arquivado`); status ação FR-011 **antes** do save (`concluida` / `atrasada` / `pendente`; data da carga = `timezone.localdate()` no início; **nunca** `em_andamento` de ação); chave natural da ação `(pdi_id, display_name(descricao), prazo)`; match **único** `canonical_key(Nome)` contra `CustomUser` (incl. inativos) para a US1 persistir — **NUNCA** `get_or_create` User; **NUNCA** `line_manager` como responsável; título vazio ou `len>200` → conflito (não truncar); **IMPORTAR** `canonical_key`/`display_name` de `apps/competencies/services/catalog_import/normalize.py` (não copiar); denylist intacta
- [X] T008 [US1] Implementar persistência em `apps/pdi/services/legacy_import/importer.py` conforme research R-idempotência e data-model: `data_carga` congelada; unidade por linha = PDI **e** ação ou nenhum; `full_clean()`+`save()` (sem `update_fields` que pule `prazo`); `AcaoPDI.save()` é o único caminho do hook — **MUST NOT** chamar `recalculate_overdue_status` / `mark_overdue_pdi_actions` soltos; `responsavel` = `pdi.usuario`; **ZERO** FK Ciclo/Avaliação; `Identificador Solicitação` não bloqueia e não persiste vínculo; upsert PDI por `solides_id`; digest novo → create 1+1 (`pdis_criados`/`acoes_criadas`); mesma chave de ação → inalterado (não reescrever título/status/descrição); chave de ação divergente no mesmo digest → `acao_chave_divergente` sem 2ª ação e sem delete; lote em **uma** `transaction.atomic()`; **PROIBIDO** `bulk_create`; denylist intacta
- [X] T009 [US1] Criar management command fino `apps/pdi/management/commands/importar_pdi.py` com `--pdi` obrigatório, opcionais `--report-file` `--dry-run` (dry-run pode stub até US3), impressão via `format_pdi_report`, exit 0/1 conforme [contracts/import-command-contract.md](./contracts/import-command-contract.md) — persistência 1+1 funcional; CLI **sem** regra de domínio; stdout **==** `--report-file` quando presente; sem UI/DRF/Celery; denylist intacta com `--pdi` obrigatório, opcionais `--report-file` `--dry-run` (dry-run pode stub até US3), impressão via `format_pdi_report`, exit 0/1 conforme [contracts/import-command-contract.md](./contracts/import-command-contract.md) — persistência 1+1 funcional; CLI **sem** regra de domínio; stdout **==** `--report-file` quando presente; sem UI/DRF/Celery; denylist intacta
- [X] T010 [US1] Validar US1 via `specs/014-import-pdi-acoes-legado/quickstart.md` C2 + C5 + C6 (1 PDI + 1 ação; concat `\n\n`; responsável = dono; zero três ações; zero PDI sem ação; de-para + atraso; digest prefixo `pdi_` len 44 ≠ concatenação; spy `mark_overdue_pdi_actions` **não** chamado; `git diff` `overdue.py`/`models.py` vazio); confirmar diff denylist vazio

**Checkpoint**: US1 independentemente testável; arquivo de PDI histórico no schema vigente (SC-002, SC-003, SC-004, SC-011, SC-012 parciais)

---

## Phase 4: User Story 2 — Resolver colaborador sem inventar pessoa (Priority: P1) 🎯 MVP (parte 2)

**Goal**: Match único por chave canônica; ID Sólides da pessoa reforça se único e coerente; zero/2+ → órfão; inativo permitido sem bypass de escopo; nunca inventar User  
**Independent Test**: Fixtures quickstart C3 + C4: nome único persiste; duplicado/ausente → `orfaos_usuario` (nunca o “primeiro”); ID vs nome único divergente → `id_vs_nome`; demitido com match único persiste; `test_scope` intacto  
**Allowlist**: `resolve.py`, `importer.py`, comando — **proibido** `get_or_create` User; **proibido** chamar `get_visible_users` / `user_in_scope` / `ScopedObjectMixin` no comando

### Implementation for User Story 2

- [X] T011 [US2] Estender `apps/pdi/services/legacy_import/resolve.py` com resolução normativa research R5: (1) se ID pessoa presente e unique hit em `CustomUser.solides_id`, usar esse User **exceto** Nome unique apontando para **outra** pessoa → conflito `id_vs_nome`; (2) senão match único `canonical_key(Nome)` incl. `is_active=False`; (3) zero ou 2+ → `orfaos_usuario`; **NUNCA** escolher o primeiro; **NUNCA** inventar colaborador; ID via `canonicalize_id` do parser 010; denylist intacta
- [X] T012 [US2] Integrar resolução de pessoa em `apps/pdi/services/legacy_import/importer.py` e no comando `apps/pdi/management/commands/importar_pdi.py`: órfãos não-fatais (skip da linha, lote continua); emitir `orfaos_usuario` / `id_vs_nome` via `report.py`; **MUST NOT** chamar `get_visible_users` / `user_in_scope` / `ScopedObjectMixin`; inatividade **não** bloqueia carga e **não** cria atalho de visibilidade; denylist intacta
- [X] T013 [US2] Validar US2 via `specs/014-import-pdi-acoes-legado/quickstart.md` C3 + C4 (órfão, ambíguo, `id_vs_nome`, inativo ok, zero User inventado); confirmar denylist diff vazio e asserts de `tests/test_scope.py` **não** alterados

**Checkpoint**: US1+US2 entregáveis — PDI/ação só com dono resolvido (SC-001, SC-003)

---

## Phase 5: Gate MVP (US1 + US2) — verificação obrigatória 🎯

**Purpose**: Fechar o **mínimo indispensável** (Sprint 6.5.6 persistência) antes de P2  
**Pré-requisito**: **obrigatório** antes de demo MVP / seguir para US3

- [X] T014 Gate MVP / regressão denylist: `git diff` vs base da feature nos paths denylist = **vazio** (`apps/cycles/services/stage.py`, `apps/cycles/services/cycle.py`, `apps/goals/services/approval.py`, `apps/accounts/services/scope.py`, `apps/reviews/services/evaluation.py`, `apps/dashboard/services/adherence.py`, `apps/dashboard/urls.py`, `apps/cycles/urls.py`, `apps/pdi/models.py`, `apps/pdi/views.py`, `apps/pdi/urls.py`, `apps/pdi/forms.py`, `apps/pdi/services/overdue.py`, `apps/pdi/services/progress.py`, `apps/pdi/tasks.py`, `apps/talent`) **e** suíte stage/scope verde: `pytest tests/test_stage_machine tests/test_scope tests/test_reject_stage_invariant -q`. Diff allowlist MUST restringir-se a `pdi/services/legacy_import/**`, comando, extensão `parse_xlsx`/`dates`/`report`, `samples/**` (quando existirem). **Zero** arquivos em `*/migrations/*`. Hook de atraso **só** via `AcaoPDI.save()`. **Não** há chamada a `mark_overdue_pdi_actions` / `calculate_pdi_progress` / `get_visible_users`.

**Checkpoint MVP**: US1+US2 entregáveis; denylist intacta; stage/scope PASS — **release mínimo viável**

---

## Phase 6: User Story 3 — Simular, reexecutar e validar com samples anonimizados (Priority: P2)

**Goal**: `--dry-run` (zero writes), idempotência, rollback atômico, fixtures anonimizadas + suite pytest CI sem `raw/`  
**Independent Test**: Simulação sem writes; duas execuções reais sem duplicar PDI pelo digest nem ação pela chave natural; `pytest tests/test_import_pdi_legado.py -q` verde só com samples (quickstart C1 + C7 + C8 + C9)  
**Allowlist**: `importer.py`, comando, `data/legado-solides/samples/**`, `tests/test_import_pdi_legado.py`

### Tests for User Story 3 ⚠️

> **NOTE**: Escrever testes com fixtures samples; garantir falha até implementação completa de dry-run/idempotência quando aplicável. **Nenhum** teste abre `data/legado-solides/raw/`.

- [ ] T015 [P] [US3] Criar fixture XLSX anonimizada `data/legado-solides/samples/pdi_min.xlsx` — subset: match único; órfão; ambíguo; inativo; `finalizado` vs `em_andamento` (prazo passado vs futuro); status desconhecido; prazo ilegível; descrição vazia; título overflow; PII sentinela na fonte (não persistir/não vazar); ID pessoa vs nome divergente se coluna opcional; **sem PII real**; **proibido** `raw/`; atualizar `data/legado-solides/samples/README.md`; denylist intacta
- [ ] T016 [US3] Criar `tests/test_import_pdi_legado.py` com testes de `--dry-run` (zero writes em `PDI`/`AcaoPDI` — SC-006), 1 PDI + 1 ação / concat `\n\n` / responsável = dono / zero três ações (SC-002/SC-003) e args/arquivo inválido (exit 1, DB inalterado) usando **somente** `data/legado-solides/samples/` (**proibido** `raw/`; denylist intacta)
- [ ] T017 [US3] Adicionar em `tests/test_import_pdi_legado.py` testes de órfão / ambíguo / `id_vs_nome` / inativo ok (SC-001), de-para FR-010/FR-011 (concluída nunca atrasada; ativo+prazo; status desconhecido; prazo ilegível; descrição vazia; zero `arquivado` — SC-011/SC-012), spy `mark_overdue_pdi_actions` **não** chamado, `git diff` `overdue.py` vazio (denylist intacta)
- [ ] T018 [US3] Adicionar em `tests/test_import_pdi_legado.py` testes de digest (`pdi_`+40 hex, len ≤ 50, ≠ nome+título concatenados, estável entre runs — SC-007), 2ª run delta 0 nas chaves naturais (SC-005; título/status inalterados), mascaramento PII no relatório (máx. 5; sem título/objetivo/nome/e-mail completos; stdout == `--report-file` — SC-008), assert nenhum path `raw/` na suíte, e teste de ouro denylist (`git diff` vazio / import não muta etapa/escopo) conforme SC-007/SC-010 (denylist intacta; **não** alterar asserts de stage/scope/reject)

### Implementation for User Story 3

- [ ] T019 [US3] Consolidar `--dry-run` (parse + resolve + totais projetados, **zero** `save`/`create`/`update`), falha fatal pré-persistência (arquivo ausente/OOXML ilegível/colunas obrigatórias ausentes) e rollback em exceção (uma `transaction.atomic()` cobre o lote) em `apps/pdi/services/legacy_import/importer.py` e `apps/pdi/management/commands/importar_pdi.py` conforme research R2 e import-command-contract §Códigos de saída (denylist intacta)
- [ ] T020 [US3] Consolidar idempotência: upsert por digest; ação pela chave `(pdi_id, display_name(descricao), prazo)`; 2ª run inalterado; divergência → conflito sem 2ª ação e sem apagar; `pdis_atualizados`/`acoes_atualizadas` permanecem 0 no caminho feliz (política conservadora) em `apps/pdi/services/legacy_import/importer.py` (SC-005; denylist intacta)
- [ ] T021 [US3] Validar US3 via `specs/014-import-pdi-acoes-legado/quickstart.md` C1 + C7 + C8 + C9 (`pytest tests/test_import_pdi_legado.py -q` verde; CI não lê `raw/`); confirmar denylist diff vazio

**Checkpoint**: SC-005, SC-006, SC-007, SC-008, SC-010 atendidos; suite CI segura

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Validação quickstart end-to-end, relatório mascarado, README legado e **gate final** de regressão  
**Pré-requisito**: após stories desejadas; gate final **sempre** antes de declarar feature done

- [ ] T022 [P] Percorrer `specs/014-import-pdi-acoes-legado/quickstart.md` completo (C0–C10) e verificar SC-001…SC-012 aplicáveis com samples; smoke opcional com `raw/` **somente** manual em staging (fora do CI)
- [ ] T023 [P] Confirmar relatório stdout/`--report-file` usa **amostra mascarada** exclusivamente (máx. 5 por seção; zero dump de título/objetivo/situação completos / nome / e-mail; logs sem linha XLSX crua) em `apps/accounts/services/legacy_import/report.py` (SC-008); evidência nos testes T018; stdout **==** `--report-file`; IDs via `mask_solides_id`; denylist intacta
- [ ] T024 [P] Atualizar `data/legado-solides/README.md` (passo 7 / PRD 6.5.6) para o comando fechado `importar_pdi`, `--pdi`, `--dry-run` obrigatório em staging, pré-condição 003+010 (011/013 opcionais) e ponteiro a `samples/pdi_min.xlsx` — sem expor PII; denylist intacta
- [ ] T025 Gate final regressão denylist: `git diff` vs base da feature nos paths denylist = **vazio** (mesmos paths da T014) **e** suíte completa verde: `pytest tests/test_stage_machine tests/test_scope tests/test_reject_stage_invariant tests/test_import_pdi_legado.py -q`. **Zero** `*/migrations/*`. Allowlist-only no diff restante. Sem chamada a stage/open/close/approval/`mark_overdue_pdi_actions`/`calcular_aderencia`/`get_visible_users`. Persistência só `full_clean`+`save`. Asserts de stage/scope/reject **não** alterados.

**Checkpoint**: Feature done; denylist intacta; pytest stage/scope + import verdes; zero migration

---

## Dependencies & Execution Order

### Phase Dependencies

| Fase | Depende de | Notas |
|------|------------|-------|
| Setup (1) | — | Imediato |
| Foundational (2) | Setup | **Bloqueia** todas as stories |
| US1 (3) | Foundational | Persistência 1 PDI + 1 ação + digest + FR-011 |
| US2 (4) | US1 | Estende resolve de pessoa (ID / órfão / inativo) |
| Gate MVP T014 (5) | US1+US2 | **Mínimo indispensável** |
| US3 (6) | T014 | Dry-run/idempotência/testes sobre pipeline core |
| Polish (7) | US3 (ou MVP se adiar testes) | Gate final **sempre** |

### User Story Dependencies

- **User Story 1 (P1)**: Após Foundational — persistência 1+1; match único de nome já no `resolve` para gravar dono
- **User Story 2 (P1)**: Após US1 — completa matriz de resolução (ID, ambíguo, inativo) sem inventar User
- **User Story 3 (P2)**: Após Gate MVP — dry-run/idempotência/samples cobrem US1+US2

### Within Each User Story

- Parse/dates/report antes de qualquer persistência
- `resolve` (concat/digest/status) antes do importer (US1)
- Resolução de pessoa completa antes de declarar US2
- Fixtures samples antes ou imediatamente antes dos testes (US3)
- Validação quickstart + denylist no fim de cada story

### Parallel Opportunities

- T003 ∥ após T001/T002
- T005 ∥ T006 ∥ após T003 (dates ∥ report; T004 parse no mesmo arquivo que 010 — sequencial internamente se houver conflito de merge)
- T007 pode iniciar em `resolve.py` em paralelo ao esqueleto do command T009 **depois** de T008 depender de T007
- T015 ∥ após Gate MVP (fixtures) em paralelo com esqueleto de T016
- T022 ∥ T023 ∥ T024 (Polish)

---

## Parallel Example: User Story 1

```bash
# Sequencial (mesmo domínio):
Task: "Implementar concat/digest/de-para em apps/pdi/services/legacy_import/resolve.py"
Task: "Implementar persist 1+1 + atomic em apps/pdi/services/legacy_import/importer.py"
Task: "Criar command importar_pdi.py"
```

## Parallel Example: User Story 2

```bash
# Sequencial (resolve.py → importer.py → command):
Task: "Estender R5 ID/órfão/inativo em apps/pdi/services/legacy_import/resolve.py"
Task: "Integrar orfaos_usuario no importer.py e importar_pdi.py"
```

## Parallel Example: User Story 3

```bash
# Fixtures primeiro (arquivo distinto), depois testes no mesmo módulo:
Task: "Criar pdi_min.xlsx em data/legado-solides/samples/"
Task: "Criar testes dry-run + 1+1 em tests/test_import_pdi_legado.py"
Task: "Adicionar testes órfãos/status/atraso no mesmo arquivo"
Task: "Adicionar testes digest/idempotência/mascaramento/raw no mesmo arquivo"
```

---

## Implementation Strategy

### MVP First (User Story 1 + User Story 2)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL — blocks all stories)
3. Complete Phase 3: US1 (1 PDI + 1 ação + digest + FR-011)
4. Complete Phase 4: US2 (resolução de pessoa)
5. **STOP and VALIDATE**: Gate MVP T014 (denylist + stage/scope)
6. Deploy/demo staging se pronto (`--dry-run` obrigatório antes do persist)

### Incremental Delivery

1. Setup + Foundational → parser/report prontos
2. US1 → arquivo de PDI histórico no produto
3. US2 → dono correto sem inventar pessoa → **MVP Sprint 6.5.6**
4. US3 → dry-run, idempotência, CI samples-only
5. Polish → quickstart + gate final

### Parallel Team Strategy

1. Time completa Setup + Foundational juntos
2. Após Foundational:
   - Dev A: US1 (`resolve` concat/digest + `importer` + command)
   - Dev B: pode preparar seções de relatório e esqueleto R5 em branch isolada de `resolve.py` **depois** do merge de T007
3. Após US1: Dev B fecha US2; Dev A inicia fixtures US3
4. Após Gate MVP: US3 + Polish

---

## Notes

- [P] = arquivos diferentes, sem dependência de task incompleta
- [Story] mapeia US1/US2/US3 para rastreabilidade
- Clarifications 2026-08-19 são **fechadas** — não reabrir (1 linha = 1+1; digest curto; responsável = dono; zero FK ciclo; prazo obrigatório; sem arquivado)
- Commit após cada task ou grupo lógico
- Parar em qualquer checkpoint para validar story
- Evitar: mutar denylist, segunda lib XLSX, inventar User, editar `overdue.py`/`models.py`, `mark_overdue_pdi_actions`, migration, ler `raw/` no CI
