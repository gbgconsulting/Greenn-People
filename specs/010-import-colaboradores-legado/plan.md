# Implementation Plan: Importação One-Shot do Legado Sólides — Colaboradores e Schema de Identificadores

**Branch**: `010-import-colaboradores-legado` | **Date**: 2026-08-12 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/010-import-colaboradores-legado/spec.md`

**Note**: Preenchido pelo workflow `/speckit-plan`. Artefatos de design em [research.md](./research.md), [data-model.md](./data-model.md), [contracts/](./contracts/), [quickstart.md](./quickstart.md).

## Summary

Evoluir o schema com `solides_id` (migration aditiva em cinco entidades) e implementar management command Django one-shot (`importar_colaboradores`) que lê `backup_colaboradores_*.xlsx` (OOXML real via **openpyxl**) e, opcionalmente, `backup_avaliacoes_*.xlsx` como crosswalk Nome → Identificador Avaliado. Popula `organization.Area`, `organization.Cargo` (faltantes), `accounts.CustomUser` (e-mail confirmado na importação, demitidos inativos) e resolve `line_manager` em segunda fase com validação acíclica (RF-04.1). Sem DRF, sem UI, sem Celery. Idempotente por e-mail normalizado (+ `solides_id` quando presente). Reutiliza `canonical_key` da spec 003. Não altera escopo, stage, approval, fórmulas nem snapshots.

Abordagem: migrations aditivas (6.5.1) + serviço em `apps/accounts/services/legacy_import/` + comando fino; testes pytest com fixtures anonimizadas em `data/legado-solides/samples/`. Ver [research.md](./research.md).

## Technical Context

**Language/Version**: Python 3.x / Django 6.0.7

**Primary Dependencies**: Django 6.0.7 (full stack, sem DRF); **openpyxl** (somente parse XLSX OOXML — ver Complexity Tracking); stdlib `unicodedata` / `datetime` / `decimal`; pytest-django; reuso read-only de `apps/competencies/services/catalog_import/normalize.py` (spec 003)

**Storage**: SQLite (dev) → PostgreSQL (prod); ORM Django; migrations aditivas `solides_id` em `CustomUser`, `Cargo`, `Competencia`, `Avaliacao`, `PDI`

**Testing**: pytest-django em `tests/test_import_colaboradores_legado.py`; fixtures anonimizadas (nunca `data/legado-solides/raw/`); gate de regressão stage/scope/reject_stage_invariant

**Target Platform**: CLI operacional (`manage.py`); locale `pt-br`; operador admin técnico / RH com acesso ao ambiente

**Project Type**: Monólito Django — superfície desta feature é management command + migrations, não UI

**Performance Goals**: ~325 colaboradores importados em segundos; relatório revisável em < 2 min (SC-010); dry-run sem writes

**Constraints**: openpyxl **apenas** para parse XLSX; sem alteração de `scope.py`, `ScopedObjectMixin`, `get_visible_users`; sem mutação de `Avaliacao.etapa`, snapshots write-once, `PROTECT`; denylist de domínio de serviços intacta; PII raw fora do CI; relatório com amostra mascarada

**Scale/Scope**: One-shot operacional; dump 2026-06-24 (~325 colaboradores, 127 ativos); 5 user stories (P1–P2); fatia 6.5.1 + 6.5.2 apenas

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Princípio | Status | Evidência no design |
|---|---|---|
| **I. Simplicidade Django-First** | ✅ PASS | Management command + serviço em `accounts`; ORM + `save()`/`clean()`; openpyxl **somente** para parse XLSX (sem UI/DRF/Celery). Ver [research.md R1](./research.md). |
| **II. Segurança e Escopo no Backend** | ✅ PASS | Import **não** altera `scope.py`, `ScopedObjectMixin`, `get_visible_users` nem regras AuthZ; comando operacional sem nova view exposta; denylist de domínio em forms permanece para cadastro normal (Decisão #21). |
| **III. Imutabilidade e Integridade** | ✅ PASS | Import **não** altera `Avaliacao.etapa`, `concluida`, `nota_final_*`; não muta snapshots write-once; `on_delete=PROTECT` intacto; migration aditiva nullable. |
| **IV. Modularidade por Domínio** | ✅ PASS | Serviço em `apps/accounts/services/legacy_import/`; migrations por app de domínio; reuso read-only de `normalize.py` (003). |
| **V. Reprodutibilidade de Cálculos** | ✅ PASS | `stage.py`, `approval.py`, `evaluation.py`, `adherence.py` na denylist; zero mutação de etapa/nota/aderência durante import de colaboradores. |
| **VI. Performance Assíncrona** | ✅ PASS | Carga síncrona no comando (~325 registros); Celery desnecessário. |

**Post-design re-check (Phase 1)**: Todos os gates permanecem ✅ PASS. Contratos formalizam CLI, allowlist/denylist, migration-safety e mapeamentos sem camadas extras.

## Project Structure

### Documentation (this feature)

```text
specs/010-import-colaboradores-legado/
├── plan.md              # This file
├── research.md          # Phase 0
├── data-model.md        # Phase 1
├── quickstart.md        # Phase 1
├── contracts/
│   ├── import-command-contract.md
│   ├── column-mapping-contract.md
│   ├── solides-id-crosswalk-contract.md
│   ├── model-allowlist.md
│   ├── non-goals-denylist.md
│   └── migration-safety.md
└── tasks.md             # Phase 2 (/speckit-tasks — NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
apps/
├── accounts/
│   ├── models.py                          # + solides_id em CustomUser
│   ├── migrations/                        # migration aditiva solides_id
│   ├── management/commands/
│   │   └── importar_colaboradores.py
│   └── services/legacy_import/
│       ├── __init__.py
│       ├── parse_xlsx.py                  # openpyxl — sheet colaboradores/avaliacoes
│       ├── dates.py                       # serial Excel + ISO
│       ├── crosswalk.py                   # Nome → Identificador Avaliado
│       ├── resolve.py                     # Area, Cargo, email, is_active
│       ├── hierarchy.py                   # line_manager 2ª fase + aciclicidade
│       ├── report.py                      # totais + amostra mascarada
│       └── importer.py                    # orquestração + atomic persist
├── organization/
│   ├── models.py                          # + solides_id em Cargo
│   └── migrations/
├── competencies/
│   ├── models.py                          # + solides_id em Competencia
│   └── migrations/
├── reviews/
│   ├── models.py                          # + solides_id em Avaliacao
│   └── migrations/
└── pdi/
    ├── models.py                          # + solides_id em PDI
    └── migrations/

data/legado-solides/
├── README.md                              # inventário (Decisão #22)
├── raw/                                   # PII — NÃO usar em CI
└── samples/                               # fixtures anonimizadas para pytest

tests/
└── test_import_colaboradores_legado.py
```

**Structure Decision**: Monólito Django existente. Feature 6.5.1 = migrations aditivas em cinco apps. Feature 6.5.2 = comando + serviço em `accounts`, reutilizando `organization`/`competencies` via ORM. Parse XLSX isolado em `parse_xlsx.py` (único módulo que importa openpyxl).

## Complexity Tracking

| Violation / Nota | Why Needed | Simpler Alternative Rejected Because |
|---|---|---|
| Django 6.0.7 vs constituição (Django 5.x) | Já ratificado nos planos 001–003 e em `requirements.txt` | Downgrade sem benefício |
| **openpyxl** (Princípio I) | Backups Sólides são OOXML real (`file` confirma); stdlib `csv` insuficiente | CSV disfarçado de `.xlsx` (003) não se aplica a `raw/`; openpyxl restrito a `parse_xlsx.py` |
| Senha unusable no create | Decisão #21 / segurança; sem hardcode | Senha temporária fixa — rejeitada (vazamento); reset forçado pós-import documentado como alternativa operacional |
| Migration em 5 apps | PRD 6.5.1 lista cinco models em apps distintas | Migration consolidada cross-app — rejeitada (viola modularidade IV) |
