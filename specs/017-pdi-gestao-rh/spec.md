# Feature Specification: Gestão RH/Gestão de PDIs Atrasados

**Feature Branch**: `017-pdi-gestao-rh`

**Created**: 2026-09-09

**Status**: Draft

**Input**: User description: "RH quer monitorar bem PDIs atrasados e fazer essa gestão. Hoje há alerta de PDIs para quem os criou/dono e tabela/listagem geral. Melhorar a gestão para visão RH/Gestão: mais filtros na listagem geral; notificação específica não só para colaborador mas para RH/Gestão; vista operacional; digest; board e fechamento do ciclo do plano."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Ver e filtrar PDIs com atraso no hub (Priority: P1)

Gestor, líder e admin (visão equipe/organização) abrem a listagem de PDIs e identificam imediatamente quais planos têm ações atrasadas. Podem filtrar para ver só esses planos e, em cada card, ver um indicador claro com a quantidade de ações atrasadas. Colaborador puro continua vendo só os próprios planos; o filtro de atrasados também se aplica à visão própria quando fizer sentido.

**Why this priority**: Sem visibilidade de atraso na listagem, RH/Gestão não consegue priorizar o acompanhamento — o status `atrasada` já existe, mas não aparece na superfície gerencial.

**Independent Test**: Criar PDIs no escopo com e sem ações atrasadas; aplicar o filtro “com atrasadas”; verificar que só os com atraso aparecem e que o indicador no card bate com a contagem real.

**Acceptance Scenarios**:

1. **Given** usuário com visão equipe/organização e PDIs no escopo (alguns com ações atrasadas, outros sem), **When** abre a listagem sem filtro de atraso, **Then** vê todos os planos elegíveis ao filtro de status/busca já existente e cada plano com atraso exibe indicador com a quantidade de ações atrasadas.
2. **Given** a mesma base, **When** aplica o filtro “com ações atrasadas”, **Then** a listagem mostra apenas PDIs do escopo que possuem ao menos uma ação atrasada (respeitando status do plano e busca já vigentes).
3. **Given** colaborador sem visão de equipe, **When** usa o filtro de atrasados, **Then** vê apenas os próprios PDIs com atraso; não vê planos de outras pessoas.
4. **Given** PDI arquivado, **When** a listagem está em “Em andamento” ou filtro de atrasados sem incluir arquivados, **Then** esse PDI não aparece entre os operacionais (arquivados só na visão de arquivados, como hoje).

---

### User Story 2 - Alertar dono e gestor quando a ação fica atrasada (Priority: P1)

Quando uma ação de PDI passa a estar atrasada, o sistema notifica o dono do plano e o gestor direto do dono (quando existir e for distinto). O lembrete preventivo já existente (antes do prazo) permanece para o dono; esta história cobre o evento de **atraso efetivo**, que hoje só marca status e não avisa ninguém.

**Why this priority**: Gestão de atraso sem notificação depende de alguém abrir a tela; o alerta fecha o ciclo entre “ficou atrasado” e “alguém age”.

**Independent Test**: Ter ação com prazo vencido elegível à marcação de atraso; após o processamento diário (ou equivalente de teste), verificar notificação ao dono e ao gestor direto, sem duplicar o mesmo evento na mesma janela.

**Acceptance Scenarios**:

1. **Given** ação não concluída cujo prazo já passou e PDI não arquivado, **When** o sistema marca a ação como atrasada, **Then** o dono do PDI recebe notificação de atraso referente a essa ação.
2. **Given** o mesmo caso e o dono possui gestor direto ativo distinto dele, **When** a ação é marcada como atrasada, **Then** o gestor direto também recebe notificação de atraso referente a essa ação.
3. **Given** dono sem gestor direto (ou gestor inativo), **When** a ação é marcada como atrasada, **Then** apenas o dono é notificado; o fluxo não falha.
4. **Given** a mesma ação já notificada como atrasada na janela de deduplicação, **When** o processamento roda de novo, **Then** não reenvia o mesmo alerta duplicado para o mesmo destinatário.
5. **Given** PDI arquivado ou ação já concluída, **When** o processamento de atraso/notificação roda, **Then** não envia alerta de atraso para essa ação.

---

### User Story 3 - Vista tabela operacional para RH/Gestão (Priority: P2)

Na visão equipe/organização, gestor e admin podem alternar entre a visão de cards e uma **vista tabela** orientada a operação: colaborador, gestor, área (quando disponível), progresso do plano, quantidade de ações atrasadas, dias do atraso mais antigo e próximo prazo. Filtros gerenciais adicionais permitem restringir por gestor, área e faixa de atraso (ex.: 1–7, 8–30, mais de 30 dias), além do filtro de “com atrasadas” e dos filtros já existentes.

**Why this priority**: Cards não escalam para RH acompanhar dezenas/centenas de planos; a tabela é a superfície de gestão diária.

**Independent Test**: Como admin/gestor na visão equipe, alternar para tabela, aplicar filtros de gestor/área/faixa de atraso e conferir que linhas e totais batem com o escopo e com os dados das ações.

**Acceptance Scenarios**:

1. **Given** admin ou gestor na visão equipe/organização, **When** escolhe a vista tabela, **Then** vê uma linha por PDI do escopo (respeitando filtros) com colaborador, gestor, progresso, nº de atrasadas, dias do atraso mais antigo e próximo prazo.
2. **Given** vista tabela, **When** filtra por gestor, área ou faixa de atraso, **Then** só permanecem PDIs do escopo que satisfazem o critério.
3. **Given** colaborador sem visão equipe, **When** acessa a listagem, **Then** não vê a vista tabela gerencial nem filtros de gestor/área de outros; permanece a experiência própria.
4. **Given** PDI sem ações atrasadas, **When** aparece na tabela sem filtro de atraso, **Then** a coluna de atrasadas mostra zero (ou equivalente vazio claro) e dias de atraso mais antigo fica vazio/não aplicável.

---

### User Story 4 - Digest periódico para RH/Admin (Priority: P2)

Admin (visão organização) recebe periodicamente um resumo consolidado de PDIs/ações atrasadas no escopo organizacional: totais, destaque de áreas ou gestores com mais atraso, e caminho claro para abrir a listagem já filtrada. Não é um e-mail por ação para RH.

**Why this priority**: RH precisa de oversight sem ruído; digest agrega o que o alerta por ação faz para colaborador/gestor.

**Independent Test**: Com base conhecida de atrasos na org, disparar o digest e verificar destinatários admin, conteúdo agregado coerente e ausência de envio quando não há atrasos (ou mensagem explícita de “zero atrasos”, conforme regra abaixo).

**Acceptance Scenarios**:

1. **Given** há ações atrasadas em PDIs não arquivados na organização, **When** o digest periódico é gerado, **Then** cada admin ativo elegível recebe um resumo com totais de ações/PDIs atrasados e indicação dos maiores focos (áreas e/ou gestores).
2. **Given** digest recebido, **When** o admin segue o caminho indicado, **Then** chega à listagem de PDIs com filtro de atrasados (ou equivalente) já aplicado no escopo organização.
3. **Given** não há ações atrasadas elegíveis na organização, **When** o digest rodaria, **Then** o sistema **não** envia e-mail vazio de “zero atrasos” (silêncio operacional).
4. **Given** líder/gestor que não é admin, **When** o digest RH roda, **Then** essa pessoa **não** recebe o digest organizacional (já recebe alertas pontuais da Story 2 no próprio time).

---

### User Story 5 - Widget de atrasos no dashboard do escopo (Priority: P3)

No dashboard já usado por líder/gestor/admin, aparece um bloco resumido de PDIs/ações atrasados no escopo do usuário, com contagem e link para a listagem filtrada. Não substitui a tabela operacional; é atalho de awareness.

**Why this priority**: Aumenta descoberta do problema sem exigir ir direto ao módulo PDI; depende das Stories 1–3 para o destino do link ser útil.

**Independent Test**: Usuário com atrasos no escopo vê contagem correta e o link abre a listagem filtrada; usuário sem atrasos vê zero ou estado vazio claro.

**Acceptance Scenarios**:

1. **Given** líder/gestor/admin com ações atrasadas no escopo, **When** abre o dashboard, **Then** vê o bloco com contagem coerente ao escopo e link para a listagem de PDIs com filtro de atrasados.
2. **Given** usuário sem atrasos no escopo, **When** abre o dashboard, **Then** o bloco mostra zero (ou estado vazio) sem erro.
3. **Given** colaborador sem dashboard gerencial (ou sem acesso ao bloco), **When** navega o produto, **Then** não vê dados de atraso de outras pessoas.

---

### User Story 6 - Board com coluna Atrasadas e conclusão do plano (Priority: P3)

No detalhe do PDI, ações atrasadas aparecem em coluna própria (não misturadas apenas em “Em andamento”). Quando todas as ações estão concluídas, o usuário autorizado no escopo pode marcar o plano como concluído (ou o sistema oferece esse fechamento de forma explícita), deixando o status `concluido` utilizável no produto — não só via import legado.

**Why this priority**: Melhora o dia a dia do acompanhamento e fecha o ciclo de vida do plano para reportar conclusão vs arquivamento.

**Independent Test**: Mover/visualizar ação atrasada na coluna correta; com 100% concluídas, concluir o plano e vê-lo no filtro de concluídos; plano arquivado permanece sem mutações indevidas.

**Acceptance Scenarios**:

1. **Given** PDI ativo com ações em status atrasada, **When** o usuário abre o detalhe/board, **Then** essas ações aparecem na coluna Atrasadas.
2. **Given** PDI ativo com todas as ações concluídas, **When** o usuário autorizado conclui o plano, **Then** o PDI passa a status concluído e aparece no filtro de concluídos da listagem.
3. **Given** PDI com alguma ação não concluída, **When** tenta concluir o plano, **Then** a operação é recusada com feedback claro.
4. **Given** PDI arquivado, **When** o usuário tenta concluir ou alterar ações, **Then** permanece o bloqueio já existente de mutações em arquivado.

---

### Edge Cases

- Ação sem prazo definido: não entra em atraso nem em faixas de atraso; não gera alerta de atraso.
- Responsável da ação diferente do dono do PDI: alertas de atraso desta feature vão ao **dono** e ao **gestor do dono** (não ao responsável, salvo se coincidir).
- Gestor do dono é o próprio dono (auto-gestão / edge): não duplicar envio; um único destinatário.
- Admin que também é gestor direto: pode receber alerta pontual (Story 2) e digest (Story 4); são canais distintos e ambos válidos.
- Mudança de prazo que tira a ação do atraso: status volta conforme regra já existente; não reenvia alerta de atraso até novo vencimento.
- Escopo: ninguém vê ou é notificado sobre PDIs fora do seu escopo hierárquico (admin = organização).
- Plano sem ações: não aparece como “com atrasadas”; progresso zero; elegível ao estado “aguardando” já existente.
- Faixa de atraso com prazo exatamente no limite: faixas são inclusivas no limite inferior e exclusivas no superior, exceto a última (“mais de 30”) que é aberta.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O sistema MUST permitir filtrar a listagem de PDIs para exibir apenas planos do escopo do usuário que possuem ao menos uma ação com status atrasada.
- **FR-002**: O sistema MUST exibir, na listagem (cards e tabela), indicador da quantidade de ações atrasadas por PDI quando essa quantidade for maior que zero.
- **FR-003**: O sistema MUST, ao marcar uma ação como atrasada, notificar o dono do PDI e, quando existir e for distinto/ativo, o gestor direto do dono.
- **FR-004**: O sistema MUST deduplicar alertas de atraso por destinatário e ação dentro da janela operacional, evitando reenvio repetido do mesmo evento.
- **FR-005**: O sistema MUST preservar o lembrete preventivo existente (antes do prazo) ao dono do PDI; esta feature NÃO remove esse lembrete.
- **FR-006**: Na visão equipe/organização, admin e gestor MUST poder alternar para vista tabela operacional com colunas: colaborador, gestor, área (se disponível no cadastro), progresso, nº de atrasadas, dias do atraso mais antigo, próximo prazo.
- **FR-007**: Na vista gerencial, o sistema MUST oferecer filtros por gestor, área e faixa de atraso (1–7 dias, 8–30 dias, mais de 30 dias), combináveis com status/busca/atrasados já definidos.
- **FR-008**: Colaborador sem visão de equipe MUST NOT acessar a vista tabela gerencial nem dados de PDIs fora do próprio escopo.
- **FR-009**: O sistema MUST enviar digest periódico (semanal) aos admins ativos com consolidado de atrasos da organização, apenas quando houver ao menos um atraso elegível.
- **FR-010**: O digest MUST incluir totais e indicação dos maiores focos (áreas e/ou gestores) e um caminho para a listagem filtrada por atrasados.
- **FR-011**: O dashboard do escopo (líder/gestor/admin) MUST exibir bloco resumido de atrasos de PDI com contagem e link para a listagem filtrada.
- **FR-012**: No detalhe do PDI, ações atrasadas MUST aparecer em coluna/agrupamento próprio “Atrasadas”.
- **FR-013**: Usuário autorizado no escopo do dono MUST poder concluir um PDI ativo somente quando todas as ações estiverem concluídas; o plano passa a status concluído e entra no filtro de concluídos.
- **FR-014**: Toda listagem, filtro, widget e notificação MUST respeitar o escopo hierárquico já vigente (colaborador / líder / gestor / admin); sem novo papel “RH” dedicado.
- **FR-015**: PDIs arquivados MUST permanecer fora dos fluxos operacionais de atraso (filtro padrão, alertas de novo atraso, digest e widget), salvo quando o usuário explicitamente consulta arquivados.

### Key Entities

- **PDI**: Plano de desenvolvimento do colaborador (dono); status ativo, concluído ou arquivado; progresso derivado das ações.
- **Ação de PDI**: Item com responsável, prazo e status (pendente, em andamento, concluída, atrasada).
- **Escopo de visibilidade**: Conjunto de colaboradores que o usuário autenticado pode ver, baseado na hierarquia (line manager) e admin organização.
- **Alerta de atraso de PDI**: Notificação disparada quando a ação entra em atraso; destinatários dono e gestor direto do dono.
- **Digest de atraso de PDI**: Resumo periódico agregado para admin, sem um e-mail por ação.
- **Vista operacional de PDI**: Representação tabular gerencial dos planos no escopo, com métricas de atraso.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Em até 1 minuto, um gestor ou admin encontra na listagem todos os PDIs com atraso do seu escopo usando o filtro dedicado (validável em base de teste conhecida).
- **SC-002**: 100% das ações que passam a atrasada geram notificação ao dono (e ao gestor direto quando aplicável) na janela do processamento diário, sem duplicata na mesma janela de dedupe.
- **SC-003**: Admin consegue, na vista tabela, identificar o PDI com maior atraso (dias) e filtrar por faixa em menos de 2 minutos em base com pelo menos 20 planos.
- **SC-004**: Digest semanal só é enviado quando há atraso; em semanas sem atraso, zero e-mails de digest RH são disparados.
- **SC-005**: Usuário sem escopo adequado não consegue ver contagens, linhas ou detalhes de PDIs de pessoas fora do escopo (incluindo via links de digest/widget).
- **SC-006**: Planos 100% concluídos podem ser marcados como concluídos na UI e passam a aparecer no filtro de concluídos sem depender de importação legada.

## Assumptions

- “RH” nesta feature corresponde ao papel **admin** já existente (visão organização); não se cria papel RH separado.
- “Gestão” corresponde a líder/gestor com visão equipe no escopo hierárquico já existente.
- O “alerta para quem criou” referido pelo negócio mapeia, no produto atual, ao **dono do PDI** (`usuario` do plano); esta feature não introduz entidade “criador” separada.
- Destinatários de alerta de atraso: **dono + gestor direto do dono**. Responsável da ação não recebe canal próprio nesta fatia (pode coincidir com o dono).
- Lembrete preventivo pré-prazo permanece só para o dono nesta fatia (cópia preventiva ao gestor fica fora de escopo).
- Canal de notificação: o mesmo canal de e-mail já usado pelos lembretes de PDI; push/in-app fora de escopo.
- Frequência do digest RH: **semanal**; dia/hora alinhados ao agendamento operacional existente de notificações.
- Vista tabela e filtros gerenciais: disponíveis para **admin e gestor** na visão equipe/organização; líder com visão equipe também pode usar a tabela no próprio escopo.
- Área na tabela: usa o dado de área já disponível no cadastro organizacional do colaborador; se ausente, coluna vazia.
- Faixas de atraso baseadas no atraso mais antigo do plano (maior número de dias em atraso entre ações atrasadas).
- Conclusão do plano é **ação explícita** do usuário autorizado quando 100% das ações estão concluídas (não conclusão silenciosa automática sem confirmação).
- Fora de escopo nesta feature: novo papel RH; API REST; push mobile; notificar todos os admins a cada ação atrasada individualmente; reescrever o módulo de aderência de liderança; importação legada adicional.
