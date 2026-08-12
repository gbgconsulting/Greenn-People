# Feature Specification: Redesign Visual por Persona (Painéis Gerenciais)

**Feature Branch**: `009-persona-visual-redesign`

**Created**: 2026-08-10

**Status**: Draft

**Input**: User description: "Redesign visual das telas do Greenn People por persona (Colaborador, Gestor/Líder, Admin RH), reaproveitando o Design System Freeze v2 — charts modernos (Chart.js), painéis gerenciais do líder, visão gerencial de ciclos para RH, consistência visual do colaborador (P2) e polish de cadastros/sistema (P3); reabre formalmente 3 pontos do Freeze v2; sem alterar máquina de estados, AuthZ, fórmulas nem trocar stack/lib de gráficos."

## Declaração do Problema (O Porquê)

O Freeze v2 e a orientação de próximo passo (spec `008-cycle-guidance-ux`) estabilizaram tipografia, componentes e “o que fazer agora” nos hubs principais. O que ainda falta é **visão gerencial**: dashboards e listas continuam pobres visualmente (gráficos de série única em verde, tabelas como superfície principal) e o Admin RH não tem um painel consolidado de um ciclo — o progresso aparece isolado e a lista de ciclos permanece operacional, não gerencial. Esta feature eleva a apresentação por persona (colaborador → clareza; líder → onde cada pessoa está; RH → ciclo como painel) sem mudar regras de negócio, AuthZ ou a stack obrigatória.

## Clarifications

### Session 2026-08-11

- Q: Reabertura Charts polish (DS v2) — tipos aceitáveis por propósito e limite de paleta além da Status Triad? → A: Catálogo por propósito (doughnut+valor central para aderência; barras horizontais para ranking de pendências; área para tendência; multi-série quando o shape já existir) + Status Triad intacta; paleta ampliada/gradientes só no acabamento Chart.js, sem novas cores semânticas de status.
- Q: Reabertura da exclusão de `dashboard/structure.html` — métrica principal da visualização gerencial? → A: Cobertura por área/cargo como visual principal; lacunas/pendências como destaque secundário acionável.
- Q: Formato da visão gerencial de Ciclos (Admin RH) — detalhe novo vs seção na lista? → A: Página de detalhe nova `cycles/<pk>/` linkada a partir de `cycle_list.html`, com escopo de segurança/AuthZ integralmente respeitado (`ScopedObjectMixin` / regras já existentes).
- Q: Novas visualizações exigem agregação nova vs `chart_payloads.py` e Celery por volume? → A: Preferir reuso/composição dos payloads existentes; permitir agregação leve síncrona no request; Celery/snapshot apenas se medição mostrar peso real (sem async prematuro).
- Q: Esforço aceitável em cadastros/sistema (story 5 / P3) até o prazo 03/09? → A: Sim — P3 pode ficar sem polish se o tempo não sobrar; P1+P2 bastam para aceite do release.

## Decisões de produto — Reabertura formal do Freeze v2

Esta feature **reabre formalmente** três pontos do Freeze v2 (`docs/design-system.md`), por decisão explícita de produto. A documentação canônica DEVE ser atualizada na mesma entrega que implementar o contrato visual correspondente.

| # | Ponto reaberto | Decisão de produto | Limite |
|---|----------------|---------------------|--------|
| A | Seção **Charts polish (DS v2)** | Permitir **novos tipos expressivos** sob catálogo por propósito: **doughnut com valor central** (aderência), **barras horizontais** (ranking de pendências/atenção), **área** (tendência temporal), **multi-série** quando o shape já existir; e **paleta ampliada** / gradientes apenas no acabamento Chart.js (não novas cores semânticas de status). | Continua Chart.js 4.5.1; **sem** troca de biblioteca; **sem** inventar métricas de negócio; Status Triad de negócio e shape de dados (`has_data` / `labels` / `values` / `series` / `colors` / equivalentes já consumidos) **permanecem**. |
| B | Exclusão de `dashboard/structure.html` do slice de gráficos | **Incluir** a estrutura organizacional no escopo de visualização gerencial. Métrica principal: **cobertura por área/cargo**; lacunas/pendências entram como **destaque secundário** acionável (não como eixo semântico principal da tela). | Continua sem inventar métrica fora do escopo de AuthZ; estrutura (cobertura) vs aderência permanece semanticamente distinta. |
| C | Novo padrão canônico **“painel gerencial”** | Documentar e padronizar composição **KPI(s) + visualização + tabela de drill-down** como padrão Freeze para superfícies gerenciais (líder e RH). | Tabela deixa de ser visão principal; permanece como detalhe/drill-down. Reutiliza tipografia, card/KPI, table-frame e empty states v2. |

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Charts modernos e gerenciais (cross-persona) (Priority: P1)

Ana (colaboradora), Bruno (líder) e Marina (RH) abrem seus painéis (`Meu painel`, time e admin) e encontram gráficos com hierarquia visual clara: paleta ampliada (não só uma família de verde), tipos mais expressivos onde o dado já existe (área, doughnut com valor central, barras horizontais comparativas, multi-série quando aplicável) e mini-KPIs / legendas ricas ao lado do gráfico. Os números e categorias continuam os mesmos de antes; a mudança é de leitura e presença gerencial. Em ausência de dados, o empty state permanece honesto.

**Why this priority**: É a fundação visual para as stories 2 e 3; sem charts ricos, os painéis gerenciais continuam tabelas com “decoração”.

**Independent Test**: Abrir as três superfícies de dashboard com dados e sem dados; confirmar tipos/legenda/KPI vizinhos e empty honesto; validar que categorias/valores de negócio e Status Triad não mudaram de significado.

**Acceptance Scenarios**:

1. **Given** usuário no painel pessoal, de time ou admin com dados de gráfico disponíveis, **When** visualiza cada bloco de gráfico, **Then** o gráfico apresenta hierarquia visual clara (paleta ampliada e/ou tipo mais expressivo que a barra monocor de série única) e mini-KPI ou legenda rica próxima ao gráfico.
2. **Given** o mesmo shape de dados e Status Triad de negócio de antes, **When** compara valores/categorias exibidos com o baseline, **Then** não há nova métrica inventada nem troca do significado das categorias de status.
3. **Given** gráfico sem dados (`has_data` falso ou equivalente), **When** a superfície carrega, **Then** aparece empty state honesto (sem série inventada) no mesmo padrão visual do produto.
4. **Given** viewport estreito (~375px de largura útil), **When** consulta o gráfico, **Then** rótulos, legenda e valor central (quando houver) permanecem consultáveis sem depender de SPA ou lib nova.

---

### User Story 2 - Painéis gerenciais do Líder/Gestor (Priority: P1)

Bruno abre o painel do time, a estrutura e a aderência e, no primeiro olhar, responde “onde cada pessoa está” e “o que fazer em seguida” por meio de KPIs, distribuição visual (etapa/área conforme a superfície), ranking ou destaque de quem precisa de atenção e links de ação direta — reutilizando o padrão de charts da story 1. A tabela permanece disponível como drill-down/detalhe, não como a única visão.

**Why this priority**: Líderes hoje operam listas; a virada gerencial do produto depende dessa mudança de composição.

**Independent Test**: Como líder com time no escopo, abrir time / estrutura / aderência; confirmar visão gerencial (KPI + visual + ações) antes da tabela; clicar ação/drill-down e chegar à superfície correta sem mudança de regra de escopo.

**Acceptance Scenarios**:

1. **Given** líder com pessoas no escopo e dados suficientes, **When** abre o painel do time, **Then** vê composição de painel gerencial (KPIs + visualização + caminho de ação) respondendo “onde o time está” antes de depender da tabela.
2. **Given** a mesma sessão nas superfícies de estrutura e aderência, **When** observa o layout, **Then** cada uma aplica o padrão de painel gerencial apropriado ao seu propósito (estrutura/cobertura vs aderência), sem regressão de escopo (só vê o que já podia ver).
3. **Given** pessoas que precisam de atenção (pendências / lacunas já existentes no domínio), **When** o líder consulta o painel, **Then** encontra destaque ou ranking acionável e links que levam à ação correta já disponível no produto.
4. **Given** necessidade de detalhe por pessoa/linha, **When** usa a tabela/listagem, **Then** ela funciona como drill-down sob o painel, não como substituto da visão principal.

---

### User Story 3 - Visão gerencial de Ciclos para Admin RH (Priority: P1)

Marina (Admin RH) deixa de depender só da lista de ciclos + checklist avisório e do progresso isolado no dashboard admin. Ela acessa uma **página de detalhe dedicada** (`cycles/<pk>/`, alcançável a partir de `cycle_list.html`) que reúne progresso por etapa, cobertura por área/cargo, aderência e o checklist de blockers já existente (spec `008`) num único painel gerencial — com AuthZ e escopo de segurança integralmente respeitados (sem relaxar `ScopedObjectMixin` / regras existentes).

**Why this priority**: RH não tem hoje um “quadro de comando” do ciclo; é o maior gap gerencial da persona Admin.

**Independent Test**: A partir da lista de ciclos, abrir o detalhe gerencial de um ciclo com e sem blockers; confirmar seções consolidadas e links de correção do checklist; confirmar que abrir/fechar ciclo e regras de blockers não mudam de comportamento além da apresentação.

**Acceptance Scenarios**:

1. **Given** Admin RH na lista de ciclos, **When** escolhe um ciclo para visão gerencial, **Then** acessa a página de detalhe `cycles/<pk>/` (não accordion/seção expandida ad hoc na lista), com autorização de detalhe validada no backend.
2. **Given** ciclo com dados de progresso/cobertura/aderência disponíveis no domínio, **When** a visão carrega, **Then** exibe progresso por etapa, cobertura por área/cargo e aderência no mesmo painel, no padrão KPI + visualização (+ drill-down quando necessário).
3. **Given** ciclo com blockers do checklist pré-abertura (spec `008`), **When** RH consulta a visão, **Then** o checklist avisório aparece no mesmo painel com caminhos de correção, sem passar a travar abertura além da regra já existente.
4. **Given** ausência de dados em uma das seções, **When** a visão renderiza, **Then** empty states honestos aparecem por seção sem inventar cobertura ou progresso.
5. **Given** usuário sem permissão/escopo para o ciclo, **When** tenta abrir o detalhe, **Then** o acesso é negado pelas mesmas regras de AuthZ já vigentes (sem bypass pela nova superfície).

---

### User Story 4 - Consistência visual do Colaborador (Priority: P2)

Ana navega nas telas mais antigas do colaborador (expectativas/metas, lista de metas, avaliações, PDI, minha classificação) e encontra o mesmo padrão visual v2 (tipografia, cards, table-frame, empty states) das superfícies já refinadas, com reforço de “o que fazer agora” alinhado ao guidance da spec `008` — sem duplicar o bloco de orientação onde ele já existe no hub.

**Why this priority**: Fecha inconsistência percebida após o Freeze v2 / 008; impacto alto de percepção, mas depende menos das stories 1–3.

**Independent Test**: Percorrer as cinco superfícies listadas como colaborador; confirmar tokens/padrões v2 e indicação clara de próximo passo ou empty honesto; confirmar ausência de segundo “Próximo passo” contraditório onde o hub já orienta.

**Acceptance Scenarios**:

1. **Given** colaborador em cada uma das telas legadas listadas no escopo P2, **When** carrega a página, **Then** tipografia, cards/KPI, table-frame e empty states seguem o Freeze v2 (pós-reabertura documentada).
2. **Given** ação pendente relevante naquela superfície, **When** o colaborador lê a página, **Then** fica claro o que fazer agora (CTA ou copy de orientação), sem duplicar o bloco de guidance do hub de forma redundante/conflitante.
3. **Given** lista ou recurso vazio, **When** a tela renderiza, **Then** empty state acionável/honesto aparece no padrão do produto.

---

### User Story 5 - Cadastros e Sistema (Priority: P3)

Marina e demais admins usam áreas, cargos, usuários, competências, auditoria e notificações com o mesmo polish visual (tipografia, table-frame, empty states). **Best-effort até 03/09**: entrega apenas se houver tempo após P1/P2; ausência de polish em P3 **não** bloqueia o aceite do release.

**Why this priority**: Superfícies de cadastro/sistema são secundárias à narrativa gerencial do ciclo; polish de consistência, não fundação.

**Independent Test**: Se entregue — abrir cada superfície P3 com itens e vazia; confirmar chrome visual alinhado ao Freeze sem mudança de regras de CRUD/AuthZ. Se omitida por prazo — confirmar que P1+P2 passaram nos critérios de aceite do release.

**Acceptance Scenarios**:

1. **Given** tempo disponível após P1/P2 até 03/09, **When** as telas de cadastro/sistema do escopo são visitadas, **Then** exibem tipografia, table-frame e empty states consistentes com o Freeze.
2. **Given** as mesmas telas (quando polishadas), **When** o usuário executa fluxos já existentes, **Then** comportamento de negócio e permissões permanece inalterado.
3. **Given** tempo esgotado após P1/P2 antes de 03/09, **When** o release é avaliado, **Then** a ausência de polish P3 NÃO falha o aceite do release.

---

### Edge Cases

- Dashboard/painel com escopo vazio (líder sem subordinados; ciclo sem avaliações): empty gerencial honesto, sem rankings inventados.
- Dados parciais (só uma série/etapa preenchida): gráfico e KPIs mostram o que existe; seções sem dado usam empty local.
- Ciclo em rascunho / sem abertura vs ciclo aberto vs ciclo encerrado: a visão gerencial de ciclo adapta copy e seções sem alterar quem pode abrir/fechar.
- Conflito potencial com guidance 008: esta feature reforça orientação visual nas superfícies, mas **não** reimplementa nem contradiz o mapa etapa → CTA da 008.
- Agregações novas para painéis: preferir reuso/composição síncrona leve; Celery/snapshot só se medição mostrar peso real — sem degradar a navegação além do padrão já aceito do produto.
- Viewport estreito: painel gerencial empilha KPI → visual → tabela; charts permanecem legíveis.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O produto MUST apresentar gráficos dos painéis pessoal, de time e admin com acabamento gerencial moderno, usando o catálogo por propósito (doughnut+valor central para aderência; barras horizontais para ranking de pendências; área para tendência; multi-série quando o shape já existir) e paleta ampliada/gradientes apenas no acabamento Chart.js — mantendo o significado das métricas e do Status Triad já existentes (sem novas cores semânticas de status).
- **FR-002**: O contrato de dados consumido pelos gráficos (presença de dados, rótulos, valores, séries, cores e equivalentes já usados) MUST permanecer compatível; polish visual NÃO inventa métrica de negócio.
- **FR-003**: Em dados ausentes, blocos de gráfico e seções de painel MUST exibir empty state honesto, sem preencher séries fictícias.
- **FR-004**: Superfícies do líder (time, estrutura, aderência) MUST adotar o padrão de painel gerencial (KPI + visualização + tabela/drill-down), respondendo “onde cada pessoa está” e “o que fazer” antes de depender da listagem.
- **FR-005**: Painéis do líder MUST incluir destaque ou ranking acionável de quem precisa de atenção e links para ações já disponíveis no produto, respeitando o escopo de visibilidade do usuário autenticado.
- **FR-006**: A estrutura organizacional MUST entrar no escopo de visualização gerencial com **cobertura por área/cargo** como métrica/visual principal e lacunas/pendências como destaque secundário acionável — sem misturar semanticamente cobertura (estrutura) com aderência nem inventar métrica fora do AuthZ.
- **FR-007**: Admin RH MUST ter uma **página de detalhe** consolidada de **um** ciclo em `cycles/<pk>/` (alcançável a partir de `cycle_list.html`, não como accordion/inline na lista), reunindo progresso por etapa, cobertura por área/cargo, aderência e o checklist de blockers já existente; a view MUST aplicar as mesmas regras de AuthZ/escopo já estabelecidas (ex.: `ScopedObjectMixin` ou equivalente).
- **FR-008**: O checklist de blockers na visão de ciclo MUST permanecer avisório quanto a travar abertura (comportamento alinhado à spec `008`), com caminhos de correção evidentes.
- **FR-009**: Telas P2 do colaborador listadas no escopo MUST consumir tipografia, cards, table-frame e empty states do Freeze v2 e comunicar “o que fazer agora” sem duplicar/conflitar com o guidance da spec `008`.
- **FR-010**: Telas P3 de cadastros/sistema (áreas, cargos, usuários, competências, auditoria, notificações) SHOULD receber o mesmo polish visual **somente** se P1 e P2 estiverem concluídos com tempo restante até **03/09**; a ausência de polish P3 MUST NOT bloquear o aceite do release.
- **FR-011**: A documentação canônica do Design System MUST registrar a reabertura dos pontos A/B/C (charts expressivos + paleta; inclusão da estrutura; padrão painel gerencial) na mesma entrega do contrato visual.
- **FR-012**: Esta feature MUST NOT alterar máquina de estados de ciclo/avaliação, regras de aprovação/reprovação, fórmulas de cálculo de nota, nem a lógica de escopo/autorização já estabelecida.
- **FR-013**: Qualquer nova agregação para painéis gerenciais MUST respeitar escopo resolvido no backend e imutabilidade de histórico; preferir reuso/composição de `chart_payloads` (ou equivalente) já existentes; agregação **leve** MAY permanecer síncrona no request; processamento assíncrono/snapshot (Celery) MUST ser adotado somente quando o cálculo for comprovadamente pesado — não de forma prematura.
- **FR-014**: A apresentação MUST permanecer em templates server-rendered com interações progressivas já adotadas pelo produto; MUST NOT introduzir SPA, API REST como superfície primária desta feature, nem nova biblioteca de gráficos.

### Key Entities

- **Painel gerencial**: Composição canônica de indicadores (KPIs), visualização (gráfico/distribuição) e detalhe tabular/drill-down, com ações diretas; aplica-se a líder e RH.
- **Bloco de gráfico**: Unidade de visualização com título, representação gráfica, legenda/mini-KPI e empty state; consome shape e Status Triad existentes.
- **Visão gerencial de ciclo**: Superfície de detalhe de um ciclo para Admin RH, consolidando progresso, cobertura, aderência e checklist operacional.
- **Destaque de atenção**: Subconjunto de pessoas/itens já elegíveis no domínio que o líder deve priorizar (pendências, lacunas), apresentado de forma visual e acionável.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Em revisão guiada com 5 líderes, ≥ 80% identificam corretamente “onde o time está” e a próxima ação prioritária em até 30 segundos no painel do time, **sem** depender de escanear a tabela linha a linha como primeira estratégia.
- **SC-002**: Em revisão guiada com 5 Admins RH, ≥ 80% localizam progresso do ciclo, cobertura e blockers na visão consolidada em até 45 segundos a partir da lista de ciclos.
- **SC-003**: Em comparação side-by-side (antes/depois) dos três painéis com gráfico, 100% dos gráficos com dados exibem hierarquia visual perceptível (não apenas barra monocor de série única) e empty states continuam honestos quando sem dados.
- **SC-004**: Em checklist de regressão de negócio, 0 mudanças detectáveis em avanços de etapa, aprovação/reprovação, notas calculadas e conjunto de usuários/visíveis por papel em cenários de teste fixos.
- **SC-005**: Nas 5 telas P2 do colaborador, 100% passam checklist visual Freeze (tipografia + table-frame/empty onde aplicável) e um avaliador independente consegue declarar “o que fazer agora” sem briefing verbal.
- **SC-006**: Após a entrega das stories P1, o Design System documentado reflete explicitamente os três pontos reabertos (A/B/C) e o padrão de painel gerencial é referenciável por outras telas.
- **SC-007**: Em viewport ~375px, as superfícies P1 permanecem utilizáveis (KPI/visual/tabela empilhados; gráficos legíveis) sem exigir zoom horizontal para a mensagem principal.

## Assumptions

- Chart.js 4.5.1 permanece a única biblioteca de gráficos; tipos novos são opções/configurações dessa lib, não troca de stack.
- Stack de apresentação permanece Django Templates + HTMX + Tailwind, alinhada à Constituição (Django-first, sem DRF nesta feature).
- “Mesma Status Triad e mesmo shape de dados” na story 1 cobre polish e apresentação; stories 2–3 podem **agregar/compor** dados já existentes no backend (ou snapshots) para KPIs/rankings via payloads existentes ou agregação leve síncrona, desde que FR-012/FR-013 sejam respeitados; Celery só sob evidência de peso.
- A visão gerencial de ciclo é uma **página de detalhe nova** em `cycles/<pk>/` (não accordion nem seção expandida em `cycle_list.html`), linkada a partir da lista de ciclos; a lista continua existindo para inventário/operações; AuthZ/escopo de detalhe permanecem íntegros.
- Guidance da spec `008` (Próximo passo, stepper, checklist avisório, badge de pendências) é **pré-requisito consumido**, não reimplementado; esta feature reforça clareza visual e painéis, sem novo mapa etapa→CTA.
- P3 é best-effort até **03/09**: pode sair do release sem polish se o tempo se esgotar após P1+P2, **sem** bloquear o aceite das stories P1/P2.
- Desktop é aceite primário; mobile precisa ser legível (empilhamento), não redesenho dedicado.
- Evidência before/after (capturas) das superfícies P1 será produzida na implementação para validar SC-003/SC-006.

## Out of Scope

- Alterar navegação de grupos do shell, login/`base_auth`, ou reabrir tipografia display/UI além do já definido no Freeze v2 (exceto os três pontos A/B/C desta feature).
- Trocar biblioteca de gráficos, introduzir SPA/front separado ou Django REST Framework.
- Mudar máquina de estados, AuthZ (`get_visible_users` / `ScopedObjectMixin`), fórmulas de nota ou política de abertura de ciclo.
- Redesign da matriz 9-box (já coberta por polish em features anteriores), salvo consumo incidental de tokens.
- Novas métricas de negócio cujo significado não exista hoje no domínio (ex.: score “saúde do ciclo” inventado sem definição de produto).
