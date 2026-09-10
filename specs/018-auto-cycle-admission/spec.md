# Feature Specification: Abertura Automática de Ciclos por Admissão

**Feature Branch**: `018-auto-cycle-admission`

**Created**: 2026-09-09

**Status**: Draft

**Input**: User description: "Abertura automática de ciclos (Opção A) a cada 6 meses a partir do mês de admissão; marco no 1º dia útil do mês (feriados Brasil nacional); prazo 20 dias após ativo; sem data de admissão não entra; ciclo ainda aberto só alerta RH e nunca bloqueia os demais; bootstrap legado = só próximo marco futuro (sem recuperar atrasados); lote do mês (ex.: 10 no corte de julho → os 10). Segurança e escopo sempre no backend; UI nunca decide; observabilidade e governança RH não-negociáveis."

## Clarifications

### Session 2026-09-09 (decisões fechadas — não reabrir)

- **Modelo**: ritmo pela **admissão** (Opção A). Quem compartilha o **mesmo mês de marco** entra **junto** no lote daquele dia (não é “1 pessoa por vez”).
- **Marco**: a cada **6 meses** contados pelo **mês** de admissão; abertura no **1º dia útil** desse mês (não no dia civil da admissão).
- **Feriados**: calendário **Brasil nacional** (geral).
- **Prazo**: ciclo automático ativo tem **20 dias corridos** para a avaliação ser concluída; `data_fim` do ciclo automático = data de ativação + 20 dias.
- **Sem data de admissão / data de entrada**: **não entra** no automático. Sem essa data **não há recorte de ciclo**. Só passa a ser considerado após cadastro/correção.
- **Ciclo ainda aberto no novo marco**: **alerta o RH**; **nunca** impede abertura/matrícula dos demais. A esteira não atrasa por causa de um caso raro.
- **Bootstrap / legado com tempo de casa (ESSENCIAL)**: calcular apenas o **próximo marco futuro**; **não** abrir marcos atrasados do passado; **não** recuperar histórico em massa no go-live.
- **Segurança / escopo**: regra e autorização **sempre no backend**; **UI nunca decide** elegibilidade, abertura, alerta ou visibilidade. Respeito ao escopo hierárquico vigente; governança global só para quem já pode gerir ciclos (RH/admin).
- **Abertura manual (015)**: permanece; automação é caminho **adicional**, não substitui o fluxo manual.
- **Múltiplos ciclos abertos**: esta feature **exige** coexistência de mais de um ciclo `aberto` (senão o lote de um mês trava o do seguinte ou o alerta de “ainda aberto” viraria bloqueio). A restrição “no máximo um ciclo aberto” da 015 **é alterada** por esta feature.
- **Forma do ciclo automático**: **um ciclo por mês de marco** (coorte do mês), matriculando **todos** os elegíveis daquele marco no 1º dia útil — não um ciclo por pessoa.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Abrir o lote do mês no 1º dia útil (Priority: P1)

No 1º dia útil do mês, o sistema identifica todos os colaboradores ativos cujo **próximo marco futuro** (mês de admissão + múltiplos de 6 meses) é aquele mês, cria **um** ciclo automático da coorte e matricula **todos** esses elegíveis (ex.: 10 no marco de julho → os 10). Quem não tem data de admissão não entra. A abertura não depende de o RH clicar “abrir” naquele dia.

**Why this priority**: É o núcleo da automação — sem o lote no marco certo, a feature não existe.

**Independent Test**: Base com 10 elegíveis no marco de julho, alguns sem data, alguns com marco em outro mês; avançar para o 1º dia útil de julho e verificar 1 ciclo automático da coorte, exatamente 10 Avaliações, zero nos demais.

**Acceptance Scenarios**:

1. **Given** 10 ativos com data de entrada cujo próximo marco futuro é julho e hoje é o 1º dia útil de julho, **When** a rotina automática roda, **Then** existe exatamente 1 ciclo automático da coorte de julho e cada um dos 10 recebe exatamente 1 Avaliação nesse ciclo.
2. **Given** ativos sem data de entrada no mesmo dia, **When** a rotina roda, **Then** esses ativos **não** recebem Avaliação automática e **não** entram no ciclo da coorte.
3. **Given** ativos cujo próximo marco futuro é agosto (não julho), **When** a rotina roda em julho, **Then** esses ativos **não** são matriculados no ciclo de julho.
4. **Given** o mesmo 1º dia útil de julho e a rotina já abriu o lote com sucesso, **When** a rotina roda de novo no mesmo dia, **Then** **não** cria segundo ciclo da mesma coorte nem duplica Avaliações (idempotência).
5. **Given** dia que **não** é o 1º dia útil do mês (ou mês sem marco elegível), **When** a rotina roda, **Then** **não** abre ciclo automático de coorte naquele dia.

---

### User Story 2 - Bootstrap seguro para quem já tem tempo de casa (Priority: P1)

Colaboradores legados com anos de casa e data de admissão preenchida **não** disparam abertura em massa de marcos passados quando a feature liga. O sistema calcula só o **próximo marco futuro** e espera esse 1º dia útil. Sem admissão, continuam de fora até cadastrar.

**Why this priority**: Essencial para não bagunçar produção no go-live nem “recuperar” ciclos atrasados que nunca existiram nessa regra.

**Independent Test**: Admitido em jan/2022; “hoje” = set/2026 com feature ligada; verificar próximo marco = jan/2027; zero abertura imediata de marcos 2022–2026; em jan/2027 (1º dia útil) a pessoa entra no lote.

**Acceptance Scenarios**:

1. **Given** colaborador com admissão antiga cujo próximo marco futuro ainda não chegou, **When** a feature está ativa e a rotina diária roda, **Then** **não** cria ciclo/Avaliação automática “atrasada” para marcos já vencidos.
2. **Given** o mesmo colaborador no 1º dia útil do mês do próximo marco futuro, **When** a rotina roda, **Then** ele entra no lote daquele mês junto com os demais elegíveis.
3. **Given** colaborador legado sem data de entrada, **When** a rotina roda em qualquer marco, **Then** permanece fora do automático até a data ser cadastrada; depois da correção, só o **próximo** marco futuro (a partir da correção) o considera — sem recuperar passado.

---

### User Story 3 - Prazo de 20 dias e alerta sem travar a esteira (Priority: P1)

Todo ciclo automático nasce com prazo de **20 dias corridos** após ficar ativo. Se no próximo marco alguém ainda tiver ciclo aberto (manual ou automático), o RH recebe **alerta** claro; o lote novo **abre mesmo assim**. Atraso de um não atrasa os outros.

**Why this priority**: Prazo e não-bloqueio são o contrato operacional com o RH; sem isso a automação vira gargalo.

**Independent Test**: Abrir coorte A; simular pessoa ainda com ciclo aberto no marco seguinte; verificar alerta ao RH + coorte B aberta com os demais matriculados; verificar `data_fim` = ativação + 20 dias.

**Acceptance Scenarios**:

1. **Given** ciclo automático ativado na data D, **When** o ciclo é criado, **Then** sua data de fim operacional é D + 20 dias corridos.
2. **Given** colaborador elegível ao novo marco que ainda possui ciclo aberto, **When** a rotina do novo marco roda, **Then** o RH recebe alerta identificando a pessoa/ciclo em aberto **e** o lote dos demais elegíveis é aberto/matriculado normalmente.
3. **Given** alerta emitido para um caso de ciclo ainda aberto, **When** a rotina processa o restante do lote, **Then** a existência do alerta **não** impede nem adia a abertura dos outros.
4. **Given** avaliação do ciclo automático não concluída após os 20 dias, **When** o RH consulta a governança, **Then** o atraso fica visível na superfície de governança (sem depender de suporte técnico).

---

### User Story 4 - Governança RH com observabilidade (Priority: P1)

O RH (quem já pode gerir ciclos) vê uma superfície de governança: quem entrou no período, quem ficou de fora por falta de admissão, alertas de ciclo ainda aberto e falhas da rotina. Cada abertura automática, pulo por falta de admissão, alerta e falha é rastreável (quando / o quê / por quê). Líder e colaborador **não** veem a fila global nem dados fora do escopo.

**Why this priority**: A automação só é aceitável se o RH governar com clareza; observabilidade e escopo são não-negociáveis.

**Independent Test**: Rodar um dia com elegíveis, sem-data e um alerta de ciclo aberto; como RH ver contagens e detalhes coerentes; como líder/colaborador não obter a fila global.

**Acceptance Scenarios**:

1. **Given** RH autorizado após um lote automático, **When** abre a governança do período, **Then** consegue responder: quem entrou, quem ficou de fora por falta de admissão, quem gerou alerta de ciclo ainda aberto, e se houve falha operacional.
2. **Given** líder ou colaborador sem permissão de gestão de ciclos, **When** tenta acessar a governança global ou listagens privilegiadas desta feature, **Then** recebe negação de acesso equivalente às demais superfícies restritas; **não** vê fila organizacional.
3. **Given** abertura automática bem-sucedida ou alerta emitido, **When** se consulta a trilha de auditoria/histórico operacional aplicável, **Then** o evento está registrado de forma append-only (ou equivalente já vigente no produto) com informação suficiente para reconstruir o fato.

---

### User Story 5 - Abertura manual e histórico intactos (Priority: P2)

O fluxo manual de abertura com “admitidos até” (015) continua disponível. Ciclos já encerrados e avaliações existentes **não** são reprocessados pela automação. Mudança posterior de data de admissão **não** apaga Avaliação já criada. Máquina de etapas, fórmulas, PDI, 9-box e escopo hierárquico de negócio **não** mudam de regra — salvo a coexistência de múltiplos ciclos abertos e as superfícies necessárias à governança automática.

**Why this priority**: Protege o arquivo e evita regressão; a automação é aditiva.

**Independent Test**: Abrir ciclo manual com corte 015 enquanto existe ciclo automático aberto; confirmar ambos válidos; ciclo encerrado intacto; edição de data não remove Avaliação.

**Acceptance Scenarios**:

1. **Given** ciclo automático aberto, **When** o RH abre um ciclo manual com corte “admitidos até” válido, **Then** a abertura manual continua possível sob as regras 015 (corte obrigatório, elegibilidade por corte), convivendo com ciclo(s) automático(s) aberto(s).
2. **Given** ciclo encerrado/histórico, **When** a rotina automática roda, **Then** zero reprocessamento que crie/apague Avaliações daquele ciclo.
3. **Given** Avaliação já criada em ciclo automático ou manual, **When** a data de entrada é editada depois, **Then** a Avaliação permanece (snapshot); elegibilidade só governa criação futura.

---

### Edge Cases

- Ativo sem data de entrada: nunca elegível ao automático; aparece como pendência de cadastro na governança RH.
- Inativo: nunca elegível ao automático, mesmo com admissão e marco no mês.
- 1º dia do mês cai em sábado/domingo/feriado nacional: abertura no **próximo** dia útil; dias anteriores do mês **não** abrem o lote.
- Go-live no meio do mês após o 1º dia útil: **não** abre “atrasado” aquele mês; espera o **próximo** marco futuro de cada pessoa (bootstrap).
- Correção de data de entrada no meio do mês do marco: se ainda não matriculado e o marco corrente ainda é o próximo marco futuro válido **e** ainda estamos no dia/janela de abertura idempotente do lote, pode entrar; se o lote do mês já fechou a janela do dia, espera o próximo marco futuro — sem recuperar passado.
- Pessoa já matriculada no ciclo da coorte do mês: não duplica Avaliação.
- Pessoa com ciclo ainda aberto e também elegível ao novo marco: gera alerta; **não** bloqueia o lote; matrícula no novo ciclo só se a regra de negócio permitir coexistência de Avaliações em ciclos distintos (uma por ciclo) — o alerta não impede os **outros**; para a própria pessoa, se já houver Avaliação no novo ciclo não duplica; se a política for “não matricular quem ainda tem ciclo aberto”, isso vale **só** para ela e deve permanecer visível no alerta — **default fechado**: a pessoa com ciclo ainda aberto **não** recebe nova Avaliação automática naquele marco (só alerta), e isso **não** atrasa os demais.
- Feriado estadual/municipal: **fora** do calendário desta feature (só Brasil nacional).
- Falha parcial da rotina: eventos de falha observáveis; reexecução idempotente não duplica o que já foi criado.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O sistema MUST, no **1º dia útil** de cada mês (calendário Brasil nacional), avaliar colaboradores ativos com data de entrada preenchida cujo **próximo marco futuro** (mês de admissão + múltiplos de 6 meses) é o mês corrente e MUST abrir **um** ciclo automático de coorte matriculando **todos** esses elegíveis.
- **FR-002**: O marco MUST basear-se no **mês** de admissão, **não** no dia civil da admissão; a abertura MUST ocorrer no 1º dia útil do mês do marco.
- **FR-003**: Sem data de entrada, o colaborador MUST NOT entrar no automático; MUST permanecer fora até o cadastro/correção da data.
- **FR-004**: Inativos MUST NOT ser matriculados pelo automático.
- **FR-005**: **Bootstrap / legado (ESSENCIAL)**: o sistema MUST calcular apenas o **próximo marco futuro**; MUST NOT abrir nem “recuperar” marcos atrasados do passado no go-live ou no dia a dia.
- **FR-006**: Ciclo automático MUST definir prazo de conclusão de **20 dias corridos** após a ativação (`data_fim` = data de ativação + 20 dias).
- **FR-007**: Se elegível ao novo marco ainda possui ciclo aberto, o sistema MUST alertar o RH e MUST NOT bloquear a abertura/matrícula dos demais elegíveis do lote.
- **FR-008**: Default da pessoa com ciclo ainda aberto no novo marco: MUST gerar alerta e MUST NOT criar nova Avaliação automática para essa pessoa naquele marco; MUST NOT usar esse caso para adiar o lote.
- **FR-009**: A rotina MUST ser idempotente por coorte/mês: MUST NOT criar dois ciclos automáticos da mesma coorte de marco nem duas Avaliações para o mesmo ciclo+colaborador.
- **FR-010**: MUST permitir **mais de um** ciclo com status aberto ao mesmo tempo (alteração deliberada da regra “só um aberto” da 015).
- **FR-011**: Abertura manual com “admitidos até” (015) MUST permanecer disponível como caminho adicional.
- **FR-012**: Elegibilidade e criação de Avaliação MUST ser decididas **somente no backend**; a UI MUST NOT ser fonte da regra (esconder botão ≠ autorização).
- **FR-013**: Superfícies de governança global, alertas de lote e listagens privilegiadas desta feature MUST restringir-se a quem já pode gerir ciclos (RH/admin conforme regra vigente); líder e colaborador MUST NOT acessar fila organizacional nem dados fora do escopo hierárquico.
- **FR-014**: Visibilidade de avaliações/ciclos para líder e colaborador MUST continuar respeitando o serviço de escopo vigente (`get_visible_users` / equivalente); esta feature MUST NOT enfraquecer escopo.
- **FR-015**: MUST oferecer governança RH com, no mínimo: entrantes do período, excluídos por falta de admissão, alertas de ciclo ainda aberto, falhas da rotina.
- **FR-016**: MUST registrar de forma observável/auditável (append-only onde houver mudança de dado) aberturas automáticas, pulos por falta de admissão, alertas de ciclo ainda aberto e falhas operacionais, com quem/quando/por quê reconstruível.
- **FR-017**: Avaliações já criadas MUST permanecer como snapshot; mudança posterior de data de entrada MUST NOT apagar, desfazer etapa ou fechar Avaliação existente.
- **FR-018**: Ciclos encerrados/históricos MUST NOT ser reprocessados pela automação para criar/apagar Avaliações.
- **FR-019**: MUST NOT alterar máquina de etapas, fórmulas de nota, aderência, 9-box, PDI, hierarquia de papéis, nem inventar papel novo — salvo o necessário à coexistência de múltiplos ciclos abertos e às superfícies de governança desta feature.
- **FR-020**: MUST NOT incluir nesta feature: Opção B (um único lote sem ritmo por admissão), recuperação em massa de marcos passados, calendário de feriados estaduais/municipais, matrícula forçada de inelegível, ou relatórios analíticos além da governança operacional descrita.
- **FR-021**: Processamento do lote diário/mensal MUST ser assíncrono/agendado (não depender de um RH abrir a tela para “disparar” o marco); a autorização de qualquer ação humana sobre governança continua no backend.
- **FR-022**: Mensagens e rótulos da governança MUST ser compreensíveis em linguagem de RH (sem exigir interpretação técnica de logs).

### Key Entities

- **Marco de admissão**: mês derivado da data de entrada + múltiplos de 6 meses; só o **próximo futuro** é acionável.
- **Ciclo automático de coorte**: um ciclo por mês de marco, criado no 1º dia útil, com `data_fim` = ativação + 20 dias, matriculando todos os elegíveis daquele marco.
- **Elegibilidade automática**: ativo ∧ data de entrada preenchida ∧ próximo marco futuro = mês corrente ∧ (no dia de abertura) ∧ sem bloqueio individual por ciclo ainda aberto (FR-008).
- **Alerta de ciclo ainda aberto**: evento de governança RH; não é trava de lote.
- **Pendência sem admissão**: ativo sem data de entrada, visível na governança, nunca matriculado pelo automático.
- **Governança RH**: superfície restrita de acompanhamento operacional do automático (entrantes, exclusões, alertas, falhas).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Em 100% dos testes do 1º dia útil do mês de marco, todos os elegíveis do lote (ex.: 10 de 10) recebem exatamente 1 Avaliação no ciclo da coorte; inelegíveis e sem data recebem 0.
- **SC-002**: Em 100% dos cenários de legado com marcos passados, o go-live / rotina diária cria **0** ciclos/Avaliações “atrasados”; a pessoa só entra no **próximo** marco futuro.
- **SC-003**: Em 100% dos ciclos automáticos criados, a data de fim operacional é ativação + 20 dias corridos.
- **SC-004**: Em 100% dos casos com pessoa ainda em ciclo aberto no novo marco, o RH recebe alerta e ≥1 outro elegível do mesmo lote é matriculado sem atraso causado pelo alerta.
- **SC-005**: Reexecução da rotina no mesmo dia de coorte: 0 ciclos duplicados e 0 Avaliações duplicadas.
- **SC-006**: Usuário sem permissão de gestão de ciclos obtém 0 acesso à governança global desta feature em 100% das tentativas de teste.
- **SC-007**: RH autorizado consegue, em até 5 minutos na governança, identificar entrantes do dia/período, pendências sem admissão e alertas de ciclo ainda aberto em base de teste controlada.
- **SC-008**: 100% das Avaliações já existentes permanecem intactas após edição de data de entrada ou após rodadas da rotina em ciclos encerrados.
- **SC-009**: Abertura manual 015 continua funcional com ciclo automático aberto (coexistência de abertos verificável em teste).

## Assumptions

- “Dia útil” = segunda a sexta, excluindo feriados nacionais brasileiros; implementação do calendário fica para o plano, a regra de negócio é Brasil nacional.
- “Concluída em 20 dias” = a avaliação do colaborador no ciclo automático deve chegar à conclusão operacional do fluxo de desempenho (etapa final de feedback concluída) dentro do prazo; a governança evidencia atraso; encerramento em massa do ciclo na `data_fim` pode ser automático ou assistido pelo RH desde que o prazo e a visibilidade existam.
- Um ciclo por coorte/mês (não um ciclo por pessoa) é o modelo que materializa “10 no corte de julho = os 10” com governança simples.
- Pessoa com ciclo ainda aberto: alerta + não matricula ela de novo no automático daquele marco; demais seguem (esteira intacta).
- Data de entrada é a mesma já usada em 015; não se cria segundo campo de admissão.
- Quem “pode gerir ciclos” continua sendo exatamente o papel/regra já vigente para abertura manual.
- Dashboards ou topbar que hoje assumem “um único ciclo aberto” precisarão tratar múltiplos abertos de forma honesta (mínimo: não mentir o contexto); redesign amplo de charts fica limitado ao necessário para não quebrar a verdade operacional.
- Dependência prática: dados de admissão preenchidos (backfill 015) — sem isso o automático só enxerga quem já tem data.
- Domínios tocados: cycles, reviews (matrícula), accounts (data de entrada), notifications/audit (alertas e trilha), possivelmente dashboard (múltiplos abertos); sem inventar app fora da constituição.
