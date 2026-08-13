# Tasks: Importação One-Shot do Legado Sólides — Colaboradores e Schema de Identificadores

**Input**: Design documents from `/specs/010-import-colaboradores-legado/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: Incluídos conforme research R17, US5 e plan.md (`tests/test_import_colaboradores_legado.py` com fixtures anonimizadas em `data/legado-solides/samples/`). **Regressão obrigatória** stage/scope (diff denylist vazio). Nenhum teste referencia `data/legado-solides/raw/`.

**Organization**: Tasks por user story. **MVP indispensável = US1 + US2 + US3** (+ gate MVP T030). Depois **US4 (P2)** e **US5 (P2)**; Polish + gate final.

## Escopo inválido (REJEITAR task/PR)

Qualquer task que proponha alterar denylist ([contracts/non-goals-denylist.md](./contracts/non-goals-denylist.md)) é **INVÁLIDA**:

| Zona | Exemplos proibidos |
|------|--------------------|
| Máquina de estados | `apps/cycles/services/stage.py`, `cycle.py` |
| Aprovação / reprovação | `apps/goals/services/approval.py` |
| AuthZ / escopo | `apps/accounts/services/scope.py`, `get_visible_users`, `ScopedObjectMixin` |
| Fórmulas / notas | `apps/reviews/services/evaluation.py` (+ mutators de nota) |
| Aderência | `apps/dashboard/services/adherence.py` |
| Avaliações na import | Mutar `Avaliacao.etapa` / `concluida` / `nota_final_*` |
| Snapshots | Mutar `peso_utilizado` / `nivel_esperado_utilizado` |
| PII | Novos campos CPF, RG, banco, endereço, telefone |
| Schema existente | Alterar tipo/nullable/unique de campos existentes (exceto **ADICIONAR** `solides_id`) |
| Integridade | Alterar `on_delete` / remover constraints |
| Stack / UX | UI de upload, DRF, Celery, abrir ciclo ativo |
| CI / OPSEC | Usar `data/legado-solides/raw/` em testes CI |

**Permitido apenas** (allowlist completa em [contracts/model-allowlist.md](./contracts/model-allowlist.md)): migrations aditivas `solides_id`; `apps/accounts/services/legacy_import/**`; comando `importar_colaboradores`; `requirements.txt` (+openpyxl); `data/legado-solides/samples/**`; `tests/test_import_colaboradores_legado.py`; reuso read-only de `apps/competencies/services/catalog_import/normalize.py`.

**Teste de ouro**: executar `importar_colaboradores` **não** altera avanço de etapa, aprovação/reprovação, notas, usuários visíveis (regras AuthZ) nem muta avaliações/PDI existentes.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Pode rodar em paralelo (arquivos diferentes, sem dependência de task incompleta)
- **[Story]**: US1…US5 conforme spec.md
- Paths relativos à raiz do repositório; cada task cita path **allowlist** e reforça **denylist intacta**

## Path Conventions

Monólito Django na raiz: allowlist em `contracts/model-allowlist.md`. Parse XLSX restrito a `apps/accounts/services/legacy_import/parse_xlsx.py` (único módulo com openpyxl).

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Congelar allowlist/denylist, dependência openpyxl e estrutura de pacotes  
**Pré-requisito**: imediato — antes de migrations ou import

- [X] T001 Confirmar allowlist/denylist em `specs/010-import-colaboradores-legado/contracts/model-allowlist.md` e `contracts/non-goals-denylist.md` (só schema aditivo + legacy_import + comando; denylist de domínio intocável — stage/approval/fórmulas/AuthZ/PII)
- [X] T002 Adicionar `openpyxl` em `requirements.txt` (justificado em plan.md Complexity Tracking; **somente** consumido por `parse_xlsx.py`; denylist intacta)
- [X] T003 Criar pacote `apps/accounts/services/legacy_import/` com `__init__.py` exportando API pública (`import_colaboradores`, tipos de relatório) conforme plan.md (allowlist; denylist intacta)
- [X] T004 [P] Criar `apps/accounts/management/__init__.py` e `apps/accounts/management/commands/__init__.py` para registrar management command Django (allowlist; denylist intacta)

**Checkpoint**: Imports do pacote `legacy_import` resolvem; diretório de commands pronto; denylist congelada

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Utilitários compartilhados de parse XLSX, datas e relatório mascarado — **BLOQUEIAM** todas as user stories  
**⚠️ CRITICAL**: Nenhuma user story começa antes desta fase. **Zero** alteração em denylist.

- [X] T005 [P] Implementar leitura OOXML (planilha colaboradores + header avaliações) e validação de colunas obrigatórias em `apps/accounts/services/legacy_import/parse_xlsx.py` conforme `contracts/column-mapping-contract.md` §Obrigatórias e research R1 (openpyxl **somente** aqui; denylist intacta)
- [X] T006 [P] Implementar parser serial Excel + ISO para `Data demissão` em `apps/accounts/services/legacy_import/dates.py` conforme research R10 e `contracts/column-mapping-contract.md` §is_active (allowlist; denylist intacta)
- [X] T007 [P] Implementar estrutura de relatório (contadores + listas detalhadas), `mask_email()`/`mask_pii()` e `format_report()` com **amostra mascarada** em `apps/accounts/services/legacy_import/report.py` conforme `contracts/import-command-contract.md` §Formato do relatório e research R14 (nunca CPF/e-mail completo; denylist intacta)

**Checkpoint**: Parse de fixtures XLSX mínimas retorna estruturas normalizadas; datas unit-testáveis; relatório formatável sem persistência

---

## Phase 3: User Story 1 — Preparar schema para rastreabilidade legado (Priority: P1) 🎯 MVP (parte 1)

**Goal**: Campo `solides_id` nullable, único quando preenchido, indexado em cinco entidades — pronto para fatias futuras  
**Independent Test**: `migrate` + shell: criar registros sem `solides_id`; duplicata non-null → IntegrityError; CRUD/login/ciclos inalterados (quickstart C1)  
**Allowlist**: `apps/*/models.py` (+field only), `apps/*/migrations/*.py` (AddField) — **proibido** alterar campos existentes

### Implementation for User Story 1

- [X] T008 [P] [US1] Adicionar `solides_id` (`CharField(max_length=50, blank=True, null=True, unique=True, db_index=True)`) em `CustomUser` em `apps/accounts/models.py` — **ADITIVA somente solides_id; sem alterar campos existentes**; denylist intacta
- [X] T009 [P] [US1] Adicionar `solides_id` idêntico em `Cargo` em `apps/organization/models.py` — **ADITIVA somente solides_id**; denylist intacta
- [X] T010 [P] [US1] Adicionar `solides_id` idêntico em `Competencia` em `apps/competencies/models.py` — **schema only** nesta fatia; denylist intacta
- [X] T011 [P] [US1] Adicionar `solides_id` idêntico em `Avaliacao` em `apps/reviews/models.py` — **sem** alterar `etapa`/`concluida`/`nota_final_*`; denylist intacta
- [X] T012 [P] [US1] Adicionar `solides_id` idêntico em `PDI` em `apps/pdi/models.py` — **schema only**; denylist intacta
- [X] T013 [US1] Gerar e revisar migrations aditivas (`AddField solides_id`) em `apps/accounts/migrations/`, `apps/organization/migrations/`, `apps/competencies/migrations/`, `apps/reviews/migrations/`, `apps/pdi/migrations/` conforme `contracts/migration-safety.md` — `sqlmigrate` MUST mostrar somente `ADD COLUMN`; sem RunPython mutando domínio; denylist intacta
- [X] T014 [US1] Validar US1 via `specs/010-import-colaboradores-legado/quickstart.md` C1 (migrate, null ok, unique enforcement, CRUD/login inalterados); confirmar diff denylist vazio nos paths de domínio

**Checkpoint**: US1 independentemente testável; cinco entidades aceitam `solides_id` null (SC-001)

---

## Phase 4: User Story 2 — Carregar colaboradores e estrutura organizacional (Priority: P1) 🎯 MVP (parte 2)

**Goal**: Comando importa colaboradores, áreas, cargos faltantes, e-mail confirmado, demitidos inativos e crosswalk `solides_id` — **sem** hierarquia ainda  
**Independent Test**: Após catálogo 003 + US1, carga com fixtures samples; demitidos inativos; áreas/cargos resolvidos; relatório completo (quickstart C2 parcial)  
**Allowlist**: `legacy_import/{resolve,crosswalk,importer}.py`, `importar_colaboradores.py` — **proibido** mutar `scope.py` / forms denylist domínio

### Implementation for User Story 2

- [X] T015 [P] [US2] Implementar resolução de e-mail (ordem empresarial→corporativo→pessoal), `Area` get_or_create, `Cargo` lookup/create (`solides_id`/`canonical_key`), `is_active` via demissão e reuso read-only de `normalize.py` em `apps/accounts/services/legacy_import/resolve.py` conforme `contracts/column-mapping-contract.md` (allowlist US2; denylist intacta)
- [X] T016 [P] [US2] Implementar índice crosswalk `canonical_key(Nome Avaliado)` → `Identificador Avaliado` com detecção de ambiguidade em `apps/accounts/services/legacy_import/crosswalk.py` conforme `contracts/solides-id-crosswalk-contract.md` (allowlist; denylist intacta)
- [X] T017 [P] [US2] Estender contadores e seções US2 (`areas_*`, `cargos_*`, `usuarios_*`, `solides_id_preenchidos`, `demitidos_inativos`, `nao_importaveis`, `conflitos`) com **amostra mascarada** em `apps/accounts/services/legacy_import/report.py` conforme `contracts/import-command-contract.md` (denylist intacta)
- [X] T018 [US2] Implementar fase A do pipeline (`Area` → `Cargo` → `CustomUser` upsert por e-mail) em `apps/accounts/services/legacy_import/importer.py` — persistência via `full_clean()` + `save()` / `create_user()` + `set_unusable_password()`; `email_confirmado_em=timezone.now()`; **sem PII extra**; `transaction.atomic()`; denylist intacta
- [X] T019 [US2] Criar management command fino `apps/accounts/management/commands/importar_colaboradores.py` com args `--colaboradores`, `[--avaliacoes]`, `[--report-file]`, impressão relatório e códigos de saída básicos conforme `contracts/import-command-contract.md` (allowlist; sem UI/DRF/Celery; denylist intacta)
- [X] T020 [US2] Validar US2 via `specs/010-import-colaboradores-legado/quickstart.md` C2 (dry-run manual se US4 pendente, carga samples, demitidos inativos, e-mail confirmado, áreas criadas); confirmar denylist diff vazio

**Checkpoint**: US2 funcional — colaboradores/áreas/cargos populados; gestores ainda pendentes (US3)

---

## Phase 5: User Story 3 — Resolver hierarquia de gestores (Priority: P1) 🎯 MVP (parte 3)

**Goal**: Fase B resolve `line_manager` via `Superior direto id` → `solides_id`; ciclos reportados sem aplicar vínculo inválido  
**Independent Test**: Após US2, fixture com superior resolvível → `line_manager` correto; superior inexistente/ciclo → relatório (quickstart C3)  
**Allowlist**: `legacy_import/hierarchy.py`, integração em `importer.py` — **proibido** bypass de `CustomUser.clean()` (RF-04.1)

### Implementation for User Story 3

- [X] T021 [US3] Implementar fase B (`Superior direto id` → lookup `CustomUser.solides_id`, `full_clean()` + `save()`, detecção aciclicidade/ciclo) em `apps/accounts/services/legacy_import/hierarchy.py` conforme research R5/R11 e `contracts/column-mapping-contract.md` §line_manager (persistência via save()/clean(); denylist intacta)
- [X] T022 [US3] Integrar fase hierarquia após persistência de todos os usuários em `apps/accounts/services/legacy_import/importer.py` e contadores `gestores_vinculados`/`sem_gestor`/`ciclos_hierarquia` em `report.py` (allowlist; denylist intacta)
- [X] T023 [US3] Validar US3 via `specs/010-import-colaboradores-legado/quickstart.md` C3 (crosswalk + gestores, superior inexistente, ciclo artificial); confirmar denylist diff vazio

**Checkpoint**: US3 independentemente testável; hierarquia acíclica ou conflitos reportados (SC-004 parcial)

---

## Phase 6: Gate MVP (US1 + US2 + US3) — verificação obrigatória 🎯

**Purpose**: Fechar o **mínimo indispensável** antes de P2; equivalente ao gate T029 da spec 009  
**Pré-requisito**: **obrigatório** antes de demo MVP / seguir para US4

- [X] T024 Gate MVP / regressão denylist: `git diff main --` paths denylist = **vazio** (`apps/cycles/services/stage.py`, `apps/cycles/services/cycle.py`, `apps/goals/services/approval.py`, `apps/accounts/services/scope.py`, `apps/reviews/services/evaluation.py`, `apps/dashboard/services/adherence.py`) **e** suíte stage/scope verde: `pytest tests/test_stage_machine tests/test_scope tests/test_reject_stage_invariant -q`. Diff allowlist MUST restringir-se a `solides_id`, `legacy_import/**`, comando, `requirements.txt`, `samples/**`. Migrations: **somente** AddField `solides_id`. — evidência 2026-08-13: base efetiva da feature `2967bf9` (merge 009)→HEAD — denylist **0 linhas** (`stage.py`/`cycle.py`/`approval.py`/`scope.py`/`evaluation.py`/`adherence.py`); pytest `test_stage_machine`+`test_scope`+`test_reject_stage_invariant` **25 PASS**; models **somente +solides_id**; migrations **somente AddField solides_id**. Nota: `git diff main` é ruidoso (`main` = commit inicial sem o app); comparar contra a base da branch. Diff restante = allowlist (`solides_id`, `legacy_import/**`, comando, `requirements.txt`+openpyxl, `samples/**`, `specs/010-*`, package inits do command, README operacional, ignore `raw/` PII); **exceção operacional** `docker-compose.yml` + celerybeat no `.gitignore` (schedule/pid em `/tmp`, sem domínio).

**Checkpoint MVP**: US1+US2+US3 entregáveis; denylist de domínio intacta; stage/scope PASS — **release mínimo viável**

---

## Phase 7: User Story 4 — Simular e reexecutar importação com segurança (Priority: P2)

**Goal**: `--dry-run`, idempotência por e-mail, erros fatais pré-persistência e exit codes 0/1  
**Independent Test**: Dry-run zero writes; segunda execução sem duplicatas; arquivo inválido exit 1 (quickstart C4)  
**Allowlist**: `importer.py`, `parse_xlsx.py`, `importar_colaboradores.py` — **proibido** raw SQL / bulk bypass

### Implementation for User Story 4

- [X] T025 [US4] Implementar modo `--dry-run` (parse + crosswalk + totais projetados, zero commit) e falha fatal pré-persistência (arquivo ausente, OOXML ilegível, colunas obrigatórias ausentes) com exit `1` em `apps/accounts/services/legacy_import/importer.py` e `parse_xlsx.py` conforme research R13 (denylist intacta)
- [X] T026 [US4] Implementar idempotência por e-mail normalizado (`criados`/`atualizados`/`inalterados`; colisão e-mail no backup → conflito sem sobrescrever) em `apps/accounts/services/legacy_import/importer.py` conforme research R12 e FR-013 (via save()/clean(); denylist intacta)
- [X] T027 [US4] Consolidar exit codes 0/1 e rollback em exceção de persistência (`transaction.atomic()`) em `apps/accounts/services/legacy_import/importer.py` e `apps/accounts/management/commands/importar_colaboradores.py` conforme `contracts/import-command-contract.md` §Códigos de saída (denylist intacta)
- [X] T028 [US4] Validar US4 via `specs/010-import-colaboradores-legado/quickstart.md` C4 (dry-run, reexecução, arquivo corrompido); confirmar denylist diff vazio — evidência 2026-08-13: C4.1 dry-run `modo: dry-run` + `usuarios_criados: 2` projetados e snapshot User/Area/Cargo inalterado (SC-006); C4.2 persist 1ª execução `usuarios_criados: 2` / 2ª execução `usuarios_criados: 0` `usuarios_atualizados: 0` `usuarios_inalterados: 2` (delta duplicatas e-mail = 0, SC-007); dry-run pós-persist também `usuarios_inalterados: 2` sem writes; C4.3 arquivo ausente e OOXML corrompido → `CommandError.returncode == 1` e DB inalterado; CLI `manage.py importar_colaboradores` sem `--colaboradores` e path inexistente → **exit 1**; denylist `git diff 2967bf9` + working tree = **0 linhas** (`stage.py`/`cycle.py`/`approval.py`/`scope.py`/`evaluation.py`/`adherence.py`). Fixtures XLSX temporárias (sem `raw/`); suíte oficial US5 permanece T030+.

**Checkpoint**: SC-006/SC-007 atendidos; dry-run operacional; reexecução estável

---

## Phase 8: User Story 5 — Validar importação com dados anonimizados (Priority: P2)

**Goal**: Fixtures anonimizadas + suite pytest em CI sem `raw/`; cobertura dry-run, idempotência, demitidos, hierarquia, crosswalk, migration reversível  
**Independent Test**: `pytest tests/test_import_colaboradores_legado.py -q` verde; nenhum teste referencia `data/legado-solides/raw/` (quickstart C5)  
**Allowlist**: `data/legado-solides/samples/**`, `tests/test_import_colaboradores_legado.py`

### Implementation for User Story 5

- [ ] T029 [P] [US5] Criar fixtures XLSX anonimizadas mínimas (`colaboradores_min.xlsx`, `avaliacoes_crosswalk_min.xlsx`) em `data/legado-solides/samples/` — subset: ativos, demitidos, sem superior, crosswalk parcial, datas serial+ISO; **sem PII real**; denylist intacta
- [ ] T030 [P] [US5] Criar `tests/test_import_colaboradores_legado.py` com testes de dry-run (zero writes) e idempotência (2ª execução delta duplicatas=0) usando **somente** `data/legado-solides/samples/` (SC-008; **proibido** `raw/`; denylist intacta)
- [ ] T031 [P] [US5] Adicionar testes de demitidos inativos, ordem preferência e-mail, Area/Cargo resolve e crosswalk parcial/ambíguo em `tests/test_import_colaboradores_legado.py` (allowlist; denylist intacta)
- [ ] T032 [P] [US5] Adicionar testes de hierarquia (`line_manager` resolvível), ciclo reportado (vínculo não aplicado) e arquivo inválido (exit 1, DB inalterado) em `tests/test_import_colaboradores_legado.py` (denylist intacta)
- [ ] T033 [US5] Adicionar teste migration reversível (`solides_id` forward/backward preserva seed) e assert diff denylist vazio pós-import em `tests/test_import_colaboradores_legado.py` conforme `contracts/migration-safety.md` §4 (denylist intacta)
- [ ] T034 [US5] Validar US5 via `specs/010-import-colaboradores-legado/quickstart.md` C5 + C6 (pytest verde; relatório sem CPF; login bloqueado sem reset); confirmar CI não lê `raw/`

**Checkpoint**: SC-008/SC-009 atendidos; suite CI segura

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: Validação quickstart end-to-end, smoke staging e **gate final** de regressão  
**Pré-requisito**: após stories desejadas; gate final **sempre** antes de declarar feature done

- [ ] T035 [P] Percorrer `specs/010-import-colaboradores-legado/quickstart.md` completo (C1–C6) e verificar SC-001…SC-010 aplicáveis; smoke opcional com `raw/` **somente** manual em staging (fora do CI)
- [ ] T036 [P] Confirmar relatório stdout/`--report-file` usa **amostra mascarada** exclusivamente (`mask_email`/`mask_pii` em `report.py`); inspecionar ausência de CPF/RG/endereço em logs e registros importados (SC-009)
- [ ] T037 Gate final regressão denylist: `git diff main --` paths denylist = **vazio** (mesmos paths da T024) **e** suíte completa verde: `pytest tests/test_stage_machine tests/test_scope tests/test_reject_stage_invariant tests/test_import_colaboradores_legado.py -q`. Migrations: **ADITIVA somente solides_id**. Allowlist-only no diff restante.

**Checkpoint**: Feature done; denylist intacta; pytest stage/scope + import verdes

---

## Dependencies & Execution Order

### Phase Dependencies

| Fase | Depende de | Notas |
|------|------------|-------|
| Setup (1) | — | Imediato |
| Foundational (2) | Setup | **Bloqueia** todas as stories |
| US1 (3) | Foundational | Schema antes de import |
| US2 (4) | US1 | FKs + `solides_id` existem |
| US3 (5) | US2 | Hierarquia **depois** persist User |
| Gate MVP T024 (6) | US1+US2+US3 | **Mínimo indispensável** |
| US4 (7) | T024 | Dry-run/idempotência sobre pipeline core |
| US5 (8) | US2 (+ US3/US4 para cobertura completa) | Fixtures + pytest |
| Polish + T037 (9) | Stories feitas | Gate final sempre |

```text
Setup → Foundational → US1 → US2 ──► US3 ──► T024 (MVP) → US4 → US5 → Polish + T037
                              └─ T015 ∥ T016 ∥ T017 (resolve ∥ crosswalk ∥ report)
```

### User Story Dependencies

| Story | Prioridade | Depende de | Entrega independente |
|-------|-----------|------------|----------------------|
| US1 | P1 | Foundational | Schema `solides_id` em 5 entidades |
| US2 | P1 | US1 | Colaboradores + áreas + cargos + crosswalk |
| US3 | P1 | US2 | + hierarquia `line_manager` |
| US4 | P2 | T024 (pipeline core) | Dry-run + idempotência + exit codes |
| US5 | P2 | US2 (+ US3/US4) | Fixtures + pytest CI |

### Within Each User Story

- Foundational (parse, dates, report base) antes de resolve/crosswalk/importer
- US1 migrations antes de qualquer persistência de import
- US2 fase A (User) antes de US3 fase B (hierarchy)
- US4 consolida dry-run/idempotência sobre `importer.py` completo
- US5 testes após implementação estável (ou TDD incremental por caso)

### Parallel Opportunities

- **Phase 1**: T004 ∥ T003 (após T001); T002 ∥ T003
- **Phase 2**: T005, T006, T007 em paralelo
- **Phase 3**: T008–T012 em paralelo (models distintos); T013 sequencial após models
- **Phase 4**: **T015 ∥ T016 ∥ T017** (resolve ∥ crosswalk ∥ report); T018/T019 sequenciais
- **Phase 8**: T029–T032 em paralelo (casos `test_*` distintos — coordenar por função)
- **Phase 9**: T035 ∥ T036

---

## Parallel Example: User Story 2

```bash
# Após US1 completo, iniciar em paralelo (arquivos distintos):
Task T015: "resolve.py — email, Area, Cargo, is_active"
Task T016: "crosswalk.py — Nome → Identificador Avaliado"
Task T017: "report.py — contadores US2 + amostra mascarada"

# Sequencial depois (User antes de hierarchy):
Task T018: "importer.py fase A — Area → Cargo → CustomUser"
Task T019: "importar_colaboradores.py command"
Task T020: "validação quickstart C2"
```

---

## Parallel Example: Foundational

```bash
# Em paralelo (devs diferentes):
Task T005: parse_xlsx.py
Task T006: dates.py
Task T007: report.py (base + mask)

# Nenhum depende de migration US1
```

---

## Parallel Example: User Story 1 (migrations)

```bash
# Models em paralelo (apps distintos):
Task T008: accounts/models.py CustomUser.solides_id
Task T009: organization/models.py Cargo.solides_id
Task T010: competencies/models.py Competencia.solides_id
Task T011: reviews/models.py Avaliacao.solides_id
Task T012: pdi/models.py PDI.solides_id

# Depois:
Task T013: makemigrations × 5 apps (ADITIVA somente)
```

---

## Implementation Strategy

### MVP First (User Stories 1 + 2 + 3)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (**crítico**)
3. Complete Phase 3: US1 — schema `solides_id`
4. Complete Phase 4: US2 — colaboradores + áreas + cargos + crosswalk
5. Complete Phase 5: US3 — hierarquia gestores
6. **STOP**: executar **T024** (diff denylist vazio + pytest stage/scope)
7. Demo/MVP se T024 PASS — **aceitável como release mínimo**

### Incremental Delivery

1. Setup + Foundational → base pronta
2. US1 → migrate solides_id → validar C1
3. US2 → carga colaboradores → validar C2 (**valor de negócio 6.5.2**)
4. US3 → hierarquia → validar C3
5. **T024** gate MVP
6. US4 → dry-run/idempotência → validar C4
7. US5 → fixtures + pytest → validar C5/C6
8. Polish + **T037** gate final

### Se o tempo apertar (corte explícito)

| Prioridade | Entrega | Aceite |
|------------|---------|--------|
| **Obrigatório** | US1 + US2 + US3 + T024 (+ T037 se merge) | Release mínimo colaboradores + schema |
| **Desejável** | + US4 | Dry-run/idempotência operacional |
| **Desejável** | + US5 | CI seguro sem `raw/` |

### Parallel Team Strategy

Com 2+ desenvolvedores após Foundational:

- Dev A: US1 migrations (T008–T014)
- Dev B: prepara T015/T016/T017 enquanto US1 não conclui (código only; testes após migrate)
- Após US1: Dev A → US2 importer/command; Dev B pode iniciar US5 fixtures (T029)
- US3 sequencial após US2 fase A
- Juntos: **T024**
- Se houver prazo: Dev A US4 ∥ Dev B US5 testes → **T037**

---

## Notes

- **[P]** = arquivos diferentes, sem dependência incompleta
- Toda task de implementação MUST citar path **allowlist** e reforçar **denylist intacta**
- Tasks de migration: **ADITIVA somente solides_id; sem alterar campos existentes**
- Tasks de persistência: **via save()/clean(); unusable password; sem PII extra**
- Tasks de relatório: **amostra mascarada**
- Task que proponha alterar denylist / mutar AuthZ / stage / approval / fórmulas / PII → **REJEITAR**
- Reutilizar `canonical_key`/`display_name` read-only de `apps/competencies/services/catalog_import/normalize.py` — **não** reimplementar catálogo 003
- Assumir `importar_competencias_cargo` (003) executado antes da carga real
- `openpyxl` **somente** em `parse_xlsx.py`
- Commit por task ou grupo lógico; **não pular T024 / T037**
- Ordem operacional completa: migrate → 003 → importar_colaboradores (ver `data/legado-solides/README.md`)
