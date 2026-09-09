# SpecKit: Princípios de Design e Diretrizes do Sistema — Greenn People

Documento de referência canônica para engenharia e design (Cursor, front-end e produto). Consolida todos os princípios, escolhas tipográficas, semântica cromática, arquitetura de componentes e regras de UX/UI lapidadas ao longo de todas as telas construídas no projeto.

---

## 1. Visão do Produto e Filosofia de Design

O **Greenn People** é uma plataforma corporativa B2B de gestão de desempenho, desenvolvimento contínuo (PDI), governança de ciclos e inteligência de RH.

### Princípios Fundamentais de Experiência (Core UX Principles)

1. **Anti-Burocracia e Baixa Carga Cognitiva:**
   - Telas não devem parecer planilhas frias ou formulários intermináveis de conformidade.
   - Cada tela responde com clareza a duas perguntas em menos de 3 segundos de escaneamento:
     - *"Qual é a minha situação atual?"*
     - *"O que eu preciso fazer agora?"*

2. **Hierarquia de Ação vs. Acompanhamento:**
   - **Ação Imediata (Sua vez):** Elemento único ou destacado com ênfase visual (Hero Banner ou CTA verde no topo).
   - **Acompanhamento Passivo:** Blocos secundários, neutros e organizados em grids respiráveis.
   - **Regra anti-fricção de CTAs:** Proibida a concorrência de CTAs idênticos ou agressivos na mesma viewport. Mantém-se um único botão primário soberano.

3. **Sobriedade Corporativa (Sem Gamificação Infantilizada):**
   - Não utilizamos confetes, emojis excessivos, mascotes, troféus ou pontuações de jogo.
   - A interface comunica **maturidade, pertencimento profissional e evolução de carreira**, tratando o colaborador como um profissional sênior e respeitado.

4. **Transparência e Mitigação de Ansiedade:**
   - Estados intermediários nunca parecem erros. Textos como *"Aguardando avaliação do líder"* ou *"Não avaliada"* usam tons neutros (cinzas e slates), nunca vermelho de alarme.
   - Gráficos e matrizes têm seus referenciais esperados (alvos de cargo) **sempre visíveis**, mesmo antes de qualquer nota ser preenchida. O usuário nunca se depara com telas vazias quebradas.

---

## 2. Fundamentos Visuais e Tokens (Design System)

### 2.1 Tipografia
A combinação tipográfica une autoridade executiva e legibilidade técnica:

* **Headlines & Títulos de Alto Nível:** `Fraunces` (Google Font, serifada, peso 600/700).
  - Usada em títulos de páginas (`h1`), cabeçalhos de seções nobres e cumprimentos acolhedores (*"Olá, Gabriel 👋"*).
  - Transmite solidez institucional, tradição corporativa e sofisticação visual.
* **Corpo, Tabelas, Métricas e Componentes de UI:** `Source Sans 3` (Google Font, sem-serifa, pesos 400, 500, 600, 700).
  - Usada em tabelas de auditoria, cadastros, formulários, badges, cards e microtextos.
  - Garante leitura rápida, numerais tabulares nítidos e neutralidade funcional.

### 2.2 Paleta de Cores e Semântica Rigorosa

A paleta adota uma matriz institucional baseada no tema **Lush Professional**:

| Função Semântica | Token / Hex | Descrição de Uso |
|---|---|---|
| **Verde Principal (Brand & Primary)** | `#059669` (Emerald 600) | Ações primárias, botões ativos, borders de seleção, barras de progresso concluídas. |
| **Verde Escuro Nobre (Hero/Header)** | `#064e3b` a `#0F3D2E` | Fundos de cartões de ação prioritária (Hero Banner), cabeçalhos de alta autoridade. |
| **Verde Suave (Surface Tint)** | `#ecfdf5` (Emerald 50) | Fundos de cards de sucesso, callouts informativos acolhedores, chips de aprovado. |
| **Superfície Base (Background)** | `#f7f9fb` a `#f8fafc` | Fundo geral da aplicação; limpo, claro, não cansa a visão. |
| **Superfície Containers (Cards & Modais)** | `#ffffff` | Cartões, gavetas (drawers) e modais; sempre brancos e planos. |
| **Bordas & Divisórias** | `#e2e8f0` a `#e5e7eb` | Linhas finas de 1px (`border-slate-200`), sutis e sem ruído. |
| **Atenção / Pendente (Sua vez)** | `#f59e0b` (Amber 500) / `#d97706` | Badges de etapas em andamento, alertas de prazos, pendências ativas. |
| **Sucesso / Concluído** | `#059669` / `#10b981` | Metas aprovadas, ciclos consolidados, etapas cumpridas. |
| **Erro Crítico / Reprovação Real** | `#ef4444` (Red 500) | **Restrito exclusivamente** a reprovação com justificativa ou prazo estourado. Nunca usado em campos vazios no prazo normal. |
| **Neutro / Em Espera** | `#64748b` (Slate 500) | Estados não preenchidos no prazo, campos bloqueados por confidencialidade. |

### 2.3 Raio de Curvatura (Roundness) e Elevação
- **Border Radius:** `8px` (`rounded-lg` no Tailwind) para cards, botões, inputs e gavetas. Curvatura contida e elegante.
- **Sombras:** Quase 100% planas (`shadow-none` ou micro-sombra `shadow-sm`), utilizando bordas sutis de `1px solid #e2e8f0` para divisão de espaço. Sem sombras pesadas artificiais.

---

## 3. Padrões de Navegação e Layout Estrutural

### 3.1 Sidebar (Desktop)
- **Largura:** Fixa em `280px` na versão expandida; ícones verticais com tooltips em `72px` na versão recolhida (mini).
- **Estrutura por Papéis (Role Segregation):**
  - `COLABORADOR`: Meu painel, Expectativas, Metas, Avaliações, Meu PDI, Minha classificação.
  - `LÍDER`: Painel do time.
  - `GERENTE`: Estrutura, Aderência, Matriz de talentos.
  - `GOVERNANÇA & CADASTROS`: Ciclos, Painel admin, Áreas, Cargos, Usuários, Competências.
  - `SISTEMA`: Auditoria, Notificações.
- **Interação:** Borda esquerda de `4px solid #059669` com fundo `bg-emerald-50/50` no item ativo.

### 3.2 Top Bar / Header de Ciclo
- Indicador compacto do ciclo atual: `🟢 Ciclo Vigente: Teste_metas (2024.1)` no canto superior direito.
- Seletor de ciclo e perfil do usuário integrados sem duplicações.

---

## 4. Padrões de Componentes e UX por Módulo

### 4.1 "Meu Painel" e "Minhas Expectativas" (Módulo do Colaborador)
1. **Identidade Pessoal e Pertencimento:**
   - Metadados do colaborador integrados ao topo: *tempo de casa, cargo atual, data de início e ponto alto histórico*.
2. **Faixa de Trajetória em Linha Única:**
   - Mini sparkline / pílulas horizontais conectadas por setas mostrando os últimos 3 ciclos consolidados (ex: `2023-Q2: 3,80 ➔ 2023-Q4: 4,40 ➔ Atual: Em avaliação`).
3. **Maturidade no Cargo vs. Nível Esperado:**
   - Substituição de números frios ("Nível 4") por régua de maturidade comparativa com percentual de prontidão (`85% - Nível JR ➔ PL`).
4. **Radar Pré-plotado (Sem Estado Vazio):**
   - Polígono do Nível Esperado desenhado desde o primeiro instante. O colaborador vê a meta antes das suas notas serem computadas.
   - Callout tranquilizador explicando que as notas mútuas (líder x liderado) surgirão na etapa de consolidação.
5. **Cards de Competências com Ícones Semânticos:**
   - Cada competência tem seu ícone próprio (ex: Acadêmico para Curiosidade, Foguete para Autonomia, Diálogo para Comunicação).
   - Régua com marcador de pino (pin) para meta esperada, diferenciando meta de nota real preenchida.

### 4.2 Gestão de Metas e Resultados
1. **Diferenciação Visual Estrita de Etapas:**
   - **Etapa de Planejamento:** Foco no alinhamento ao Objetivo Estratégico e método de medição (Percentual, Numérico, Binário).
   - **Etapa de Resultados:** Preenchimento do resultado apurado com justificativa / anexos.
2. **Aprovação Direta e Sem Fricção (Visão do Líder):**
   - Tabela com ações rápidas na própria linha: botões contextuais `Aprovar` e `Reprovar` (com modal obrigatório de justificativa construtiva).
   - Eliminação de cliques intermediários para aprovações simples.

### 4.3 PDI (Plano de Desenvolvimento Individual)
1. **Fluxo em Duas Camadas:**
   - **Plano Macro (Porta de Entrada / Hub):** Nome do plano, ciclo de referência, objetivo de desenvolvimento macro e prazos.
   - **Ações de PDI:** Ações concretas vinculadas às competências a desenvolver (cursos, mentorias, entregas práticas).
2. **Empty States Guiados:**
   - Quando não há PDI, a tela exibe ilustração limpa, frase inspiradora e um único CTA: `"Criar meu primeiro PDI"`.

### 4.4 Listagens de Cadastros e Governança (Usuários, Cargos, Áreas, Competências, Auditoria)
1. **Barra de Ações e Filtros Padronizada:**
   - Campo de busca textual rápida à esquerda (`Buscar por nome, cargo ou e-mail...`).
   - Botão de filtros discretos via ícone expansível (filtros profundos por Área, Gestor ou Tipo de Competência ficam ocultos até o clique, despoluindo a tela).
   - Botão de ação primária destacado à direita (`+ Novo Cadastro`).
2. **Tabelas de Alta Densidade com Leitura Fluida:**
   - Linhas com `border-b border-slate-100`, hover suave `hover:bg-slate-50/80`.
   - Badges de status discretos com texto escuro sobre fundo pastel (ex: `Ativo`, `Inativo`, `Pendente`).
   - Coluna de ações padronizada com links textuais diretos ou menu kebab de 3 pontos.

### 4.5 Dashboards Estruturais e Gerenciais (Panorama da Estrutura & Aderência)
1. **Desacoplamento de Conceitos:**
   - **Cobertura:** Percentual de pessoas elegíveis que iniciaram o ciclo.
   - **Aderência:** Percentual de prazos e etapas cumpridos rigorosamente pela liderança.
2. **Visão em Drawer Lateral:**
   - O clique em um colaborador ou líder abre uma gaveta deslizante à direita sem perder o contexto do grid principal.

---

## 5. Checklist de Qualidade para Novas Implementações

Antes de commitar ou aprovar qualquer nova tela do Greenn People:
- [ ] O `h1` está usando a fonte **Fraunces**?
- [ ] O corpo de texto e componentes usam **Source Sans 3**?
- [ ] A paleta de cores respeita os verdes `#059669` e `#064e3b`, sem tons azuis genéricos?
- [ ] O border-radius padrão é `8px` (`rounded-lg`)?
- [ ] Há apenas **um único** botão/CTA primário com peso dominante?
- [ ] Estados de espera/pendência usam tons neutros ou âmbar suave, evitando o vermelho de alarme?
- [ ] O seletor de ciclo e os metadados contextuais estão visíveis e padronizados?
- [ ] Filtros secundários estão contidos no menu discreto para manter a tela limpa?
