# Feature Specification: Fundação Visual e UX Estável

**Feature Branch**: `004-ux-visual-foundation`

**Created**: 2026-07-29

**Status**: Draft

**Input**: User description: "Estabelecer e estabilizar a fundação visual/UX do Greenn People a partir do estado atual em development (baseline limpo, sem o WIP do Impeccable), sem novas capacidades de produto. Melhorar hierarquia, clareza e consistência nas superfícies críticas; congelar tokens/padrões antes das features de gráficos no dashboard e 9-box interativa."

## Declaração do Problema (O Porquê)

O Greenn People já opera com UI funcional (shell autenticado, dashboards por papel, ciclos, PDI, avaliações, matriz 9-box estática), mas a hierarquia visual e a consistência entre superfícies críticas ainda dificultam o scan rápido por RH e liderança. Tentativas amplas de polish (ex.: trabalho estacionado fora desta linha) não produziram ganho perceptível e não devem ser a base desta feature. Sem uma fundação visual congelada — tokens, padrões de componente e critérios before/after nas telas-piloto — as próximas capacidades (visualizações no dashboard e 9-box interativa) arriscam sobrepor ruído sobre um chassis inconsistente.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Marina encontra Governança em segundos no shell (Priority: P1)

Marina (admin DP/RH) abre qualquer sessão autenticada e, na Administração, enxerga progressive disclosure clara: Governança (Ciclos, Aderência e correlatos) destacada visualmente em relação a Cadastros e Sistema. Ela identifica em poucos segundos onde governar o ciclo ativo e acompanhar aderência, sem confundir com CRUD genérico.

**Why this priority**: O dia a dia do RH gira em torno de governança do ciclo; a hierarquia do shell é a alavanca de maior impacto perceptível para a persona central, sem mudar regras de negócio.

**Independent Test**: Com usuário admin autenticado, abrir o shell e verificar agrupamento Governança / Cadastros / Sistema, destaque de Ciclos + Aderência vs. itens de cadastro, e que o fluxo atual de navegação para cada item permanece funcional.

**Acceptance Scenarios**:

1. **Given** sessão autenticada de administrador, **When** a Administração é apresentada, **Then** os itens aparecem organizados sob grupos claros de Governança, Cadastros e Sistema (progressive disclosure).
2. **Given** a seção Governança visível, **When** Marina compara visualmente Ciclos e Aderência com itens de Cadastros, **Then** Ciclos e Aderência têm destaque perceptivelmente maior que CRUD genérico (peso tipográfico, posição ou ênfase visual documentada).
3. **Given** o shell reorganizado, **When** Marina navega para Ciclos ou Aderência, **Then** chega à mesma superfície operacional de sempre, sem perda de permissão ou quebra de fluxo.

---

### User Story 2 - Líder faz scan de status do time em menos de 5 segundos (Priority: P1)

Um líder/gerente autenticado abre o dashboard de time (e correlatos no escopo) e, em menos de 5 segundos, identifica o status agregado mais relevante do ciclo no seu escopo hierárquico — sem precisar ler longas listas primeiro. A hierarquia tipográfica, badges e indicadores de KPI tornam o scan possível para os três papéis cumulativos, sem otimizar só o chrome Admin.

**Why this priority**: Liderança depende de scan rápido para priorizar acompanhamento; é o critério de sucesso explícito do pedido e bloqueia a percepção de “fundação pronta”.

**Independent Test**: Com líder autenticado e ciclo com dados no escopo, abrir o dashboard de time (e, se aplicável, painéis correlatos) e medir se status-chave (pendências, progresso, indicadores de ciclo) são identificáveis no primeiro olhar, com before/after registrado na tela-piloto.

**Acceptance Scenarios**:

1. **Given** líder autenticado com subordinados no escopo e ciclo aberto, **When** abre o dashboard de time, **Then** pelo menos um indicador de status operacional do ciclo no escopo é legível no primeiro viewport útil (sem scroll excessivo em desktop padrão).
2. **Given** a mesma tela após o polish, **When** um revisor compara com o baseline before, **Then** a hierarquia (títulos, badges, KPIs) está claramente mais escaneável do que o before na checklist da tela-piloto.
3. **Given** colaborador sem papel de liderança, **When** acessa o painel pessoal, **Then** a melhoria de clareza também se aplica (não apenas o chrome Admin), sem expor 9-box se a regra atual de liberação negar o acesso.

---

### User Story 3 - Colaborador percorre autoatendimento com padrões consistentes (Priority: P2)

O colaborador (toda sessão autenticada inclui essa visão) usa login, painel pessoal, listas/detalhes de PDI e avaliações, e formulários comuns, encontrando tipografia, espaçamento, botões, badges, empty states e tabelas consistentes com o visual incumbente. Empty states e erros permanecem acionáveis; fluxos existentes de atualização parcial da página não quebram.

**Why this priority**: Autoatendimento é o volume de uso; consistência nessas superfícies consolida a fundação sem novas capacidades.

**Independent Test**: Percorrer login → painel pessoal → detalhe de PDI → detalhe/listagem de avaliação → um formulário comum, verificando consistência visual e que ações que antes atualizavam só parte da página ainda atualizam as regiões esperadas.

**Acceptance Scenarios**:

1. **Given** colaborador autenticado, **When** navega painel pessoal, PDI e avaliação nas telas-piloto, **Then** botões, badges, tipografia e espaçamento seguem o mesmo conjunto de decisões documentadas (sem “ilhas” de estilo conflitante).
2. **Given** lista ou detalhe sem conteúdo relevante, **When** a empty state é exibida, **Then** há mensagem clara e, quando aplicável, próximo passo acionável.
3. **Given** interação que antes atualizava só parte da página, **When** o colaborador dispara a mesma ação após o polish, **Then** o comportamento de atualização parcial e feedback permanece correto.

---

### User Story 4 - Topbar com contexto operacional mínimo (Priority: P2)

Qualquer usuário autenticado vê na topbar um contexto operacional mínimo do ciclo (ex.: ciclo aberto / status operacional resumido), sem inchá-la com widgets, filtros ou ações secundárias. O destaque do shell e do conteúdo principal permanece; a topbar informa, não compete.

**Why this priority**: Reduz desorientação de “em que ciclo estou?” sem criar chrome novo ruidoso.

**Independent Test**: Autenticar-se com ciclo aberto e com ciclo fechado/ausente; verificar presença ou fallback do contexto mínimo e que a topbar não ganhou densidade excessiva.

**Acceptance Scenarios**:

1. **Given** ciclo aberto existente, **When** o usuário autenticado vê a topbar, **Then** há indicação mínima do ciclo aberto (ou status operacional acordado) sem filtros, listas ou CTAs secundários na topbar.
2. **Given** ausência de ciclo aberto, **When** a topbar é renderizada, **Then** há fallback claro (ex.: “sem ciclo aberto”) sem quebrar layout.
3. **Given** topbar após a mudança, **When** um revisor avalia densidade, **Then** o contexto cabe em uma linha resumida e não desloca navegação primária.

---

### User Story 5 - Acessibilidade mínima do shell e modal (Priority: P2)

Usuário que navega por teclado consegue: pular para o conteúdo principal (skip link), perceber o item atual da navegação, ver foco visível em controles interativos, permanecer preso no modal aberto até fechar, e perceber o indicador de carregamento parcial da página com rótulo acessível adequado.

**Why this priority**: Fundação estável exige a11y mínima do chrome antes de features densas (gráficos, 9-box interativa).

**Independent Test**: Percorrer shell e modal apenas com teclado; inspecionar skip link, item atual da nav, foco visível, trap no modal e indicador de carregamento parcial quanto a rótulo acessível.

**Acceptance Scenarios**:

1. **Given** página autenticada, **When** o usuário pressiona Tab no início da página, **Then** encontra um skip link que leva ao conteúdo principal.
2. **Given** um item de navegação correspondente à rota atual, **When** a nav é apresentada, **Then** o item atual é anunciado/marcado como página atual de forma acessível.
3. **Given** modal aberto, **When** o usuário navega por Tab, **Then** o foco permanece dentro do modal até fechá-lo; ao fechar, o foco retorna de forma previsível.
4. **Given** ação que dispara atualização parcial com indicador de progresso, **When** o indicador aparece, **Then** há rótulo acessível coerente (estado de carregamento perceptível a leitores de tela).

---

### User Story 6 - Congelar tokens e padrões após critérios before/after (Priority: P1)

Ao concluir as melhorias nas 5–8 telas-piloto, a equipe documenta decisões de tipografia, espaçamento, badges, botões, empty states, tabelas e indicadores (KPI/cards) alinhadas ao visual incumbente, registra critérios before/after perceptíveis e declara freeze: mudanças posteriores de produto (gráficos, 9-box interativa) consomem esses tokens/padrões em vez de reinventá-los.

**Why this priority**: O sucesso declarado é “fundação congelada” antes das próximas features; sem freeze e before/after, o trabalho não se diferencia de polish ad hoc.

**Independent Test**: Revisar documentação de design (DESIGN.md ou equivalente de design system no repositório), checklist before/after das telas-piloto e confirmação explícita de freeze no registro da feature.

**Acceptance Scenarios**:

1. **Given** as telas-piloto elegíveis (login; dashboards admin/pessoal/time/estrutura; matriz 9-box; listas de ciclos; PDI; avaliações; formulários comuns), **When** a feature é aceita, **Then** 5–8 delas têm registro before/after perceptível (screenshot ou descrição objetiva de hierarquia/clareza).
2. **Given** decisões de tokens/padrões documentadas, **When** um novo trabalho de UI começa depois do freeze, **Then** a documentação aponta o conjunto congelado como fonte da verdade (sem reabrir redesign de marca).
3. **Given** o escopo OUT (gráficos novos, 9-box interativa, WIP Impeccable, redesign marketing), **When** a feature é revisada, **Then** nenhum desses itens está entregue como parte desta especificação.

---

### Edge Cases

- Usuário com papéis cumulativos (colaborador + líder + admin): o shell mostra apenas o que o papel permite, mas os padrões visuais aplicados nas telas visíveis são os mesmos tokens.
- Colaborador sem liberação de 9-box: polish da matriz 9-box (tela-piloto para quem vê) não altera regra de visibilidade; quem não tem acesso continua sem ver.
- Listas vazias, ciclos sem dados ou dashboards sem KPIs ainda: empty states e hierarquia permanecem claros; não inventar dados falsos.
- Janela estreita / viewport móvel: shell e topbar permanecem usáveis; progressive disclosure não esconde Governança atrás de mais de um nível desnecessário.
- Falha ou atraso de atualização parcial: indicador acessível e estados de erro existentes continuam compreensíveis; polish não remove feedback.
- Baseline: trabalho visual NÃO depende do WIP Impeccable estacionado; parte do UI operacional já existente em development.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O produto MUST melhorar hierarquia visual, clareza e consistência nas superfícies-piloto sem introduzir novas capacidades de negócio (sem novas métricas, regras de cálculo, fluxos de produto ou APIs).
- **FR-002**: Superfícies-piloto in-scope MUST incluir: login; dashboards (admin, pessoal, time, estrutura); matriz 9-box (somente apresentação/clareza da visão já existente); listas de ciclos; PDI; avaliações; formulários comuns compartilhados.
- **FR-003**: O shell de Administração MUST organizar itens com progressive disclosure em Governança, Cadastros e Sistema.
- **FR-004**: Ciclos e Aderência MUST ter destaque visual perceptivelmente maior que itens de CRUD genérico (Cadastros), documentado no before/after.
- **FR-005**: A topbar MUST exibir contexto operacional mínimo do ciclo (ciclo aberto / status resumido ou fallback quando não houver ciclo aberto) e MUST NOT ser expandida com filtros, listas ou ações secundárias.
- **FR-006**: Tipografia, espaçamento, badges, botões, empty states, tabelas e indicadores (KPI/cards) MUST seguir decisões consistentes alinhadas ao visual incumbente (sem reinventar marca).
- **FR-007**: Decisões de tokens e padrões MUST ser documentadas (DESIGN.md e/ou documentação de design system do repositório, conforme já usado no projeto) e congeladas ao concluir a feature.
- **FR-008**: Critérios before/after perceptíveis MUST ser registrados para 5–8 telas-piloto elegíveis.
- **FR-009**: O shell MUST oferecer skip link para o conteúdo principal.
- **FR-010**: A navegação MUST marcar o item da página atual de forma acessível.
- **FR-011**: Controles interativos do shell e superfícies-piloto MUST apresentar foco visível adequado à navegação por teclado.
- **FR-012**: Modais MUST reter o foco enquanto abertos (focus trap) e restaurar o foco de forma previsível ao fechar.
- **FR-013**: Indicadores de carregamento de atualização parcial MUST expor rótulo/estado acessível coerente.
- **FR-014**: Melhorias visuais MUST preservar regras de escopo e segurança já aplicadas no backend (nenhuma mudança de visibilidade baseada só em ocultar UI).
- **FR-015**: Fluxos de atualização parcial existentes nas telas-piloto MUST continuar funcionando após o polish.
- **FR-016**: Mudanças MUST ser pequenas e por superfície ou padrão (uma superfície/padrão por vez); MUST NOT fazer redesign massivo indiscriminado de dezenas de templates sem critério de piloto/before-after.
- **FR-017**: Esta feature MUST NOT entregar: gráficos novos no dashboard; 9-box interativa (arrastar, drawer de edição, interações avançadas na matriz); novas métricas ou mudanças de regras de cálculo; SPA/API dedicada; reaplicação ou dependência do WIP Impeccable estacionado; redesign marketing/landing; refatoração ampla não relacionada a visual/a11y do chrome.
- **FR-018**: Melhorias nas telas-piloto MUST servir papéis cumulativos (colaborador, líder, admin) e MUST NOT otimizar exclusivamente o chrome Admin.

### Key Entities

- **Tela-piloto**: Superfície elegível para polish e critério before/after (login, dashboards por visão, 9-box estática, ciclos, PDI, avaliações, formulários comuns).
- **Token / padrão de UI**: Decisão documentada de tipografia, espaçamento, cor de status, badge, botão, empty state, tabela ou indicador KPI/card; conjunto sujeito a freeze ao fim da feature.
- **Grupo do shell (Administração)**: Agrupamento Governança / Cadastros / Sistema usado para progressive disclosure e hierarquia perceptível.
- **Contexto de ciclo (topbar)**: Resumo mínimo do ciclo aberto ou fallback quando inexistente; não é um novo domínio de dados.
- **Critério before/after**: Evidência perceptível (visual ou descritiva objetiva) de melhoria de hierarquia/clareza em uma tela-piloto.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Em revisão guiada, Marina (admin) localiza Ciclos e Aderência na Governança do shell em menos de 5 segundos após abrir a Administração.
- **SC-002**: Em revisão guiada com dados representativos, líder identifica o status operacional mais relevante do ciclo no dashboard de time em menos de 5 segundos no primeiro viewport útil.
- **SC-003**: Entre 5 e 8 telas-piloto apresentam before/after aceito por revisor (clareza/hierarquia claramente melhor), incluindo pelo menos um dashboard e pelo menos uma superfície de autoatendimento (PDI ou avaliação ou painel pessoal).
- **SC-004**: 100% dos itens de a11y mínima do shell (skip link, página atual na nav, foco visível, focus trap no modal, indicador de carregamento com rótulo acessível) passam em verificação manual por teclado.
- **SC-005**: Zero regressões funcionais conhecidas nos fluxos de atualização parcial das telas-piloto tocadas (ações críticas ainda atualizam a região esperada).
- **SC-006**: Documentação de tokens/padrões publicada e marcada como congelada (freeze) antes do início das features seguintes de visualizações no dashboard e 9-box interativa.
- **SC-007**: Escopo OUT verificado: nenhum gráfico novo, nenhuma 9-box interativa e nenhuma reintrodução do WIP Impeccable como dependência desta entrega.

## Assumptions

- O baseline é o estado operacional atual em development, limpo relativamente ao WIP Impeccable; este trabalho não reaplica nem depende desse WIP.
- Papéis são cumulativos como no produto: toda sessão autenticada inclui visão de colaborador; liderança e admin acumulam conforme hierarquia e flag de admin.
- 9-box permanece não visível por padrão ao colaborador até liberação já existente; polish da matriz respeita essa regra.
- Visual incumbente (marca, cores e tipografia já em uso) é a direção; o objetivo é hierarquia e consistência, não nova identidade.
- “Antes de 5 segundos” é critério de revisão humana guiada (RH/produto/dev), não exigência de telemetria automatizada nesta feature.
- Telas-piloto concretas entre as elegíveis podem ser priorizadas até fechar a faixa 5–8, desde que cubram shell/governança, ao menos um dashboard de liderança/admin e autoatendimento.
- Documentação pode viver em DESIGN.md e/ou docs de design system já previstos no repositório; não é obrigatório criar novo canal de docs fora do que o projeto já usa.
- Escopo/segurança e regras de cálculo permanecem intactos no backend; UI não é fonte de autorização.
- Stack de apresentação continua a do produto (templates servidor + atualizações parciais + utilitários de estilo já adotados); desvios exigem justificativa fora deste escopo.

## Out of Scope

- Gráficos novos no dashboard.
- Matriz 9-box interativa (arrastar, drawer de edição, interações avançadas).
- Novas métricas, mudanças de regras de cálculo, SPA ou API dedicada.
- Reaplicar ou depender do WIP Impeccable estacionado.
- Redesign marketing/landing.
- Refatoração ampla não relacionada a visual ou a11y do chrome.
- Alteração de políticas de escopo, permissões ou máquina de estados de ciclo/avaliação.
