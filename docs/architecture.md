# Arquitetura

O sistema é organizado em **apps Django isoladas por domínio de negócio**, cada uma responsável por uma fatia clara do produto. Essa separação permite evoluir cada módulo de forma independente, mantendo o código simples e coeso.

## Apps Django

| App | Responsabilidade |
|---|---|
| `core` | Recursos compartilhados: modelo base com `created_at`/`updated_at`, mixins, templates base, componentes de UI reutilizáveis. |
| `accounts` | Usuário customizado, login por e-mail, cadastro, visões cumulativas (colaborador/líder/gerente/admin). |
| `organization` | Áreas, cargos, hierarquia colaborador → line manager. |
| `competencies` | Competências, escalas, perfil esperado por cargo. |
| `goals` | Objetivos estratégicos e metas do colaborador. |
| `cycles` | Ciclos de avaliação e máquina de estados das etapas. |
| `reviews` | Avaliações, autoavaliação, feedbacks. |
| `pdi` | Planos de desenvolvimento individual e ações. |
| `talent` | Classificação 9-box e controle de visibilidade. |
| `dashboard` | Views agregadas por visão do usuário (colaborador/líder/gerente/admin), cálculo de aderência de liderança. |
| `notifications` | Tarefas Celery de e-mail e agendamentos (Celery Beat). |
| `audit` | Registro e consulta de logs de auditoria. |

## Resolução de escopo

Um serviço simples por app (ex.: função `get_visible_users(request.user)`) resolve o queryset permitido conforme a posição do usuário na hierarquia (`line_manager`), e não um campo fixo de papel:

- **Colaborador** → apenas o próprio registro.
- **Líder** → próprio + membros diretos do seu time (via `line_manager`).
- **Gerente** → próprio + toda a cadeia de liderados dos seus líderes.
- **Admin** → sem filtro.

Essa resolução acontece sempre na view (nunca só no template), evitando vazamento de dados.

### Regra de ouro

O mesmo filtro de escopo é aplicado em dois pontos, não só um:

1. **Listagens** (`ListView.get_queryset()`): o usuário só vê, na lista, o que está no seu escopo.
2. **Objeto individual** (`get_object()` de `DetailView`/`UpdateView`/`DeleteView`): antes de exibir ou permitir editar um registro específico, a view confirma que aquele registro pertence ao escopo do usuário logado — mesmo que o ID venha direto na URL.

Na prática, isso é implementado como um mixin único (`ScopedObjectMixin`), reaproveitado por todas as views sensíveis do sistema (avaliações, PDI, feedbacks, classificação 9-box).

### Validação de hierarquia

- `Area.parent` e `User.line_manager` validam ausência de ciclo no `clean()`/`save()`.
- A resolução de escopo de gerente (subárvore completa) deve usar query otimizada (CTE recursiva ou materialização em cache) — traversal recursivo puro em Python gera N+1 e risco de stack overflow em estruturas profundas.

## Política de `on_delete` em FKs organizacionais

| FK | Comportamento | Motivo |
|---|---|---|
| `User.line_manager` | `SET_NULL` | Colaborador permanece ativo se gestor for desativado |
| `User.area`, `User.cargo` | `PROTECT` | Impede exclusão de área/cargo com usuários vinculados |
| `Area.parent` | `PROTECT` | Impede exclusão física de área com subáreas ativas vinculadas — remoção lógica via `is_active` quando necessário |
| `CargoCompetencia.cargo/competencia` | `PROTECT` | Impede apagar cargo/competência com perfil ou histórico |
| `Avaliacao`, `Meta`, `PDI`, `Feedback` | `PROTECT` em FKs de usuário/ciclo | Preserva histórico — nunca CASCADE em dados de ciclo |
