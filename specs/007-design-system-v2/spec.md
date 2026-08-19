# Feature Specification: Design System v2 — Polish Visual

**Feature Branch**: `007-design-system-v2`

**Created**: 2026-08-06

**Status**: Draft

**Input**: User description: "Polish visual / Design System v2 — Greenn People: elevar a qualidade visual do app autenticado (shell + superfícies existentes), atualizando o Freeze para v2 (tipografia, botões, cards/KPI, charts, matriz 9-box), sem novas capacidades de negócio; login e base_auth explicitamente fora de escopo."

## Declaração do Problema (O Porquê)

A fundação visual 004 congelou tokens e padrões a partir do UI incumbente (Inter, cards/KPI básicos, Status Triad) — suficiente para desbloquear features, mas não um acabamento percebido como premium. As entregas 005 (charts) e 006 (9-box interativa) trouxeram capacidades reais, porém as superfícies autenticadas ainda parecem cruas: tipografia plana, botões/cards sem hierarquia refinada, gráficos densos sem acabamento e matriz funcionalmente rica mas tipograficamente inconsistente com o nível da tela de login. Sem um Design System v2 documentado e aplicado nas mesmas superfícies piloto, cada tela continua improvisando. Esta feature é decisão explícita de produto para reabrir e atualizar o Freeze (doc + tokens/CSS + componentes na mesma entrega), exclusivamente como polish de apresentação.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Tipografia e tokens v2 no app autenticado (Priority: P1)

Marina (admin DP/RH), um líder e um colaborador, em qualquer sessão autenticada (exceto login), passam a ver tipografia com hierarquia clara: fontes expressivas para display e UI legível para corpo/controles. Títulos de página, KPIs e rótulos secundários tornam-se escaneáveis; o carregamento tipográfico respeita a política do projeto (local/self-hosted). A tela de login e demais superfícies de `base_auth` permanecem visualmente intactas.

**Why this priority**: Tipografia e tokens são a base perceptível do Design System v2; sem eles, refinamentos de botões, charts e matriz não consolidam uma linguagem única.

**Independent Test**: Comparar before/after em pelo menos três superfícies autenticadas piloto (ex.: dashboard admin, dashboard time, lista in-app); confirmar hierarquia display vs UI e que login/`base_auth` não mudaram.

**Acceptance Scenarios**:

1. **Given** usuário autenticado em qualquer papel, **When** abre uma superfície piloto do app autenticado, **Then** títulos e KPIs exibem hierarquia tipográfica perceptivelmente mais clara que o baseline Inter plano da 004.
2. **Given** a tipografia v2 aplicada no shell autenticado, **When** um revisor abre a tela de login, **Then** tipografia, layout e painel narrativo permanecem pixel/comportamento inalterados em relação ao before.
3. **Given** tokens tipográficos documentados no Freeze v2, **When** um designer/dev consulta `docs/design-system.md`, **Then** encontra escala tipográfica (display vs UI), pesos e usos descritos de forma acionável.

---

### User Story 2 - Botões, cards, KPI, table-frame e empty states refinados (Priority: P2)

Nas superfícies piloto (dashboards, listas, formulários in-app), Marina e demais papéis encontram botões (primary/secondary/outlined/loading) com ritmo, pesos e estados hover/focus refinados, e blocos de KPI/lista/empty com densidade e hierarquia alinhadas ao DS v2 — preferindo composição limpa a “cardificar” tudo. A semântica e as variantes existentes dos componentes compartilhados permanecem; não há novas ações de negócio.

**Why this priority**: Depois da tipografia, controles e contêineres de conteúdo são o maior diferencial de acabamento no uso diário, sem tocar login.

**Independent Test**: Percorrer dashboards + uma lista + um formulário/detalhe piloto; validar variantes de botão, densidades de KPI/table-frame/empty e consistência visual entre telas; garantir que CTAs e submits existentes seguem funcionando.

**Acceptance Scenarios**:

1. **Given** componentes de botão nas superfícies piloto, **When** o usuário interage com primary/secondary/outlined e estado loading, **Then** vê ritmo, pesos e feedback hover/focus refinados, mantendo as mesmas variantes semânticas.
2. **Given** dashboard ou lista piloto, **When** o revisor avalia KPI, table-frame e empty states, **Then** densidade e bordas/sombra (se houver) reforçam hierarquia sem transformar toda a tela em cards desnecessários.
3. **Given** empty state em lista ou dashboard sem dados, **When** a superfície é exibida, **Then** permanece honesta e acionável (padrão 004/005), apenas com acabamento visual alinhado ao v2.

---

### User Story 3 - Charts 005 com acabamento visual coerente (Priority: P3)

Marina e líderes abrem dashboards com gráficos existentes (status triad, empty honestos) e percebem acabamento: tipografia de eixos/tooltips/legendas, espaçamento do bloco de chart, radius/thickness, grid lines sutis e altura/ritmo alinhados ao DS v2. Nenhuma métrica, biblioteca ou endpoint novo; Status Triad e labels textuais (a11y) permanecem.

**Why this priority**: Charts já entregam informação; o polish fecha o gap entre dados úteis e percepção premium, sem ampliar produto.

**Independent Test**: Abrir dashboard admin (e, se aplicável, time) com e sem dados; validar polish visual do bloco de chart e que payloads/comportamento de negócio da 005 não mudaram; empty states continuam honestos.

**Acceptance Scenarios**:

1. **Given** dashboard com charts populados, **When** o revisor compara before/after, **Then** eixos, legendas, tooltips, espaçamento e grid lines estão refinados e coerentes com o DS v2.
2. **Given** dashboard sem dados para um chart, **When** empty state é exibido, **Then** permanece honesto (sem fake data), apenas com acabamento visual v2.
3. **Given** usuário que depende de a11y, **When** interpreta status dos charts, **Then** continua havendo rótulos textuais além da cor (Status Triad preservada).

---

### User Story 4 - Matriz 9-box interativa alinhada ao DS v2 (Priority: P4)

Líderes e admin com acesso à matriz interativa veem grade, person cards, drawer de domínio e feedback de drag/drop/empty visualmente alinhados ao DS v2. Interações da 006 (AuthZ, fórmulas, drag somente potencial, contratos HTMX do drawer/move/toggle) permanecem intactas; o polish é apenas apresentação (classes/markup visual / ARIA de suporte visual).

**Why this priority**: A matriz é a superfície mais nova e ainda “crua”; alinhá-la ao v2 fecha o before/after sem reabrir escopo de produto da 006.

**Independent Test**: Executar happy paths do quickstart 006 (abrir matriz, drawer, move de potencial autorizado, empty); confirmar aparência refinada e zero regressão funcional nos contratos de negócio.

**Acceptance Scenarios**:

1. **Given** usuário autorizado na matriz, **When** visualiza a grade e person cards, **Then** tipografia, densidade e estados vazios estão coerentes com o DS v2.
2. **Given** sessão com permissão de mover potencial, **When** executa drag/drop permitido, **Then** feedback visual de drag/drop está polido e o movimento continua obedecendo à política potencial-only da 006.
3. **Given** abertura do drawer de pessoa, **When** conteúdo e shell do drawer são apresentados, **Then** o acabamento visual está alinhado ao v2 sem alteração de payloads HTMX, AuthZ ou fórmulas.

---

### User Story 5 - Freeze v2 documentado + aceite before/after + checklist OUT (Priority: P5)

O time de produto/design valida que `docs/design-system.md` declara Freeze v2 (tipografia, botões, cards/KPI, charts polish, ninebox polish), que há evidência before/after perceptível em 5–8 superfícies piloto (exceto login), e que o checklist OUT confirma: login/`base_auth` intocados; zero regressão funcional nos happy paths 005 e 006; nenhuma mudança de regra de negócio.

**Why this priority**: Aceite formal da decisão de reabrir o Freeze; fecha a feature como Dualidade doc ↔ CSS/componentes.

**Independent Test**: Revisão guiada (scan ≤ N segundos por tela piloto) + checklist OUT preenchido + diff/confirmação de que arquivos de login não foram alterados.

**Acceptance Scenarios**:

1. **Given** Freeze v2 publicado, **When** um revisor lê o design system, **Then** tipografia, botões, cards, charts e ninebox polish estão documentados com status Freeze v2.
2. **Given** 5–8 superfícies piloto autenticadas, **When** o revisor compara before/after em scan rápido, **Then** distingue melhoria perceptível em pelo menos 5 superfícies, nenhuma sendo login.
3. **Given** checklist OUT, **When** validado no aceite, **Then** confirma login intocado e happy paths 005/006 sem regressão funcional.

---

### Edge Cases

- Superfície piloto sem dados (charts vazios, matriz vazia, lista vazia): polish aplica-se ao empty state; continua honesto e acionável.
- Papéis sem acesso a 9-box ou a certos dashboards: polish das demais superfícies não exibe conteúdo fora de escopo; AuthZ inalterada.
- Formulário com erros de validação: acabamento visual não obscurece mensagens de erro nem estados inválidos já existentes.
- Loading de botão e respostas parciais de página: feedback visual permanece correto após refino de classes.
- Tentativa de “aproveitar” a feature para nova rota, métrica ou lib: deve ser rejeitada e documentada como OUT.
- Login e `base_auth`: qualquer regressão visual ou comportamental é falha de aceite, não trade-off.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O produto autenticado MUST aplicar tipografia v2 (display vs UI) e tokens atualizados em shell e superfícies piloto, com hierarquia documentada no Freeze.
- **FR-002**: Tipografia/tokens v2 MUST NOT ser aplicados à tela de login nem a templates baseados em `accounts/base_auth` (OUT duro).
- **FR-003**: O sistema MUST refinar visualmente o componente de botão compartilhado nas variantes existentes (primary, secondary, outlined, loading), preservando semântica e contratos de uso.
- **FR-004**: Cards/KPI, table-frame e empty states nas superfícies piloto MUST receber densidade, bordas e (se necessário) sombra mínima alinhadas ao DS v2, preferindo composição sem cardificar excessivamente.
- **FR-005**: Charts existentes (005) MUST receber polish visual (eixos, tooltips, legendas, espaçamento do bloco, radius/thickness, grid lines sutis, altura/ritmo) sem novas métricas, bibliotecas ou endpoints.
- **FR-006**: Charts MUST continuar Status Triad + rótulos textuais além da cor (a11y mínima preservada).
- **FR-007**: A matriz 9-box interativa (006) MUST receber polish visual de grade, person cards, drawer de domínio, feedback de drag/drop e empty, sem alterar AuthZ, fórmulas, política drag=potencial-only nem contratos HTMX/POST de negócio.
- **FR-008**: Refinamentos de shell autenticado (sidebar/topbar), se incluídos, MUST limitar-se a densidade/tipografia dentro da estrutura Freeze atual, sem redesign de IA de navegação nem reagrupar Governança/Cadastros/Sistema.
- **FR-009**: A entrega MUST atualizar o Freeze na mesma release: documentação do design system + tokens/CSS + componentes tocados, declarando status Freeze v2.
- **FR-010**: A entrega MUST produzir evidência before/after perceptível em 5 a 8 superfícies piloto autenticadas (sugeridas: dashboard admin com charts, dashboard time, dashboard pessoal/gaps, matriz 9-box, uma lista de ciclos ou avaliações, um detalhe PDI ou formulário comum, shell como chrome de referência).
- **FR-011**: A feature MUST NOT introduzir novas capacidades de negócio, rotas, views de domínio, models, migrations, permissões, métricas, campos, flags, serializers ou tarefas assíncronas.
- **FR-012**: A feature MUST NOT adicionar novas bibliotecas de front-end/chart além do que já existe no projeto para as superfícies piloto.
- **FR-013**: Mudanças em templates de piloto e em scripts de apresentação (charts / feedback visual da matriz) MUST limitar-se a classes, markup visual, opções visuais e ARIA de suporte; payloads e URLs de negócio permanecem iguais.
- **FR-014**: WIP Impeccable e marketing Verdee NÃO são dependência obrigatória; eventual referência ao guia Figma Verdee é opcional e cherry-pick de peças só se pesquisa justificar peça a peça.
- **FR-015**: Aceite MUST incluir checklist OUT: login/`base_auth` intocados; zero regressão funcional nos happy paths documentados de 005 e 006.

### Key Entities

- **Freeze Design System v2**: Conjunto documentado de decisões visuais (tipografia, tokens, botões, cards/KPI, charts polish, ninebox polish) alinhado aos artefatos de estilo do app autenticado; versionado como v2 em substituição/atualização do Freeze 004.
- **Superfície piloto**: Tela autenticada escolhida para evidência before/after (dashboards, matriz, lista, form/detalhe, shell); exclui login e marketing externo.
- **Componente de apresentação compartilhado**: Peças reutilizáveis de UI (botão, badge, empty state, padrões de KPI/card/table-frame) refinadas sem nova lógica de negócio.
- **Checklist OUT**: Artefato de aceite que prova exclusões duras (login intocado; sem regressão 005/006; sem produto novo).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Revisor externo ao time de implementação distingue before/after em pelo menos 5 superfícies piloto autenticadas em scan de até 10 segundos por tela, sem usar a tela de login como evidência.
- **SC-002**: Login e superfícies `base_auth` permanecem visual e comportamentalmente inalterados (checklist OUT 100% marcado para esses itens).
- **SC-003**: Happy paths de charts (005) e matriz interativa (006) passam sem regressão funcional nos fluxos de aceitação rápida respectivos (abrir, interpretar vazio/populado, drag autorizado, drawer).
- **SC-004**: Documentação do design system declara explicitamente Freeze v2 cobrindo tipografia, botões, cards/KPI, charts polish e ninebox polish.
- **SC-005**: Em revisão guiada, hierarquia tipográfica (títulos vs corpo vs KPI) é citada como melhoria por ≥80% dos revisores que completam o scan das superfícies piloto (ou, se um único revisor de aceite, deve registrar tipografia como mudança perceptível em ≥3 superfícies).
- **SC-006**: Nenhuma nova capacidade de negócio, rota de domínio ou biblioteca front-end é introduzida por esta feature (verificável por checklist OUT + escopo da entrega).

## Assumptions

- O branch de trabalho já é `007-design-system-v2`; esta especificação não cria produto novo — apenas polish + Freeze v2.
- A escolha exata de família tipográfica (quais faces display/UI) é decisão de research/plan dentro do princípio “expressiva + self-hosted”, desde que login não herde a mudança.
- Shell leve (sidebar/topbar) é desejável se couber após tipografia/componentes/charts/matriz; não bloqueia o MVP se adiado dentro da mesma feature após os P1–P4, mas o chrome de referência permanece na lista de superfícies piloto quando houver capacidade.
- Drawer canônico global só entra se research da implementação justificar; o drawer da 9-box pode permanecer de domínio `talent` com polish visual.
- a11y mínima (contraste, focus-visible, rótulos além da cor) mantém-se; auditoria WCAG formal completa continua fora de escopo.
- Guia Figma Verdee e stash Impeccable são referências opcionais, não baseline obrigatório.
- Aceite é visual (before/after + revisão guiada), não suite TDD visual obrigatória.
- Stack e dualidade doc ↔ CSS do projeto permanecem; UI não autoriza.

## Out of Scope (OUT)

- Qualquer mudança em login, `accounts/base_auth.html`, `accounts/login.html` ou copy do painel narrativo de auth
- Landing/marketing externa
- Novas features de produto, métricas, cálculos, AuthZ, escopo hierárquico, queries de negócio
- Alterar contratos de negócio da 006 (drag=só potencial, drawer HTMX, gates) além de classes/markup visual
- Novas libs de chart / SPA / DRF / GraphQL / Alpine / React / Sortable etc.
- Export/relatórios
- Redesign de IA da navegação Admin (grupos Governança/Cadastros/Sistema permanecem)
- Dark mode obrigatório
- Auditoria WCAG formal completa
- Reaplicar WIP Impeccable como base ou portar marketing Verdee por completo
- Novas rotas, views, models, migrations, apps, Celery tasks, serializers, permissões, flags ou copy de regra de negócio
