# Feature Specification: Gestão de Desempenho, PDI e Talentos

**Feature Branch**: `001-gestao-desempenho-talentos`

**Created**: 2026-07-08

**Status**: Draft

**Input**: User description: "Gestores carecem de visibilidade clara sobre o desempenho e o potencial da equipe (...). Colaboradores não compreendem como suas atividades diárias se conectam aos objetivos estratégicos (...). A ausência de um plano de desenvolvimento estruturado (PDI) impede o crescimento contínuo do talento e a sucessão interna."

## Declaração do Problema (O Porquê)

- **Gestores** carecem de visibilidade clara sobre o desempenho e o potencial da equipe, tornando a tomada de decisão sobre promoções e remunerações subjetiva e ineficiente.
- **Colaboradores** não compreendem como suas atividades diárias se conectam aos objetivos estratégicos da empresa, gerando desengajamento.
- A **ausência de um plano de desenvolvimento estruturado (PDI)** impede o crescimento contínuo do talento e a sucessão interna.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Colaborador entende expectativas e registra seu desempenho (Priority: P1)

O colaborador acessa o sistema e visualiza com clareza o que é esperado de sua função: as competências associadas ao seu cargo, o nível esperado em cada uma e as metas vinculadas aos objetivos estratégicos da empresa. Ao longo do ciclo, ele registra o progresso de suas metas e realiza a autoavaliação com base em critérios objetivos.

**Why this priority**: É a base de transparência do produto. Sem clareza sobre expectativas e sem registro de resultados pelo próprio colaborador, nenhum ciclo de avaliação justo pode acontecer. Entrega valor imediato ao reduzir o desengajamento e conectar o trabalho diário aos objetivos.

**Independent Test**: Pode ser testado criando um colaborador vinculado a um cargo com competências e nível esperado definidos, atribuindo metas ligadas a um objetivo estratégico, e verificando que o colaborador consegue visualizar expectativas, registrar progresso e concluir a autoavaliação de forma isolada.

**Acceptance Scenarios**:

1. **Given** um colaborador com cargo definido e competências esperadas vinculadas, **When** ele acessa sua página de expectativas, **Then** vê cada competência, o nível esperado e as metas do ciclo ligadas aos objetivos estratégicos.
2. **Given** uma meta aprovada no ciclo corrente, **When** o colaborador registra o percentual de progresso, **Then** o valor é salvo e refletido no acompanhamento do seu desempenho.
3. **Given** que chegou a etapa de avaliação, **When** o colaborador realiza sua autoavaliação por competência, **Then** as notas são registradas e ficam disponíveis para o líder consultar.
4. **Given** um colaborador sem cargo ou competências vinculadas, **When** ele acessa sua página de expectativas, **Then** o sistema informa que o vínculo está pendente em vez de exibir conteúdo vazio ou incorreto.

---

### User Story 2 - Líder avalia a equipe com base em critérios objetivos (Priority: P1)

O líder acompanha os colaboradores do seu time, aprova metas e resultados, fornece feedback contínuo e estruturado e avalia cada competência comparando o desempenho apresentado ao nível esperado do cargo, reduzindo vieses. Ao final, obtém uma nota consolidada por colaborador.

**Why this priority**: Concretiza o critério de **Justiça**. A avaliação estruturada por competências e metas quantificáveis é o coração da tomada de decisão sobre desempenho. Depende da transparência estabelecida na Story 1, mas é igualmente essencial para o MVP.

**Independent Test**: Pode ser testado atribuindo um time a um líder, submetendo metas e resultados de um colaborador para aprovação, registrando feedbacks e notas por competência, e verificando que a nota consolidada é calculada e que o líder só enxerga membros do seu próprio escopo.

**Acceptance Scenarios**:

1. **Given** um colaborador com metas submetidas, **When** o líder aprova ou reprova cada meta, **Then** apenas metas aprovadas seguem para a etapa de acompanhamento de resultados.
2. **Given** que todas as metas de um colaborador foram aprovadas e os resultados registrados, **When** o líder avalia as competências, **Then** o sistema gera a nota consolidada do colaborador para o ciclo.
3. **Given** um líder autenticado, **When** ele tenta acessar dados de um colaborador fora do seu escopo hierárquico, **Then** o acesso é negado.
4. **Given** um colaborador em qualquer etapa do ciclo, **When** o líder registra um feedback, **Then** o feedback fica associado ao colaborador e visível no histórico.

---

### User Story 3 - Colaborador e líder gerenciam o Plano de Desenvolvimento Individual (Priority: P2)

O colaborador possui um espaço dedicado para acompanhar seu PDI, com ações de aprendizado e crescimento, prazos e status. O líder pode propor e acompanhar ações de desenvolvimento para os membros do time, conectando lacunas identificadas na avaliação a ações concretas.

**Why this priority**: Endereça diretamente a lacuna de crescimento contínuo e sucessão interna citada no problema. É de alto valor, porém depende de expectativas e avaliações já existirem (Stories 1 e 2) para ser plenamente útil.

**Independent Test**: Pode ser testado criando ações de PDI para um colaborador, com prazos e status, e verificando que colaborador e líder conseguem visualizar e atualizar o andamento das ações independentemente do ciclo de avaliação estar em curso.

**Acceptance Scenarios**:

1. **Given** um colaborador autenticado, **When** ele acessa seu PDI, **Then** vê a lista de ações de desenvolvimento com descrição, prazo e status.
2. **Given** um líder acompanhando o time, **When** ele cria uma ação de PDI para um colaborador, **Then** a ação aparece no PDI do colaborador.
3. **Given** uma ação de PDI em andamento, **When** o colaborador ou o líder atualiza seu status, **Then** a mudança fica registrada com data de atualização.

---

### User Story 4 - RH centraliza ciclos e monitora aderência (Priority: P2)

O RH/Administrador configura e centraliza todos os ciclos de avaliação em um único local com informações padronizadas, monitora a aderência dos gestores aos prazos e às políticas de feedback, e obtém uma visão agregada da organização para identificar lacunas de competências.

**Why this priority**: Garante **Agilidade** e governança. Sem centralização e monitoramento de aderência, o processo não escala e volta a depender de controles manuais. Importante, mas o valor central ao colaborador/líder (Stories 1 e 2) precede.

**Independent Test**: Pode ser testado abrindo e encerrando um ciclo como administrador, verificando que registros de avaliação são criados para todos os colaboradores ativos, e consultando indicadores de aderência da liderança e visão agregada de competências.

**Acceptance Scenarios**:

1. **Given** um administrador, **When** ele abre um novo ciclo de avaliação, **Then** o sistema cria a avaliação inicial para todos os colaboradores ativos.
2. **Given** um ciclo em andamento, **When** o RH consulta o painel de aderência, **Then** vê quais gestores estão dentro ou fora dos prazos e políticas de feedback.
3. **Given** um administrador, **When** ele encerra manualmente o ciclo, **Then** nenhuma etapa pode mais avançar e avaliações não concluídas são marcadas como tal para o indicador de conclusão.
4. **Given** a organização com avaliações registradas, **When** o RH consulta a visão agregada, **Then** identifica lacunas de competências por área e por cargo.

---

### User Story 5 - Identificação de talentos e potencial (Priority: P3)

O gestor identifica facilmente quem são os talentos de alto potencial e quem necessita de suporte imediato, através de uma classificação que cruza desempenho e potencial (matriz 9-box).

**Why this priority**: Apoia decisões de promoção, remuneração e sucessão, mas depende de avaliações consolidadas (Story 2) para gerar valor. É um refinamento estratégico sobre os dados de desempenho já coletados.

**Independent Test**: Pode ser testado com avaliações consolidadas de um time e verificando que o gestor visualiza cada colaborador posicionado na matriz de desempenho x potencial, com filtros por área.

**Acceptance Scenarios**:

1. **Given** colaboradores com avaliações consolidadas, **When** o gestor acessa a matriz de talentos, **Then** cada colaborador aparece posicionado por desempenho e potencial.
2. **Given** a matriz de talentos exibida, **When** o gestor filtra por área ou cargo, **Then** a visualização é atualizada dentro do seu escopo hierárquico.

---

### Edge Cases

- **Colaborador sem gestor direto (topo da hierarquia)**: aprovações de metas e resultados precisam de um responsável alternativo definido, sem impedir o avanço do ciclo.
- **Colaborador sem cargo, área ou competências vinculadas**: fica fora do escopo de líderes, mas visível ao administrador, com sinalização de pendência.
- **Reprovação pontual de uma meta ou resultado**: reabre apenas o item reprovado, sem retroceder a etapa agregada do colaborador nem afetar itens já aprovados.
- **Mudança de peso de competência ou de escala após avaliações registradas**: notas já calculadas devem permanecer reproduzíveis com os valores vigentes no momento da avaliação.
- **Desativação de um colaborador que ainda lidera outras pessoas**: deve ser impedida até que os liderados sejam reatribuídos.
- **Tentativa de avançar de etapa com itens pendentes**: o avanço só ocorre com 100% dos itens da etapa aprovados e ao menos um item existente.
- **Ciclo encerrado**: nenhuma etapa pode avançar após o encerramento; avaliações incompletas contam como não concluídas.

## Requirements *(mandatory)*

### Functional Requirements

**Transparência e expectativas (Colaborador)**

- **FR-001**: O sistema DEVE permitir que cada colaborador visualize as competências associadas ao seu cargo e o nível esperado em cada competência.
- **FR-002**: O sistema DEVE permitir que cada colaborador visualize suas metas do ciclo e a qual objetivo estratégico da empresa cada meta está vinculada.
- **FR-003**: O sistema DEVE permitir que o colaborador registre o progresso de suas metas durante a etapa apropriada do ciclo.
- **FR-004**: O sistema DEVE permitir que o colaborador realize a autoavaliação de seu desempenho com base em competências e critérios objetivos.
- **FR-005**: O sistema DEVE exibir ao colaborador seu nível esperado e sua nota atual de forma clara.

**Avaliação e feedback (Líder/Gestor)**

- **FR-006**: O sistema DEVE permitir que o líder visualize apenas os colaboradores dentro de seu escopo hierárquico.
- **FR-007**: O sistema DEVE permitir que o líder aprove ou reprove metas e resultados de cada colaborador.
- **FR-008**: O sistema DEVE permitir que o líder registre feedback contínuo e estruturado para os colaboradores do seu time, mantendo o histórico.
- **FR-009**: O sistema DEVE permitir que o líder avalie cada competência comparando o desempenho apresentado com o nível esperado do cargo.
- **FR-010**: O sistema DEVE calcular uma nota consolidada de desempenho por colaborador por ciclo, de forma reproduzível e independente de alterações futuras em pesos ou escalas.
- **FR-011**: O sistema DEVE permitir ao gestor identificar talentos de alto potencial e colaboradores que necessitam de suporte, cruzando desempenho e potencial.

**Desenvolvimento (PDI)**

- **FR-012**: O sistema DEVE fornecer a cada colaborador um espaço dedicado para acompanhar seu Plano de Desenvolvimento Individual, com ações, prazos e status.
- **FR-013**: O sistema DEVE permitir que o líder crie e acompanhe ações de desenvolvimento para os colaboradores do seu time.
- **FR-014**: O sistema DEVE registrar a atualização de status das ações de PDI com data.

**Centralização e governança (RH/Administrador)**

- **FR-015**: O sistema DEVE permitir que o administrador crie, abra e encerre ciclos de avaliação centralizados e padronizados.
- **FR-016**: Ao abrir um ciclo, o sistema DEVE criar automaticamente o registro de avaliação inicial para todos os colaboradores ativos.
- **FR-017**: O sistema DEVE permitir apenas o encerramento manual do ciclo pelo administrador, após o qual nenhuma etapa pode avançar.
- **FR-018**: O sistema DEVE permitir que o RH monitore a aderência dos gestores aos prazos e às políticas de feedback.
- **FR-019**: O sistema DEVE fornecer ao RH uma visão agregada da organização que identifique lacunas de competências por área e por cargo.
- **FR-020**: O sistema DEVE conduzir cada colaborador por etapas sequenciais do ciclo (input de metas, aprovação de metas, resultados, aprovação de resultados, avaliação, feedback), impedindo o avanço sem a conclusão da etapa anterior.
- **FR-021**: O sistema DEVE tratar cada colaborador com progresso independente pelas etapas, sem estado global de ciclo por colaborador.

**Justiça, rastreabilidade e integridade**

- **FR-022**: O sistema DEVE basear as avaliações em metas quantificáveis e comportamentos/competências pré-definidos.
- **FR-023**: O sistema DEVE manter histórico auditável de todas as decisões sobre desempenho e desenvolvimento, com registro de valor anterior e novo.
- **FR-024**: O sistema DEVE preservar a imutabilidade dos dados históricos de ciclos, impedindo exclusão em cascata de registros de avaliação, PDI e auditoria.
- **FR-025**: O sistema DEVE congelar (snapshot) peso e nível esperado utilizados em cada avaliação no momento de sua criação, garantindo reprodutibilidade.
- **FR-026**: Ao reprovar uma meta ou resultado individual, o sistema DEVE reabrir apenas o item reprovado sem retroceder a etapa agregada do colaborador.
- **FR-027**: O sistema DEVE definir um responsável alternativo pelas aprovações de colaboradores sem gestor direto.
- **FR-028**: O sistema DEVE impedir a desativação de um colaborador que ainda possua liderados ativos até que estes sejam reatribuídos.

### Key Entities *(include if feature involves data)*

- **Colaborador (Usuário)**: Pessoa da organização; possui área, cargo, gestor direto e visões cumulativas (colaborador, líder, gerente, administrador) derivadas da posição hierárquica.
- **Área**: Unidade organizacional, com possível relação de área pai/filha.
- **Cargo**: Posição/senioridade à qual se vinculam competências esperadas e seus pesos.
- **Competência**: Habilidade avaliável (técnica, comportamental ou de liderança), com nível esperado por cargo.
- **Escala**: Faixa de avaliação reutilizável com valor mínimo e máximo, usada na normalização das notas.
- **Objetivo Estratégico**: Objetivo da empresa ao qual as metas dos colaboradores se conectam.
- **Meta**: Compromisso quantificável do colaborador, vinculado a um objetivo estratégico, com status de aprovação, progresso e status de resultado.
- **Ciclo de Avaliação**: Janela temporal de desempenho, aberta e encerrada manualmente pelo administrador.
- **Avaliação**: Registro por colaborador por ciclo, com etapa atual, notas por competência e nota consolidada.
- **Feedback**: Retorno estruturado registrado por líderes ao longo do ciclo.
- **Ação de PDI**: Item do plano de desenvolvimento individual, com descrição, prazo e status.
- **Classificação de Talento**: Posicionamento do colaborador cruzando desempenho e potencial (matriz 9-box).
- **Registro de Auditoria**: Trilha append-only de alterações relevantes, com autor, campo, valor anterior e valor novo.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001** (Transparência): 100% dos colaboradores ativos conseguem visualizar seu nível esperado e sua nota atual em cada ciclo.
- **SC-002** (Transparência): Um colaborador consegue localizar suas competências esperadas e a conexão de suas metas com os objetivos estratégicos em menos de 2 minutos.
- **SC-003** (Justiça): 100% das avaliações consolidadas são derivadas de metas quantificáveis e competências pré-definidas, sem entradas manuais fora dos critérios.
- **SC-004** (Justiça): Notas consolidadas permanecem idênticas quando recalculadas após mudanças em pesos ou escalas, comprovando reprodutibilidade.
- **SC-005** (Agilidade): Ao abrir um ciclo, os registros de avaliação de todos os colaboradores ativos são criados sem intervenção manual adicional.
- **SC-006** (Agilidade): O RH consegue acompanhar o percentual de ciclos concluídos e a aderência dos gestores sem consolidar dados manualmente em planilhas.
- **SC-007** (Rastreabilidade): 100% das decisões sobre desempenho e desenvolvimento possuem registro auditável com autor, data e valores anterior/novo.
- **SC-008** (Rastreabilidade): Nenhum registro histórico de avaliação, PDI ou auditoria pode ser removido por exclusão de área, cargo ou usuário.
- **SC-009** (Desenvolvimento): 100% dos colaboradores ativos possuem um espaço de PDI acessível com ações e prazos visíveis.
- **SC-010** (Potencial): O gestor consegue identificar, dentro do seu escopo, os colaboradores de alto potencial e os que necessitam de suporte em uma única visualização.

## Assumptions

- O sistema é uma aplicação web interna corporativa, sem acesso público, com um único gestor direto por colaborador (sem lideranças matriciais na v1).
- Os papéis (colaborador, líder, gerente, administrador) são visões cumulativas derivadas da posição hierárquica, não estados exclusivos.
- Apenas um ciclo de avaliação fica aberto por vez na v1.
- As metas alimentam o eixo de desempenho de forma consultiva; a nota consolidada é derivada das competências avaliadas pelo líder.
- A classificação de talentos utiliza o modelo de matriz 9-box (desempenho x potencial).
- Notificações e cálculos agregados pesados podem ser processados de forma assíncrona, sem impacto neste escopo funcional.
- A base de referência de requisitos detalhados é o PRD do Greenn People e a constituição do projeto.
