# Feature Specification: Elegibilidade de Ciclo por “Admitidos até” (Corte na Abertura)

**Feature Branch**: `015-cycle-admission-cutoff`

**Created**: 2026-08-20

**Status**: Draft

**Input**: User description: "Elegibilidade de ciclo por 'admitidos até' (corte na abertura). Abrir ciclo deixa de matricular todos os ativos; RH informa data de corte por ciclo; elegíveis = ativo + data de entrada preenchida ≤ corte (inclusivo). Mesma regra na matrícula mid-cycle. Snapshot = Avaliacao já criada permanece. Backfill idempotente da data de entrada a partir do backup de colaboradores (coluna ignorada na 010). Spec seguinte à 014; não é fatia de importação de legado, mas precisa de dados de admissão."

## Clarifications

### Session 2026-08-20 (decisões fechadas — não reabrir)

- **Critério**: uma data de corte **por ciclo** (“admitidos até”), independente de `data_inicio` / `data_fim`. Não reutilizar `data_inicio`. Não criar lista manual/M2M de participantes. Não criar coorte no usuário.
- **Momento operacional**: ABERTURA do ciclo. RH **deve** informar “admitidos até” para abrir. Sem essa data, o ciclo **não** abre e **não** cria avaliações.
- **Elegível**: ativo **e** data de entrada preenchida **e** data de entrada ≤ corte (inclusivo). Inativo nunca entra. Sem data de entrada = não elegível (não matricula).
- **Mesma regra** na abertura **e** na matrícula mid-cycle (cadastro ativo / reativação com ciclo aberto).
- **Snapshot**: a própria Avaliação. Quem já foi matriculado permanece, mesmo se a data de entrada for editada depois. Elegibilidade só governa **criação**, nunca remoção/desfazer etapa/fechar avaliação.
- **Ciclos históricos** já encerrados (import 011 e arquivo operacional): **não** reprocessar. Campo de corte ausente/nulo é válido. Não criar/apagar Avaliação de ciclo encerrado.
- **Quem abre/cria ciclo**: exatamente os papéis/regras já existentes. Esta feature **não** inventa papel, **não** muda hierarquia, **não** muda `get_visible_users` / `ScopedObjectMixin`. Líder e colaborador **não** definem o corte.
- **Dados**: reutilizar a data de entrada já existente no colaborador. Persistir o corte **no ciclo**, aditivo e opcional no armazenamento; obrigatório só na regra de abertura operacional nova. Uma evolução aditiva de schema; sem M2M, sem tabela de participantes, sem alterar tipo/unicidade da data de entrada.
- **Pré-requisito de dados**: carga idempotente que preenche data de entrada **vazia** a partir de “Data admissão” do backup de colaboradores (formatos já aceitos no legado). Não sobrescrever data já preenchida. Não reimportar outros campos. Sem UI de upload.
- **Única trava nova de abertura**: ausência do “admitidos até”. Checklist 008 (área/cargo/competências) permanece avisório. Pessoas sem data simplesmente não entram.
- **Exceção pontual** (forçar inelegível no ciclo): fora de escopo. Correção de data de entrada que passa a cumprir o critério **pode** gerar matrícula mid-cycle se o ciclo ainda estiver aberto e ainda não houver avaliação.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Abrir ciclo só com elegíveis pelo corte (Priority: P1)

O RH (mesmo papel que já abre ciclo) informa a data “Admitidos até” ao abrir um ciclo. O sistema matricula **somente** colaboradores ativos com data de entrada preenchida e ≤ ao corte (inclusivo). Inativos, ativos com entrada posterior ao corte e ativos sem data de entrada **não** recebem avaliação. A mensagem de sucesso **não** afirma mais que foram matriculados “todos os ativos”. Continua a existir no máximo um ciclo aberto.

**Why this priority**: É o núcleo do problema — ciclo e avaliações deixam de significar “todos os ativos”. Sem isto o produto não entrega o controle de coorte por admissão.

**Independent Test**: Abrir um ciclo com corte D e base controlada de ativos (entrada ≤ D, entrada > D, sem entrada) e inativos; verificar exatamente 1 Avaliação por elegível, zero nos demais, e mensagem de sucesso coerente com o novo contrato.

**Acceptance Scenarios**:

1. **Given** ciclo ainda não aberto e data de corte D informada pelo RH autorizado, **When** a abertura é confirmada, **Then** cada ativo com data de entrada ≤ D recebe exatamente 1 Avaliação neste ciclo; ativos com entrada > D, ativos sem entrada e inativos recebem zero.
2. **Given** tentativa de abrir sem informar o corte, **When** a abertura é solicitada, **Then** a operação falha de forma visível; o ciclo permanece não aberto; zero Avaliações novas são criadas.
3. **Given** abertura bem-sucedida, **When** o RH vê a confirmação, **Then** a mensagem **não** diz que foram matriculados “todos os ativos”; reflete que a matrícula seguiu o critério de elegibilidade do corte.
4. **Given** já existe um ciclo aberto, **When** se tenta abrir outro, **Then** permanece o erro/comportamento já existente de “só um ciclo aberto”; esta feature não altera essa regra.
5. **Given** ciclo já aberto, **When** a abertura é reenviada, **Then** continua o erro existente; não duplica Avaliações (ainda no máximo 1 por ciclo+colaborador).

---

### User Story 2 - Preview honesto antes de abrir (Priority: P1)

No fluxo de abertura que o admin/RH já usa, ao informar (ou ao preparar) o “Admitidos até”, o RH vê contagens honestas: quantos ativos entram, quantos ficam de fora por admissão posterior e quantos ativos estão sem data de entrada. O preview é informativo; não exige confirmação em duas etapas além do POST de abrir já existente. Apenas o mesmo papel que já vê a abertura tem acesso a essas contagens — sem rota pública e sem vazar listas de pessoas fora do escopo para líder/colaborador.

**Why this priority**: Sem preview, o RH abre “às cegas” e não consegue validar o impacto do corte antes de matricular.

**Independent Test**: Com base conhecida, informar corte D e verificar que as três contagens batem com a regra de elegibilidade; usuário sem permissão de gestão de ciclo não obtém o preview.

**Acceptance Scenarios**:

1. **Given** RH autorizado no fluxo de abertura com corte D, **When** o preview é apresentado, **Then** mostra: (a) quantidade de ativos elegíveis (entrada ≤ D); (b) quantidade de ativos excluídos por admissão posterior (entrada > D); (c) quantidade de ativos sem data de entrada.
2. **Given** preview exibido, **When** o RH segue com o POST de abrir já existente, **Then** não há etapa adicional obrigatória de confirmação além desse POST.
3. **Given** usuário sem permissão para gerir ciclos, **When** tenta obter preview ou abrir, **Then** recebe a mesma negação de acesso já vigente (equivalente ao 403 de hoje na abertura); nenhuma lista de exclusões é exposta a líder/colaborador fora do escopo.

---

### User Story 3 - Matrícula mid-cycle com a mesma elegibilidade (Priority: P1)

Com ciclo aberto que possui corte D, um novo cadastro ativo ou uma reativação **só** gera Avaliação se a pessoa for elegível sob a mesma regra (ativo + data de entrada ≤ D). Cadastro/reativação com entrada > D ou sem data de entrada **não** matricula. Com ciclo encerrado, zero matrícula nova por esse caminho. Se a data de entrada for corrigida depois e a pessoa passar a ser elegível ainda no ciclo aberto **e** ainda não tiver Avaliação, a matrícula mid-cycle existente **pode** criar a Avaliação; se já tiver, não duplica.

**Why this priority**: Se o corte só valesse na abertura, o cadastro mid-cycle furaria a regra — isso é bug, não escopo futuro.

**Independent Test**: Ciclo aberto com D; cadastrar/reativar ativo elegível → 1 Avaliação; inelegível ou sem data → 0; ciclo encerrado → 0; correção de data para elegível sem Avaliação prévia → 1; com Avaliação prévia → continua 1.

**Acceptance Scenarios**:

1. **Given** ciclo aberto com corte D e novo cadastro ativo com entrada ≤ D, **When** a matrícula mid-cycle ocorre, **Then** é criada exatamente 1 Avaliação.
2. **Given** ciclo aberto com corte D e cadastro/reativação ativo com entrada > D ou sem entrada, **When** a matrícula mid-cycle é avaliada, **Then** zero Avaliações são criadas.
3. **Given** ciclo encerrado, **When** ocorre cadastro/reativação, **Then** zero Avaliações novas por esse fluxo.
4. **Given** pessoa inelegível no ciclo aberto cuja data de entrada é corrigida para ≤ D e ainda sem Avaliação, **When** a matrícula mid-cycle vigente se aplica, **Then** pode ser criada 1 Avaliação; se já existia Avaliação, permanece 1 (não duplica).
5. **Given** pessoa já matriculada neste ciclo, **When** a data de entrada é editada depois (inclusive para valor > D ou vazio), **Then** a Avaliação existente **permanece**; não é apagada, não desfaz etapa e não fecha por mudança de data.

---

### User Story 4 - Backfill da data de entrada a partir do backup (Priority: P1)

Antes de usar o corte em produção com legado, o operador técnico executa uma carga idempotente que preenche **somente** data de entrada **vazia** a partir da coluna “Data admissão” do backup de colaboradores (mesmos formatos de data já aceitos no legado: serial Excel e ISO). Não sobrescreve data já preenchida no cadastro. Não reimporta nome, e-mail, área, cargo, gestor nem ativo. Não chama abertura/fechamento de ciclo. Sem PII extra no relatório além de totais e amostra mascarada. Suporta dry-run (zero writes), persistência em transação e sem UI de upload. Residuais sem data no Excel ou só auto-cadastro continuam não elegíveis; o preview na abertura mostra a contagem.

**Why this priority**: A importação 010 ignorou “Data admissão”; sem backfill o corte exclui quase todo o legado e a feature de elegibilidade fica inoperante na prática.

**Independent Test**: Dry-run sem writes; persist preenche só vazios; segunda execução com delta 0 nesses campos; usuário com data já preenchida intacto; zero efeito em abertura/fechamento de ciclo.

**Acceptance Scenarios**:

1. **Given** backup com “Data admissão” interpretável e colaborador com data de entrada vazia, **When** a carga persiste, **Then** a data de entrada é preenchida com o valor interpretado; demais campos do colaborador permanecem intactos.
2. **Given** colaborador com data de entrada já preenchida, **When** a carga roda, **Then** essa data **não** é sobrescrita.
3. **Given** dry-run, **When** a carga é executada, **Then** zero gravações; o relatório ainda traz totais esperados.
4. **Given** segunda execução após persist bem-sucedido, **When** a carga roda de novo, **Then** o delta de preenchimento nesses campos é 0.
5. **Given** linha sem data no Excel ou pessoa só de auto-cadastro sem data, **When** a carga termina, **Then** a pessoa permanece sem data de entrada (não elegível até preencher); o preview de abertura continua mostrando a contagem de ativos sem data.
6. **Given** execução da carga, **When** o relatório é gerado, **Then** inclui totais operacionais e amostra mascarada; sem UI de upload; não chama abrir/fechar ciclo.

---

### User Story 5 - Ciclos históricos e denylist intactos (Priority: P2)

Ciclos já encerrados (import 011 e arquivo operacional) com corte ausente/nulo permanecem válidos e intactos: nenhuma Avaliação extra criada nem removida; elegibilidade **não** é relida. Importações 010/011/013/014 e comandos associados **não** passam a exigir o novo campo nem a chamar abertura. Domínios de etapa, aprovação de metas, fórmula, aderência, 9-box, PDI, notificações, visão histórica 012, AuthZ/hierarquia, encerramento manual e freeze de conclusão no close **não** mudam de comportamento de negócio. Checklist 008 permanece avisório para área/cargo/competências — a **única** trava nova de abertura é a ausência do “admitidos até”.

**Why this priority**: Protege o arquivo histórico e evita regressão em superfícies que não são esta feature.

**Independent Test**: Ciclo encerrado sem corte permanece com o mesmo conjunto de Avaliações; suite vigente de etapa/escopo/rejeição/fórmula verde sem alterar asserts alheios; testes de “matrícula = todos os ativos” atualizados de propósito para o novo contrato; gold diff vazio nas áreas da denylist.

**Acceptance Scenarios**:

1. **Given** ciclo 011/arquivo encerrado sem corte, **When** qualquer operação desta feature ocorre, **Then** o ciclo e suas Avaliações permanecem intactos (zero criações/remoções por reprocessamento de elegibilidade).
2. **Given** comandos/cargas 010/011/013/014, **When** executados após esta feature, **Then** **não** exigem o campo de corte; **não** chamam abertura; status encerrado permanece intacto (exceto o backfill estrito de data de entrada vazia desta feature).
3. **Given** abertura de ciclo operacional novo, **When** área/cargo/competências estão incompletos no sentido do checklist 008, **Then** o checklist continua avisório; a abertura **só** é bloqueada pela ausência do “admitidos até” (além das regras já existentes, ex.: um ciclo aberto).
4. **Given** líder no escopo vigente, **When** alguém do time não foi matriculado por inelegibilidade, **Then** simplesmente não há Avaliação daquela pessoa naquele ciclo; escopo e URLs de negócio de avaliação/metas/PDI/dashboard permanecem os mesmos.

### Edge Cases

- Ativo sem data de entrada: nunca elegível; conta no preview como “sem data”; não gera Avaliação na abertura nem mid-cycle.
- Inativo: nunca elegível, mesmo com data ≤ corte.
- Corte igual à data de entrada: elegível (inclusivo).
- Corte informado e depois a data de entrada do matriculado muda: Avaliação existente permanece (snapshot).
- Correção de data que torna elegível alguém ainda sem Avaliação em ciclo aberto: matrícula mid-cycle pode criar; se já tinha, não duplica.
- Abrir sem corte: falha visível; ciclo não abre; zero Avaliações novas.
- Ciclo encerrado / importado sem corte: campo nulo válido; sem reprocessamento.
- Tentativa de matricular forçadamente inelegível ou “desfazer” Avaliação por mudança de data: fora de escopo (não suportado).
- Usuário sem permissão de gestão de ciclo: mesma negação de acesso da abertura hoje; sem preview privilegiado.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O sistema MUST exigir uma data de corte “admitidos até” **por ciclo** no momento da abertura operacional; sem essa data, MUST negar a abertura e MUST NOT criar Avaliações.
- **FR-002**: A data de corte MUST ser independente de `data_inicio` e `data_fim` do ciclo; MUST NOT reutilizar `data_inicio` como corte.
- **FR-003**: Na abertura, o sistema MUST criar Avaliação apenas para colaboradores que sejam **ativos**, com **data de entrada preenchida** e **data de entrada ≤ corte** (inclusivo, data de calendário).
- **FR-004**: Inativos e ativos sem data de entrada MUST NOT receber Avaliação por abertura ou matrícula mid-cycle.
- **FR-005**: A mesma regra de elegibilidade de FR-003/FR-004 MUST aplicar-se à matrícula mid-cycle (cadastro ativo / reativação com ciclo aberto).
- **FR-006**: Elegibilidade MUST governar apenas a **criação** de Avaliação; MUST NOT apagar, desfazer etapa ou fechar Avaliação já existente por mudança posterior da data de entrada.
- **FR-007**: MUST persistir o valor do corte no ciclo de forma aditiva; ciclos históricos/importados sem corte MUST permanecer válidos com corte ausente/nulo.
- **FR-008**: Ciclos já encerrados MUST NOT ser reprocessados para reler elegibilidade nem para criar/apagar Avaliações.
- **FR-009**: MUST reutilizar a data de entrada já existente no colaborador; MUST NOT criar segundo campo de admissão; MUST NOT tornar a data de entrada obrigatória no armazenamento para auto-cadastro/legado.
- **FR-010**: Schema MUST evoluir de forma aditiva (um passo aditivo); MUST NOT introduzir M2M/tabela de participantes/mapa; MUST NOT alterar tipo/unicidade da data de entrada; MUST NOT criar FK nova Avaliação↔ciclo além da já existente.
- **FR-011**: No fluxo de abertura do papel admin/RH já autorizado, o sistema MUST oferecer preview com contagens: elegíveis, excluídos por admissão posterior, ativos sem data de entrada.
- **FR-012**: Preview e gravação de corte/abertura MUST restringir-se a quem já pode gerir ciclos; POST de abertura sem permissão MUST manter a mesma negação de acesso vigente; MUST NOT criar rota pública de preview nem expor listas de exclusão a líder/colaborador fora do escopo.
- **FR-013**: Mensagem de sucesso da abertura MUST NOT afirmar matrícula de “todos os ativos”.
- **FR-014**: A regra “no máximo um ciclo aberto” MUST permanecer inalterada.
- **FR-015**: Backend MUST ser a fonte da regra de elegibilidade e criação de Avaliação; a UI MUST NOT ser a fonte da regra.
- **FR-016**: MUST incluir carga operacional idempotente de backfill da data de entrada vazia a partir de “Data admissão” do backup de colaboradores (formatos serial Excel e ISO já aceitos), com dry-run, transação, relatório de totais + amostra mascarada, sem UI de upload e sem chamar abrir/fechar ciclo.
- **FR-017**: O backfill MUST NOT sobrescrever data de entrada já preenchida e MUST NOT reimportar nome, e-mail, área, cargo, gestor ou ativo.
- **FR-018**: Importações/comandos 010/011/013/014 MUST NOT passar a exigir o campo de corte nem a chamar abertura; MUST permanecer intactos exceto pelo backfill estrito de FR-016/FR-017.
- **FR-019**: Checklist 008 (área/cargo/competências) MUST permanecer avisório; a **única** trava **nova** de abertura MUST ser a ausência do “admitidos até”.
- **FR-020**: Autorização, hierarquia e escopo vigentes (`get_visible_users` / `ScopedObjectMixin` e papéis que já abrem ciclo) MUST permanecer inalterados; líder e colaborador MUST NOT definir o corte.
- **FR-021**: Auditoria append-only existente MUST registrar o que o produto já grava em mudanças de ciclo/usuário; o valor do “admitidos até” MUST ser rastreável no ciclo após a abertura (sem inventar trilha paralela).
- **FR-022**: MUST NOT alterar máquina de etapas, aprovação/reprovação de metas, fórmulas de nota, aderência, 9-box, PDI, notificações, visão histórica 012, URLs de negócio de avaliação/metas/PDI/dashboard, encerramento manual, imutabilidade de avaliações existentes nem freeze de conclusão no close — salvo o ajuste do fluxo de abertura de ciclo (campo + preview + mensagem) nas telas de ciclo que o admin já usa.
- **FR-023**: MUST NOT oferecer nesta feature: filtros de cadastro novos, paginação 15, varredura visual/Freeze, lista manual de exceções, matrícula forçada de inelegível ou desfazer Avaliação.
- **FR-024**: Idempotência de matrícula MUST garantir no máximo 1 Avaliação por ciclo+colaborador (abertura e mid-cycle).

### Key Entities

- **Ciclo**: período operacional de avaliação; passa a poder armazenar opcionalmente a data de corte “admitidos até”; na abertura operacional nova o corte é obrigatório pela regra de negócio.
- **Data de entrada (colaborador)**: data de calendário já existente no cadastro; base do critério de elegibilidade; pode permanecer vazia (legado/auto-cadastro).
- **Avaliação**: matrícula do colaborador no ciclo; criação condicionada à elegibilidade; uma vez criada, permanece como snapshot mesmo se a data de entrada mudar.
- **Elegibilidade**: regra de negócio (ativo ∧ data de entrada preenchida ∧ data de entrada ≤ corte); aplica-se na abertura e na matrícula mid-cycle; não remove matrículas existentes.
- **Backfill de admissão**: carga one-shot/operacional que completa data de entrada vazia a partir do backup de colaboradores, sem reabrir o restante da importação 010.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Em 100% das aberturas com corte D em base de teste controlada, ativos com entrada ≤ D recebem exatamente 1 Avaliação; ativos com entrada > D, sem entrada e inativos recebem 0.
- **SC-002**: 100% das tentativas de abrir sem informar o corte falham de forma visível, deixam o ciclo não aberto e criam 0 Avaliações novas.
- **SC-003**: Em ciclo aberto, 100% dos cadastros/reativações elegíveis geram 1 Avaliação; 100% dos inelegíveis (entrada > D ou sem entrada) geram 0; ciclo encerrado gera 0.
- **SC-004**: Após matrícula, 100% das edições posteriores da data de entrada **não** removem nem fecham a Avaliação já existente daquele ciclo.
- **SC-005**: Ciclos encerrados/importados sem corte permanecem com o mesmo conjunto de Avaliações (0 criações/remoções por reprocessamento).
- **SC-006**: RH autorizado consegue, no fluxo de abertura, ver as três contagens do preview alinhadas à regra antes de confirmar a abertura.
- **SC-007**: Backfill em dry-run: 0 writes; em persist: só preenche data de entrada antes vazia; segunda execução: delta 0 nesses campos; datas já preenchidas intactas em 100% dos casos de teste.
- **SC-008**: Mensagem de sucesso da abertura, em 100% dos casos, deixa de afirmar matrícula de “todos os ativos”.
- **SC-009**: Testes vigentes de etapa, escopo, rejeição e fórmula permanecem verdes sem mudança de asserts de negócio alheios; testes que assumiam “matrícula = todos os ativos” são atualizados de propósito para o novo contrato; gold com diff vazio em stage, approval, evaluation (fórmula), adherence, talent, pdi (salvo se o backfill não os toca), scope e urls 012.

## Assumptions

- “Até” é inclusivo na data de calendário já usada no cadastro (date, não datetime / mesmo fuso operacional do cadastro).
- Preview é informativo; não exige confirmação em duas etapas além do POST de abrir já existente.
- Exceção pontual (meter alguém inelegível no ciclo) fica fora; RH corrige a data de entrada e, se ainda no ciclo aberto e passar a elegível sem Avaliação prévia, a matrícula mid-cycle vigente pode criar a Avaliação.
- Volume da abertura continua síncrono (N ativos), sem novo processamento em fila só para o corte.
- Domínios tocados: cycles (corte + abertura), reviews (matrícula/criação de Avaliação), accounts (data de entrada + backfill); sem app nova.
- A feature **não** é fatia de importação de legado no sentido 010–014, mas **depende** do backfill de admissão para o corte funcionar com o legado em produção.
- Quem pode abrir ciclo continua sendo exatamente quem já pode hoje (admin/RH conforme regras vigentes).
- Data de entrada já é visível ao admin de organização no cadastro; esta feature não cria novas superfícies de exposição dessa data para colaborador/líder além do necessário ao admin na abertura (contagens agregadas no preview).
