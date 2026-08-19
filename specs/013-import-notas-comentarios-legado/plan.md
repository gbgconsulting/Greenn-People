# Implementation Plan: Importação One-Shot do Legado Sólides — Notas por Competência e Comentários Qualitativos

**Branch**: `013-import-notas-comentarios-legado` | **Date**: 2026-08-18 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/013-import-notas-comentarios-legado/spec.md`

**Note**: Preenchido pelo workflow `/speckit-plan`. Artefatos de design em [research.md](./research.md), [data-model.md](./data-model.md), [contracts/](./contracts/), [quickstart.md](./quickstart.md). Clarifications 2026-08-18 são **decisões fechadas** — não reabrir, não marcar NEEDS CLARIFICATION. **Não** gera `tasks.md` (isso é `/speckit-tasks`). **Não** reescreve `spec.md`.

## Summary

Management command one-shot Django (`importar_notas_comentarios`) com **DUAS fases** na mesma `transaction.atomic()` (notas → comentários). **ZERO migration** (FR-019). Parser OOXML = **openpyxl já justificado na 010**, **SOMENTE** em `apps/accounts/services/legacy_import/parse_xlsx.py`. Orquestração de domínio em `apps/reviews/services/legacy_import/` (**novo**). Reuso read-only: `canonical_key`/`display_name` (003), `nivel_esperado_for` (003 `mapping.py`), algoritmo de agregação 011 (`cycles/services/legacy_import/aggregate.py` — **IMPORTAR, não copiar**), `calcular_nota_final_lider` / `calcular_nota_final_autoavaliacao` (`reviews/services/evaluation.py` — **CHAMAR, NÃO EDITAR**). Sem UI, DRF, Celery, lib nova, templates/urls da 012.

Abordagem: serviço fino em `reviews` + extensão parse/dates/report em `accounts` + testes pytest com samples anonimizados. Ver [research.md](./research.md).

## Technical Context

**Language/Version**: Python 3.x / Django 6.0.7

**Primary Dependencies**: Django 6.0.7 (full stack, sem DRF); **openpyxl** (já na 010 — somente parse XLSX OOXML); stdlib `datetime` / `decimal` / `unicodedata`; pytest-django; reuso read-only de `canonical_key`/`display_name` (003), `nivel_esperado_for` (003 `mapping.py`), `aggregate.py` (011), `calcular_nota_final_*` (evaluation.py)

**Storage**: SQLite (dev) → PostgreSQL (prod); ORM `save()`/`full_clean()`; schema **existente** (`Avaliacao`, `AvaliacaoCompetencia` unique `(avaliacao, competencia)`, snapshots write-once no `save()`, `Feedback.tipo`/`ciente_em`, `Competencia.solides_id`, `CustomUser.solides_id`). **Sem AddField. Sem RunPython de domínio. Sem migration.**

**Testing**: pytest-django em `tests/test_import_notas_comentarios_legado.py`; samples em `data/legado-solides/samples/` (**NUNCA** `raw/`). Gate: `git diff` vazio na denylist + pytest `test_stage_machine` / `test_scope` / `test_reject_stage_invariant` **SEM alterar asserts**

**Target Platform**: CLI operacional (`manage.py`); locale `pt-BR`; operador técnico (admin de plataforma), não papel de produto novo

**Project Type**: Monólito Django — management command; **sem UI**

**Performance Goals**: dump 2026-06-24 ~7.360 notas + ~1.494 comentários + rebuild do mapa a partir de `backup_avaliacoes_*` (~1.925 linhas cabeçalho); carga **síncrona**; relatório < 3 min (SC-010); dry-run zero write (SC-008)

**Constraints**: openpyxl **apenas** no parser; **não** alterar/chamar `get_visible_users`, `scope.py`, `ScopedObjectMixin`; **não** mutar `etapa`/`concluida` da 011; **não** chamar `create_competency_lines`; **não** editar `evaluation.py`; **não** copiar `aggregate.py`; PII `raw/` fora do CI; relatório mascarado (máx. 5/seção)

**Scale/Scope**: One-shot operacional; 3 user stories (P1 notas, P1 comentários, P2 dry-run/idempotência/CI); fatia PRD 6.5.5 apenas (PDI/9-box/012 UI fora)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design. Violação não justificada BLOQUEIA.*

| Princípio | Status | Evidência no design |
|---|---|---|
| **I. Simplicidade Django-First** | ✅ PASS | Management command + ORM `full_clean()`/`save()`; openpyxl **só** no parser (já 010, **sem nova lib** — Complexity Tracking). Sem upload, DRF, Celery, SPA. Ver [research.md R1/R2](./research.md). |
| **II. Segurança e Escopo no Backend** | ✅ PASS | Import **NÃO** altera/chama `get_visible_users`, `scope.py`, `ScopedObjectMixin`. Import **não** “libera” nota. Leitura posterior = AuthZ vigente. Relatório mascarado (máx. 5/seção; sem comentário/nome/e-mail completos; logs sem linha XLSX crua). `raw/` fora do CI. |
| **III. Imutabilidade e Integridade** | ✅ PASS | `on_delete=PROTECT` intacto; sem CASCADE; `peso_utilizado` / `nivel_esperado_utilizado` write-once (respeitar `ValidationError` do model); **NÃO** apagar `Avaliacao` 011 para refazer; `Feedback` append-only (não reescrever conteúdo alheio). |
| **IV. Modularidade por Domínio** | ✅ PASS | Persistência em `reviews/services/legacy_import/`; parse **só** em `accounts/.../parse_xlsx.py`; 003 `mapping.py` e 011 `aggregate.py` **read-only**. Sem segundo parser. Sem openpyxl em `reviews`. |
| **V. Reprodutibilidade de Cálculos** | ✅ PASS | **CHAMAR** `calcular_nota_final_*` existente; **NÃO** editar `evaluation.py`; **NÃO** reimplementar normalização; **NÃO** chamar `create_competency_lines` (snapshotaria `CargoCompetencia` ATUAL — viola FR-010/RF-19.2). `stage.py` / `cycle.py` open-close / `approval.py` / `adherence.py` intocáveis. `etapa`/`concluida` 011 intactas. |
| **VI. Performance Assíncrona** | ✅ PASS | Sem task Celery; sem `calcular_aderencia`; sem `ClassificacaoTalento` a partir da nota. Carga síncrona one-shot (~7k + ~1.5k) no CLI — não é request HTTP; precedente 003/010/011. |

**Post-design re-check (Phase 1)**: Todos os gates permanecem ✅ PASS. Contratos formalizam CLI (3 paths obrigatórios), resolução de IDs colapsados (consome 011, não reabre), snapshots/fórmula (MUST call / MUST NOT edit), allowlist/denylist (inclui 012 urls/templates), e migration-safety = **zero** migrations. Clarifications 2026-08-18 não reabertas. Nenhum NEEDS CLARIFICATION residual.

## Project Structure

### Documentation (this feature)

```text
specs/013-import-notas-comentarios-legado/
├── plan.md              # This file
├── research.md          # Phase 0
├── data-model.md        # Phase 1
├── quickstart.md        # Phase 1
├── contracts/
│   ├── import-command-contract.md
│   ├── column-mapping-contract.md
│   ├── collapsed-id-resolution.md
│   ├── snapshot-and-formula.md
│   ├── model-allowlist.md
│   ├── non-goals-denylist.md
│   └── migration-safety.md
├── checklists/
│   └── requirements.md  # já passou — plan NÃO reescreve spec.md
└── tasks.md             # Phase 2 (/speckit-tasks — NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
apps/
├── accounts/services/legacy_import/
│   ├── parse_xlsx.py          # ESTENDER: sheets notas + comentários [+ habilidades opcional]
│   ├── dates.py               # ESTENDER se necessário: datetime Criado em (serial Excel)
│   └── report.py              # ESTENDER: seções notas_*/comentarios_*/orfaos_*/conflitos_*
├── cycles/services/legacy_import/
│   └── aggregate.py           # REUSO READ-ONLY — IMPORTAR, não copiar
├── competencies/services/catalog_import/
│   ├── normalize.py           # REUSO READ-ONLY: canonical_key, display_name
│   ├── mapping.py             # REUSO READ-ONLY: nivel_esperado_for, is_kpi, is_ambiguous
│   └── importer.py            # REUSO READ-ONLY: resolve_default_escala (extras)
├── reviews/
│   ├── models.py              # SEM alteração de schema (write-once / Feedback vigentes)
│   ├── services/evaluation.py # CHAMAR calcular_nota_final_*; MUST NOT edit; NÃO create_competency_lines
│   ├── services/legacy_import/
│   │   ├── __init__.py
│   │   ├── resolve.py         # avaliação canônica, competência, autor, ciclo aberto
│   │   ├── importer.py        # orquestração atomic: notas → comentários → fórmula
│   │   └── snapshots.py       # opcional: peso/nível write-once
│   └── management/commands/
│       └── importar_notas_comentarios.py   # CLI fino — duas fases
└── dashboard/ / pdi/ / talent/            # INTÁVEIS nesta fatia

data/legado-solides/
├── README.md
├── raw/                       # PII — NÃO usar em CI
└── samples/                   # + notas_min.xlsx, comentarios_min.xlsx, avaliacoes_headers (011)

tests/
└── test_import_notas_comentarios_legado.py
```

**Structure Decision**: Infra de parse XLSX permanece em `accounts/services/legacy_import/` (openpyxl + dates + report das 010/011 — evita parsers divergentes). Domínio de nota/feedback orquestra em `reviews/services/legacy_import/`. Mapa de IDs colapsados **consome** `cycles/.../aggregate.py`. Um comando com duas fases espelha 011. Sem tocar dashboard, templates, urls da 012, pdi, talent.

## Complexity Tracking

| Violation / Nota | Why Needed | Simpler Alternative Rejected Because |
|---|---|---|
| Django 6.0.7 vs constituição (Django 5.x) | Já ratificado nos planos 001–012 e em `requirements.txt` | Downgrade sem benefício |
| **openpyxl** (Princípio I) | Já justificado e presente na 010; backups Sólides são OOXML real | Nova lib / CSV — rejeitado; esta fatia **não** adiciona dependência nova |
| Pacote domínio em `reviews` + parse em `accounts` | Princípio IV + reuso sem duplicar openpyxl | Duplicar `parse_xlsx` em `reviews` — rejeitado (dois parsers); tudo em `accounts` — rejeitado (nota/feedback não são domínio accounts) |
| IMPORTAR `aggregate.py` da 011 (não copiar) | FR-003; IDs colapsados não estão no banco | Copiar algoritmo — rejeitado (divergência silenciosa); tabela persistida — rejeitado (PII extra) |
| Persistência direta de snapshots **sem** `create_competency_lines` | Clarification #2; FR-010/RF-19.2 | Chamar `create_competency_lines` — rejeitado (retrato do `CargoCompetencia` atual) |
| Carga síncrona ~7k linhas (Princípio VI) | CLI one-shot, não request HTTP; precedente 011 | Celery — rejeitado (FR-001; sem fila nesta fatia) |
