# Feature Specification: Visualizações Gerenciais e Históricas Pós-Legado

**Feature Branch**: `012-gerencial-historico-legado`

**Created**: 2026-08-14

**Status**: Draft

**Input**: User description: "Spec 012 — Visualizações gerenciais e históricas pós-legado (escala, pipeline e evolução entre ciclos). Após a 011, o ambiente tem dezenas de ciclos históricos e centenas de avaliações terminais sem notas; painéis/gráficos (005/007/009) saturam, misturam arquivo com operação e caem em fallback silencioso. Separar visão operacional do ciclo vigente vs histórico explícito; pipeline de etapas de primeira classe; densidade controlada (Top-N + Outros); estética moderna/leve Freeze v2; evolução entre ciclos no escopo do gestor; sem alterar domínio de etapa/ciclo/nota nem inventar métricas."

## Declaração do Problema (O Porquê)

A importação da spec `011` enriqueceu o histórico (dezenas de ciclos encerrados e centenas de avaliações em estado terminal, ainda sem notas/competências). Os painéis e gráficos das specs `005`, `007` e `009` foram desenhados para poucos ciclos operacionais. Com o volume legado, a leitura gerencial quebrou: rótulos saturados, arquivo histórico misturado com operação, fallback silencioso para um ciclo encerrado qualquer quando não há ciclo aberto, KPIs que contam o arquivo como “saúde da operação”, pipeline ilegível e empty states enganosos (ex.: ciclo “100% concluído” sem nota de desempenho).

Marina (Admin RH) e Bruno (gestor) precisam **separar com clareza** (1) a visão operacional do ciclo vigente e (2) a visão histórica/arquivo entre ciclos — sem perder o legado — com hierarquia visual caprichada (KPI → visual → drill), pipeline de etapas legível e gráficos modernos, leves e escaneáveis em qualquer superfície com chart do produto.

## Clarifications

### Session 2026-08-14

- Q: Métrica default da US3 (“evoluiu ou não?”) nesta fatia, sabendo que a 011 só tem cabeçalho/etapa — sem notas e provavelmente sem snapshot de aderência? → A: Etapa/conclusão agora (pipeline no tempo); gap/aderência empty até haver dado.
- Q: Onde mora a visão histórica explícita (distinta da home operacional)? → A: Modo/toggle ou query nas superfícies já existentes (admin, time, detalhe de ciclo).
- Q: O painel pessoal (`dashboard/personal`) entra no 100% de charts desta fatia? → A: Só teto de densidade + empty honesto + estética (sem tendência nova).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Marina opera o ciclo vigente sem o arquivo legado explodir a tela (Priority: P1)

Marina abre o painel admin e superfícies correlatas de RH (progresso/pipeline do ciclo, distribuição de aderência, cobertura por área/cargo, lista/filtro de ciclos, detalhe do ciclo). A visão padrão é o **ciclo aberto**. Se não houver ciclo aberto, ela vê empty state operacional **honesto** — nunca um ciclo encerrado escolhido em silêncio dentre dezenas do arquivo. O histórico legado continua acessível por seletor/arquivo **explícito**. KPIs de “ciclos” não misturam operação com arquivo. O pipeline de etapas é a leitura principal do andamento: hierarquia clara, totais no KPI, visual arejado. Categorias longas (áreas, cargos, ciclos no seletor) usam Top-N + “Outros”, busca/paginação ou agrupamento — nenhum eixo com dezenas de rótulos crus.

**Why this priority**: Sem estabilizar a operação RH pós-legado, o produto fica inutilizável no dia a dia; é o MVP desta feature.

**Independent Test**: Com dump da 011 no banco e zero ciclo aberto, admin carrega sem overflow de rótulos e com empty operacional limpo; ao abrir um ciclo operacional, pipeline e KPIs refletem **somente** esse ciclo; arquivo permanece acessível por intenção explícita.

**Acceptance Scenarios**:

1. **Given** ambiente com dezenas de ciclos encerrados legados e **nenhum** ciclo aberto, **When** Marina abre o painel admin / progresso operacional, **Then** vê empty state operacional honesto e leve — sem seleção silenciosa de um ciclo encerrado e sem gráfico fantasma.
2. **Given** um ciclo aberto operacional, **When** Marina consulta pipeline, KPIs e aderência/cobertura do ciclo, **Then** os números e o visual refletem **somente** esse ciclo; ciclos encerrados do arquivo não poluem eixos nem KPIs de “saúde da operação”.
3. **Given** Marina precisa consultar um ciclo histórico, **When** escolhe explicitamente no seletor/arquivo (operacional em destaque; histórico agrupado/buscável), **Then** acessa o ciclo escolhido sem que a home operacional volte a misturar arquivo por padrão.
4. **Given** categorias longas (áreas, cargos ou listagem de ciclos), **When** um gráfico de barras/cobertura/ranking renderiza, **Then** aplica teto de densidade (Top-N + “Outros” ou equivalente) — nenhum eixo com 50+ rótulos crus.
5. **Given** viewport estreito (~375px), **When** Marina consulta o painel, **Then** a mensagem principal (KPI → visual → drill) permanece legível sem scroll horizontal do canvas.

---

### User Story 2 - Bruno vê o time no ciclo operacional com pipeline e painel gerencial (Priority: P1)

Bruno abre o painel do time (e estrutura/aderência do líder, no mesmo padrão) e vê KPI + pipeline/status do escopo + ranking acionável, somente pessoas do seu escopo hierárquico. Sem ciclo aberto: empty honesto, não gráfico fantasma. Com ciclo aberto: pipeline de etapas do time (incluindo “sem avaliação”) legível e leve; destaque de atenção continua. Cobertura por área/cargo e aderência no escopo permanecem semanticamente distintas (cobertura ≠ aderência). Densidade controlada com Top-N + “Outros”.

**Why this priority**: Gestores precisam de visão estável do ciclo atual no mesmo release que corrige a saturação RH; sem isso a narrativa gerencial da 009 regrede sob volume legado.

**Independent Test**: Líder com escopo e ciclo aberto vs sem ciclo; zero dado fora do escopo; nenhum gráfico saturado ou visualmente pesado; empty honesto quando aplicável.

**Acceptance Scenarios**:

1. **Given** líder com pessoas no escopo e ciclo aberto, **When** abre painel do time / estrutura / aderência, **Then** vê composição gerencial (1–3 KPIs → visual principal → drill) respondendo “onde o time está” antes da tabela, só com dados do escopo.
2. **Given** líder sem ciclo aberto, **When** abre as mesmas superfícies, **Then** empty operacional honesto aparece — sem série inventada nem ciclo encerrado implícito.
3. **Given** pipeline de etapas do time, **When** o visual renderiza, **Then** usa as etapas já existentes do domínio (incluindo ausência de avaliação quando aplicável), com ritmo visual claro e sem parede de rótulos.
4. **Given** cobertura e aderência no escopo, **When** Bruno compara as duas superfícies, **Then** cobertura ≠ aderência permanece; destaque de atenção/ranking continua acionável com densidade controlada (Top-N + “Outros”).
5. **Given** viewport ~375px, **When** consulta o painel, **Then** a pilha KPI → visual → drill permanece consultável sem zoom horizontal.

---

### User Story 3 - Evolução histórica entre ciclos no escopo do gestor (Priority: P2)

Bruno (e Marina no recorte RH) ativa uma **visão histórica explícita** — distinta da home operacional — via **modo/toggle ou query nas superfícies já existentes** (admin, time, detalhe de ciclo). Não há página/seção dedicada de “histórico / evolução”; o seletor de ciclo sozinho não substitui a superfície de tendência. O **painel pessoal** (`dashboard/personal`) **não** recebe essa visão de evolução nesta fatia. Compara os mesmos indicadores já existentes ao longo dos ciclos encerrados (legado + operacionais) das pessoas no seu escopo: colaboradores do líder; líderes/organização no recorte admin. A pergunta de produto é “evoluiu ou não?”. **Nesta fatia, o default que responde essa pergunta é etapa/conclusão no tempo** (pipeline histórico: avançou de etapa / concluiu / estável / sem dado). Aderência por snapshot e gap esperado×nota **não** são o visual principal agora: empty honesto até existir dado (notas/6.5.5 e snapshot de aderência quando houver). A série temporal (área suave) ou comparativo agrupado usa **somente** métricas já calculadas no domínio — sem inventar 9-box nem nota final. Default: últimos N ciclos relevantes no escopo (N pequeno, ordenado por data), com opção de escolher ciclos; nunca plotar dezenas de séries cruas. A tendência parece spark/área contemporânea, não gráfico de linhas com muitas legendas.

**Why this priority**: É o valor novo pós-legado (evolução entre ciclos), mas depende da separação operacional/histórico das stories P1.

**Independent Test**: Líder ativa modo/query histórico no painel do time (sem rota nova) e vê tendência de etapa/conclusão só do escopo; admin idem nas superfícies RH existentes; ciclo sem dado → empty local, resto da página intacta; aderência/gap empty até haver dado; default com N pequeno; seleção explícita de ciclos adicionais.

**Acceptance Scenarios**:

1. **Given** gestor com histórico de ciclos no escopo, **When** ativa o modo/toggle ou query histórico numa superfície já existente (admin, time ou detalhe de ciclo) — não uma página nova —, **Then** vê tendência de **etapa/conclusão** dos últimos N ciclos relevantes (N pequeno), respondendo “evoluiu / estável / sem dado” num relance; séries de aderência/gap, se presentes, ficam empty até haver dado. A home operacional permanece o default até essa intenção explícita.
2. **Given** necessidade de outro recorte temporal, **When** escolhe ciclos no seletor histórico, **Then** a série atualiza apenas para os ciclos escolhidos — sem plotar o arquivo completo de uma vez.
3. **Given** ciclo/pessoa sem nota (cabeçalho legado terminal sem desempenho), **When** a série de nota/gap seria plotada, **Then** empty local honesto aparece para essa série; pipeline/etapa podem continuar visíveis onde fizer sentido; resto da página intacta.
4. **Given** Admin RH na visão histórica, **When** consulta o recorte de líderes/organização, **Then** vê apenas o escopo autorizado e a mesma disciplina de densidade/empty da visão do líder.
5. **Given** ausência de dado em um ponto da série, **When** a página renderiza, **Then** não inventa valor zero de desempenho nem série fictícia (`has_data` falso → empty).

---

### Edge Cases

- Zero ciclo aberto + dezenas de ciclos encerrados: empty operacional; histórico só por intenção explícita.
- Cabeçalho legado `concluida` + etapa terminal **sem nota**: pipeline pode mostrar etapas; desempenho/gap/9-box ficam empty ou “sem nota” — nunca “ciclo saudável/completo” de desempenho.
- Um único ciclo aberto com muitas áreas/cargos: Top-N + “Outros” (ou busca/paginação no seletor), sem saturar eixos.
- Escopo vazio (líder sem subordinados visíveis): empty honesto de escopo, sem vazar dados de fora.
- Ciclo histórico escolhido explicitamente com 100% etapas avançadas mas sem notas: empty de desempenho local; não misturar com KPI de operação vigente.
- Viewport estreito e muitos pontos: tooltip + Top-N; sem parede de datalabels; sem scroll horizontal do canvas.
- Atualização parcial de lista/região já existente: o bloco de gráfico permanece íntegro e não inventa série.
- Painel pessoal (`dashboard/personal`): aplica teto de densidade, empty honesto e estética; MUST NOT aparecer tendência de evolução entre ciclos nesta fatia.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O sistema MUST tratar o ciclo **aberto** como default da visão operacional em todas as superfícies gerenciais desta fatia (admin, time, estrutura, aderência, detalhe de ciclo e correlatos).
- **FR-002**: Na ausência de ciclo aberto, o sistema MUST exibir empty state operacional honesto e leve; MUST NOT selecionar em silêncio um ciclo encerrado do arquivo.
- **FR-003**: O histórico/arquivo de ciclos MUST permanecer acessível apenas por intenção explícita do usuário (seletor/arquivo com operacional em destaque e histórico agrupado/buscável). A visão de evolução entre ciclos MUST viver como modo/toggle ou query nas superfícies já existentes (admin, time, detalhe de ciclo); MUST NOT criar página/seção dedicada de “histórico / evolução”; MUST NOT reduzir-se ao seletor de ciclo sem superfície de tendência.
- **FR-004**: KPIs e indicadores de “ciclos / saúde da operação” MUST NOT misturar contagem ou status do arquivo legado com a operação vigente (ex.: dezenas de ciclos encerrados Sólides não contam como pipeline operacional).
- **FR-005**: O pipeline de etapas (etapas já existentes da avaliação, incluindo “sem avaliação” quando aplicável) MUST ser a leitura principal de andamento nas superfícies operacionais relevantes, com hierarquia KPI → visual → drill.
- **FR-006**: Todo gráfico com muitas categorias MUST respeitar teto de densidade: Top-N + “Outros” (ou busca/paginação/agrupamento equivalente); MUST NOT renderizar eixos com dezenas de rótulos crus.
- **FR-007**: Séries temporais / tendência entre ciclos MUST limitar o default aos últimos N ciclos relevantes no escopo (N pequeno) e permitir escolha explícita; MUST NOT plotar o arquivo completo de ciclos de uma vez.
- **FR-008**: Quando `has_data` for falso (ou equivalente), o sistema MUST exibir empty state; MUST NOT inventar série fictícia, zero de desempenho ou gráfico cinza fantasma.
- **FR-009**: Cabeçalhos legados terminais sem nota MUST NOT ser apresentados como desempenho completo/saudável; séries de nota/gap/9-box MUST usar empty ou “sem nota”; pipeline de etapas pode permanecer.
- **FR-010**: Visões de time/estrutura/aderência do gestor MUST restringir dados ao escopo hierárquico já autorizado no backend; a UI MUST NOT autorizar.
- **FR-011**: Cobertura por área/cargo e aderência MUST permanecer semanticamente distintas (cobertura ≠ aderência).
- **FR-012**: A visão histórica de evolução MUST usar somente métricas já persistidas/expostas no domínio; o visual default desta fatia MUST ser etapa/conclusão no tempo (pipeline histórico). Aderência por snapshot e gap esperado×nota MUST permanecer empty honesto até existir dado; MUST NOT ser o visual principal agora, MUST NOT inventar métrica nova nem implementar importação de notas.
- **FR-013**: A composição visual gerencial MUST seguir o padrão painel gerencial: 1–3 KPIs no máximo, um insight curto, visual principal arejado, tabela/ranking como drill — sem figcaption que repita label+valor do chart.
- **FR-014**: Gráficos MUST seguir a diretriz estética de leveza (pouco ink, grade de valor/eixos ruidosos off, sem cardificação/sombra excessiva, datalabel só com N baixo, doughnut com valor central + legenda texto, área suave para tendência, barras horizontais para ranking/atenção, grouped só para comparar duas séries) alinhada ao contrato Freeze de charts; Status Triad de negócio intacta; informação não depende só da cor.
- **FR-015**: Em viewport ~375px, a mensagem principal MUST permanecer consultável sem scroll horizontal do canvas (pilha KPI → visual → drill).
- **FR-016**: 100% das superfícies com gráfico no produto tocadas por esta fatia (admin, time, estrutura, aderência, detalhe de ciclo, lista de ciclos e painel pessoal) MUST cumprir empty honesto, teto de densidade e diretriz estética. O painel pessoal (`dashboard/personal`) MUST NOT receber tendência/evolução nova entre ciclos nesta fatia.
- **FR-017**: Atualizações parciais de listas/regiões já existentes MUST continuar funcionando; o bloco de gráfico MUST NOT quebrar a região atualizada.
- **FR-018**: Esta feature MUST NOT alterar regras de domínio de etapa, abertura/fechamento de ciclo, aprovação, fórmulas de aderência, escopo, snapshots write-once, nem models/migrations de nota; MUST NOT implementar notas/comentários (6.5.5) nem PDI.
- **FR-019**: Se o contrato de densidade/histórico/leveza dos charts for formalizado, a documentação canônica do design system MUST ser atualizada na mesma entrega.
- **FR-020**: Agregação para estas visões MUST preferir cálculo leve síncrono no request reutilizando payloads/composições existentes; processamento assíncrono/snapshot novo só se medição demonstrar peso real.

### Key Entities

- **Ciclo operacional (aberto)**: âncora da visão padrão de operação; no máximo um aberto; distinto do arquivo histórico.
- **Ciclo histórico / arquivo**: ciclos encerrados (legado e operacionais anteriores); acessíveis por seleção explícita; não alimentam KPIs de “saúde da operação” por default.
- **Avaliação (cabeçalho)**: estado de etapa/conclusão já existente; pode existir sem nota de desempenho (legado 011); pipeline usa etapa; desempenho exige nota quando a métrica a exige.
- **Escopo hierárquico**: conjunto de pessoas visíveis ao usuário autenticado; base de todas as visões de time e histórica do gestor.
- **Indicador já existente**: etapa/conclusão (default da tendência US3 nesta fatia); aderência, cobertura, gap esperado×nota (quando houver nota) — plotáveis ao longo do tempo sem nova fórmula; aderência/gap empty até existir dado.
- **Painel gerencial**: composição KPI(s) + visual principal + drill; pergunta da tela respondida num relance. Visão operacional é o default; visão histórica de evolução é modo/toggle ou query na mesma superfície — não uma home nova.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Com dump da 011 e zero ciclo aberto, painéis admin e de time carregam em menos de 3 segundos percebidos, sem overflow de rótulos e com empty operacional honesto e leve.
- **SC-002**: Com um ciclo aberto, pipeline e KPIs refletem somente esse ciclo; o arquivo histórico não polui eixos nem KPIs de operação; charts permanecem arejados (sem grade de valor ruidosa, insight único, sem duplicar números em figcaption).
- **SC-003**: Gestor no escopo lê status atual e tendência de etapa/conclusão dos últimos N ciclos (evoluiu / estável / sem dado) num relance após ativar o modo/query histórico numa superfície já existente; aderência/gap não substituem esse default enquanto não houver dado.
- **SC-004**: 100% dos gráficos do produto nas superfícies desta fatia (incluindo painel pessoal) passam no teto de densidade, empty honesto e diretriz estética (moderno/leve vs. relatório pesado); o pessoal não ganha série de evolução nesta fatia.
- **SC-005**: Comparação side-by-side com o padrão da spec 009: hierarquia KPI → visual → drill preservada ou melhorada; nenhum gráfico saturado, monocor pesado ou com eixos ruidosos.
- **SC-006**: Em viewport ~375px, a mensagem principal de cada painel gerencial permanece compreensível sem scroll horizontal do canvas.
- **SC-007**: Regressão de regras de etapa, escopo e invariantes de rejeição de etapa permanece verde; nenhuma alteração indevida nos serviços/domínio denylist desta feature.

## Assumptions

- Pré-condição: importação da spec `011` aplicada no ambiente de validação (ciclos + cabeçalhos no banco).
- Notas/competências (6.5.5) **não** entram nesta feature; empty honesto de desempenho é o comportamento esperado para cabeçalhos sem nota.
- Métrica default da US3 nesta fatia: **etapa/conclusão no tempo** (pipeline histórico). Gap e aderência por snapshot ficam empty até haver dado; a US3 **não** espera 6.5.5 e **não** usa aderência como visual principal enquanto o legado não tiver snapshot.
- A visão histórica explícita mora como **modo/toggle ou query** nas superfícies já existentes (admin, time, detalhe de ciclo). Não é página dedicada de “histórico / evolução”; não é só o seletor de ciclo sem superfície de tendência. Histórico não é a home.
- Painel pessoal (`dashboard/personal`) **entra** no 100% de charts desta fatia só para teto de densidade, empty honesto e estética; **não** recebe tendência/evolução nova entre ciclos (isso fica no recorte gestor/RH da US3).
- “N pequeno” para Top-N e para default de ciclos na tendência fica na faixa típica de leitura gerencial (cerca de 5–10), calibrável no plano sem mudar a regra de produto “nunca plotar o arquivo completo”.
- Catálogo visual e stack de apresentação permanecem os do Freeze v2 / spec 009 (mesma biblioteca de gráficos já adotada; sem SPA, sem lib nova de gráfico, sem API REST na v1).
- Autorização continua 100% no backend (escopo hierárquico / mixins e requisitos de papel já existentes).
- Não-objetivos confirmados: trocar biblioteca de gráficos; 9-box drag; mudar máquina de estados; importar notas; dashboard executivo genérico fora de escopo/hierarquia; misturar cobertura com aderência; contar arquivo legado como pipeline da operação; visual de “dashboard corporativo pesado” (grades densas, 3D, gauges, arco-íris, cards com sombra forte); evolução pessoal entre ciclos no `dashboard/personal`.
- Superfícies no escopo de correção/evolução: painéis admin, time, estrutura, aderência, lista e detalhe de ciclo, e componentes compartilhados de bloco/payload/script de charts já usados pelo produto. Painel pessoal: mesma disciplina visual (densidade/empty/estética), sem US3 de tendência.
