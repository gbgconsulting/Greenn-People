# Feature Specification: 9-box Interativa (Matriz de Talentos)

**Feature Branch**: `006-ninebox-interativa`

**Created**: 2026-07-31

**Status**: Draft

**Input**: User description: "Transformar a matriz 9-box existente (estática) em superfície interativa para admin: drawer in-matrix para inspecionar/editar potencial e visibilidade, drag-and-drop para reposicionar potencial com persistência e feedback, mantendo leitura no escopo para líder/gerente, sem novas fórmulas, sem SPA/DRF, consumindo Freeze 004."

## Declaração do Problema (O Porquê)

A matriz 9-box já classifica talentos (desempenho derivado da nota do líder, potencial definido pelo admin, quadrante calculado) e é consultável com filtros e escopo. Porém é estática: para ajustar potencial ou liberar/ocultar a classificação ao colaborador, o admin precisa sair da grade para a página de classificação ou para ações de página completa. Isso quebra o fluxo de calibração — não dá para reposicionar pessoas na grade nem inspecionar/editar sem navegar embora. A matriz precisa passar de consultiva a operacional para quem já tem permissão de classificar, sem afrouxar regras de negócio nem o gate de visibilidade ao colaborador.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Admin calibra potencial e visibilidade via drawer in-matrix (Priority: P1)

Marina (admin DP/RH) está na matriz 9-box filtrada (ciclo, área, cargo). Ela seleciona uma pessoa em uma célula; abre-se um painel lateral (drawer) na mesma página com nome, área/cargo, desempenho, potencial, quadrante e o estado Visível/Oculto ao colaborador. Ela altera o potencial, salva, e/ou libera/oculta a classificação — sem navegar para a página `classify` como caminho principal. A grade e o drawer refletem o resultado com feedback claro de sucesso ou erro; loading não é confundido com sucesso silencioso.

**Why this priority**: Remove a maior fricção do fluxo atual (ida e volta para `classify`/toggle full-page). É o MVP demonstrável sozinho, mesmo sem drag.

**Independent Test**: Com admin autenticado, ciclo com classificações, abrir a matriz, selecionar uma pessoa, alterar potencial e toggle de visibilidade no drawer, verificar persistência e atualização da UI sem full page reload obrigatório; com potencial inválido ou falha, verificar mensagem de erro honesta.

**Acceptance Scenarios**:

1. **Given** admin autenticado e matriz com pessoas classificadas no ciclo filtrado, **When** seleciona uma pessoa em uma célula, **Then** o drawer abre na mesma página exibindo nome, área/cargo (quando disponíveis), desempenho, potencial, quadrante e estado de visibilidade ao colaborador.
2. **Given** drawer aberto para uma pessoa no escopo, **When** admin altera o potencial (1–3) e salva, **Then** o novo potencial é persistido, o quadrante é recalculado conforme as regras vigentes, e a pessoa aparece na célula correta da grade sem exigir navegação para outra página.
3. **Given** drawer aberto, **When** admin libera ou oculta a classificação ao colaborador, **Then** o estado Visível/Oculto é persistido e refletido no drawer e na grade (badge ou equivalente), sem full page reload obrigatório.
4. **Given** falha de validação ou de persistência, **When** admin tenta salvar ou togglear, **Then** vê mensagem de erro compreensível em português e o estado anterior permanece até correção — sem sucesso silencioso.
5. **Given** líder, gerente ou colaborador (não admin), **When** tenta acionar edição/salvar/toggle via UI ou requisição direta, **Then** a ação é negada no backend; a UI de escrita não é oferecida a esses papéis na matriz.

---

### User Story 2 - Admin reposiciona potencial por drag-and-drop na grade (Priority: P2)

Marina calibra várias pessoas arrastando o cartão/identificador de cada uma entre células da grade 3×3. Ao soltar, apenas o **potencial** muda (eixos alinhados à regra vigente); o **desempenho** continua derivado da nota do líder e não é inventado pelo arraste. A grade atualiza a célula de origem e destino com feedback imediato; em erro (permissão, escopo, potencial inválido, conflito de eixo), a pessoa volta à posição coerente e o erro é comunicado.

**Why this priority**: Acelera calibração em lote visual; depende do mesmo modelo de persistência do drawer (P1) e da política clara “drag = só potencial”.

**Independent Test**: Com admin, arrastar pessoa para célula com potencial diferente (mesma faixa de desempenho da pessoa), verificar persistência do potencial e novo quadrante; tentar soltar em célula cuja faixa de desempenho não corresponde à nota da pessoa e verificar rejeição/snap sem alterar desempenho derivado; tentar como não-admin e verificar falha no backend.

**Acceptance Scenarios**:

1. **Given** admin na matriz interativa e pessoa com desempenho derivado D e potencial P, **When** arrasta e solta em célula com o mesmo desempenho D e potencial P′ válido (1–3), **Then** o potencial passa a P′, o quadrante é recalculado pelas regras vigentes, e a UI move a pessoa para a nova célula com feedback de sucesso ou loading honesto até confirmar.
2. **Given** a mesma pessoa, **When** admin tenta soltar em célula cuja faixa de desempenho difere do desempenho derivado da nota, **Then** o sistema NÃO altera o desempenho derivado; a ação é rejeitada ou a pessoa é reposicionada na célula coerente (desempenho derivado + potencial pretendido, se aplicável), com feedback claro de que só o potencial é editável por arraste.
3. **Given** operação de drag em andamento ou recém-solta, **When** a persistência falha (rede, validação, permissão), **Then** a pessoa permanece ou retorna à posição anterior coerente e o erro é exibido — sem sucesso silencioso.
4. **Given** usuário sem papel admin, **When** tenta mover pessoa (UI ou requisição), **Then** nenhuma mudança é persistida; a UI não oferece handle de arraste para escrita.
5. **Given** viewport onde drag é inadequado (ex.: touch/mobile), **When** admin precisa alterar potencial, **Then** o drawer (ou formulário equivalente in-matrix) permanece disponível como caminho completo de edição — drag pode degradar sem bloquear a calibração.

---

### User Story 3 - Líder/gerente leem a matriz interativa no escopo; a11y e estados honestos (Priority: P3)

Um líder ou gerente abre a matriz, aplica filtros de ciclo/área/cargo e vê apenas pessoas do seu escopo hierárquico. Pode abrir o drawer em modo somente leitura para inspecionar detalhe (nome, área/cargo, desempenho/potencial/quadrante) sem controles de salvar potencial ou liberar/ocultar. Empty e loading states são honestos. O drawer é operável por teclado/foco; informação das células não depende só da cor.

**Why this priority**: Consome a mesma superfície interativa sem expandir poderes; fecha acessibilidade mínima e clareza para quem calibra visualmente mas não edita.

**Independent Test**: Com líder autenticado, abrir matriz e drawer de uma pessoa do escopo (sem ações de escrita); confirmar ausência de pessoas fora do escopo; com escopo/filtro vazio, empty state; navegar drawer por teclado; verificar rótulos além da cor nas células.

**Acceptance Scenarios**:

1. **Given** líder/gerente autenticado, **When** abre a matriz com filtros, **Then** vê apenas pessoas do escopo autorizado e filtros ciclo/área/cargo continuam aplicando; interação não revela pessoas fora do escopo.
2. **Given** líder/gerente, **When** seleciona uma pessoa, **Then** pode inspecionar no drawer em somente leitura (sem salvar potencial nem toggle de visibilidade).
3. **Given** filtro ou escopo sem pessoas a exibir, **When** a matriz renderiza, **Then** empty state claro aparece; loading não é apresentado como “grade vazia definitiva” de forma enganosa.
4. **Given** usuário em desktop com teclado, **When** abre e fecha o drawer, **Then** o foco é gerenciável (entrar no painel, fechar, retornar de forma previsível) sem armadilha de foco.
5. **Given** células da grade coloridas por quadrante, **When** qualquer papel consulta a matriz, **Then** há rótulo/texto/alternativa além da cor para identificar a posição (eixos desempenho × potencial ou nome do quadrante).

---

### Edge Cases

- Pessoa sem classificação ainda no ciclo: admin pode iniciá-la via drawer (potencial + regras vigentes) se o produto já permitir classificação; caso contrário, empty/ação explícita “classificar” no drawer sem inventar desempenho.
- Colaborador sem `visivel_ao_colaborador`: continua sem ver a própria 9-box; esta feature não torna a matriz visível por padrão.
- Tentativa IDOR (mover/editar/toggle pessoa fora do escopo ou sem papel admin): backend nega; UI não autoriza.
- Papéis cumulativos (admin + líder): ações de escrita seguem o poder admin; leitura de escopo não amplia dados além do já permitido pela matriz atual.
- Concorrência: dois admins editando a mesma pessoa — último salvamento válido prevalece; feedback reflete o estado persistido ao concluir a ação do usuário.
- Filtros ativos durante drag/drawer: após salvar, a pessoa permanece sujeita aos filtros; se deixar de atender o filtro, some da vista filtrada de forma coerente (não “vaza” em outra célula).
- Ciclo fechado ou restrição já existente que impeça edição: respeitar regra vigente; mensagem clara se edição for bloqueada.
- Mobile/touch: matriz consultável; calibração completa via drawer/formulário se drag for degradado.
- Drag cancelado (Esc / soltar fora da grade): nenhuma persistência; posição visual restaurada.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: A matriz 9-box MUST permitir ao admin abrir um drawer (ou painel lateral equivalente) in-matrix ao selecionar uma pessoa, exibindo identidade, contexto organizacional básico (área/cargo quando disponíveis), desempenho, potencial, quadrante e estado de visibilidade ao colaborador.
- **FR-002**: No drawer, o admin MUST poder salvar um novo potencial válido (1–3) e MUST poder liberar/ocultar a classificação ao colaborador, persistindo via os mesmos serviços/regras de negócio já usados para classificação e toggle — sem full page reload obrigatório como caminho principal.
- **FR-003**: Após salvar potencial, o sistema MUST recalcular o quadrante segundo as regras vigentes e MUST refletir a pessoa na célula correta da grade; o desempenho MUST permanecer derivado da nota do líder (não editável por esta feature como valor livre).
- **FR-004**: A matriz MUST oferecer ao admin reposicionamento por drag-and-drop entre células que altere somente o **potencial**; arraste MUST NOT alterar nem substituir o desempenho derivado. Tentativas de soltar em célula incompatível com o desempenho derivado MUST ser rejeitadas ou corrigidas para a célula coerente, com feedback explícito.
- **FR-005**: Atualizações de célula/matriz/drawer MUST fornecer feedback imediato e honesto (loading, sucesso, erro em português); MUST NOT reportar sucesso quando a persistência falhou.
- **FR-006**: Somente admin MUST poder classificar, editar potencial, arrastar para persistir ou alterar visibilidade; líder/gerente MUST ver a matriz (e opcionalmente o drawer somente leitura) no escopo, sem ações de escrita; colaborador MUST continuar vendo apenas classificação liberada pelas regras vigentes.
- **FR-007**: Filtros existentes (ciclo, área, cargo) MUST continuar funcionando; interações MUST NOT revelar ou permitir edição de pessoas fora do escopo resolvido no backend.
- **FR-008**: Autorização e escopo MUST ser aplicados 100% no backend; a UI MUST NOT ser a fonte de autorização (incluindo tentativas IDOR de mover/editar/toggle).
- **FR-009**: A feature MUST NOT alterar fórmulas ou políticas de `derive_desempenho`, cálculo de quadrante (além de recalcular após potencial válido), faixas de nota, nem tornar a 9-box visível por padrão ao colaborador.
- **FR-010**: Em viewports onde drag for inadequado (notavelmente mobile/touch), a calibração completa MUST permanecer possível via drawer/formulário in-matrix; degradação de drag é aceitável.
- **FR-011**: Acessibilidade mínima MUST incluir: operação do drawer por teclado/foco; alternativa não-pointer ao drag (edição de potencial no drawer); informação de células/quadrantes não depender apenas da cor.
- **FR-012**: A feature MUST consumir tokens e padrões da fundação visual Freeze 004 (badges, botões, empty states, padrões de modal/drawer se existirem); MUST NOT redesenhar shell/nav/topbar/marca nem reabrir polish amplo de design system (pós-006).
- **FR-013**: A página dedicada de classificação (`classify`) MAY permanecer como fallback, mas MUST deixar de ser o caminho principal de calibração para o admin após esta feature.
- **FR-014**: Entrega MUST ser fatiável: (1) drawer + edição/toggle in-matrix (MVP), (2) drag-and-drop com persistência, (3) refinamentos de leitura para líder/gerente + a11y/empty — de modo que o slice 1 seja utilizável sozinho.

### Key Entities

- **Classificação de Talento (na matriz)**: Associação pessoa × ciclo com desempenho derivado, potencial definido pelo admin, quadrante calculado e flag de visibilidade ao colaborador.
- **Célula da Grade 3×3**: Posição na matriz identificada pelo par desempenho × potencial (ou equivalente nomeado do produto); contém zero ou mais pessoas do conjunto filtrado/escopo.
- **Drawer in-matrix**: Painel lateral na página da matriz para inspecionar e, se admin, editar potencial e visibilidade sem sair da página.
- **Movimentação por Arraste**: Ação de UI que solicita mudança de potencial (não de desempenho) com confirmação visual e persistência.
- **Escopo de Visibilidade**: Conjunto de pessoas que o usuário autenticado pode ver na matriz, resolvido no backend pela hierarquia vigente.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Em revisão guiada, admin completa inspecionar + alterar potencial + liberar/ocultar de uma pessoa via drawer sem navegar para a página `classify` como passo obrigatório, em até 1 minuto por pessoa.
- **SC-002**: Em revisão guiada, admin reposiciona com sucesso o potencial de pelo menos 3 pessoas via drag (ou via drawer se drag degradado) e vê a grade coerente com os valores persistidos sem full page reload obrigatório entre cada uma.
- **SC-003**: 100% dos casos de teste de permissão/escopo relevantes (admin escreve; líder/gerente só lê no escopo; colaborador sem liberação não vê 9-box; IDOR negado) passam após a feature.
- **SC-004**: Em cenários de falha simulada (validação/rede/permissão), 100% das tentativas exibem erro honesto e nenhuma alteração indevida permanece visível como “salva”.
- **SC-005**: Em viewport móvel típico, a matriz é consultável e a calibração admin é concluível via drawer/formulário mesmo se drag estiver degradado.
- **SC-006**: Em revisão de a11y mínima, drawer é operável por teclado e células/quadrantes têm identificação além da cor.
- **SC-007**: Nenhuma mudança verificável nas fórmulas de desempenho/quadrante (contrato vigente) além do recálculo após potencial válido; gate de visibilidade ao colaborador permanece restritivo (default não liberado).

## Assumptions

- Regras de classificação em vigor (desempenho derivado da nota do líder; potencial manual 1–3; quadrante calculado; visibilidade ao colaborador default oculta) permanecem a fonte da verdade; esta feature só muda a superfície de operação.
- **Política de drag**: arraste altera somente potencial; desempenho nunca é “pintado” pela célula de destino se divergir do valor derivado — rejeição ou snap para a célula coerente.
- Papel **admin** é o único com escrita na matriz, alinhado ao comportamento atual de `classify` / toggle; líder/gerente já veem a grade no escopo sem edição.
- Serviços existentes de upsert de classificação e toggle de visibilidade são reutilizados; novos pontos de entrada de UI (partials/ações na página da matriz) chamam a mesma lógica de negócio.
- Stack de apresentação: páginas servidor + atualizações parciais (HTMX e/ou JS mínimo local para drag), sem SPA, sem API pública/DRF, sem Chart.js nesta feature.
- Fundação visual 004 (Freeze) está disponível; novos padrões de drawer/drag só entram em `docs/design-system.md` se forem canônicos e mínimos.
- A página `classify` pode permanecer como fallback/legado até eventual deprecação futura fora desta feature.
- Auditoria append-only já existente, se cobrir mudanças de potencial/visibilidade, é apenas consumida — histórico visual de movimentações na grade está fora de escopo.
- “A11y mínima” = teclado/foco no drawer, alternativa ao drag, rótulos além da cor; auditoria WCAG formal completa está fora.

## Out of Scope

- Novas métricas, faixas de desempenho, alteração de `derive_desempenho` / política de cálculo de quadrante (exceto recalcular após potencial válido).
- Edição livre de desempenho via UI (desempenho continua derivado da nota).
- SPA, API pública/DRF, GraphQL.
- Redesign de marca / reabrir Freeze / WIP Impeccable / polish amplo de fontes-botões-cards em todo o produto.
- Charts do dashboard (005) e qualquer dependência de Chart.js nesta feature.
- Export/relatórios, calibração multi-ciclo em lote, histórico visual de movimentações na grade.
- Tornar 9-box visível por padrão ao colaborador.
- Deprecação obrigatória da página `classify` (pode permanecer como fallback).
