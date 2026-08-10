# Feature Specification: Orientação de Próximo Passo no Ciclo de Desempenho (Guidance UX)

**Feature Branch**: `008-cycle-guidance-ux`

**Created**: 2026-08-07

**Status**: Draft

**Input**: User description: "Orientação de próximo passo no ciclo de desempenho (guidance UX) — Greenn People: reduzir fricção de UX no ciclo (colab/líder/RH) com bloco Próximo passo + stepper, hierarquia de CTAs no hub da avaliação, badge de pendências do líder, feedback em ações longas e checklist pré-abertura — sem alterar máquina de estados, fórmulas, AuthZ, URLs de negócio nem navegação de grupos; não é continuação do 007-design-system-v2; entrega alvo produção 06/09/2026."

## Declaração do Problema (O Porquê)

A lógica de negócio do ciclo de desempenho, a máquina de estados e a autorização já estão estáveis e validadas em UAT. O bloqueio restante para a virada de produção (alvo 06/09/2026, toda a Greenn) é fricção de orientação: o usuário não sabe “o que fazer agora”. Jargão de etapa, hub da avaliação com vários CTAs sem hierarquia, líder sem indicação clara de pendências e RH sem checklist operacional pré-abertura geram dependência de demos verbais e atrito operacional. Esta feature fecha esse gap de guidance UX reutilizando a linguagem visual já estabelecida (Freeze / componentes existentes), sem reabrir design system, cálculos, AuthZ, URLs de negócio ou a IA de navegação.

## Clarifications

### Session 2026-08-07

- Q: Como congelar o mapa de apresentação etapa → título / frase / CTA / rota (só leitura do estado atual)? → A: Tabela completa no spec: por etapa (+ papel quando diferir) → título, frase, rótulo do CTA e nome de rota já existente.
- Q: O que compõe o badge de pendências do líder (agregação visual das fontes já elegíveis)? → A: Um único total somado: aprovações + avaliações + feedbacks elegíveis (mesmas queries/regras atuais), exibido num badge na nav do líder.
- Q: Como o checklist RH se apresenta em relação à abertura de ciclo (somente aviso)? → A: Só aviso: checklist + links de correção; botão Abrir permanece no comportamento/regra já existente (nunca trava nova).
- Q: Como entregar o stepper de etapas (Meu painel + detalhe)? → A: Partial/component shared em templates/components (reuso Meu painel + detalhe da avaliação).
- Q: Qual o aceite de apresentação mobile vs desktop? → A: Desktop é aceite primário; mobile apenas legível (stack vertical), stepper pode compactar (só rótulos/números).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Colaborador e líder veem “Próximo passo” + stepper de etapas (Priority: P1)

Ana (colaboradora) e Bruno (líder) abrem o Meu painel e imediatamente veem um bloco “Próximo passo” com título claro, uma frase curta do que fazer agora e um único botão principal que leva à ação correta para a etapa atual da Avaliação no ciclo aberto. No mesmo painel (e no detalhe da avaliação) um stepper visual das 6 etapas do ciclo (do input de metas ao feedback) mostra o que já ficou para trás, o que está em andamento, o que ainda virá e o que está bloqueado. Se não houver ciclo aberto, se o vínculo ainda estiver pendente ou se o ciclo já estiver concluído para aquela pessoa, o bloco comunica esse estado sem pedir “próxima ação de etapa”.

**Why this priority**: Sem orientação no ponto de entrada principal, a produção em massa gera suporte verbal e abandono; é o maior redutor de fricção para colaborador e líder.

**Independent Test**: Com papel colaborador (e depois líder) em ciclo aberto em etapa conhecida, abrir Meu painel e detalhe da avaliação; confirmar bloco “Próximo passo” + stepper coerentes com a etapa; repetir para estados sem ciclo, vínculo pendente e ciclo concluído para o usuário. Pessoa nova no papel deve identificar a ação sem instrução verbal.

**Acceptance Scenarios**:

1. **Given** colaborador com avaliação no ciclo aberto em uma etapa ativa, **When** abre o Meu painel, **Then** vê bloco “Próximo passo” (título + uma frase + um CTA primário) derivado da etapa atual e o CTA leva à superfície correta daquela ação.
2. **Given** o mesmo colaborador no Meu painel ou no detalhe da avaliação, **When** observa o stepper das 6 etapas, **Then** identifica visualmente etapas concluídas, a etapa atual, etapas futuras e etapas bloqueadas, alinhadas ao estado real da avaliação.
3. **Given** usuário sem ciclo aberto, com vínculo pendente ou com ciclo já concluído para si, **When** abre o Meu painel, **Then** o bloco comunica esse estado (sem sugerir CTA de avanço de etapa inexistente) e permanece honesto.
4. **Given** pessoa nova no papel (colaborador ou líder) sem briefing verbal do processo, **When** usa apenas o Meu painel, **Then** consegue nomear e iniciar a ação correta da etapa atual.

---

### User Story 2 - Hub da avaliação e navegação do líder com menos fricção (Priority: P1)

Bruno abre o detalhe da avaliação e encontra um único CTA primário alinhado ao próximo passo; demais ações ficam claramente secundárias. Os textos usam linguagem humana (o que fazer), não só rótulo técnico de etapa. Na navegação lateral do líder, sem redesenhar os grupos já estabelecidos, aparece indicação de quantidade de pendências no escopo dele (aprovações, avaliações e feedbacks elegíveis). Onde já existir hint de próximo passo em superfícies de meta, o produto reaproveita essa orientação em vez de inventar mensagem contraditória.

**Why this priority**: O hub e a nav do líder são os pontos de continuidade diária após o painel; CTAs competitivos e falta de contagem de pendências mantêm a fricção mesmo com stepper.

**Independent Test**: Abrir detalhe de avaliação em etapa conhecida e confirmar hierarquia de um CTA primário + ações secundárias e copy legível; como líder com itens pendentes no escopo, ver badge/contagem na nav sem mudança de agrupamento da sidebar; onde houver hint já existente de próximo passo em metas, confirmar coerência.

**Acceptance Scenarios**:

1. **Given** usuário no detalhe da avaliação com ação pendente, **When** visualiza a área de ações, **Then** existe exatamente um CTA primário alinhado ao próximo passo e as demais ações aparecem como secundárias.
2. **Given** o mesmo detalhe, **When** lê título/descrição/CTA, **Then** a copy descreve a ação em linguagem humana (não depende só de “etapa X”).
3. **Given** líder com aprovações, avaliações e/ou feedbacks elegíveis no seu escopo, **When** consulta a navegação lateral, **Then** vê **um único** badge/total (soma dessas fontes já elegíveis) sem alteração dos grupos de navegação já definidos.
4. **Given** superfície de metas que já exibe hint de próximo passo, **When** o usuário compara com o bloco/orientação do hub, **Then** as mensagens não se contradizem e o hint existente continua útil.

---

### User Story 3 - Menos atrito nas ações longas do ciclo (Priority: P2)

Bruno avalia o colaborador e, durante o preenchimento longo, vê progresso claro (quantas notas ainda faltam), contexto estável de quem está sendo avaliado e confirmação inequívoca de salvamento. Após uma reprovação, Ana recebe mensagem e próximo passo acionável para corrigir o que foi pedido. No fluxo de feedback, a ação que cabe ao ciente fica mais óbvia e com menos idas e voltas desnecessárias, sem mudar as regras de negócio do feedback.

**Why this priority**: Mesmo com orientação de entrada, ações longas ainda abandonam ou geram erro operacional; reduz atrito na execução sem tocar nas regras de avanço.

**Independent Test**: Percorrer avaliação do líder com itens parciais; simular reprovação e validar mensagem/próximo passo do colaborador; executar fluxo de feedback ciente e confirmar caminho mais óbvio e com hops reduzidos quando possível sem alterar regras.

**Acceptance Scenarios**:

1. **Given** líder no fluxo de avaliação com notas ainda incompletas, **When** está preenchendo, **Then** vê indicação de progresso (“faltam N notas” ou equivalente inequívoco), contexto sticky do colaborador e feedback claro de salvamento.
2. **Given** item reprovado na avaliação/ciclo, **When** o colaborador retorna ao seu ponto de entrada ou à superfície afetada, **Then** recebe mensagem compreensível e um próximo passo acionável para corrigir.
3. **Given** usuário elegível ao papel de ciente no feedback, **When** inicia ou continua o fluxo, **Then** a ação esperada fica evidente e o caminho exige menos saltos de tela do que o baseline, sem mudança nas regras de quem pode/deve ciencia.

---

### User Story 4 - RH: checklist pré-abertura de ciclo (Priority: P2)

Marina (RH/admin), antes ou no fluxo de abertura de ciclo (lista/fluxo de ciclos e pendentes de vínculo), vê uma superfície de checklist operacional que aponta bloqueadores conhecidos: usuários sem área/cargo e cargos sem competências/pesos — cada item com caminho para corrigir. A regra de quem pode abrir ciclo não é reescrita além do que já existe; se a abertura continuar permitida com pendências, os blockers permanecem evidentes para decisão consciente.

**Why this priority**: Falhas de cadastro descobertas depois da abertura geram retrabalho e suporte; checklist pré-abertura reduz atrito operacional do go-live sem inventar nova política de abertura.

**Independent Test**: Como RH, abrir lista/fluxo de ciclos com e sem bloqueadores cadastrais; verificar listagem acionável com links de correção; confirmar que abertura só segue o que a regra atual já permite (sem nova trava inventada além do existente).

**Acceptance Scenarios**:

1. **Given** RH no fluxo ou lista de ciclos/pendentes de vínculo, **When** há usuários sem área/cargo ou cargos sem competências/pesos, **Then** o checklist exibe esses bloqueadores de forma óbvia com links para corrigir.
2. **Given** o mesmo checklist sem bloqueadores relevantes, **When** RH revisa a superfície, **Then** fica claro que não há pendências operacionais listadas nesse escopo.
3. **Given** a regra vigente de abertura (permitida ou não com pendências), **When** RH tenta abrir, **Then** o comportamento de abertura permanece o já existente; o checklist é só aviso + links e não introduz trava, disable ou política nova.

---

### Edge Cases

- Usuário com mais de um papel (colaborador e líder): o Meu painel e a nav refletem o próximo passo e as pendências adequados a cada contexto sem contradizer a etapa da própria avaliação.
- Ciclo aberto sem avaliação ainda vinculada ao usuário: bloco comunica vínculo/avaliação pendente em vez de inventar etapa.
- Stepper com etapa bloqueada por regra existente (ex.: dependência de aprovação): estado “bloqueada” é distinto de “futura” e não oferece CTA primário enganoso.
- Líder sem pendências no escopo: badge/contagem ausente ou zero, sem alarme falso.
- Contagens de pendência do líder devem respeitar o mesmo escopo de visibilidade já aplicado (sem vazar fora da hierarquia).
- Checklist RH com muitos bloqueadores: lista permanece escaneável e acionável (não só um total opaco).
- Pós-reprovação quando o colaborador já corrigiu: orientação não insiste em ação já resolvida.
- Superfície sem ação disponível (somente leitura / concluído): ausência de CTA primário de avanço é intencional e explicada.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O Meu painel MUST exibir um bloco “Próximo passo” com título, uma frase de orientação e no máximo um CTA primário derivado do estado da Avaliação do usuário no ciclo aberto (ou dos estados especiais: sem ciclo, vínculo pendente, ciclo concluído para o usuário).
- **FR-001a**: O conteúdo do bloco “Próximo passo” (título, frase, rótulo do CTA e destino) MUST seguir o **contrato de apresentação** da tabela abaixo — derivado apenas do estado já existente da Avaliação/ciclo e do papel no contexto; rotas listadas são nomes de URL **já existentes** (FR-013); quando a ação primária não cabe ao papel atual, o bloco comunica espera/estado sem inventar avanço.
- **FR-002**: O Meu painel e o detalhe da avaliação MUST exibir um stepper visual das 6 etapas do ciclo (input de metas → … → feedback) com estados distintos: concluída, atual, futura e bloqueada, coerentes com o estado real da avaliação. A marcação MUST ser um **partial/component shared** em `templates/components` (mesmo markup nos dois pontos), sem estender design system Freeze/tipografia/charts (FR-014) e sem alterar estados de negócio.
- **FR-003**: O CTA primário do “Próximo passo” MUST levar o usuário à superfície correta da ação da etapa atual; pessoa nova no papel MUST conseguir identificar essa ação sem instrução verbal.

#### Contrato de apresentação — mapa etapa → orientação (somente UI)

Fonte da etapa: `Avaliacao.etapa` vigente. Destinos: URLs de negócio já existentes. Hints de reprovação em metas MUST permanecer coerentes com `_proximo_passo_pos_reprovacao` (FR-007). Copy pode ser polida na implementação desde que mantenha o mesmo significado e destino.

| Estado / etapa | Papel no contexto | Título | Frase | Rótulo CTA | Destino (url name existente) |
|----------------|-------------------|--------|-------|------------|------------------------------|
| Sem ciclo aberto | qualquer | Sem ciclo em andamento | Não há ciclo de desempenho aberto no momento. | — (sem CTA de avanço) | — |
| Vínculo / avaliação pendente | colaborador | Avaliação ainda não vinculada | Seu vínculo ao ciclo ainda não está pronto; acompanhe com o RH se necessário. | — ou Ver painel | `dashboard:personal` |
| `input_metas` | colaborador (dono) | Defina suas metas | Cadastre e ajuste as metas deste ciclo antes de enviar para aprovação. | Ir para metas | `goals:meta_list` |
| `input_metas` | líder (escopo) | Aguardando metas do time | Os colaboradores do seu escopo ainda estão na etapa de input de metas. | Ver time / metas | `goals:meta_list` ou `dashboard:team` (já existente) |
| `aprovacao_metas` | líder (ator) | Aprove as metas | Revise e aprove ou reprove as metas pendentes no seu escopo. | Revisar metas | `goals:meta_list` |
| `aprovacao_metas` | colaborador (dono) | Metas em aprovação | Aguarde a decisão do líder; se houver reprovação, corrija e reenvie. | Ver metas | `goals:meta_list` |
| `resultados` | colaborador (dono) | Atualize os resultados | Informe o progresso/resultados das metas deste ciclo. | Atualizar resultados | `goals:meta_list` |
| `resultados` | líder (escopo) | Aguardando resultados | O time ainda registra resultados das metas. | Ver metas do time | `goals:meta_list` |
| `aprovacao_resultados` | líder (ator) | Aprove os resultados | Revise e aprove ou reprove os resultados pendentes. | Revisar resultados | `goals:meta_list` |
| `aprovacao_resultados` | colaborador (dono) | Resultados em aprovação | Aguarde a decisão do líder; se houver reprovação, corrija o progresso e reenvie. | Ver resultados | `goals:meta_list` |
| `avaliacao` | colaborador (dono) | Faça a autoavaliação | Preencha as notas das competências na sua avaliação. | Autoavaliar | `reviews:self_assessment` |
| `avaliacao` | líder (ator) | Avalie o colaborador | Preencha as notas de competências do liderado nesta etapa. | Avaliar | `reviews:leader_assessment` |
| `feedback` | líder (ator) | Registre o feedback | Conduza o feedback da avaliação quando elegível pelas regras atuais. | Ir ao feedback | `reviews:feedback_create` ou `reviews:feedback_list` |
| `feedback` | colaborador (ciente) | Confirme ciência do feedback | Leia o feedback e registre ciência quando a regra atual permitir. | Dar ciência | `reviews:feedback_acknowledge` |
| Ciclo / avaliação concluída para o usuário | qualquer | Ciclo concluído para você | Não há próxima ação de etapa nesta avaliação. | Ver avaliação | `reviews:detail` |
| Hub (qualquer etapa com ação) | ator elegível | (mesmo título da linha da etapa) | (mesma frase) | (mesmo CTA; hierarquia FR-004) | `reviews:detail` como hub + CTA primário aponta ao destino da linha |
- **FR-004**: No detalhe da avaliação, MUST haver hierarquia clara: um CTA primário alinhado ao próximo passo e demais ações como secundárias.
- **FR-005**: Copy de orientação no hub da avaliação MUST usar linguagem humana da ação (o quê fazer agora), não depender apenas de jargão de número/nome técnico de etapa.
- **FR-006**: A navegação do líder MUST exibir **um único badge/total** com a soma das pendências elegíveis no escopo — **somente** as fontes já vigentes: (1) aprovações, (2) avaliações e (3) feedbacks — reutilizando as mesmas queries/regras de elegibilidade e o mesmo escopo de visibilidade já aplicados hoje; MUST NÃO inventar nova elegibilidade nem redesenhar/reordenar grupos de navegação (FR-013). Sem pendências: badge ausente ou zero (sem alarme falso).
- **FR-007**: Onde já existir hint de próximo passo em superfícies de metas, o produto MUST reutilizar ou manter coerência com essa orientação (sem mensagens contraditórias).
- **FR-008**: No fluxo de avaliação do líder, o usuário MUST ver progresso de preenchimento (notas restantes), contexto persistente do colaborador avaliado e confirmação clara de salvamento.
- **FR-009**: Após reprovação relevante ao colaborador, o sistema MUST apresentar mensagem compreensível e próximo passo acionável para correção.
- **FR-010**: O fluxo de feedback para o papel ciente MUST tornar a ação esperada óbvia e reduzir saltos de tela quando possível, sem alterar regras de quem pode/deve dar ciência.
- **FR-011**: No fluxo/lista de ciclos e pendentes de vínculo, RH MUST ver checklist operacional de bloqueadores (usuários sem área/cargo; cargos sem competências/pesos) com links para correção.
- **FR-012**: O checklist de RH MUST ser **somente avisório**: exibe bloqueadores com links de correção e MUST NÃO alterar, desabilitar ou “travar” a abertura de ciclo além da regra já existente; o controle Abrir MUST permanecer com o mesmo comportamento vigente. Se abertura permanecer permitida com pendências, os blockers MUST continuar evidentes. Qualquer proposta de soft-disable/trava nova é **fora de escopo** (FR-013 / SC-002).
- **FR-013**: A feature MUST NÃO alterar fórmulas de nota/aderência/9-box, máquina de estados / regras de avanço de etapa, AuthZ/escopo, URLs de negócio, models/migrations, nem a organização dos grupos de navegação Governança/Cadastros/Sistema.
- **FR-014**: A feature MUST reutilizar a linguagem visual e componentes já disponíveis (botão, card, badge de status, empty state / Freeze vigente), sem polish tipográfico amplo de cadastros nem extensão de design system por tipografia/charts.
- **FR-015**: Critérios de aceite desta spec MUST ser verificáveis via quickstart/roteiro escrito, sem dependência de demos verbais do processo de ciclo.

### Key Entities

- **Ciclo de desempenho**: período operacional aberto/fechado em que avaliações e etapas ocorrem.
- **Avaliação**: vínculo do colaborador ao ciclo; carrega a etapa atual e o progresso no fluxo das 6 etapas.
- **Etapa do ciclo**: uma das 6 fases sequenciais (do input de metas ao feedback); tem estados de apresentação concluída / atual / futura / bloqueada.
- **Próximo passo**: orientação derivada do estado da avaliação (ou ausência de ciclo/vínculo/conclusão) composta por título, frase e CTA opcional.
- **Pendência do líder**: item elegível no escopo do líder que exige ação (aprovação, avaliação ou feedback). O badge exibe a **soma** dessas três fontes já existentes; não é uma nova entidade de negócio.
- **Bloqueador operacional (RH)**: condição de cadastro que prejudica abertura/execução saudável do ciclo (usuário sem área/cargo; cargo sem competências/pesos).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Em amostra de 3 papéis (colaborador, líder, admin/RH), a ação correta da etapa (ou a correção de bloqueador, no caso RH) é alcançada em ≤ 2 cliques a partir do ponto de entrada principal correspondente (Meu painel, hub da avaliação/nav do líder, ou fluxo de ciclos).
- **SC-002**: Zero regressão na máquina de estados e nos testes existentes de escopo e etapas: nenhuma alteração de comportamento de avanço/reprovação/cálculo/AuthZ é introduzida por esta feature.
- **SC-003**: Todos os critérios de aceite das user stories desta spec são verificáveis por quickstart/roteiro escrito, sem necessidade de demos verbais do processo de ciclo.
- **SC-004**: Em teste com pessoa nova no papel (colaborador ou líder), ≥ 90% identifica corretamente a próxima ação só com a UI (bloco “Próximo passo” + stepper/hub), sem coaching.
- **SC-005**: Líder com pendências no escopo reconhece a existência e a magnitude aproximada das pendências pela nav em ≤ 5 segundos após carregar a área autenticada.
- **SC-006**: Em viewport desktop (aceite primário), bloco “Próximo passo”, stepper, hub com hierarquia de CTAs, badge do líder e checklist RH são utilizáveis conforme as user stories. Em viewport mobile, as mesmas superfícies permanecem **legíveis** (conteúdo empilhado verticalmente); o stepper MAY compactar (números/rótulos curtos) sem exigir paridade visual pixel-a-pixel com o desktop.

## Assumptions

- Máquina de estados, AuthZ/escopo, fórmulas e URLs de negócio já estáveis em UAT permanecem a fonte da verdade; esta feature apenas apresenta orientação derivada desses estados.
- As 6 etapas do ciclo já estão definidas no produto; o stepper mapeia estados existentes, não inventa etapas.
- “Meu painel” corresponde ao dashboard pessoal já usado como home do usuário autenticado no papel colaborador/líder.
- Hints existentes de próximo passo em metas (quando presentes) são a referência de copy a reaproveitar/alinhar.
- Badge do líder = soma única das pendências elegíveis já determinadas pelas regras/escopo atuais (aprovações + avaliações + feedbacks); apresentação apenas.
- Checklist RH lista bloqueadores operacionais conhecidos e priorizados no input (usuários sem área/cargo; cargos sem competências/pesos); não amplia para import em massa nem novos cadastros.
- Checklist RH é informativo/acionável (aviso + links) e não cria trava nem soft-disable de abertura; se a regra vigente permitir abrir com pendências, isso permanece.
- Aceite de apresentação: desktop é primário; mobile é legível (stack vertical), stepper compactável — sem paridade pixel.
- Stack e apresentação: reutilizar padrões atuais do produto (templates + interações progressivas + utilitários de estilo já adotados); stepper como partial shared em `templates/components`; sem novas bibliotecas de frontend nem extensão do design system.
- Fora de escopo: continuação do polish 007 (tipografia/charts/9-box), import de colaboradores, Docker/deploy, redesign de auth/login, mudança de grupos de navegação da 004, novas regras de avanço de etapa.

## Out of Scope

- Novas regras de avanço de etapa ou alteração da máquina de estados
- Mudanças em cálculo de nota, aderência ou 9-box
- Alteração de AuthZ, escopo hierárquico ou models/migrations
- Mudança de URLs de negócio
- Redesign ou reorganização dos grupos de navegação (Governança / Cadastros / Sistema)
- Import de colaboradores; Docker/deploy; redesign de autenticação/login
- Polish visual amplo de cadastros; extensão do Freeze por tipografia/charts/9-box (feature 007)
- Novas bibliotecas de frontend
