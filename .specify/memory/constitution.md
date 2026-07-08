<!--
SYNC IMPACT REPORT
==================
Version change: TEMPLATE (unversioned) → 1.0.0
Rationale: Ratificação inicial da constituição (MAJOR bump de template não preenchido
           para versão 1.0.0 com conjunto completo de princípios governança).

Modified principles: N/A (ratificação inicial)
Added principles:
  - I. Simplicidade Django-First
  - II. Segurança e Escopo Aplicados no Backend
  - III. Imutabilidade e Integridade do Histórico
  - IV. Modularidade por Domínio
  - V. Reprodutibilidade de Cálculos
  - VI. Performance por Processamento Assíncrono
Added sections:
  - Restrições Tecnológicas (Stack Obrigatória)
  - Arquitetura, Estrutura de Apps e Fluxo de Desenvolvimento
Removed sections: N/A

Templates status:
  - .specify/templates/plan-template.md ...... ✅ compatível (Constitution Check genérico)
  - .specify/templates/spec-template.md ...... ✅ compatível (sem acoplamento a princípios)
  - .specify/templates/tasks-template.md ..... ✅ compatível (categorização de tasks compatível)
  - .specify/templates/checklist-template.md . ✅ compatível
  - .specify/templates/constitution-template.md ✅ fonte do template (inalterado)

Follow-up TODOs: nenhum. RATIFICATION_DATE assumida como a data desta ratificação inicial.
-->

# Greenn People Constitution

## Core Principles

### I. Simplicidade Django-First

Recursos nativos do Django DEVEM ser preferidos antes de qualquer biblioteca externa. A
arquitetura é um monólito enxuto: Django 5.x full stack, sem Django REST Framework na v1.
A camada de apresentação DEVE usar Django Template Language (DTL) + HTMX + Tailwind CSS
(CLI standalone). Adicionar uma dependência externa exige justificativa explícita de que o
recurso nativo é insuficiente ou introduz complexidade maior que a biblioteca.

**Rationale**: Reduz superfície de manutenção, acelera onboarding e evita acoplamento a
frameworks que dificultam a evolução modular de um time pequeno.

### II. Segurança e Escopo Aplicados no Backend

A segurança de dados DEVE ser garantida no backend, NUNCA apenas por ocultação no frontend.
Regras não-negociáveis:

- A visibilidade DEVE ser resolvida por um serviço de escopo (ex.: `get_visible_users`)
  baseado na posição hierárquica (`line_manager`), NÃO em papéis fixos.
- `ScopedObjectMixin` (ou equivalente) DEVE ser aplicado em toda `DetailView`, `UpdateView`
  e `DeleteView`, validando no `get_object()` se o registro pertence ao escopo do usuário
  autenticado.
- Toda nova view que exponha dados sensíveis DEVE declarar explicitamente seu escopo.

**Rationale**: Autorização baseada em hierarquia dinâmica evita vazamento de dados entre
áreas e mantém a segurança independente da camada de UI.

### III. Imutabilidade e Integridade do Histórico

Dados de ciclo e histórico são imutáveis e protegidos:

- `on_delete=PROTECT` DEVE ser usado na maioria das FKs de dados sensíveis/históricos.
  Exclusão em cascata NUNCA é permitida em dados de ciclo/histórico.
- Auditoria DEVE ser append-only, com registro granular por campo (campo, valor antigo,
  valor novo).
- Campos como `peso` e `nivel_esperado` nas avaliações DEVEM ser snapshots write-once,
  copiados da definição do cargo no momento da criação da avaliação.

**Rationale**: Garante reprodutibilidade histórica e conformidade de auditoria mesmo quando
definições de cargo, escalas ou pesos mudam no futuro.

### IV. Modularidade por Domínio

O código DEVE ser organizado em apps Django isoladas, cada uma responsável por um único
domínio de negócio: `core`, `accounts`, `organization`, `competencies`, `goals`, `cycles`,
`reviews`, `pdi`, `talent`, `dashboard`, `notifications`, `audit`. Regras compartilhadas
(model base `TimeStampedModel`, mixins, componentes de UI) DEVEM residir em `core`.
Dependências entre apps DEVEM fluir do específico para o compartilhado, evitando ciclos.

**Rationale**: Isolamento de domínio facilita evolução, testes e substituição de partes sem
efeitos colaterais amplos.

### V. Reprodutibilidade de Cálculos

Cálculos derivados DEVEM ser reprodutíveis e independentes de mudanças posteriores em
escalas:

- `nota_final_lider` DEVE ser calculada pela normalização das notas por competência
  `((nota - min) / (max - min))`.
- A etapa da avaliação é um estado agregado. A reprovação de itens individuais (meta/
  resultado) reabre pontualmente o item, mas NÃO retrocede a etapa global. O avanço de etapa
  EXIGE 100% de aprovação dos itens.

**Rationale**: Normalização e máquina de estados bem definida garantem resultados
consistentes e auditáveis ao longo do tempo.

### VI. Performance por Processamento Assíncrono

Cálculos pesados (aderência de liderança, dashboards) DEVEM ser processados via Celery e
persistidos em snapshots, garantindo tempo de resposta baixo nas requisições síncronas.
Tarefas agendadas (e-mails, verificação de prazos) DEVEM usar Celery Beat. Requisições HTTP
NÃO DEVEM executar cálculos agregados pesados de forma síncrona.

**Rationale**: Desacoplar processamento pesado da requisição preserva a experiência do
usuário e a escalabilidade sob carga.

## Restrições Tecnológicas (Stack Obrigatória)

A stack a seguir é obrigatória e qualquer desvio exige justificativa registrada na seção
Complexity Tracking do plano:

- **Backend**: Django 5.x (full stack, sem DRF na v1).
- **Frontend**: Django Template Language (DTL) + HTMX + Tailwind CSS (CLI standalone).
- **Banco de Dados**: SQLite em desenvolvimento; PostgreSQL em produção.
- **Assíncrono/Fila**: Redis + Celery + Celery Beat.
- **Autenticação**: Sistema nativo do Django com `AbstractUser` customizado
  (`USERNAME_FIELD = 'email'`).

O código DEVE funcionar de forma equivalente em SQLite (dev) e PostgreSQL (prod); recursos
específicos de banco que quebrem essa paridade NÃO DEVEM ser usados sem justificativa.

## Arquitetura, Estrutura de Apps e Fluxo de Desenvolvimento

- A estrutura de apps de domínio (Princípio IV) é a organização canônica do projeto e DEVE
  ser respeitada em todo novo trabalho.
- Toda feature que exponha ou modifique dados DEVE mapear explicitamente: (a) escopo de
  visibilidade (Princípio II), (b) política de `on_delete` das FKs (Princípio III),
  (c) necessidade de snapshot/imutabilidade (Princípio III), e (d) se há cálculo pesado que
  exija Celery (Princípio VI).
- Alterações em dados de avaliação DEVEM preservar a semântica de máquina de estados
  (Princípio V).
- Mudanças que introduzam bibliotecas externas, quebrem a stack obrigatória ou violem um
  princípio DEVEM ser documentadas e justificadas antes da implementação.

## Governance

Esta constituição supersede quaisquer outras práticas de desenvolvimento em conflito. Todo
plano (`plan.md`), especificação (`spec.md`) e conjunto de tarefas (`tasks.md`) DEVE ser
verificado quanto à conformidade com estes princípios; violações não justificadas bloqueiam
o avanço (gate).

- **Emendas**: DEVEM ser propostas por escrito, com descrição do impacto e plano de
  migração quando aplicável, e registradas via atualização deste arquivo.
- **Versionamento (SemVer)**:
  - MAJOR: remoção/redefinição incompatível de princípios ou governança.
  - MINOR: adição de princípio/seção ou expansão material de orientação.
  - PATCH: esclarecimentos, correções e refinamentos não-semânticos.
- **Revisão de conformidade**: PRs e revisões DEVEM verificar aderência aos princípios.
  Complexidade adicional DEVE ser justificada na seção Complexity Tracking do plano.

**Version**: 1.0.0 | **Ratified**: 2026-07-08 | **Last Amended**: 2026-07-08
