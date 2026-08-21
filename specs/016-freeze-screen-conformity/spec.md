# Feature Specification: Conformidade visual das telas ao Freeze v2

**Feature Branch**: `016-freeze-screen-conformity`

**Created**: 2026-08-21

**Status**: Draft

**Input**: User description: "Refinamento visual das telas — consumo estrito do Freeze v2 (conformidade, não redesign); Category A excelente / Category B decente; violações conhecidas; progresso fake → chart real; sem decisão visual nova."

## Declaração do Problema (O Porquê)

O Design System já está documentado e congelado em `docs/design-system.md` (Freeze v2 + reaberturas A/B/C + incrementação D). Mesmo assim, telas autenticadas ainda apresentam violações concretas: progresso simulado em markup genérico, badges com cor ad hoc, formulários sem largura controlada e cores fora da paleta. Esta feature não introduz decisão visual nova — é auditoria e remediação de conformidade. Qualquer necessidade fora do Freeze deve parar e escalar, não “adaptar”.

## Clarifications

### Session 2026-08-21

- Q: Relação com `009-persona-visual-redesign`? → A: Conformidade pura pós-Freeze; pode re-tocar telas A já entregues na 009 se ainda violarem.
- Q: Inventário desta rodada? → A: Category A = telas do brief mais painel do time; Category B = Áreas, Cargos, Usuários e Competências apenas (listas de ciclo ficam para rodada futura).
- Q: Progresso fake do ciclo? → A: Entra nesta feature como remediação P1 (admin + detalhe de ciclo), alinhada ao Freeze A/D — sem depender de arquivo `patch-progresso-etapas-ciclo.md` ausente no repo.

### Session 2026-08-21 — Table-frame · listas Category B (decisão B1)

Decisão de produto **B1** (aprovada): extensão pontual do contrato de tabelas **somente** para listas Category B. Não reabre Freeze A/B/C/D (charts, painel gerencial, densidade). Deve ser documentada em `docs/design-system.md` (seção Table-frame · listas de cadastro) na mesma entrega da implementação.

**Layout de largura**

- Listas B: container centralizado com cap — até 4 colunas com largura máxima média-larga; mais de 4 colunas com largura máxima um degrau maior.
- Formulários B da mesma entidade: mantêm o cap de form já definido — **não** precisam compartilhar o mesmo cap da lista.
- Category A: permanece full-bleed no conteúdo do painel (sem este cap).

**Anatomia da tabela B**

- Tabela com larguras de coluna fixas/proporcionais (via definição de colunas), evitando que a coluna de nome estique e afaste as ações.
- Coluna **Ações**: alinhada à direita; links com separador leve (espaço / ponto médio muted) — **proibido** separador `|` denso.
- Em viewport estreito (~375px): scroll horizontal permanece **dentro** do frame da tabela, sem bleed da página.

### Mapa persona × inventário (esta rodada)

| Persona | Category A (no escopo) | Category B (no escopo) | Fora desta rodada |
|---|---|---|---|
| **Admin RH** | Painel admin; Ciclo (detalhe); Matriz (se já acessar) | Áreas, Cargos, Usuários, Competências | Listas de ciclo; demais CRUDs |
| **Gestor / líder** | Painel do time; Aderência; Estrutura; Matriz de talentos | — | Cadastros B (não são fluxo do gestor nesta rodada) |
| **Colaborador** | Meu painel | — | Expectativas, metas, avaliações, PDI, minha classificação (009 P2; não reabertos aqui) |

AuthZ/escopo de dados **não** mudam nesta feature — a tabela define só **quais superfícies** entram na auditoria visual por persona.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Progresso do ciclo como visualização real (Priority: P1)

Marina (Admin RH) abre o painel admin e o detalhe do ciclo e vê o progresso das avaliações por etapa como visualização gerencial real do catálogo Freeze (barras horizontais mono teal/cyan, amber só no gargalo), não como barra com largura/cor ad hoc. Empty states permanecem honestos quando não há dado.

**Why this priority**: É a violação mais visível e já especificada conceitualmente; destrava confiança no restante da conformidade A.

**Independent Test**: Abrir admin e detalhe de ciclo com ciclo em andamento e sem dados; confirmar visualização real + ausência da barra fake; validar que números/categorias de negócio não mudaram de significado.

**Acceptance Scenarios**:

1. **Given** ciclo com avaliações em etapas distintas, **When** Marina abre o painel admin ou o detalhe do ciclo, **Then** o progresso por etapa aparece como visualização do catálogo Freeze (não como bloco com largura/cor ad hoc).
2. **Given** a mesma superfície, **When** há um gargalo (etapa de maior volume), **Then** o destaque amber aparece só nesse item; demais barras seguem acabamento mono teal/cyan.
3. **Given** ausência de dados para o progresso, **When** a seção carrega, **Then** empty state usa a taxonomia Freeze D adequada — sem série inventada.

---

### User Story 2 - Telas gerenciais (Category A) em conformidade plena (Priority: P1)

Marina, Bruno (líder) e Ana (colaboradora) percorrem as superfícies gerenciais da rodada e encontram tipografia, componentes, composição de painel gerencial e charts alinhados ao Freeze — sem sombra em cards/KPIs, sem chips de status inventados, sem cores fora da paleta, com KPI → visual → drill-down → ações nessa ordem.

**Why this priority**: São as telas de maior exposição gerencial; conformidade “excelente” é o padrão de qualidade desta categoria.

**Independent Test**: Percorrer inventário A com e sem dados; checar checklist de conformidade A; testar viewport ~375px sem scroll horizontal.

**Inventário Category A (fechado nesta rodada)**:

- Painel admin
- Painel do time (líder)
- Aderência
- Estrutura
- Matriz de talentos
- Ciclo (detalhe)
- Meu painel

**Acceptance Scenarios**:

1. **Given** qualquer tela do inventário A com dados, **When** o revisor avalia a composição, **Then** a ordem é KPI(s) → visual → drill-down/tabela → ações (tabela não é a visão principal).
2. **Given** gráficos presentes, **When** inspecionados, **Then** são visualizações reais do catálogo Freeze; aderência usa somente Status Triad (3 fatias); rankings longos respeitam Top-N + “Outros” onde o Freeze D exigir; pipeline de etapas permanece conjunto fechado sem Top-N.
3. **Given** badges/status e CTAs, **When** renderizados, **Then** usam componentes canônicos do Freeze (sem chip/botão solto reescrevendo o padrão).
4. **Given** viewport ~375px, **When** navega a tela, **Then** não há scroll horizontal nem bleed.

---

### User Story 3 - Cadastros (Category B) limpos e funcionais (Priority: P2)

Marina usa Áreas, Cargos, Usuários e Competências (listas e formulários) e encontra layout controlado (form não “boiando” na largura total), inputs/botões/cards canônicos, tabelas no frame Freeze e zero cor fora da paleta — sem KPI, gráfico ou decoração que a tela não pedia. Listas B seguem o contrato Table-frame · listas de cadastro (decisão B1).

**Why this priority**: Fecha o gap operacional de cadastro sem exigir polish de chart; padrão “decente”.

**Independent Test**: Abrir lista + formulário de cada entidade B; validar checklist B; confirmar ausência de elementos gerenciais indevidos e conformidade B1 (cap de largura, colunas proporcionais, ações à direita).

**Inventário Category B (fechado nesta rodada)**:

- Áreas (lista + form)
- Cargos (lista + form)
- Usuários (lista + form; telas correlatas de usuários pendentes se fizerem parte do mesmo fluxo visual)
- Competências (lista + form; escalas só se forem parte inseparável do mesmo fluxo — caso contrário, fora desta rodada)

**Fora desta rodada (B futuro)**: listas de ciclo e demais CRUDs não listados.

**Acceptance Scenarios**:

1. **Given** formulário de nova/editar área (e demais forms B), **When** a página carrega, **Then** o form está em container com largura controlada e centralizado, usando card Freeze sem sombra.
2. **Given** lista B, **When** exibida, **Then** a tabela está no frame Freeze — sem cardificar cada linha.
3. **Given** qualquer tela B, **When** o revisor busca gráfico/KPI decorativo, **Then** não encontra elementos que a tela não pedia.
4. **Given** lista B com poucas colunas (ex.: Cargos, Áreas), **When** exibida, **Then** a tabela usa larguras de coluna fixas/proporcionais, evitando que a coluna de nome estique e afaste a coluna de ações.
5. **Given** a coluna de Ações em qualquer lista B, **When** renderizada, **Then** os links ficam alinhados à direita, com separador leve entre eles — sem `|` denso.
6. **Given** lista B, **When** exibida, **Then** está em container centralizado com cap médio-largo (≤4 colunas) ou um degrau maior (>4 colunas); o form correspondente da entidade permanece no cap de form já definido (mais estreito que a lista).

---

### User Story 4 - Filtros e paginação reutilizados na fonte (Priority: P3)

Quando filtros/busca/paginação forem necessários nas telas B desta rodada, Marina vê o mesmo padrão já existente no produto (não um componente novo). Se o padrão fonte tiver violação de token, a correção ocorre uma vez no include compartilhado antes de propagar.

**Why this priority**: Evita proliferação de UIs de paginação e garante correção única.

**Independent Test**: Localizar o include canônico de paginação; aplicar/reusar em telas B que já tenham ou ganhem controles; confirmar que não há segunda implementação paralela.

**Acceptance Scenarios**:

1. **Given** tela B com lista paginável/filtrável, **When** os controles são renderizados, **Then** reutilizam o padrão existente (busca via input canônico; ação via botão canônico; paginação via include único).
2. **Given** violação visual no componente fonte de paginação, **When** corrigida, **Then** a correção é na fonte única — não cópia por tela.

---

### Edge Cases

- Tela A sem dado suficiente para KPI/chart: empty Freeze D correto; layout não colapsa em tabela-só sem contextualizar o vazio.
- Tela A com N baixo: datalabels legíveis conforme Freeze; sem inventar tipo de gráfico.
- Form B em erro de validação: mantém container/largura e componentes canônicos; não introduz estilo de erro fora do Freeze.
- Necessidade visual não prevista no Freeze: implementação para e escala para decisão de produto — não cria ilha de estilo.
- Viewport estreito (~375px): filtros empilham; sem overflow horizontal da página; scroll de tabela B, se necessário, fica dentro do frame.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Cada tela do inventário A e B DEVE ser auditada contra o Freeze aplicável em `docs/design-system.md` e remediada até eliminar violações — sem adicionar elementos não exigidos pelo Freeze.
- **FR-002**: Esta feature NÃO DEVE introduzir decisão visual nova (cor, sombra, peso tipográfico, componente ou composição) ausente do Freeze; dúvidas DEVEM ser escaladas antes de implementar. Exceção explícita e pontual: decisão B1 (Table-frame · listas B), documentada no DS na mesma entrega.
- **FR-003**: Superfícies Category A DEVEM seguir o padrão de painel gerencial (KPI → visual → drill-down → ações).
- **FR-004**: Indicadores de progresso, contagem, ranking e aderência nas telas A DEVEM usar visualizações do catálogo Freeze; é proibido simular gráfico com markup/estilo ad hoc.
- **FR-005**: A seção de progresso das avaliações no ciclo (painel admin e detalhe do ciclo) DEVE ser remediada na P1 conforme Freeze A/D (barras horizontais mono + amber só no gargalo).
- **FR-006**: Status/badges DEVEM usar o componente e a semântica Freeze; chips de cor ad hoc são proibidos.
- **FR-007**: Cards/KPIs DEVEM seguir o chrome Freeze (borda/superfície, sem sombra).
- **FR-008**: Tipografia de título de página e pesos de texto DEVEM respeitar a escala Freeze (sem pesos tipográficos proibidos pelo Freeze).
- **FR-009**: Formulários Category B DEVEM ter largura controlada e centralizada, com inputs/botões/card canônicos.
- **FR-010**: Tabelas de listagem DEVEM usar o frame de tabela Freeze.
- **FR-011**: Empty states DEVEM usar a taxonomia Freeze D (operacional / escopo / sem_dado / sem_nota) — nunca copy genérica “sem dados” quando houver kind específico.
- **FR-012**: Filtros/paginação, quando presentes, DEVEM reutilizar o padrão existente; correções de token na fonte única.
- **FR-013**: Cores de UI DEVEM permanecer na paleta Freeze permitida; qualquer família de cor fora dela é violação.
- **FR-014**: Fora de escopo explícito: reordenar nav; alterar shell; mexer em autenticação/login; adotar elementos do guia Figma Verdee; inventar tipo de gráfico fora do catálogo; listas de ciclo e demais cadastros não listados nesta rodada.
- **FR-015**: Listas Category B DEVEM estar em container centralizado com largura máxima controlada (cap médio-largo para ≤4 colunas; um degrau maior para >4 colunas). Formulários B mantêm o cap de form já definido; não é obrigatório unificar cap lista↔form. Superfícies A não usam este cap.
- **FR-016**: Tabelas Category B DEVEM usar larguras de coluna fixas/proporcionais; coluna Ações alinhada à direita com separador leve entre links (sem `|` denso).
- **FR-017**: A extensão Table-frame · listas B DEVE ser registrada em `docs/design-system.md` na mesma entrega (consumo + documentação da decisão B1; sem reabrir A/B/C/D).

### Key Entities

- **Inventário Category A**: conjunto fechado de superfícies gerenciais desta rodada (admin, time, aderência, estrutura, matriz, detalhe de ciclo, meu painel).
- **Inventário Category B**: conjunto fechado de cadastros desta rodada (áreas, cargos, usuários, competências).
- **Violação visual**: desvio observável em relação a um contrato Freeze (token, componente, composição ou catálogo de chart).
- **Componente canônico**: include compartilhado do design system já existente no produto.
- **Largura de tabela B**: contrato de layout desta rodada — cap + colunas proporcionais + ações à direita; extensão pontual do Table-frame para cadastros (decisão B1), não reabertura geral do Freeze.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% das telas do inventário A passam no checklist de conformidade Category A (auditoria registrada por tela).
- **SC-002**: 100% das telas do inventário B passam no checklist de conformidade Category B (incluindo contrato B1 de largura/colunas/ações).
- **SC-003**: Progresso de etapas no admin e no detalhe do ciclo deixa de apresentar barra fake; revisor confirma visualização Freeze-compliant em até 5 minutos de inspeção por superfície.
- **SC-004**: Em viewport ~375px, 0 telas da rodada apresentam scroll horizontal da página ou bleed de conteúdo.
- **SC-005**: Auditoria amostral pós-entrega encontra 0 ocorrências de sombra em card/KPI, chip de status ad hoc ou cor fora da paleta Freeze nas telas da rodada.
- **SC-006**: Nenhuma decisão visual nova é adicionada ao Freeze nesta feature além da extensão pontual B1 já aprovada (documento de DS permanece consumo-only para A/B/C/D; B1 é a única adição documental prevista).

## Assumptions

- Fonte da verdade visual = `docs/design-system.md` (Freeze v2 + A/B/C/D); Figma Verdee permanece fora de escopo.
- Violações listadas no brief são amostra inicial, não lista exaustiva — cada tela exige levantamento próprio antes de remediar.
- Lógica de queryset/paginação no backend é independente e pode avançar em paralelo; só a UI dos controles entra no checklist desta feature.
- O include de paginação já existente no produto é o padrão a reutilizar.
- “Usuários pendentes” e forms de escala entram só se forem inseparáveis do fluxo visual de Usuários/Competências; caso contrário, ficam para rodada futura junto com listas de ciclo.
- Remediação pode re-tocar telas já trabalhadas na 009 sem reabrir contratos A/B/C/D.
- A decisão B1 (Table-frame · listas B) é a única extensão documental prevista nesta feature; tokens concretos de largura (`max-w-5xl` / `max-w-6xl`, `table-fixed`, `colgroup`) residem no DS e nas telas B, não como reabertura de charts/painel/densidade.

## Dependencies

- `docs/design-system.md` (Freeze canônico)
- Contratos de referência intactos: charts / painel gerencial / densidade-histórico-empty das features 009 e 012
- Componentes compartilhados já existentes (button, input, card, badge_status, empty_state, table-frame, chart block, pagination)
