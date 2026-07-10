# Implementation Plan: Gestão de Desempenho, PDI e Talentos

**Branch**: `001-gestao-desempenho-talentos` | **Date**: 2026-07-09 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-gestao-desempenho-talentos/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

O Greenn People é uma aplicação web interna Django 6.0.7 que centraliza o ciclo de desempenho (metas → resultados → avaliação → feedback), PDI, classificação 9-box e dashboards de aderência. A abordagem técnica segue um monólito Django enxuto: DTL + HTMX + Tailwind CLI para UI, escopo de dados resolvido no backend via hierarquia `line_manager`, snapshots imutáveis para reprodutibilidade de notas, e processamento assíncrono (Celery + Redis) para aderência, agregações e e-mails.

## Technical Context

**Language/Version**: Python 3.x / Django 6.0.7

**Primary Dependencies**: Django 6.0.7 (full stack, sem DRF na v1); HTMX; Tailwind CSS CLI standalone; Celery + Redis (broker e result backend); Celery Beat

**Storage**: SQLite (desenvolvimento) → PostgreSQL (produção planejada); apenas ORM padrão Django, sem recursos exclusivos de banco

**Testing**: Django TestCase / pytest-django — planejado para sprints finais

**Target Platform**: Aplicação web interna (sem landing page pública), acesso via navegador; locale `pt-br`, timezone `America/Sao_Paulo`

**Project Type**: Web application (monólito Django full stack)

**Performance Goals**: Páginas comuns e dashboards < 2s; cálculos pesados (aderência, agregações, e-mails) fora do ciclo de request via Celery

**Constraints**: Sem SPA; toda lógica de permissão no servidor; `paginate_by = 20` em ListViews; sessão 2 semanas (`SESSION_COOKIE_AGE` padrão); validadores de senha nativos Django (`min_length=8`); código em inglês, UI em português brasileiro; CBVs sempre que possível; ruff/flake8 PEP 8, aspas simples

**Scale/Scope**: Time pequeno/único desenvolvedor; evolução incremental em sprints; ~12 apps Django de domínio; 5 user stories priorizadas (P1–P3); Docker e testes automatizados nas sprints finais

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Princípio | Status | Evidência no design |
|---|---|---|
| I. Simplicidade Django-First | ✅ PASS (com nota) | Monólito DTL+HTMX+Tailwind CLI; sem DRF, sem SPA. **Nota**: constituição cita Django 5.x; projeto ratifica Django 6.0.7 (ver Complexity Tracking). |
| II. Segurança e Escopo no Backend | ✅ PASS | `get_visible_users()` + `ScopedObjectMixin` em todas as views sensíveis; escopo por `line_manager`, não papel fixo. |
| III. Imutabilidade e Integridade | ✅ PASS | `on_delete=PROTECT` em FKs históricas; `AuditLog` append-only; snapshots `peso_utilizado`/`nivel_esperado_utilizado` write-once. |
| IV. Modularidade por Domínio | ✅ PASS | 12 apps conforme constituição; dependências unidirecionais documentadas em `data-model.md`. |
| V. Reprodutibilidade de Cálculos | ✅ PASS | Normalização por escala; máquina de estados agregada por `Avaliacao.etapa`; reprovação pontual de meta não retrocede etapa global. |
| VI. Performance Assíncrona | ✅ PASS | `AderenciaSnapshot` via Celery; e-mails e verificação de prazos via Celery Beat; dashboards leem snapshots. |

**Post-design re-check (Phase 1)**: Todos os gates permanecem ✅ PASS. Contratos em `contracts/` formalizam escopo, máquina de estados e cálculos sem introduzir camadas extras.

## Project Structure

### Documentation (this feature)

```text
specs/001-gestao-desempenho-talentos/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
config/                         # projeto Django (settings, urls, celery.py)
├── settings/
│   ├── base.py
│   ├── dev.py
│   └── prod.py
├── celery.py
└── urls.py

apps/
├── core/                       # TimeStampedModel, mixins, templates base, componentes UI
├── accounts/                   # CustomUser, login por e-mail, cadastro, visões cumulativas
├── organization/               # Área, Cargo, hierarquia colaborador → line_manager
├── competencies/               # Competência, Escala, CargoCompetencia
├── goals/                      # ObjetivoEstrategico, Meta
├── cycles/                     # Ciclo, máquina de estados das etapas
├── reviews/                    # Avaliacao, AvaliacaoCompetencia, autoavaliação, Feedback
├── pdi/                        # PDI, AcaoPDI
├── talent/                     # ClassificacaoTalento (9-box) e visibilidade
├── dashboard/                  # Views agregadas, AderenciaSnapshot
├── notifications/              # Tasks Celery de e-mail, Celery Beat, NotificacaoLog
└── audit/                      # AuditLog (append-only)

templates/
├── base.html
├── components/
├── 404.html / 403.html
└── <app>/

static/
└── css/                        # CSS gerado pelo Tailwind CLI

tests/                          # sprints finais (pytest-django)
```

**Structure Decision**: Monólito Django com apps de domínio em `apps/`, settings split em `config/settings/`, templates globais em `templates/` na raiz. O projeto atual (`core/` na raiz) será migrado para `config/` conforme Sprint 0 do PRD. Dependências entre apps: `core` → base; `accounts` + `organization` → fundação; `competencies`/`goals`/`cycles` → alimentam `reviews`; `talent`/`dashboard` consomem `reviews`/`cycles`; `notifications`/`audit` transversais via signals.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Django 6.0.7 vs constituição (Django 5.x) | Projeto já inicializado com Django 6.0.7 (`requirements.txt`, `manage.py`); PRD v1.4 ratifica 6.0.7 | Downgrade para 5.x adiciona risco sem benefício; Django 6 mantém compatibilidade ORM e CBVs usados no design |
| Resolução de subárvore para gerente | Escopo de gerente exige todos os descendentes via `line_manager` | Filtro só por `line_manager` direto não atende RF-06/FR-006; traversal Python puro gera N+1 (documentado em `research.md`) |
| `django-environ` (Sprint 0) | Variáveis sensíveis em `.env` sem hardcode | `os.environ` manual escala mal com `base`/`dev`/`prod` split |
