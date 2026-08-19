---
description: "Task list for feature implementation"
---

# Tasks: Importação One-Shot do Legado Sólides — Notas por Competência e Comentários Qualitativos

**Input**: Design documents from `/specs/013-import-notas-comentarios-legado/`

**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/, quickstart.md

**Tests**: Incluídos conforme FR-022, SC-009, US3 e quickstart C9 (`tests/test_import_notas_comentarios_legado.py` + fixtures em `data/legado-solides/samples/`). **MUST NOT** ler `data/legado-solides/raw/`. Regressão `test_stage_machine` / `test_scope` / `test_reject_stage_invariant` **sem** alterar asserts. Gate: `git diff` vazio na denylist (inclui `evaluation.py` — **chamar ≠ editar**).

**Organization**: Tasks por user story. Sequência obrigatória do plan: Fundação → US1 P1 → US2 P1 → Gate MVP → US3 P2. **MVP = Fundação + US1 + US2**. US2 consome `resolve`/mapa da US1 na mesma `transaction.atomic()`. US3 **não** começa antes do gate MVP.

## Escopo inválido (REJEITAR task/PR)

Qualquer task que proponha alterar denylist ([contracts/non-goals-denylist.md](./contracts/non-goals-denylist.md) / [contracts/model-allowlist.md](./contracts/model-allowlist.md)) é **INVÁLIDA**:

| Zona | Exemplos proibidos |
|------|--------------------|
| Máquina de estados | `apps/cycles/services/stage.py`; mutar `Avaliacao.etapa` / `concluida` |
| Abrir / fechar ciclo | `apps/cycles/services/cycle.py` (`open_cycle` / `close_cycle`) |
| Aprovação | `apps/goals/services/approval.py` |
| Fórmula | **Editar** `apps/reviews/services/evaluation.py`; reimplementar `normalize_score`; chamar `create_competency_lines` |
| Aderência / 9-box | `apps/dashboard/services/adherence.py`; `ClassificacaoTalento` a partir da nota |
| AuthZ / escopo | `apps/accounts/services/scope.py`; `get_visible_users`; mixins |
| Snapshots | Mutar `peso_utilizado` / `nivel_esperado_utilizado` já gravados; ler `CargoCompetencia` vigente como passado |
| Schema | Qualquer `*/migrations/*`; `AddField`; editar `models.py`; tabela de mapa de IDs |
| Agregação 011 | Copiar `apps/cycles/services/legacy_import/aggregate.py`; reabrir 1:1; inventar `Avaliacao`/`Ciclo`/`User` |
| UI 012 | `apps/dashboard/urls.py`; `apps/cycles/urls.py`; templates 012; rota `/historico/` |
| PDI / talent | Mutators `apps/pdi/**`, `apps/talent/**` |
| Stack | SPA, DRF, Celery, lib nova, UI de upload |
| CI / OPSEC | Ler `data/legado-solides/raw/` em testes |

**Permitido apenas** a allowlist em [contracts/model-allowlist.md](./contracts/model-allowlist.md): estender `parse_xlsx.py` / `dates.py` / `report.py`; pacote **novo** `apps/reviews/services/legacy_import/**`; comando `importar_notas_comentarios`; samples + `tests/test_import_notas_comentarios_legado.py`. Reuso **read-only**: `aggregate.py` (011), `canonical_key`/`display_name`/`nivel_esperado_for`/`is_kpi`/`is_ambiguous`/`map_grupo_tipo`/`resolve_default_escala`, **CHAMAR** `calcular_nota_final_*`. **Zero** migrations ([contracts/migration-safety.md](./contracts/migration-safety.md)).

**Teste de ouro**: executar `importar_notas_comentarios` **não** avança etapa, não abre/fecha ciclo, não aprova, não muda quem vê quem, **não edita** a fórmula, não cria PDI/9-box, não dispara aderência, não toca telas/rotas 012. Diff dessas regras = **vazio**. Permitido persistir `AvaliacaoCompetencia`/`Feedback`/`Competencia` mínima e preencher `nota_final_*` **chamando** a fórmula vigente.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Pode rodar em paralelo (arquivos diferentes, sem dependência de task incompleta)
- **[Story]**: US1…US3 conforme spec.md
- Paths relativos à raiz; cada task cita path **allowlist** e reforça **denylist intacta**

## Path Conventions

Monólito Django na raiz. Parse XLSX (openpyxl) **somente** em `apps/accounts/services/legacy_import/parse_xlsx.py`. Domínio nota/feedback em `apps/reviews/services/legacy_import/`. Sem UI.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Congelar contratos e criar esqueleto do pacote de domínio + management command  
**Pré-requisito**: imediato — specs 003 + 010 + 011 aplicadas no ambiente alvo. **Zero** `makemigrations`.

- [X] T001 Confirmar allowlist/denylist congeladas em `specs/013-import-notas-comentarios-legado/contracts/model-allowlist.md` e `contracts/non-goals-denylist.md` (comando `importar_notas_comentarios`; parse só em `parse_xlsx.py`; domínio em `reviews/services/legacy_import/`; denylist inclui `stage.py` / `cycle.py` / `evaluation.py` **diff vazio** / `scope.py` / urls 012 / `pdi` / `talent`; **zero** migrations; sem nova lib)
- [X] T002 Criar pacote `apps/reviews/services/legacy_import/` com `__init__.py` expondo a API pública do importer (entrypoint + tipos de relatório) conforme plan.md Project Structure — stubs `NotImplementedError` em `resolve.py` / `importer.py` / `snapshots.py` (allowlist; denylist intacta)
- [X] T003 [P] Criar `apps/reviews/management/__init__.py` e `apps/reviews/management/commands/__init__.py` para registrar management command Django (allowlist; denylist intacta)

**Checkpoint**: Pacote `reviews.services.legacy_import` importável; diretório de commands pronto; denylist congelada; zero migration

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Estender parse/dates/report da 010/011 para notas + comentários — **BLOQUEIA** todas as user stories  
**⚠️ CRITICAL**: Nenhuma user story começa antes desta fase. **Zero** alteração em denylist. **Zero** persistência de `AvaliacaoCompetencia`/`Feedback` ainda. **Zero** `openpyxl` fora de `parse_xlsx.py`.

- [X] T004 Estender `apps/accounts/services/legacy_import/parse_xlsx.py` com `parse_notas_xlsx`, `parse_comentarios_xlsx` e parser opcional `parse_habilidades_xlsx` (só se `--habilidades`) conforme [contracts/column-mapping-contract.md](./contracts/column-mapping-contract.md) e research R1 — reusar `_load_sheet_rows` / `canonicalize_id` / `_require_columns`; colunas notas: `Identificador`, `Identificador Avaliação`, `Nome Avaliador`, `Nome Avaliado`, `Identificador Habilidade`, `habilidade`, `Fator no Momento`, `Nota` (**sem** coluna de nível); colunas comentários: `Identificador` (avaliação), `Identificador Avaliador`, `Nome Avaliador`, `Nome Avaliado`, `Comentário`, `Criado em`; habilidades: `Identificador`, `Habilidade`, `Grupo`; **NÃO** redefinir parser de `--avaliacoes` (reusar `parse_avaliacoes_headers_xlsx`); openpyxl **somente** aqui; denylist intacta
- [X] T005 [P] Estender `apps/accounts/services/legacy_import/dates.py` com `parse_legacy_datetime` (serial Excel **com fração de dia** → `datetime`; `date`/`datetime` tipados; ISO; `0`/vazio → ausente; `date` sem hora → meia-noite aware se `USE_TZ`) conforme column-mapping §Datas — **sem** importar openpyxl; denylist intacta
- [X] T006 [P] Estender `apps/accounts/services/legacy_import/report.py` com seções estáveis `notas_criadas`/`atualizadas`/`inalteradas`, `comentarios_criados`/`inalterados`, `orfaos_avaliacao`/`orfaos_competencia`/`orfaos_autor`, `conflitos_lider_divergente`/`conflitos_ciclo_aberto`, `habilidades_extras_criadas`/`ids_colapsados_resolvidos` e conflitos genéricos (peso, escala, snapshot, cálculo, ciência) + `format_notas_comentarios_report` conforme [contracts/import-command-contract.md](./contracts/import-command-contract.md) §Formato — amostra mascarada máx. 5/seção via `mask_solides_id`/`mask_pii`; **sem** comentário completo, nome ou e-mail; denylist intacta

**Checkpoint**: Parse de fixtures XLSX mínimas retorna rows normalizados; datetime `Criado em` unit-testável; relatório formatável sem persistência

---

## Phase 3: User Story 1 — Persistir notas históricas, snapshots e nota final (Priority: P1) 🎯 MVP (parte 1)

**Goal**: Resolver avaliação canônica (incl. IDs colapsados 011), persistir `AvaliacaoCompetencia` com auto vs líder corretos, snapshots write-once (Fator + tabela 003) e preencher `nota_final_*` **chamando** a fórmula vigente  
**Independent Test**: Com 003/010/011 carregados, importar fase de notas (quickstart C2–C5): linhas na avaliação canônica; auto vs líder sem inversão; snapshots estáveis na reexecução; IDs colapsados resolvem; zero 2ª `Avaliacao`; ciclo aberto → skip; `nota_final_lider` via `calcular_nota_final_lider`; `git diff evaluation.py` vazio  
**Allowlist**: `apps/reviews/services/legacy_import/{resolve,snapshots,importer}.py`, `importar_notas_comentarios.py` — **proibido** editar `evaluation.py` / chamar `create_competency_lines` / inventar `Avaliacao`

### Implementation for User Story 1

- [X] T007 [P] [US1] Implementar em `apps/reviews/services/legacy_import/resolve.py`: rebuild do mapa em memória via `parse_avaliacoes_headers_xlsx` + **IMPORTAR** `aggregate_avaliacao_headers` de `apps/cycles/services/legacy_import/aggregate.py` (não copiar); `resolve_avaliacao` na ordem canônico → mapa → órfão conforme [contracts/collapsed-id-resolution.md](./contracts/collapsed-id-resolution.md); skip se `avaliacao.ciclo.status == aberto` (R10; **não** importar `get_open_ciclo` de `goals`); `is_auto` via `canonical_key` (R5); `resolve_competencia` por `Competencia.solides_id` e create mínima (R11: `display_name`, `not is_kpi`, `not is_ambiguous`, `resolve_default_escala`, `map_grupo_tipo` se `--habilidades`, senão `tecnica`; **zero** `CargoCompetencia`); **NUNCA** `get_or_create(ciclo=..., usuario=...)`; denylist intacta
- [X] T008 [P] [US1] Implementar helpers de snapshot em `apps/reviews/services/legacy_import/snapshots.py` conforme [contracts/snapshot-and-formula.md](./contracts/snapshot-and-formula.md) e research R7: `peso_utilizado` ← `Decimal(Fator no Momento)` (ausente/não-numérico/≤0 → `fator_invalido`; **não** assumir 1); `nivel_esperado_utilizado` ← `nivel_esperado_for(avaliado.cargo.nivel)` da 003 (cargo irresolvível → `nivel_irresolvivel`); **NUNCA** ler `CargoCompetencia`; na 2ª run **não** reatribuir snapshots; divergência → `snapshot_divergente` (capturar `ValidationError` write-once); denylist intacta
- [X] T009 [US1] Implementar fase Notas em `apps/reviews/services/legacy_import/importer.py`: agrupar por `(avaliacao_canônica, competencia)` **antes** do persist; `is_auto` → só `nota_autoavaliacao`; senão só `nota_lider`; dois líderes divergentes → `conflitos_lider_divergente` sem média e sem persistir líder (auto unívoca do mesmo par **pode** persistir); nota fora da escala → `nota_fora_da_escala` sem clip; upsert `AvaliacaoCompetencia` via `full_clean()`+`save()` (unique `(avaliacao, competencia)`); após o lote de cada avaliação tocada **CHAMAR** `calcular_nota_final_lider` / `calcular_nota_final_autoavaliacao` e mapear `CalculationError` → conflito **sem** média inventada; **PROIBIDO** `create_competency_lines`; **PROIBIDO** atribuir `etapa`/`concluida`; `transaction.atomic()` no modo persist; denylist intacta
- [X] T010 [US1] Criar management command fino `apps/reviews/management/commands/importar_notas_comentarios.py` com args obrigatórios `--notas` `--comentarios` `--avaliacoes`, opcionais `--habilidades` `--report-file` `--dry-run` (dry-run pode stub até US3), impressão via `format_notas_comentarios_report`, exit 0/1 conforme [contracts/import-command-contract.md](./contracts/import-command-contract.md) — fase Notas funcional; fase Comentários pode stub até US2; `--avaliacoes` **só** mapa (zero upsert de cabeçalho); sem UI/DRF/Celery; denylist intacta
- [X] T011 [US1] Validar US1 via `specs/013-import-notas-comentarios-legado/quickstart.md` C2 + C3 + C4 + C5 (auto vs líder; peso=Fator; nível=tabela 003 não `CargoCompetencia`; ID canônico/colapsado/órfão; dois líderes; ciclo aberto; `nota_final_*` via fórmula; spy `create_competency_lines` **não** chamado; `git diff` `evaluation.py` vazio); confirmar diff denylist vazio

**Checkpoint**: US1 independentemente testável; notas históricas na avaliação canônica (SC-001…SC-004, SC-006, SC-012, SC-014 parciais)

---

## Phase 4: User Story 2 — Persistir comentários / feedback qualitativo (Priority: P1) 🎯 MVP (parte 2)

**Goal**: Na mesma execução (fase seguinte às notas, mesma `transaction.atomic()`), persistir `Feedback` na avaliação canônica, com autor resolvido, tipo auto vs líder, N por avaliação, `ciente_em` preenchido em líder histórico  
**Independent Test**: Após (ou juntamente com) notas, importar comentários (quickstart C6): vínculo à canônica; autor sem inventar User; tipo coerente; N textos; ciência no líder; `etapa`/`concluida` intactas  
**Allowlist**: `resolve.py` (autor), `importer.py` (fase comentários), comando, `dates.py` já da Fundação — **proibido** mutar etapa/concluída; **proibido** unique de schema novo

### Implementation for User Story 2

- [X] T012 [US2] Estender `apps/reviews/services/legacy_import/resolve.py` com `resolve_autor`: primário `CustomUser.solides_id == Identificador Avaliador`; fallback match **único** `canonical_key(Nome Avaliador)`; inativo (010) permitido; irresolvível → `orfaos_autor`; **nunca** inventar User; mesmo `resolve_avaliacao`/mapa da US1 (ID colapsado de comentário = mesma resolução); denylist intacta
- [X] T013 [US2] Implementar fase Comentários em `apps/reviews/services/legacy_import/importer.py` conforme research R12: `Feedback.tipo` = `COLABORADOR` se `is_auto` senão `LIDER`; `conteudo` = `Comentário` (persistido no registro; **não** no relatório); `ciente_em` **somente** líder = `parse_legacy_datetime(Criado em)` (`ciencia_data_invalida` se ilegível — não persistir nulo em massa); colaborador → `ciente_em` null; após `save()`, `QuerySet.update(created_at=...)` se instante parseável; chave natural `(avaliacao_id, autor_id, tipo, display_name(conteudo), instante)` — match → não duplicar e **não** reescrever `conteudo`; N por avaliação válido; ciclo aberto → mesmo skip da US1; **NÃO** atribuir `Avaliacao.etapa`/`concluida`; denylist intacta
- [X] T014 [US2] Integrar fase Comentários no comando `apps/reviews/management/commands/importar_notas_comentarios.py` (ordem fixa: notas → fórmula → comentários na **mesma** `transaction.atomic()`) e emitir seções `comentarios_*` / `orfaos_autor` via `report.py` conforme import-command-contract (denylist intacta)
- [X] T015 [US2] Validar US2 via `specs/013-import-notas-comentarios-legado/quickstart.md` C6 (líder com ciência; auto sem ciência; autor inativo ok; autor irresolvível órfão; N textos; etapa/concluída intactas); confirmar denylist diff vazio

**Checkpoint**: US1+US2 entregáveis — notas + comentários na canônica (SC-007); handoff para 012 passar a ter desempenho/texto

---

## Phase 5: Gate MVP (US1 + US2) — verificação obrigatória 🎯

**Purpose**: Fechar o **mínimo indispensável** (Sprint 6.5.5 persistência) antes de P2  
**Pré-requisito**: **obrigatório** antes de demo MVP / seguir para US3

- [X] T016 Gate MVP / regressão denylist: `git diff` vs base da feature nos paths denylist = **vazio** (`apps/cycles/services/stage.py`, `apps/cycles/services/cycle.py`, `apps/goals/services/approval.py`, `apps/accounts/services/scope.py`, `apps/reviews/services/evaluation.py`, `apps/dashboard/services/adherence.py`, `apps/dashboard/urls.py`, `apps/cycles/urls.py`, `apps/pdi`, `apps/talent`) **e** suíte stage/scope verde: `pytest tests/test_stage_machine tests/test_scope tests/test_reject_stage_invariant -q`. Diff allowlist MUST restringir-se a `reviews/services/legacy_import/**`, comando, extensão `parse_xlsx`/`dates`/`report`, `samples/**` (quando existirem). **Zero** arquivos em `*/migrations/*`. **Há** chamada a `calcular_nota_final_*`. **Não** há chamada a `create_competency_lines`.
  **DONE 2026-08-18**: base efetiva `39000bf` (merge 012 / `development`)→HEAD+worktree — denylist **0 linhas**; `*/migrations/*` **0**; pytest `test_stage_machine.py`+`test_scope.py`+`test_reject_stage_invariant.py` **25 PASS**; asserts desses arquivos **não** alterados. Allowlist: `reviews/services/legacy_import/**`, comando `importar_notas_comentarios`, `parse_xlsx`/`dates`/`report`, `tests/test_import_notas_comentarios_legado.py`, specs `013-*`; `.specify/feature.json` só aponta a feature. `_reference/v0/**` removido (fora da allowlist). `importer.py` **chama** `calcular_nota_final_lider` / `calcular_nota_final_autoavaliacao`; **não** chama `create_competency_lines`. `git diff development -- evaluation.py` vazio.

**Checkpoint MVP**: US1+US2 entregáveis; denylist intacta; stage/scope PASS — **release mínimo viável**

---

## Phase 6: User Story 3 — Simular, reexecutar e validar com samples anonimizados (Priority: P2)

**Goal**: `--dry-run` (zero writes), idempotência, rollback atômico, fixtures anonimizadas + suite pytest CI sem `raw/`  
**Independent Test**: Simulação sem writes; duas execuções reais sem duplicar linhas de competência nem feedbacks; snapshots 100% estáveis na 2ª run; `pytest tests/test_import_notas_comentarios_legado.py -q` verde só com samples (quickstart C1 + C7 + C8 + C9)  
**Allowlist**: `importer.py`, comando, `data/legado-solides/samples/**`, `tests/test_import_notas_comentarios_legado.py`

### Tests for User Story 3 ⚠️

> **NOTE**: Escrever testes com fixtures samples; garantir falha até implementação completa de dry-run/idempotência quando aplicável. **Nenhum** teste abre `data/legado-solides/raw/`.

- [X] T017 [P] [US3] Criar fixtures XLSX anonimizadas `data/legado-solides/samples/notas_min.xlsx` e `comentarios_min.xlsx` (reusar `avaliacoes_headers_min.xlsx` da 011 para o mapa) — subset: auto (`Nome Avaliador`=`Nome Avaliado`) e líder; ID canônico `1001` + ID colapsado `1002`/`1003`; órfão de avaliação; dois líderes divergentes; Fator válido vs inválido; nota fora da escala; habilidade extra não-KPI vs nome KPI/ambíguo 003; comentário líder com `Criado em` serial; comentário auto; autor irresolvível; PII sentinela na fonte (não persistir/não vazar); **sem PII real**; **proibido** `raw/`; atualizar `data/legado-solides/samples/README.md`; denylist intacta
- [X] T018 [US3] Criar `tests/test_import_notas_comentarios_legado.py` com testes de `--dry-run` (zero writes em `AvaliacaoCompetencia`/`Feedback`/`nota_final_*` — SC-008), ID canônico / colapsado / órfão (SC-006; zero 2ª `Avaliacao`) e args/arquivo inválido (exit 1, DB inalterado) usando **somente** `data/legado-solides/samples/` (**proibido** `raw/`; denylist intacta)
- [X] T019 [US3] Adicionar em `tests/test_import_notas_comentarios_legado.py` testes de dois líderes divergentes (sem média), ciclo `status=aberto` (SC-012), write-once na 2ª run (SC-005; fixture `CargoCompetencia` vigente **divergente** não é copiada), habilidade extra vs órfão KPI (SC-014; zero `CargoCompetencia`), spy `create_competency_lines` **não** chamado, `calcular_nota_final_lider` **é** chamado, `CalculationError` → conflito sem média (denylist intacta)
- [X] T020 [US3] Adicionar em `tests/test_import_notas_comentarios_legado.py` testes de comentários (tipo, `ciente_em` líder, colaborador null, N textos, chave natural sem duplicata), mascaramento PII no relatório (máx. 5; sem comentário/nome/e-mail completos), assert nenhum path `raw/` na suíte, e teste de ouro denylist (`git diff` vazio / import não muta `etapa`/`concluida`) conforme SC-007/SC-009/SC-010/SC-013 (denylist intacta; **não** alterar asserts de stage/scope/reject)

### Implementation for User Story 3

- [X] T021 [US3] Consolidar `--dry-run` (parse + mapa + totais projetados, **zero** `save`/`create`/`update`), falha fatal pré-persistência (arquivo ausente/OOXML ilegível/colunas obrigatórias ausentes) e rollback em exceção (uma `transaction.atomic()` cobre **as duas fases**) em `apps/reviews/services/legacy_import/importer.py` e `apps/reviews/management/commands/importar_notas_comentarios.py` conforme research R2 e import-command-contract §Códigos de saída (denylist intacta)
- [X] T022 [US3] Consolidar idempotência: unique `(avaliacao, competencia)` (update só `nota_*`; snapshots bit-a-bit estáveis; `snapshot_divergente` sem apagar); Feedback pela chave natural sem duplicar nem reescrever `conteudo`; delta `Avaliacao` por `(ciclo, usuario)` = 0 em `apps/reviews/services/legacy_import/importer.py` (SC-005; denylist intacta)
- [X] T023 [US3] Validar US3 via `specs/013-import-notas-comentarios-legado/quickstart.md` C1 + C7 + C8 + C9 (`pytest tests/test_import_notas_comentarios_legado.py -q` verde; CI não lê `raw/`); confirmar denylist diff vazio
  **DONE 2026-08-18**: `pytest tests/test_import_notas_comentarios_legado.py -q` → **86 PASS** (32.92s). C1 dry-run: `test_t018_dry_run_*` + `test_t021_dry_run_*` (zero writes / zero `save`/`create`/`update`). C7 idempotência: `test_t022_segunda_run_samples_delta_zero_sc005` + write-once/`Feedback` chave natural. C8: `test_t019_habilidade_extra_vs_orfao_kpi_zero_cargo_competencia` (extra não-KPI criada; KPI/ambíguo órfãos; `CargoCompetencia` = 0). C9: `test_t018_suite_usa_somente_samples` + `test_t020_suite_nao_referencia_raw` — suíte **não** abre `data/legado-solides/raw/` (só asserts de ausência; fixtures `samples/notas_min.xlsx` + `comentarios_min.xlsx` + `avaliacoes_headers_min.xlsx`). Denylist vs `39000bf` (`development`) e vs HEAD = **0 linhas** (`stage.py`/`cycle.py`/`approval.py`/`scope.py`/`evaluation.py`/`adherence.py`/urls 012/`pdi`/`talent`); `*/migrations/*` **0**; asserts stage/scope/reject **intactos**. `importer.py` **chama** `calcular_nota_final_*`; **não** chama `create_competency_lines`.

**Checkpoint**: SC-005, SC-008, SC-009, SC-013 atendidos; suite CI segura

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Validação quickstart end-to-end, relatório mascarado, README legado e **gate final** de regressão  
**Pré-requisito**: após stories desejadas; gate final **sempre** antes de declarar feature done

- [X] T024 [P] Percorrer `specs/013-import-notas-comentarios-legado/quickstart.md` completo (C1–C10 + §0) e verificar SC-001…SC-014 aplicáveis com samples; smoke opcional com `raw/` **somente** manual em staging (fora do CI)
  **DONE 2026-08-18**: walkthrough samples-only (zero `raw/` no CI). §0: `git diff development` (`39000bf`) denylist **0 linhas**; `*/migrations/*` **0**; asserts `test_stage_machine.py`/`test_scope.py`/`test_reject_stage_invariant.py` **intactos**; pytest stage/scope/reject **25 PASS**; `pytest tests/test_import_notas_comentarios_legado.py -q` **90 PASS** (32.60s). C1–C10 mapeados na suíte (`test_t024_quickstart_c1_c10_cobertos_na_suite` + `test_t024_walkthrough_samples_c1_a_c10`). SC-002…SC-010 e SC-012…SC-014 verificados com samples. **SC-001** (volume ~7.360) e **SC-011** (tempo operador) = homologação dump real, staging MANUAL. `git diff origin/main` na denylist **não** é o gate — `main` está atrás de 010/011/012; quickstart §0 corrigido para `development` e paths `.py`. `importer.py` **chama** `calcular_nota_final_*`; **não** chama `create_competency_lines`.
- [X] T025 [P] Confirmar relatório stdout/`--report-file` usa **amostra mascarada** exclusivamente (máx. 5 por seção; zero dump de comentário completo / nome / e-mail; logs sem linha XLSX crua) em `apps/accounts/services/legacy_import/report.py` (SC-010); evidência nos testes T020; stdout **==** `--report-file`; IDs via `mask_solides_id`; denylist intacta
  **DONE 2026-08-18**: `format_notas_comentarios_report` trunca máx. 5/seção, mascara IDs com `mask_solides_id`, redige tipo/lado livres e faz 2ª passagem anti-PII; comando emite o **mesmo** texto em stdout e `--report-file` (stderr vazio; sem `logging`/print de linha XLSX). Evidência: `test_t020_relatorio_mascara_pii_max_5` + `test_t025_*`. `pytest tests/test_import_notas_comentarios_legado.py -q` → **95 PASS** (34.29s). Denylist vs HEAD **0 linhas**; `*/migrations/*` **0**.
- [X] T026 [P] Atualizar `data/legado-solides/README.md` (passo 6.5.5 / comando provisório `importar_notas`) para o nome fechado `importar_notas_comentarios`, ordem segura 011→013, `--dry-run` obrigatório em staging e ponteiro a samples — sem expor PII; denylist intacta
  **DONE 2026-08-19**: README aponta `importar_notas_comentarios` (não `importar_notas`/`importar_comentarios`); ordem 011→013; `--dry-run` obrigatório em staging; samples `notas_min.xlsx`/`comentarios_min.xlsx`; zero PII extra. Denylist só documentada, não alterada.
- [X] T027 Gate final regressão denylist: `git diff` vs base da feature nos paths denylist = **vazio** (mesmos paths da T016, **incluindo** `evaluation.py` e urls 012) **e** suíte completa verde: `pytest tests/test_stage_machine tests/test_scope tests/test_reject_stage_invariant tests/test_import_notas_comentarios_legado.py -q`. **Zero** `*/migrations/*`. Allowlist-only no diff restante. Sem chamada a stage/open/close/approval/`create_competency_lines`/`calcular_aderencia`. **Há** chamada a `calcular_nota_final_*`. Asserts de stage/scope/reject **não** alterados.
  **DONE 2026-08-19**: base `39000bf` (`development`)→worktree. Denylist **0 linhas** (`stage.py`/`cycle.py`/`approval.py`/`scope.py`/`evaluation.py`/`adherence.py`/`dashboard/urls.py`/`cycles/urls.py`/`pdi`/`talent`). `*/migrations/*` **0**. `pytest tests/test_stage_machine.py tests/test_scope.py tests/test_reject_stage_invariant.py tests/test_import_notas_comentarios_legado.py -q` → **120 PASS** (46.72s). Asserts stage/scope/reject **intactos** vs base. Diff restante allowlist + `specs/013-*` + `.specify/feature.json` (aponta a feature). `.dockerignore` restaurado à base (padrão extra do speckit Setup saía da allowlist). `importer.py` **chama** `calcular_nota_final_lider` / `calcular_nota_final_autoavaliacao`; **não** chama `create_competency_lines` / `open_cycle` / `close_cycle` / `advance_stage` / `calcular_aderencia`.

**Checkpoint**: Feature done; denylist intacta; pytest stage/scope + import verdes; zero migration

---

## Dependencies & Execution Order

### Phase Dependencies

| Fase | Depende de | Notas |
|------|------------|-------|
| Setup (1) | — | Imediato |
| Foundational (2) | Setup | **Bloqueia** todas as stories |
| US1 (3) | Foundational | Notas + snapshots + fórmula |
| US2 (4) | US1 | Mesmo mapa/canônica; fase comentários na mesma atomic |
| Gate MVP T016 (5) | US1+US2 | **Mínimo indispensável** |
| US3 (6) | T016 | Dry-run/idempotência/testes sobre pipeline core |
| Polish (7) | US3 (ou MVP se adiar testes) | Gate final **sempre** |

### User Story Dependencies

- **User Story 1 (P1)**: Após Foundational — persistência de notas; sem dependência de US2
- **User Story 2 (P1)**: Após US1 — reusa `resolve_avaliacao`/mapa; mesma transação
- **User Story 3 (P2)**: Após Gate MVP — dry-run/idempotência/samples cobrem US1+US2

### Within Each User Story

- Parse/dates/report antes de qualquer persistência
- `resolve` + `snapshots` antes do importer de notas (US1)
- Fase notas + `calcular_nota_final_*` antes da fase comentários (US2)
- Fixtures samples antes ou imediatamente antes dos testes (US3)
- Validação quickstart + denylist no fim de cada story

### Parallel Opportunities

- T003 ∥ após T001/T002
- T005 ∥ T006 ∥ após T003 (dates ∥ report; T004 parse no mesmo arquivo — sequencial internamente)
- T007 ∥ T008 (resolve ∥ snapshots — arquivos distintos)
- T017 ∥ após Gate MVP (fixtures) em paralelo com esqueleto de T018
- T024 ∥ T025 ∥ T026 (Polish)

---

## Parallel Example: User Story 1

```bash
# Launch em paralelo (arquivos distintos):
Task: "Implementar resolve_avaliacao/mapa/competência em apps/reviews/services/legacy_import/resolve.py"
Task: "Implementar snapshots peso/nível em apps/reviews/services/legacy_import/snapshots.py"
# Sequencial depois:
Task: "Implementar fase Notas + calcular_nota_final_* em importer.py"
Task: "Criar command importar_notas_comentarios.py"
```

## Parallel Example: User Story 2

```bash
# Sequencial (resolve.py → importer.py → command):
Task: "Estender resolve_autor em apps/reviews/services/legacy_import/resolve.py"
Task: "Implementar fase Comentários em apps/reviews/services/legacy_import/importer.py"
Task: "Integrar fase 2 no command importar_notas_comentarios.py"
```

## Parallel Example: User Story 3

```bash
# Fixtures primeiro (arquivo distinto), depois testes no mesmo módulo:
Task: "Criar notas_min.xlsx e comentarios_min.xlsx em data/legado-solides/samples/"
Task: "Criar testes dry-run + IDs + órfãos em tests/test_import_notas_comentarios_legado.py"
Task: "Adicionar testes conflitos/write-once/extras/fórmula no mesmo arquivo"
Task: "Adicionar testes comentários/idempotência/mascaramento/raw no mesmo arquivo"
```

---

## Implementation Strategy

### MVP First (User Story 1 + User Story 2)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL — blocks all stories)
3. Complete Phase 3: US1 (notas + snapshots + fórmula)
4. Complete Phase 4: US2 (comentários)
5. **STOP and VALIDATE**: Gate MVP T016 (denylist + stage/scope)
6. Deploy/demo staging se pronto (`--dry-run` obrigatório antes do persist)

### Incremental Delivery

1. Setup + Foundational → parsers/report prontos
2. US1 → notas históricas + `nota_final_*` via fórmula vigente
3. US2 → feedback qualitativo → **MVP Sprint 6.5.5**
4. US3 → dry-run, idempotência, CI samples-only
5. Polish → quickstart + gate final

### Parallel Team Strategy

1. Time completa Setup + Foundational juntos
2. Após Foundational:
   - Dev A: US1 (`resolve`/`snapshots`/`importer` fase notas + command)
   - Dev B: pode preparar parser de comentários já na Fundação e esqueleto `resolve_autor`
3. Após US1: Dev B fecha US2; Dev A inicia fixtures US3
4. Após Gate MVP: US3 + Polish

---

## Notes

- [P] = arquivos diferentes, sem dependência de task incompleta
- [Story] mapeia US1/US2/US3 para rastreabilidade
- Clarifications 2026-08-18 são **fechadas** — não reabrir (extras só FK de nota + filtro 003; nível pela tabela 003; ciência preenchida em líder histórico)
- Commit após cada task ou grupo lógico
- Parar em qualquer checkpoint para validar story
- Evitar: mutar denylist, segunda lib XLSX, inventar User/Ciclo/Avaliacao, editar `evaluation.py`, chamar `create_competency_lines`, migration, ler `raw/` no CI
