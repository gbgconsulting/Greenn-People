# Implementation Plan: Importação One-Shot do Catálogo Legado

**Branch**: `003-import-catalogo-legado` (git: `feat/carga-cargos-competencias`) | **Date**: 2026-07-28 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/003-import-catalogo-legado/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

Implementar management command Django one-shot (`importar_competencias_cargo`) que lê `lista-cargos.xlsx` e `lista-competencias.xlsx` (CSV com extensão `.xlsx`) e popula o catálogo existente — `organization.Cargo`, `competencies.Competencia`, `competencies.CargoCompetencia`, `competencies.Escala` — com de-para de senioridade, tipo, `nivel_esperado`, peso=1, filtro de KPI e relatório de carga. Sem DRF, sem UI de upload, sem openpyxl; parse via `csv` + UTF-8. Idempotente por nome canônico entre ativos; soft-delete (`is_active=False`) não reativa silenciosamente. Não altera fórmula de avaliação nem snapshots históricos.

Abordagem: serviço de domínio em `apps/competencies/services/catalog_import/` + comando fino; testes pytest cobrindo mapeamentos, KPI, matriz idêntica, reexecução e soft-delete. Ver [research.md](./research.md).

## Technical Context

**Language/Version**: Python 3.x / Django 6.0.7

**Primary Dependencies**: Django 6.0.7 (full stack, sem DRF); stdlib `csv` / `unicodedata` / `decimal`; pytest-django (já no projeto). Sem openpyxl.

**Storage**: SQLite (dev) → PostgreSQL (prod); ORM Django; reutiliza `UniqueConstraint` condicionais `unique_*_ativa` / `unique_cargo_competencia` já existentes (feature 002)

**Testing**: pytest-django em `tests/test_import_catalogo_legado.py` (+ fixtures CSV mínimas); validação manual via quickstart

**Target Platform**: CLI operacional no servidor/app Django (`manage.py`); locale `pt-br`

**Project Type**: Web application (monólito Django) — superfície desta feature é management command, não UI

**Performance Goals**: Catálogo legado típico (~134 cargos, ~43 competências) importado e relatório legível em segundos; SC-007: revisão do relatório < 1 min

**Constraints**: Sem DRF/SPA/UI de upload; sem import de users/avaliações/PDI; sem mudança de fórmula/`nota_final_lider`; `PROTECT` e snapshots de avaliação intactos; soft-delete não reativado; caminhos de arquivo via args do comando

**Scale/Scope**: One-shot operacional; ~130 cargos; dezenas de competências avaliáveis após exclusão de KPI; 4 user stories (P1–P2)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Princípio | Status | Evidência no design |
|---|---|---|
| I. Simplicidade Django-First | ✅ PASS | Management command + serviços na app `competencies`; parse CSV stdlib; sem DRF, sem openpyxl, sem UI. |
| II. Segurança e Escopo no Backend | ✅ PASS | Sem novas views/dados sensíveis de usuário; comando operacional (admin técnico); CRUD existente permanece sob escopo atual. |
| III. Imutabilidade e Integridade | ✅ PASS | Só catálogo/vínculos; não toca avaliações; `peso`/`nivel_esperado` futuros continuam snapshot na criação da avaliação; `PROTECT` inalterado. |
| IV. Modularidade por Domínio | ✅ PASS | Import vive em `competencies` (+ uso de `organization.Cargo`); sem novo app. |
| V. Reprodutibilidade de Cálculos | ✅ PASS | Fórmula e máquina de estados fora de escopo / inalteradas. |
| VI. Performance Assíncrona | ✅ PASS | Carga pequena, síncrona no comando; Celery desnecessário. |

**Post-design re-check (Phase 1)**: Todos os gates permanecem ✅ PASS. Contratos formalizam CLI, mapeamentos e relatório sem camadas extras.

## Project Structure

### Documentation (this feature)

```text
specs/003-import-catalogo-legado/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
│   ├── import-command-contract.md
│   └── legado-domain-mapping-contract.md
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
apps/
├── organization/
│   └── models.py                    # Cargo (reutilizado; sem migration nova esperada)
└── competencies/
    ├── models.py                    # Escala, Competencia, CargoCompetencia (reutilizados)
    ├── management/
    │   └── commands/
    │       └── importar_competencias_cargo.py
    └── services/
        └── catalog_import/
            ├── __init__.py          # API pública do serviço
            ├── parse.py             # leitura CSV + expansão pipe
            ├── normalize.py         # chave canônica de nomes
            ├── mapping.py           # de-para senioridade/tipo/KPI/nivel_esperado
            ├── reconcile.py         # união/divergência das duas vistas
            ├── report.py            # totais + detalhes estruturados
            └── importer.py          # orquestração + atomic persist

lista-cargos.xlsx                    # fonte legado (raiz; CSV)
lista-competencias.xlsx              # fonte legado (raiz; CSV)

tests/
└── test_import_catalogo_legado.py   # pytest: mapeamentos, KPI, matriz, idempotência, soft-delete
```

**Structure Decision**: Monólito Django existente. Feature concentrada em `apps/competencies` (comando + serviço), reutilizando `organization.Cargo`. Sem novos models/migrations se constraints atuais bastarem; fontes permanecem na raiz do repo com caminhos overrideáveis por args.

## Complexity Tracking

> Preenchido apenas onde há desvio justificado ou nota de constituição já conhecida

| Violation / Nota | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Django 6.0.7 vs constituição (Django 5.x) | Já ratificado nos planos 001/002 e em `requirements.txt` | Downgrade sem benefício |
| Extensão `.xlsx` com conteúdo CSV | Fontes reais do legado; parse determinístico sem openpyxl | openpyxl adiciona dependência desnecessária (Princípio I) |
| Soft-delete: não reativar inativos | Assumption da spec + catálogo 002 | Reativar silenciosamente reverteria offboarding/soft-delete |
