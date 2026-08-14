# Implementation Plan: Importação One-Shot do Legado Sólides — Ciclos Históricos e Cabeçalhos de Avaliação

**Branch**: `011-import-ciclos-avaliacoes-legado` | **Date**: 2026-08-13 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/011-import-ciclos-avaliacoes-legado/spec.md`

**Note**: Preenchido pelo workflow `/speckit-plan`. Artefatos de design em [research.md](./research.md), [data-model.md](./data-model.md), [contracts/](./contracts/), [quickstart.md](./quickstart.md). Clarifications 2026-08-13 são **decisões fechadas** — não reabrir.

## Summary

Evoluir o schema com **uma** migration aditiva (`Ciclo.solides_id`) e implementar management command Django one-shot (`importar_ciclos_avaliacoes`) com duas fases atômicas: (1) `backup_solicitacoes_*` → ciclos históricos **sempre** `status=encerrado`; (2) `backup_avaliacoes_*` → cabeçalhos `Avaliacao` agregados 1:1 por `(ciclo, usuario)` em estado terminal (`etapa=feedback`, `concluida=True`) **sem** chamar `stage` / `open_cycle` / `close_cycle` / approval. Parser OOXML via **openpyxl** já justificado na 010 — estender `apps/accounts/services/legacy_import/` (parse/dates/report); orquestração de domínio em `apps/cycles/services/legacy_import/`. Sem DRF, UI ou Celery. Pré-condição: specs 003 + 010 aplicadas.

Abordagem: migration aditiva só em `cycles` + serviço fino + testes pytest com samples anonimizados. Ver [research.md](./research.md).

## Technical Context

**Language/Version**: Python 3.x / Django 6.0.7

**Primary Dependencies**: Django 6.0.7 (full stack, sem DRF); **openpyxl** (já na 010 — somente parse XLSX OOXML); stdlib `datetime` / `unicodedata`; pytest-django; reuso de `apps/accounts/services/legacy_import/{parse_xlsx,dates,report,crosswalk}` e `canonical_key`/`display_name` (003)

**Storage**: SQLite (dev) → PostgreSQL (prod); ORM Django; migration aditiva `Ciclo.solides_id` (única alteração de schema desta fatia); `Avaliacao.solides_id` já existe (010)

**Testing**: pytest-django em `tests/test_import_ciclos_avaliacoes_legado.py`; fixtures em `data/legado-solides/samples/` (nunca `raw/`); gate denylist + regressão stage/scope/reject_stage_invariant

**Target Platform**: CLI operacional (`manage.py`); locale `pt-br`; operador admin técnico / RH

**Project Type**: Monólito Django — management command + migration; sem UI

**Performance Goals**: ~57 solicitações + ~1.925 linhas de avaliação; carga síncrona; relatório revisável em < 3 min (SC-009/SC-010); dry-run sem writes

**Constraints**: openpyxl **apenas** no parser; **não** alterar `scope.py` / AuthZ; **não** mutar snapshots write-once; **não** chamar `stage.py`, `cycle.py` (open/close), `approval.py`, `evaluation.py`, `adherence.py`; migration **somente** `Ciclo.solides_id`; PII raw fora do CI; relatório mascarado

**Scale/Scope**: One-shot operacional; dump 2026-06-24 (~57 ciclos, ~1.925 linhas → N grupos agregados); 3 user stories (P1–P2); fatia pré-6.5.4 + 6.5.4 cabeçalhos; notas/comentários fora (6.5.5)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Princípio | Status | Evidência no design |
|---|---|---|
| **I. Simplicidade Django-First** | ✅ PASS | Management command + ORM `full_clean()`/`save()`; openpyxl **só** no parser (já justificado na 010 — sem nova lib); estende `legacy_import` compartilhado; sem UI/DRF/Celery. Ver [research.md R1/R2](./research.md). |
| **II. Segurança e Escopo no Backend** | ✅ PASS | Import **não** altera `scope.py`, `ScopedObjectMixin`, `get_visible_users`; comando operacional; relatório com amostra mascarada (sem dump PII). |
| **III. Imutabilidade e Integridade** | ✅ PASS | Não muta snapshots write-once (`peso_utilizado` / `nivel_esperado_utilizado`); `on_delete=PROTECT` intacto; migration **aditiva** só `Ciclo.solides_id`; não altera campos existentes de Ciclo/Avaliacao. |
| **IV. Modularidade por Domínio** | ✅ PASS | Migration em `apps/cycles`; comando + importer de domínio em `apps/cycles/services/legacy_import/`; parse/dates/report compartilhados em `accounts` (evita segundo parser). |
| **V. Reprodutibilidade de Cálculos** | ✅ PASS | `stage.py`, `cycle.py` (open/close), `approval.py`, `evaluation.py`, `adherence.py` **intocáveis**; persistência histórica direta de `etapa`/`concluida`/`status` via ORM apenas — sem máquina de estados. |
| **VI. Performance Assíncrona** | ✅ PASS | Carga síncrona (~57 + ~1925 linhas); Celery desnecessário nesta fatia. |

**Post-design re-check (Phase 1)**: Todos os gates permanecem ✅ PASS. Contratos formalizam CLI, agregação, allowlist/denylist, migration-safety e mapeamentos sem camadas extras nem reabertura das clarifications.

## Project Structure

### Documentation (this feature)

```text
specs/011-import-ciclos-avaliacoes-legado/
├── plan.md              # This file
├── research.md          # Phase 0
├── data-model.md        # Phase 1
├── quickstart.md        # Phase 1
├── contracts/
│   ├── import-command-contract.md
│   ├── column-mapping-contract.md
│   ├── aggregation-contract.md
│   ├── model-allowlist.md
│   ├── non-goals-denylist.md
│   └── migration-safety.md
└── tasks.md             # Phase 2 (/speckit-tasks — NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
apps/
├── accounts/services/legacy_import/
│   ├── parse_xlsx.py          # ESTENDER: sheets solicitações + avaliações (cabeçalho)
│   ├── dates.py               # REUSAR: serial Excel + ISO; helper rótulo de nome serial
│   ├── report.py              # ESTENDER: seções grupos_agregados / ids_colapsados
│   └── crosswalk.py           # REUSAR read-only: fallback nome→user quando necessário
├── cycles/
│   ├── models.py              # + solides_id (aditivo)
│   ├── migrations/            # ÚNICA migration de schema desta fatia
│   ├── management/commands/
│   │   └── importar_ciclos_avaliacoes.py   # CLI fino — duas fases
│   └── services/legacy_import/
│       ├── __init__.py
│       ├── aggregate.py       # group-by + linha canônica (aggregation-contract)
│       ├── resolve.py         # ciclo por solides_id; user por solides_id / fallback
│       └── importer.py        # orquestração atomic: ciclos → cabeçalhos
└── reviews/
    └── models.py              # SEM alteração de schema (solides_id já na 010)

data/legado-solides/
├── README.md
├── raw/                       # PII — NÃO usar em CI
└── samples/                   # + solicitacoes_min.xlsx, avaliacoes_headers_min.xlsx

tests/
└── test_import_ciclos_avaliacoes_legado.py
```

**Structure Decision**: Infra de parse XLSX permanece em `accounts/services/legacy_import/` (já contém openpyxl + dates + report da 010 — evita parsers divergentes). Domínio Ciclo/Avaliação histórica orquestra em `cycles/services/legacy_import/`. Um comando com duas fases espelha o padrão 010 (`--colaboradores` + arquivo secundário).

## Complexity Tracking

| Violation / Nota | Why Needed | Simpler Alternative Rejected Because |
|---|---|---|
| Django 6.0.7 vs constituição (Django 5.x) | Já ratificado nos planos 001–010 e em `requirements.txt` | Downgrade sem benefício |
| **openpyxl** (Princípio I) | Já justificado e presente na 010; backups Sólides são OOXML real | Nova lib / CSV — rejeitado; esta fatia **não** adiciona dependência nova |
| Pacote domínio em `cycles` + parse em `accounts` | Princípio IV + reuso sem duplicar openpyxl | Duplicar `parse_xlsx` em `cycles` — rejeitado (dois parsers); tudo em `accounts` — rejeitado (Ciclo não é domínio accounts) |
| Persistência direta `etapa=feedback` | Clarification 2026-08-13; histórico encerrado | Chamar `advance_stage` / open-close — rejeitado (denylist V) |
