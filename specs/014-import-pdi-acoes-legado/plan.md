# Implementation Plan: Importação One-Shot do Legado Sólides — PDIs e Ações

**Branch**: `014-import-pdi-legado` (artefatos em `specs/014-import-pdi-acoes-legado/`) | **Date**: 2026-08-19 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/014-import-pdi-acoes-legado/spec.md`

**Note**: Preenchido pelo workflow `/speckit-plan`. Artefatos de design em [research.md](./research.md), [data-model.md](./data-model.md), [contracts/](./contracts/), [quickstart.md](./quickstart.md). Clarifications 2026-08-19 são **decisões fechadas** — não reabrir, não marcar NEEDS CLARIFICATION. **Não** gera `tasks.md` (isso é `/speckit-tasks`). **Não** reescreve `spec.md`.

## Summary

UM management command Django (`importar_pdi`, app `pdi`) com **UM** path `--pdi`. Sem segundo comando. Sem UI/DRF/Celery/lib nova. **ZERO migration**. Parser OOXML = **openpyxl já justificado na 010**, **SOMENTE** em `apps/accounts/services/legacy_import/parse_xlsx.py` (`parse_pdi_xlsx`). Domínio **NOVO** em `apps/pdi/services/legacy_import/` (`resolve.py` + `importer.py`). CLI fino em `apps/pdi/management/commands/importar_pdi.py`. Estender `dates.py` (se necessário) e `report.py` (seções `pdis_*` / `acoes_*` / `orfaos_usuario` / `conflitos_*`). Nenhum módulo em `pdi/` importa openpyxl.

Reuso READ-ONLY: `canonical_key` / `display_name` (003 `normalize.py`). Persistência via `PDI`/`AcaoPDI.full_clean()` + `save()` — `AcaoPDI.save()` **já** invoca `recalculate_overdue_status`. **MUST NOT** editar `overdue.py`, `progress.py`, `tasks.py`, `views.py`, `urls.py`, `forms.py`, `models.py`. Schema vigente: `PDI.solides_id` (010, `max_length=50`, unique nullable) + `AcaoPDI` (`descricao`, `responsavel`, `prazo`, `status`) + `on_delete=PROTECT` intacto. **ZERO** `solides_id` em `AcaoPDI`. **ZERO** FK Ciclo/Avaliação.

Abordagem: serviço fino em `pdi` + extensão parse/dates/report em `accounts` + testes pytest com `pdi_min.xlsx`. Ver [research.md](./research.md).

## Technical Context

**Language/Version**: Python 3.x / Django 6.0.7 (alinhar `requirements.txt`)

**Primary Dependencies**: Django 6.0.7 (full stack, sem DRF); **openpyxl** (já na 010 — somente parse XLSX OOXML); stdlib `hashlib` / `datetime`; pytest-django; reuso read-only de `canonical_key`/`display_name` (003); hook de atraso **via** `AcaoPDI.save()` (não editar `overdue.py`)

**Storage**: SQLite (dev) → PostgreSQL (prod); ORM `full_clean()`/`save()`; schema **existente** (`PDI.solides_id` 010; `AcaoPDI` sem ID Sólides). **Sem AddField. Sem RunPython de domínio. Sem migration.**

**Testing**: pytest-django em `tests/test_import_pdi_legado.py`; sample `data/legado-solides/samples/pdi_min.xlsx` (**NUNCA** `raw/`). Gate: `git diff` vazio na denylist + pytest `test_stage_machine` / `test_scope` / `test_reject_stage_invariant` **SEM alterar asserts**

**Target Platform**: CLI operacional (`manage.py`); locale `pt-BR`; operador técnico (admin de plataforma), não papel de produto novo; **MUST NOT** superfície HTTP

**Project Type**: Monólito Django — management command; **sem UI**

**Performance Goals**: dump 2026-06-24 ~86 linhas (67 `finalizado` / 19 `em_andamento`); carga **síncrona**; relatório < 3 min (SC-008); dry-run zero write (SC-006); staging `--dry-run` primeiro

**Constraints**: openpyxl **apenas** no parser; **não** alterar/chamar `get_visible_users`, `scope.py`, `ScopedObjectMixin` no comando; **não** editar `overdue.py` / `progress.py` / `tasks.py` / views/urls/forms/models PDI; **não** `mark_overdue_pdi_actions`; **não** `calculate_pdi_progress` / dashboard; PII `raw/` fora do CI; relatório mascarado (máx. 5/seção); FR-018/019/020

**Scale/Scope**: One-shot operacional; 3 user stories (P1 persistência, P1 resolução pessoa, P2 dry-run/CI); fatia PRD 6.5.6 (treinamentos/9-box/012 UI fora). Pré-requisito ambiente: **003 + 010**. 011/013 **não** bloqueiam.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design. Violação não justificada BLOQUEIA.*

| Princípio | Status | Evidência no design |
|---|---|---|
| **I. Simplicidade Django-First** | ✅ PASS | Management command + ORM `full_clean()`/`save()`; openpyxl **só** no parser (já 010, **sem nova lib** — Complexity Tracking). Sem upload, DRF, Celery, SPA. Ver [research.md R1/R2](./research.md). |
| **II. Segurança e Escopo no Backend** | ✅ PASS | Import = CLI privilegiado de plataforma. **MUST NOT** view/url/upload/HTMX/API. **MUST NOT** chamar `get_visible_users` / `user_in_scope` / `ScopedObjectMixin` no comando. Leitura posterior = `LoginRequiredMixin` + `ScopedObjectMixin` + `user_in_scope` + `_get_scoped_pdi` **já vigentes**. Diff `views.py`/`forms.py`/`urls.py`/`scope.py` **vazio**. Inativo **sem** bypass. Relatório mascarado. `raw/` fora do CI. Teste de ouro II: usuário fora da hierarquia → 404; asserts `test_scope` intactos. |
| **III. Imutabilidade e Integridade** | ✅ PASS | `on_delete=PROTECT` intacto; sem CASCADE; **NÃO** apagar PDI/ação para refazer; digest SHA-256 truncado **não** é PII em claro em `solides_id`. |
| **IV. Modularidade por Domínio** | ✅ PASS | Persistência em `pdi/services/legacy_import/`; parse **só** em `accounts/.../parse_xlsx.py`; 003 `normalize.py` **read-only**. Sem segundo parser. Sem openpyxl em `pdi`. |
| **V. Reprodutibilidade de Cálculos** | ✅ PASS | Status da ação = FR-011 **antes** do `save`; hook vigente (`recalculate_overdue_status`) só via `AcaoPDI.save()` e **pode só rebaixar** `atrasada→pendente` se `prazo≥hoje`. **MUST NOT** editar `overdue.py`. **MUST NOT** `mark_overdue_pdi_actions`. **MUST NOT** `calculate_pdi_progress` / dashboard. `stage.py` / `cycle.py` / `approval.py` / `adherence.py` / `evaluation.py` intocáveis. |
| **VI. Performance Assíncrona** | ✅ PASS | Sem task Celery nesta fatia (~86, CLI one-shot). Sem 9-box/aderência/e-mail. Precedente 010–013. |

**Post-design re-check (Phase 1)**: Todos os gates permanecem ✅ PASS. Contratos formalizam CLI (`--pdi` obrigatório), column-mapping (concat `\n\n`, datas, digest), allowlist/denylist (inclui 012 urls/templates + overdue/tasks/views), e migration-safety = **zero** migrations. Clarifications 2026-08-19 não reabertas. Nenhum NEEDS CLARIFICATION residual.

**FAIL do plan se**: view nova sem escopo; “esconder no frontend”; papel fixo no lugar de `line_manager`; `NEEDS CLARIFICATION` residual.

## Project Structure

### Documentation (this feature)

```text
specs/014-import-pdi-acoes-legado/
├── plan.md              # This file
├── research.md          # Phase 0
├── data-model.md        # Phase 1
├── quickstart.md        # Phase 1
├── contracts/
│   ├── import-command-contract.md
│   ├── column-mapping-contract.md
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
│   ├── parse_xlsx.py          # ESTENDER: parse_pdi_xlsx
│   ├── dates.py               # ESTENDER se necessário: Data de Entrega + Criado em (serial Excel + ISO)
│   └── report.py              # ESTENDER: pdis_* / acoes_* / orfaos_usuario / conflitos_*
├── competencies/services/catalog_import/
│   └── normalize.py           # REUSO READ-ONLY: canonical_key, display_name
├── pdi/
│   ├── models.py              # SEM alteração (PROTECT + solides_id vigentes)
│   ├── views.py / urls.py / forms.py   # INTÁVEIS (escopo vigente)
│   ├── services/overdue.py    # CHAMAR via AcaoPDI.save(); MUST NOT edit
│   ├── services/progress.py   # MUST NOT edit / MUST NOT call no import
│   ├── tasks.py               # MUST NOT edit / MUST NOT mark_overdue_pdi_actions
│   ├── services/legacy_import/
│   │   ├── __init__.py
│   │   ├── resolve.py         # pessoa, digest, concatenação, de-para status
│   │   └── importer.py        # orquestração atomic: 1 PDI + 1 ação por linha
│   └── management/
│       ├── __init__.py        # NOVO se faltar
│       └── commands/
│           ├── __init__.py    # NOVO se faltar
│           └── importar_pdi.py
└── dashboard/ / talent/ / cycles urls 012   # INTÁVEIS nesta fatia

data/legado-solides/
├── README.md                  # Decisão #22; passo 7 / 6.5.6
├── raw/                       # PII — NÃO usar em CI
└── samples/                   # + pdi_min.xlsx (+ README samples)

tests/
└── test_import_pdi_legado.py
```

**Structure Decision**: Infra de parse XLSX permanece em `accounts/services/legacy_import/` (openpyxl + dates + report das 010/011/013 — evita parsers divergentes). Domínio de PDI/ação orquestra em `pdi/services/legacy_import/`. Um comando, um path. Sem tocar dashboard, templates/urls da 012, talent, overdue/progress/tasks/views.

## Complexity Tracking

| Violation / Nota | Why Needed | Simpler Alternative Rejected Because |
|---|---|---|
| Django 6.0.7 vs constituição (Django 5.x) | Já ratificado nos planos 001–013 e em `requirements.txt` | Downgrade sem benefício |
| **openpyxl** (Princípio I) | Já justificado e presente na 010; backups Sólides são OOXML real | Nova lib / CSV — rejeitado; esta fatia **não** adiciona dependência nova (`requirements.txt` fora da allowlist) |
| Pacote domínio em `pdi` + parse em `accounts` | Princípio IV + reuso sem duplicar openpyxl | Duplicar `parse_xlsx` em `pdi` — rejeitado (dois parsers); tudo em `accounts` — rejeitado (PDI não é domínio accounts) |
| Carga síncrona ~86 linhas (Princípio VI) | CLI one-shot, não request HTTP; precedente 010–013 | Celery — rejeitado (FR-001; volume pequeno; sem fila nesta fatia) |

## Teste de ouro do plan (FR-021 + Princípio II)

Executar `importar_pdi` **não** avança etapa, **não** abre/fecha ciclo, **não** aprova meta, **não** muda quem vê quem, **não** edita fórmula, **não** toca notas/feedback, **não** classifica 9-box, **não** dispara aderência, **não** toca 012, **não** edita `overdue.py`/`tasks.py`/`views.py`. Diff dessas regras = **vazio**.

Após a carga, usuário autenticado **fora** da hierarquia do dono recebe **404** ao abrir detalhe/editar/apagar PDI ou ação; colaborador inativo **não** aparece na listagem de quem já não o via.
