# Research: Gestão de Desempenho, PDI e Talentos

**Branch**: `001-gestao-desempenho-talentos` | **Date**: 2026-07-09

## R1 — Versão do Django (6.0.7 vs constituição 5.x)

- **Decision**: Adotar Django 6.0.7 como versão canônica do projeto.
- **Rationale**: O repositório já foi inicializado com Django 6.0.7; o PRD v1.4 alinha com essa versão. A API de CBVs, ORM, auth e signals permanece compatível com o design. A constituição deve ser emendada (PATCH) de "Django 5.x" para "Django 6.x" em follow-up.
- **Alternatives considered**:
  - Downgrade para Django 5.x — rejeitado por retrabalho sem ganho funcional.
  - Adicionar DRF — rejeitado por violar princípio I (sem API REST na v1).

## R2 — Resolução de escopo hierárquico (`get_visible_users`)

- **Decision**: Implementar `accounts.services.scope.get_visible_users(user)` retornando queryset de `User` filtrado por visão cumulativa; para gerente, usar query iterativa em camadas (BFS via ORM) com cache de curta duração opcional (`cache` framework Django, TTL 5 min).
- **Rationale**: CTE recursiva (`WITH RECURSIVE`) não é portável entre SQLite e PostgreSQL sem raw SQL duplicado. BFS em 2–4 queries (uma por nível hierárquico) atende profundidade esperada (colaborador → líder → gerente) com paridade SQLite/PostgreSQL. Índice em `User.line_manager_id` garante performance.
- **Alternatives considered**:
  - CTE recursiva raw SQL — rejeitado por quebrar paridade SQLite/PostgreSQL.
  - Traversal recursivo em Python — rejeitado por N+1 e risco de stack overflow.
  - Biblioteca `django-mptt`/`treebeard` — rejeitado por violar simplicidade (auto-relacionamento simples suficiente).

## R3 — Padrão HTMX com Class-Based Views

- **Decision**: Usar HTMX para submissão de formulários (`hx-post` + `hx-target`), atualização parcial de listas (`hx-get` em fragmentos), e modais inline. Views retornam partial templates (`*_partial.html`) quando `request.htmx` é True (via middleware `django-htmx` **não** usado — detectar header `HX-Request` manualmente ou helper em `core` para evitar dependência extra).
- **Rationale**: Detecção manual do header `HX-Request` é trivial e evita nova dependência. CBVs com `TemplateResponse` e template condicional mantêm padrão Django-first.
- **Alternatives considered**:
  - `django-htmx` package — rejeitado na v1 (dependência externa desnecessária).
  - SPA com Alpine.js — rejeitado por violar restrição sem SPA.

## R4 — Celery + Redis integração

- **Decision**: Configurar Celery app em `config/celery.py`; broker e result backend Redis; tasks em `notifications/tasks.py` e `dashboard/tasks.py`; Celery Beat schedule diário para prazos (RF-32, RF-32.1).
- **Rationale**: Padrão documentado Django+Celery; desacopla e-mails e aderência do request cycle (Princípio VI). `AderenciaSnapshot` persiste resultado para leitura síncrona < 2s.
- **Alternatives considered**:
  - `django-q` / `huey` — rejeitado por menor adoção e documentação no ecossistema Django corporativo.
  - Cálculo síncrono com cache — rejeitado por violar Princípio VI em dashboards agregados.

## R5 — Tailwind CSS build (sem Node.js)

- **Decision**: Tailwind CLI standalone (binário) com `input.css` em `static/src/` e output em `static/css/tailwind.css`; comando watch em dev documentado em `quickstart.md`.
- **Rationale**: Alinha com stack obrigatória; sem dependência Node.js reduz setup para desenvolvedor único.
- **Alternatives considered**:
  - CDN Tailwind — rejeitado por não permitir purge/customização do design system.
  - npm + PostCSS — rejeitado por exigir Node.js.

## R6 — Snapshots e reprodutibilidade de notas

- **Decision**: Ao transicionar `Avaliacao` para etapa `avaliação`, serviço `reviews.services.evaluation.create_competency_lines(avaliacao)` copia `peso` e `nivel_esperado` de `CargoCompetencia` para `AvaliacaoCompetencia.peso_utilizado` e `nivel_esperado_utilizado` (write-once, validado no `save()`). `calcular_nota_final_lider()` usa apenas campos snapshot e escala vigente da competência.
- **Rationale**: Atende FR-010, FR-025, SC-004 e Princípio V. Fórmula: `nota_normalizada = (nota_lider - min) / (max - min)`; `nota_final = Σ(normalizada × peso_utilizado) / Σ(peso_utilizado)`.
- **Alternatives considered**:
  - Recalcular com pesos atuais — rejeitado por violar reprodutibilidade.
  - Versionamento completo de cargo — rejeitado por over-engineering.

## R7 — Máquina de estados do ciclo (`Avaliacao.etapa`)

- **Decision**: Estado agregado por colaborador/ciclo com transições explícitas em `cycles.services.stage.advance_stage(avaliacao)`. Reprovação de meta/resultado altera apenas `Meta.status`/`Meta.status_resultado`, nunca retrocede `etapa`. Avanço exige 100% aprovação + ao menos 1 meta.
- **Rationale**: Atende RF-17.1/17.2, edge cases da spec e Princípio V.
- **Alternatives considered**:
  - Estado global por ciclo — rejeitado (spec exige progresso independente por colaborador).
  - Retroceder etapa em reprovação — rejeitado por spec (FR-026).

## R8 — Auditoria append-only

- **Decision**: Model `AuditLog` sem `updated_at`; signals em `audit/signals.py` conectados via `audit/apps.py`; admin read-only; tentativas IDOR registradas apenas quando registro existe mas está fora do escopo (`ScopedObjectMixin`).
- **Rationale**: Atende FR-023, RF-33, RF-35, RF-36.
- **Alternatives considered**:
  - `django-simple-history` — rejeitado por dependência externa e modelo append-only customizado é suficiente.
  - Log apenas em views — rejeitado por cobertura incompleta (signals capturam alterações admin/shell).

## R9 — Autenticação e confirmação de e-mail

- **Decision**: `AbstractUser` customizado com `USERNAME_FIELD = 'email'`; confirmação via `PasswordResetTokenGenerator` especializado; domínio `@greenn.com.br` validado no `RegisterForm`; `email_confirmado_em` separado de `is_active`.
- **Rationale**: RF-02/RF-02.1 do PRD; sem django-allauth.
- **Alternatives considered**:
  - django-allauth — rejeitado por stack obrigatória.
  - Aprovação manual admin — rejeitado por RF-02.

## R10 — Estratégia de testes (sprints finais)

- **Decision**: pytest-django com fixtures por app; testes de escopo (US-09) como prioridade; factory pattern simples sem factory_boy na v1 (criar helpers em `tests/factories.py`).
- **Rationale**: PRD prevê testes nas sprints finais; foco em IDOR e máquina de estados.
- **Alternatives considered**:
  - TDD desde Sprint 0 — rejeitado por PRD (testes nas sprints finais).
  - Apenas Django TestCase — pytest-django oferece melhor DX com mesmo esforço.
