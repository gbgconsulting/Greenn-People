# Feature Specification: Visualizações Gráficas nos Dashboards

**Feature Branch**: `005-dashboard-charts`

**Created**: 2026-07-30

**Status**: Draft

**Input**: User description: "Melhorar os dashboards do Greenn People com visualizações gráficas das métricas já existentes (aderência, conclusão de ciclo/avaliações, gaps de competência / status do escopo), sem inventar novas fórmulas de negócio nem abrir SPA. Consome tokens da fundação visual (004); não reabre redesign de marca nem polish amplo do chrome."

## Declaração do Problema (O Porquê)

Os painéis atuais (admin, time/escopo, pessoal) já expõem KPIs numéricos e tabelas úteis (ex.: líderes com menor aderência), mas a leitura do estado do ciclo e do escopo ainda exige esforço cognitivo: média + lista não mostram distribuição, progresso por etapa nem gaps de competência de forma imediata. A fundação visual (004) estabilizou shell, tokens e padrões; esta feature deve torná-los acionáveis com gráficos leves sobre dados já existentes — sem novas fórmulas, sem SPA e sem reabrir redesign de marca.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Marina vê distribuição de aderência e progresso do ciclo (Priority: P1)

Marina (admin DP/RH) abre o painel administrativo e, além da média e da tabela de líderes com menor aderência, vê pelo menos duas visualizações gráficas: (1) distribuição de aderência em faixas alta/média/baixa (ou equivalente já usado pelo produto) e (2) progresso/conclusão de avaliações ou etapas do ciclo (funil ou barras). Empty states são honestos quando não há snapshot ou ciclo com dados. A tabela complementar de menor aderência permanece quando fizer sentido.

**Why this priority**: Visão agregada de RH é o maior ganho perceptível; o MVP declara pelo menos duas visualizações no painel admin.

**Independent Test**: Com admin autenticado, ciclo aberto e snapshots/dados de aderência e avaliações disponíveis, abrir o dashboard admin e verificar as duas visualizações, a preservação da tabela útil e empty states sem inventar números.

**Acceptance Scenarios**:

1. **Given** admin autenticado e dados de aderência disponíveis para o ciclo, **When** abre o dashboard admin, **Then** vê uma visualização da distribuição de aderência por faixas (alta/média/baixa ou equivalente do produto), não apenas a média numérica.
2. **Given** o mesmo contexto com avaliações/etapas do ciclo, **When** consulta o painel, **Then** vê progresso ou conclusão por etapa/avaliações em formato gráfico (funil ou barras), coerente com os totais já expostos pelo sistema.
3. **Given** dados de líderes com menor aderência, **When** o gráfico de aderência é exibido, **Then** a tabela/lista complementar de menor aderência continua disponível e alinhada aos mesmos dados.
4. **Given** ausência de snapshot, ciclo sem avaliações ou conjunto vazio, **When** o painel renderiza, **Then** empty states claros aparecem sem preencher gráficos com dados fictícios.

---

### User Story 2 - Líder/gerente vê status do escopo em gráfico no dashboard de time (Priority: P2)

Um líder ou gerente abre o dashboard de time (e correlatos de escopo hierárquico, se a mesma métrica já for exposta lá) e vê o status agregado do seu escopo em visualização gráfica simples — reutilizando apenas métricas/status já calculados e visíveis para aquele papel. Nenhum indicador novo é inventado; o escopo continua restrito ao que o backend já autoriza.

**Why this priority**: Scan de status do time é o segundo maior valor; depende do padrão visual validado no admin (slice 1).

**Independent Test**: Com líder autenticado e subordinados no escopo com status de ciclo, abrir o dashboard de time e verificar uma visualização agregada alinhada aos dados já mostrados em KPI/lista, sem vazamento fora do escopo.

**Acceptance Scenarios**:

1. **Given** líder/gerente autenticado com pessoas no escopo e ciclo com status, **When** abre o dashboard de time, **Then** vê pelo menos uma visualização gráfica do status agregado do escopo (ex.: distribuição de etapas/status já existentes).
2. **Given** colaborador no escopo de outro líder, **When** o líder atual consulta o painel, **Then** nenhum dado fora do escopo hierárquico autorizado aparece no gráfico ou no texto associado.
3. **Given** escopo vazio ou sem dados de ciclo, **When** o painel é aberto, **Then** empty state honesto é exibido; loading state não é confundido com “zero inventado”.

---

### User Story 3 - Colaborador vê gaps esperado × nota por competência (Priority: P3)

O colaborador abre o painel pessoal e, quando existem notas e nível esperado por competência, vê esses gaps em forma gráfica simples (ex.: barras comparativas). Se a regra atual negar exposição da 9-box, o painel continua sem expor 9-box. Sem dados de competência/nota, empty state claro — sem inventar gaps.

**Why this priority**: Autoatendimento e clareza individual; valor real, mas secundário ao acompanhamento de ciclo por RH e liderança no MVP.

**Independent Test**: Com colaborador autenticado que possui avaliação com competências e notas, abrir o painel pessoal e verificar gráfico de gap; com usuário sem dados ou sem liberação de 9-box, verificar empty/ocultação conforme regra vigente.

**Acceptance Scenarios**:

1. **Given** colaborador com competências avaliadas (nível esperado e nota existentes), **When** abre o painel pessoal, **Then** vê visualização gráfica simples do gap esperado × nota por competência, coerente com os valores já exibidos textual/numericamente.
2. **Given** colaborador sem notas ou sem competências no ciclo, **When** o painel renderiza a área de gaps, **Then** empty state honesto aparece sem barras fictícias.
3. **Given** regra atual que nega 9-box ao colaborador, **When** o painel pessoal é exibido após esta feature, **Then** a 9-box continua não exposta (esta feature não altera essa regra).

---

### Edge Cases

- Papéis cumulativos (colaborador + líder + admin): cada painel mostra apenas visualizações do seu contexto; gráficos não cruzam dados de outro papel além do já permitido.
- Snapshot de aderência ausente ou desatualizado: empty/aviso honesto; não recalcular fórmula nova no request só para “encher” o gráfico.
- Ciclo fechado, sem ciclo aberto ou zero avaliações: empty states; gráficos não inventam progresso.
- Viewport móvel: gráficos legíveis via scroll; não exigem SPA nem layout desktop-only bloqueante.
- Daltonismo / dependência só de cor: faixas e séries têm texto, rótulos ou padrão além da cor (Status Triad / tokens congelados).
- Atualizações parciais HTMX já existentes em listas/partials do dashboard: continuam funcionando; gráfico não quebra regions HTMX adjacentes.
- Muitos pontos (muitos líderes ou competências): visualização permanece usável (agrupamento nas faixas já existentes, scroll ou foco nas séries principais) sem criar métricas novas.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O sistema MUST apresentar no dashboard administrativo pelo menos duas visualizações gráficas no MVP: distribuição de aderência por faixas e progresso/conclusão de avaliações ou etapas do ciclo.
- **FR-002**: Visualizações MUST usar exclusivamente métricas, agregações e regras de negócio já existentes (aderência, status de ciclo/avaliações, gaps nível esperado × nota, status de escopo); MUST NOT introduzir novas fórmulas, faixas ou snapshots de negócio.
- **FR-003**: O dashboard administrativo MUST preservar tabelas/listas úteis que complementam o gráfico (em especial líderes com menor aderência), alinhadas aos mesmos dados da visualização.
- **FR-004**: O dashboard de time (e correlatos de escopo já existentes, se aplicável) MUST exibir visualização gráfica do status agregado do escopo hierárquico do usuário autenticado, sem ampliar o conjunto de pessoas ou métricas além do já autorizado/exposto.
- **FR-005**: O painel pessoal MUST exibir visualização gráfica simples de gap (nível esperado × nota) por competência quando esses dados existirem para o colaborador.
- **FR-006**: Empty states e loading states MUST ser honestos: sem dados inventados, sem confundir carregamento com “zero”, com mensagem compreensível em português.
- **FR-007**: Visualizações MUST ser acessíveis o suficiente: informação não depender só da cor; texto, rótulos ou alternativa equivalente MUST acompanhar o gráfico.
- **FR-008**: Visibilidade e autorização MUST permanecer 100% resolvidas no backend (escopo hierárquico / mixins existentes); a UI MUST NOT ser a fonte de autorização.
- **FR-009**: A feature MUST NOT alterar regras de liberação da 9-box nem introduzir 9-box interativa (drag, drawer, edição in-matrix).
- **FR-010**: A feature MUST consumir os tokens e padrões congelados da fundação visual (Emerald, Status Triad, tipografia e componentes documentados); MUST NOT reabrir redesign de marca, polish amplo de shell/nav/topbar nem o WIP Impeccable — apenas ajustes mínimos de layout se o gráfico exigir.
- **FR-011**: Fluxos de atualização parcial já existentes nas listas/partials dos dashboards MUST continuar corretos após a inclusão das visualizações.
- **FR-012**: Entrega MUST seguir slices incrementais: (1) admin — MVP, (2) time/escopo, (3) pessoal — de modo que o slice 1 seja demonstrável e utilizável sozinho.
- **FR-013**: A equipe MUST documentar brevemente qual biblioteca de gráfico foi adotada e em quais superfícies/templates de dashboard ela é carregada (somente onde necessário).

### Key Entities

- **Distribuição de Aderência**: Contagem ou proporção de líderes/unidades nas faixas já definidas pelo produto (alta/média/baixa ou equivalente), derivada dos dados de aderência já persistidos/expostos.
- **Progresso do Ciclo**: Totais ou proporções de avaliações/etapas já conhecidos pelo sistema (ex.: concluídas vs. pendentes por etapa), sem novo modelo de negócio.
- **Status do Escopo**: Agregação de status operacionais já visíveis no dashboard de time/estrutura para o conjunto `get_visible_users` (ou equivalente) do usuário.
- **Gap de Competência**: Par nível esperado × nota (ou equivalente já exibido) por competência no contexto do colaborador autenticado.
- **Empty/Loading de Visualização**: Estados de UI que comunicam ausência de dado ou carregamento sem alterar a semântica das métricas.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Em revisão guiada com Marina (admin), ela identifica distribuição de aderência e progresso do ciclo em até 10 segundos no dashboard admin — mais rápido que apenas média + tabela.
- **SC-002**: O MVP entrega pelo menos 2 visualizações gráficas distintas e utilizáveis no painel admin (aderência por faixa + conclusão/progresso de ciclo).
- **SC-003**: Em revisão guiada com líder, o status agregado do escopo no dashboard de time é compreendido em até 10 segundos quando o slice de time estiver entregue.
- **SC-004**: 100% dos casos de teste de permissão/escopo existentes para dashboards continuam passando; nenhum dado fora do escopo aparece nos gráficos.
- **SC-005**: Em cenários sem dados (sem snapshot, sem avaliações, sem notas), 100% das áreas gráficas mostram empty state honesto — zero valores inventados verificáveis na revisão.
- **SC-006**: Em viewport móvel típico, as visualizações do MVP são consultáveis por scroll sem perda de informação essencial (rótulos/valores legíveis).
- **SC-007**: Documentação breve da biblioteca de gráfico e das páginas em que é carregada está disponível na entrega do MVP.

## Assumptions

- A fundação visual 004 (tokens/padrões em `docs/design-system.md`, Freeze) está disponível para consumo; esta feature não a reabre.
- Faixas de aderência alta/média/baixa (ou nomenclatura já usada na UI/dados) já existem no produto; o gráfico apenas as visualiza.
- Serviços e views de dashboard já expõem (ou podem reexpor no contexto da página) os agregados necessários sem novos cálculos de negócio — apenas formatação para visualização.
- MVP = slice 1 (admin: duas visualizações + tabela de menor aderência). Slices 2 (time) e 3 (pessoal) são sequenciais e podem ser planejados/entregues após o MVP sem bloquear valor de RH.
- Biblioteca de gráfico leve é aceitável como dependência justificada (nativo insuficiente para charts), carregada somente nas páginas de dashboard que usam gráficos; dados via contexto de página / partials — sem SPA e sem API pública nova.
- Stack de apresentação permanece páginas servidor + atualizações parciais onde já existem; shell/nav/topbar não são alvo de redesign.
- “Correlatos de escopo” (ex.: estrutura) só entram no slice 2 se já expuserem as mesmas métricas de status; não criar painel novo.
- Acessibilidade “suficiente” = contraste/rótulos/texto além da cor; auditoria WCAG completa formal está fora desta feature.

## Out of Scope

- 9-box interativa (drag, drawer, edição in-matrix) — feature seguinte.
- Novas métricas, fórmulas, faixas ou snapshots de negócio; mudança de regras de aderência ou de notas.
- SPA, API pública/DRF, redesign de shell/nav/topbar além do mínimo necessário ao gráfico.
- Reabrir Freeze do design system / WIP Impeccable / redesign de marca.
- Relatórios exportáveis, drill-down profundo multi-página ou novos dashboards fora dos existentes (admin, time/escopo correlato, pessoal).
