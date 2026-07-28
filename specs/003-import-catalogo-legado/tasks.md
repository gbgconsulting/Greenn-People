# Tasks: Importação One-Shot do Catálogo Legado de Cargos e Competências

**Input**: Design documents from `/specs/003-import-catalogo-legado/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: Incluídos conforme research R13 e plan.md (`tests/test_import_catalogo_legado.py` com fixtures CSV mínimas). Suíte na Phase 7 (Polish).

**Organization**: Tasks agrupadas por user story para implementação e validação independentes.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Pode rodar em paralelo (arquivos diferentes, sem dependência de tarefas incompletas)
- **[Story]**: User story (US1–US4); Setup/Foundational/Polish sem label de story
- Incluir caminhos de arquivo exatos nas descrições

## Path Conventions

Monólito Django: `config/`, `apps/<domain>/`, `tests/` na raiz do repositório. Fontes legadas na raiz: `lista-cargos.xlsx`, `lista-competencias.xlsx`.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Estrutura de pacotes para comando e serviço de importação

- [X] T001 Criar pacote `apps/competencies/services/catalog_import/` com `__init__.py` exportando API pública (`import_catalog`, tipos de relatório) conforme plan.md
- [X] T002 [P] Criar `apps/competencies/management/__init__.py` e `apps/competencies/management/commands/__init__.py` para registrar management commands Django

**Checkpoint**: Imports do pacote `catalog_import` resolvem sem erro; diretório de commands pronto para `importar_competencias_cargo`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Utilitários compartilhados de parse, normalização, mapeamento e relatório — BLOQUEIAM todas as user stories

**⚠️ CRITICAL**: Nenhuma user story deve começar antes desta fase

- [X] T003 [P] Implementar `display_name`, `canonical_key` e `split_pipe` em `apps/competencies/services/catalog_import/normalize.py` conforme `contracts/legado-domain-mapping-contract.md` §1–2
- [X] T004 [P] Implementar de-paras (`infer_cargo_nivel`, `nivel_esperado_for`, `map_grupo_tipo`, `classify_competencia`, sets KPI/ambíguos) em `apps/competencies/services/catalog_import/mapping.py` conforme `contracts/legado-domain-mapping-contract.md` §3–6 e `data-model.md`
- [X] T005 Implementar leitura CSV UTF-8, validação de colunas obrigatórias e expansão pipe-separated em `apps/competencies/services/catalog_import/parse.py` conforme research R2 e `contracts/import-command-contract.md` §Pré-condições
- [X] T006 [P] Implementar estrutura de relatório (contadores + listas detalhadas) e `format_report()` em `apps/competencies/services/catalog_import/report.py` conforme `contracts/import-command-contract.md` §Formato do relatório

**Checkpoint**: Parse de fixtures CSV mínimas retorna estruturas normalizadas; mapeamentos unitários testáveis; relatório formatável sem persistência

---

## Phase 3: User Story 1 — Carregar catálogo de cargos e competências (Priority: P1) 🎯 MVP

**Goal**: Comando importa cargos (com `nivel` correto) e competências avaliáveis (tipo + escala 1–5) a partir das fontes legadas

**Independent Test**: Executar importação em catálogo vazio; verificar cargos/competências no CRUD existente com nomes normalizados, tipos corretos e escala `Escala padrão 1-5` (quickstart C1)

### Implementation for User Story 1

- [ ] T007 [US1] Implementar `resolve_default_escala()` em `apps/competencies/services/catalog_import/importer.py` — reutilizar escala ativa `Escala padrão 1-5` ou criar; conflito fatal se só inativa (research R9)
- [ ] T008 [US1] Implementar upsert de `organization.Cargo` (create/update ativo por `canonical_key`; `nivel` via `infer_cargo_nivel`) em `apps/competencies/services/catalog_import/importer.py`
- [ ] T009 [US1] Implementar upsert de `competencies.Competencia` (somente avaliáveis; `tipo`, `descricao`, FK escala) em `apps/competencies/services/catalog_import/importer.py`
- [ ] T010 [US1] Orquestrar fase parse→persist (Escala → Cargos → Competências) em `import_catalog()` com `transaction.atomic()` em `apps/competencies/services/catalog_import/importer.py`
- [ ] T011 [US1] Criar management command fino `apps/competencies/management/commands/importar_competencias_cargo.py` com args `--cargos`, `--competencias`, `--report-file`, `--dry-run` e impressão do relatório

**Checkpoint**: US1 funcional — catálogo de cargos e competências populado; KPIs ainda podem ser filtrados mas vínculos ainda ausentes

---

## Phase 4: User Story 2 — Montar perfil esperado cargo↔competência (Priority: P1)

**Goal**: Criar vínculos `CargoCompetencia` com `peso=1` e `nivel_esperado` coerente; reconciliar duas fontes

**Independent Test**: Após importação, cargo conhecido tem competências vinculadas com `peso=1` e `nivel_esperado` conforme senioridade; CRUD US-14 editável (quickstart C2)

### Implementation for User Story 2

- [ ] T012 [P] [US2] Implementar extração de pares `(cargo, competencia)` das vistas A/B em `apps/competencies/services/catalog_import/reconcile.py`
- [ ] T013 [US2] Implementar detecção de divergências (symmetric difference) e matriz final (união de pares elegíveis) em `apps/competencies/services/catalog_import/reconcile.py` conforme `contracts/legado-domain-mapping-contract.md` §8
- [ ] T014 [US2] Implementar upsert de `competencies.CargoCompetencia` (`update_or_create` por par; `peso=Decimal('1')`; `nivel_esperado` via `nivel_esperado_for(cargo.nivel)`) em `apps/competencies/services/catalog_import/importer.py`
- [ ] T015 [US2] Integrar reconcile + persistência de vínculos no pipeline `import_catalog()` após cargos/competências em `apps/competencies/services/catalog_import/importer.py`

**Checkpoint**: US1 + US2 completos — perfil esperado por cargo disponível no CRUD existente (SC-008)

---

## Phase 5: User Story 3 — Separar competências de KPIs operacionais (Priority: P2)

**Goal**: KPIs/métricas excluídos do catálogo; ambíguos em `nao_mapeados`; relatório distinguível

**Independent Test**: Itens operacionais (SLA, Lead time, Throughput, etc.) ausentes como `Competencia` ativa e listados em `Excluídos KPI` (quickstart C3)

### Implementation for User Story 3

- [ ] T016 [US3] Completar match por família/prefixo de KPI (throughput, índice de incidentes, variantes com sufixo) em `apps/competencies/services/catalog_import/mapping.py` conforme `contracts/legado-domain-mapping-contract.md` §6.1
- [ ] T017 [US3] Garantir lista de ambíguos documentados bloqueia persistência com `motivo=ambiguo` em `apps/competencies/services/catalog_import/mapping.py` conforme §6.2
- [ ] T018 [US3] Preencher seções `Excluídos KPI` e `Não mapeados` no relatório com contadores alinhados às listas em `apps/competencies/services/catalog_import/report.py` e integração no fluxo de `parse.py`/`importer.py`

**Checkpoint**: SC-005 atendido — zero KPI ativo no catálogo; operador distingue excluídos vs avaliáveis no relatório

---

## Phase 6: User Story 4 — Reexecutar importação de forma segura (Priority: P2)

**Goal**: Idempotência por nome canônico; soft-delete não reativado; dry-run; erros fatais sem writes parciais

**Independent Test**: Segunda execução idêntica sem duplicatas; cargo/competência inativo permanece inativo com entrada em `Conflitos` (quickstart C4–C5)

### Implementation for User Story 4

- [ ] T019 [US4] Implementar lookup por `canonical_key` com ramos ativo (update/noop) vs inativo (conflito `inativo_existente`, skip create) para Cargo e Competencia em `apps/competencies/services/catalog_import/importer.py` conforme `contracts/legado-domain-mapping-contract.md` §9
- [ ] T020 [US4] Implementar modo `--dry-run` (parse + totais projetados, zero commit) e códigos de saída 0/1 em `apps/competencies/services/catalog_import/importer.py` e `apps/competencies/management/commands/importar_competencias_cargo.py`
- [ ] T021 [US4] Implementar falha fatal pré-persistência (arquivo ausente, encoding/colunas inválidas, escala inativa) com exit `1` e rollback em `apps/competencies/services/catalog_import/parse.py` e command
- [ ] T022 [US4] Registrar entradas `merged` (mesma chave canônica, grafias distintas) durante normalização em `apps/competencies/services/catalog_import/normalize.py` e seção correspondente em `report.py`

**Checkpoint**: SC-006 atendido — reexecução estável; dry-run operacional; soft-delete respeitado

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Suíte de testes, validação quickstart e verificação de conformidade constitucional

- [ ] T023 [P] Criar `tests/test_import_catalogo_legado.py` com fixtures CSV temporárias e testes de de-para `Cargo.nivel` / `nivel_esperado` (research R13)
- [ ] T024 [P] Adicionar testes de filtro KPI + ambíguos em `tests/test_import_catalogo_legado.py`
- [ ] T025 [P] Adicionar testes de reconciliação de matriz e divergências reportadas em `tests/test_import_catalogo_legado.py`
- [ ] T026 [P] Adicionar testes de idempotência (2ª execução) e soft-delete não reativado em `tests/test_import_catalogo_legado.py`
- [ ] T027 Adicionar teste de arquivo inválido/ausente (exit 1, DB inalterado) em `tests/test_import_catalogo_legado.py`
- [ ] T028 Executar validação manual dos cenários C1–C5 em `specs/003-import-catalogo-legado/quickstart.md` contra `lista-cargos.xlsx` e `lista-competencias.xlsx` na raiz

**Checkpoint**: `pytest tests/test_import_catalogo_legado.py -q` verde; quickstart smoke ok; SC-001..SC-007 verificados

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: Sem dependências — iniciar imediatamente
- **Foundational (Phase 2)**: Depende de Setup — **BLOQUEIA** todas as user stories
- **User Stories (Phase 3–6)**: Dependem de Foundational
  - US1 (Phase 3) antes de US2 (Phase 4) — vínculos exigem cargos/competências persistidos
  - US3 (Phase 5) pode overlap com US1/US2 no código de `mapping.py`, mas validação US3 assume pipeline US1+US2
  - US4 (Phase 6) consolida idempotência sobre pipeline completo — idealmente após US1–US3
- **Polish (Phase 7)**: Depende de US1–US4 implementados

### User Story Dependencies

| Story | Prioridade | Depende de | Entrega independente |
|-------|-----------|------------|----------------------|
| US1 | P1 | Foundational | Catálogo cargos + competências |
| US2 | P1 | US1 | + vínculos CargoCompetencia |
| US3 | P2 | US1 (classificação) | KPI/ambíguos no relatório |
| US4 | P2 | US1 + US2 (+ US3) | Reexecução segura |

### Within Each User Story

- Foundational (normalize, mapping, parse, report) antes de importer
- Importer parcial antes de command
- Reconcile antes de persistência de vínculos (US2)
- Testes automatizados após implementação (Phase 7)

### Parallel Opportunities

- **Phase 1**: T002 ∥ T001 (após T001 criar dir pai)
- **Phase 2**: T003, T004, T006 em paralelo; T005 após T003
- **Phase 4**: T012 ∥ T014 (arquivos diferentes); T013/T015 sequenciais
- **Phase 7**: T023–T026 em paralelo (mesmo arquivo de teste, mas casos distintos — coordenar por função `test_*` separada)

---

## Parallel Example: User Story 2

```bash
# Após US1 completo, iniciar em paralelo:
Task T012: "pares vista A/B em reconcile.py"
Task T014: "upsert CargoCompetencia em importer.py"

# Sequencial depois:
Task T013: "divergências + união em reconcile.py"
Task T015: "integrar reconcile no import_catalog()"
```

---

## Parallel Example: Foundational

```bash
# Em paralelo (devs diferentes):
Task T003: normalize.py
Task T004: mapping.py
Task T006: report.py

# Depois:
Task T005: parse.py (usa normalize)
```

---

## Implementation Strategy

### MVP First (User Stories 1 + 2)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (**crítico**)
3. Complete Phase 3: US1 — catálogo base
4. Complete Phase 4: US2 — perfil cargo↔competência
5. **STOP and VALIDATE**: quickstart C1 + C2
6. Demo/deploy operacional do catálogo + perfis

### Incremental Delivery

1. Setup + Foundational → base pronta
2. US1 → catálogo cargos/competências → validar C1
3. US2 → vínculos → validar C2 (**valor de negócio Sprint 6.5.3**)
4. US3 → higiene KPI → validar C3
5. US4 → idempotência/dry-run → validar C4–C5
6. Polish → pytest + smoke SC-001..SC-007

### Parallel Team Strategy

Com 2+ desenvolvedores após Foundational:

- Dev A: US1 (importer cargos/competências + command)
- Dev B: US2 (reconcile + vínculos) — inicia T012/T014 quando T008–T009 estável
- US3/US4 sequenciais ou em paralelo após pipeline core

---

## Notes

- Reutilizar models existentes (`organization.Cargo`, `competencies.*`) — **sem migrations novas** esperadas (plan.md)
- Sem openpyxl, DRF, UI ou Celery — stdlib `csv` + ORM Django
- Não importar users, avaliações, PDIs; não alterar fórmula de notas (constituição III/V)
- Fontes legadas na raiz do repo; paths overrideáveis via `--cargos` / `--competencias`
- Commit após cada task ou grupo lógico; parar em checkpoints para validar story independentemente
