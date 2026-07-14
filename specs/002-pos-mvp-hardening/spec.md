# Feature Specification: Hardening Operacional Pós-MVP

**Feature Branch**: `002-pos-mvp-hardening`

**Created**: 2026-07-14

**Status**: Draft

**Input**: User description: "Feature hardening pós-MVP do Greenn People (~130 colaboradores / 6 gestores). Corrigir lacunas operacionais após o MVP da gestão de desempenho, PDI e talentos, sem introduzir DRF/SPA e mantendo escopo no backend, imutabilidade de histórico e stack atual."

## Declaração do Problema (O Porquê)

Após o MVP, o ciclo de desempenho opera, mas lacunas operacionais travam o dia a dia do RH e dos gestores: colaborador fica sem caminho após reprovação pontual; admitidos mid-cycle ficam sem avaliação; offboarding com liderados exige retrabalho manual; catálogos fragilizam integridade; gestor ausente bloqueia aprovações; lembretes e PDI atrasada geram ruído; falta preparação mínima para produção e verificação automatizada das regras críticas.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Destravar item reprovado sem retroceder a etapa (Priority: P1)

Após a reprovação de uma meta ou de um resultado individual, o colaborador e o gestor precisam de um caminho claro para corrigir, avançar progresso e solicitar nova aprovação. Apenas o item reprovado reabre; itens já aprovados e a etapa agregada da Avaliação permanecem intactos.

**Why this priority**: Hoje a reprovação marca o item e cria um dead-end operacional (FR-026 incompleto). Sem esse fluxo, o ciclo trava no nível da pessoa e o RH precisa de intervenção manual. É o bloqueio mais frequente no uso diário.

**Independent Test**: Pode ser testado reprovando uma meta (e depois um resultado) em uma Avaliação já na etapa correspondente, editando/corrigindo apenas o item, reenviando à aprovação e confirmando que a etapa agregada não retrocede e que itens já aprovados não são afetados.

**Acceptance Scenarios**:

1. **Given** uma meta reprovada na etapa de aprovação de metas, **When** o colaborador corrige e resubmete a meta, **Then** o item volta ao fluxo de aprovação e a etapa agregada da Avaliação permanece a mesma.
2. **Given** um resultado reprovado, **When** o colaborador atualiza o progresso/resultado e o gestor reaprova, **Then** apenas aquele item conclui a correção; demais resultados aprovados permanecem aprovados.
3. **Given** metas misturadas (algumas aprovadas, uma reprovada), **When** a reprovada é corrigida e aprovada, **Then** o avanço da etapa só ocorre quando 100% dos itens da etapa estão aprovados (regra já existente preservada).
4. **Given** um item reprovado, **When** o colaborador ou gestor acessa a Avaliação, **Then** há indicação clara do próximo passo (corrigir / reenviar / reaprovar), sem tela sem ação.

---

### User Story 2 - Avaliação automática para admitidos com ciclo aberto (Priority: P1)

Quando um colaborador ativo é cadastrado ou ativado enquanto já existe um ciclo aberto, o sistema cria automaticamente a Avaliação inicial desse colaborador no ciclo corrente, alinhado ao espírito de FR-016 (criação em lote na abertura).

**Why this priority**: Admitidos mid-cycle ficam invisíveis no processo de desempenho até correção manual. Com ~130 colaboradores e contratações recorrentes, a lacuna gera exclusão do ciclo e retrabalho de RH.

**Independent Test**: Pode ser testado com um ciclo aberto, ativando/cadastrando um colaborador ativo e verificando que a Avaliação inicial existe e que colaboradores já cobertos não recebem duplicata.

**Acceptance Scenarios**:

1. **Given** um ciclo de avaliação aberto e um novo colaborador ativo (cadastro ou ativação), **When** o registro fica ativo, **Then** uma Avaliação inicial para aquele ciclo é criada automaticamente.
2. **Given** um colaborador que já possui Avaliação no ciclo aberto, **When** ocorre reativação ou edição sem mudança de elegibilidade, **Then** não é criada Avaliação duplicata.
3. **Given** nenhum ciclo aberto, **When** um colaborador ativo é cadastrado, **Then** nenhuma Avaliação é criada até a próxima abertura de ciclo (comportamento de FR-016).

---

### User Story 3 - Integridade de catálogos e offboarding com reatribuição em lote (Priority: P2)

O RH mantém Área, Cargo, Escala e Competência sem exclusão física destrutiva: desativa (soft-delete) em vez de apagar, preservando histórico referenciado, com unicidade de nome/chave de negócio entre registros ativos. Além disso, antes ou durante o offboarding de um gestor com liderados, o admin/RH reatribui em lote os liderados a outro gestor e só então conclui a desativação (compleando FR-028).

**Why this priority**: Catálogos duplicados e exclusões quebram governança; offboarding bloqueado sem reatribuição impede operações de RH. Ambos são frequentes e de risco operacional médio.

**Independent Test**: Pode ser testado desativando um catálogo em uso (sem perda de histórico), tentando criar duplicata ativa (bloqueada), e reatribuindo N liderados em uma ação antes de desativar o gestor.

**Acceptance Scenarios**:

1. **Given** uma Área/Cargo/Escala/Competência referenciada por histórico, **When** o admin “remove” o registro, **Then** o registro fica inativo (não é excluído fisicamente) e vínculos históricos permanecem íntegros.
2. **Given** um nome (ou chave de negócio) já usado por registro ativo da mesma entidade, **When** o admin tenta criar outro ativo com o mesmo valor, **Then** a operação é rejeitada com mensagem clara.
3. **Given** um gestor com liderados ativos, **When** o admin tenta desativá-lo sem reatribuir, **Then** a desativação continua impedida (FR-028).
4. **Given** um gestor com N liderados, **When** o admin reatribui em lote todos a outro gestor válido, **Then** os liderados passam a ter o novo gestor e a desativação do gestor original passa a ser permitida.

---

### User Story 4 - Aprovação por administrador quando o gestor está ausente (Priority: P2)

Quando o gestor direto está ausente, o administrador (RH) pode aprovar ou reprovar metas e resultados no lugar do gestor, com registro de auditoria identificando o ator real. O escopo hierárquico normal dos líderes permanece; esta é uma exceção explícita de governança RH, não um bypass genérico de visibilidade.

**Why this priority**: Ausência de gestor trava o ciclo para o time. A exceção de admin desbloqueia operação sem enfraquecer o modelo de escopo.

**Independent Test**: Pode ser testado com um colaborador cujo gestor não age: admin aprova/reprova um item, verifica auditoria com o admin como ator, e confirma que um líder comum ainda não acessa fora do próprio escopo.

**Acceptance Scenarios**:

1. **Given** metas ou resultados pendentes de aprovação, **When** um administrador aprova ou reprova no lugar do gestor, **Then** o item muda de status como se aprovado/reprovado no fluxo normal e a etapa agregada respeita as mesmas regras.
2. **Given** a ação de aprovação/reprovação feita pelo admin, **When** a auditoria é consultada, **Then** consta o administrador como ator real da decisão (não o gestor ausente).
3. **Given** um líder não administrador fora do escopo hierárquico do colaborador, **When** ele tenta aprovar ou visualizar fora do escopo, **Then** o acesso continua negado (a exceção não se aplica a ele).

---

### User Story 5 - Lembretes sem duplicata e PDI atrasada coerente (Priority: P3)

Lembretes/notificações agendadas não devem ser reenviados indevidamente para o mesmo evento. Ao estender o prazo de uma ação de PDI que estava atrasada, o status de atraso é recalculado de forma coerente (ex.: deixa de ser “atrasada” se o novo prazo for futuro), com trilha auditável da alteração.

**Why this priority**: Reduz ruído operacional e inconsistência de status, mas não trava o ciclo de avaliação como P1/P2.

**Independent Test**: Pode ser testado disparando o job de lembretes duas vezes para o mesmo pendente (sem segundo envio indevido) e estendendo o prazo de uma ação atrasada para data futura (status deixa de indicar atraso; auditoria registra a mudança).

**Acceptance Scenarios**:

1. **Given** um pendente elegível a lembrete já notificado no período/janela aplicável, **When** o agendamento roda novamente, **Then** o mesmo aviso não é reenviado indevidamente.
2. **Given** uma ação de PDI com status de atraso e prazo no passado, **When** o prazo é estendido para uma data futura, **Then** o status de atraso deixa de indicar atraso (recalculado/resetado de forma coerente).
3. **Given** a extensão de prazo de uma ação de PDI, **When** a auditoria é consultada, **Then** há registro do valor anterior e do novo prazo (e do efeito de status, quando aplicável).

---

### User Story 6 - Prontidão para produção, garantia automatizada e polish de UX (Priority: P3)

A organização consegue colocar o sistema em produção com configuração mínima segura, verificação de saúde, arquivos estáticos servidos corretamente e estratégia de backup do banco documentada. Em paralelo, regras críticas de escopo (visibilidade / acesso indevido) e da máquina de estados (incluindo o fluxo pós-reprovação) são cobertas por testes automatizados. A interface com atualizações parciais oferece indicadores de loading, empty states com CTA e acessibilidade básica de modais.

**Why this priority**: Não adiciona fluxo de produto novo, mas habilita go-live e reduz regressão das regras mais sensíveis (escopo e stage machine).

**Independent Test**: Pode ser validado por checklist de deploy (health responde; backup documentado; ambiente de produção configurável), execução da suíte de testes de escopo/estados, e revisão de UX em telas com loading/empty/modal.

**Acceptance Scenarios**:

1. **Given** uma instância configurada para produção, **When** o endpoint de saúde é consultado, **Then** responde de forma adequada para monitoramento.
2. **Given** a documentação de operação, **When** o time de plataformas segue a estratégia de backup do banco, **Then** há procedimento claro e aplicável (frequência/retenção mínimas documentadas).
3. **Given** as regras de escopo e de transição de etapa/pós-reprovação, **When** a suíte automatizada focada nesses comportamentos é executada, **Then** as violações de escopo e as transições inválidas falham nos testes; os fluxos válidos passam.
4. **Given** uma interação parcial que aguarda resposta do servidor, **When** o usuário dispara a ação, **Then** há indicador visual de carregamento até a conclusão.
5. **Given** uma lista sem itens (ex.: sem metas, sem ações de PDI), **When** o usuário abre a tela, **Then** vê empty state com CTA claro para a próxima ação possível.
6. **Given** um modal aberto, **When** o usuário navega por teclado/leitor básico, **Then** foco e fechamento se comportam de forma previsível (acessibilidade básica).

---

### Edge Cases

- **Reprovação de único item com demais já aprovados**: apenas o item reprovado reabre; avance de etapa permanece bloqueado até 100% de aprovação.
- **Colaborador ativado e desativado rapidamente com ciclo aberto**: não criar Avaliações órfãs desnecessárias; se reativado no mesmo ciclo sem Avaliação, criar; se já existir, não duplicar.
- **Reatribuição em lote parcial**: se nem todos os liderados forem reatribuídos, a desativação do gestor continua impedida.
- **Novo gestor inválido ou inativo na reatribuição**: operação rejeitada; liderados permanecem inalterados.
- **Admin aprova item já aprovado ou fora de etapa elegível**: operação rejeitada sem efeito colateral; auditoria não registra sucesso falso.
- **Soft-delete de catálogo ainda referenciado**: permitido como inativação; criação de novos vínculos a registros inativos deve ser impedida ou claramente sinalizada (padrão: não oferecer inativos em seleções de criação).
- **Unicidade**: nomes iguais a registros inativos podem ser reutilizados por novos ativos (unicidade entre ativos), salvo se a chave de negócio exigir unicidade global — assumir unicidade entre ativos.
- **Extensão de prazo de PDI para data ainda no passado**: status de atraso permanece coerente (continua atrasada).
- **Ciclo encerrado**: nenhum fluxo de correção pós-reprovação ou criação mid-cycle altera avaliações de ciclo já encerrado.
- **Lembrete após resolução do pendente**: não enviar lembrete se o item já não está elegível.

## Requirements *(mandatory)*

### Functional Requirements

**Fluxo pós-reprovação (FR-026 completo)**

- **FR-001**: Ao reprovar uma meta ou um resultado individual, o sistema DEVE reabrir apenas aquele item para correção e nova submissão/aprovação, sem retroceder a etapa agregada da Avaliação.
- **FR-002**: O sistema DEVE preservar o status de itens já aprovados na mesma etapa enquanto um item reprovado está em correção.
- **FR-003**: O sistema DEVE apresentar ao colaborador e ao gestor o próximo passo acionável após reprovação (corrigir, reenviar, reavaliar), evitando tela sem caminho (dead-end).
- **FR-004**: O avanço de etapa DEVE continuar exigindo 100% de aprovação dos itens da etapa e a existência de ao menos um item (regra canônica preservada).

**Avaliação mid-cycle**

- **FR-005**: Ao cadastrar ou ativar um colaborador ativo com ciclo aberto, o sistema DEVE criar automaticamente a Avaliação inicial desse colaborador no ciclo corrente (alinhado a FR-016).
- **FR-006**: O sistema NÃO DEVE criar Avaliação duplicata para o mesmo colaborador no mesmo ciclo.
- **FR-007**: Sem ciclo aberto, a ativação/cadastro NÃO DEVE criar Avaliação.

**Integridade de catálogos**

- **FR-008**: Área, Cargo, Escala e Competência DEVEM preferir desativação lógica (soft-delete) à exclusão física.
- **FR-009**: Exclusões ou desativações NÃO DEVEM remover em cascata histórico de ciclo, avaliação, PDI ou auditoria; referências históricas DEVEM permanecer protegidas.
- **FR-010**: O sistema DEVE garantir unicidade de nome (ou chave de negócio equivalente) entre registros ativos de Área, Cargo, Escala e Competência.

**Offboarding e reatribuição**

- **FR-011**: O sistema DEVE continuar impedindo a desativação de colaborador com liderados ativos até que estes sejam reatribuídos (FR-028).
- **FR-012**: O administrador/RH DEVE poder reatribuir em lote os liderados de um gestor a outro gestor válido, antes ou durante o fluxo de offboarding.
- **FR-013**: A reatribuição em lote DEVE registrar auditoria da mudança de gestor dos liderados afetados.

**Governança — gestor ausente**

- **FR-014**: O administrador DEVE poder aprovar ou reprovar metas e resultados no lugar do gestor direto quando necessário.
- **FR-015**: Cada aprovação/reprovação feita pelo administrador DEVE registrar na auditoria o ator real (administrador), de forma distinguível.
- **FR-016**: A exceção de FR-014 NÃO DEVE ampliar a visibilidade genérica de líderes comuns fora do escopo hierárquico.

**Lembretes e PDI**

- **FR-017**: Lembretes/notificações agendadas DEVEM ser deduplicados para não reenviar o mesmo aviso indevidamente ao mesmo destinatário/evento elegível.
- **FR-018**: Ao alterar o prazo de uma ação de PDI, o sistema DEVE recalcular o status de atraso de forma coerente com a nova data (ex.: sair de atrasada se o novo prazo for futuro).
- **FR-019**: A alteração de prazo (e o efeito no status de atraso, quando houver) DEVE deixar trilha auditável.

**Prontidão operacional e qualidade**

- **FR-020**: O sistema DEVE oferecer configuração mínima de produção, incluindo verificação de saúde (health) e entrega correta de arquivos estáticos.
- **FR-021**: A estratégia de backup do banco de produção DEVE estar documentada e aplicável pela operação.
- **FR-022**: Deve haver cobertura de testes automatizados focada em escopo de visibilidade (anti-acesso indevido) e na máquina de estados das avaliações, incluindo o fluxo pós-reprovação.
- **FR-023**: Interações parciais da interface DEVEM exibir indicador de carregamento enquanto aguardam resposta.
- **FR-024**: Listas vazias relevantes DEVEM apresentar empty state com CTA para a próxima ação possível.
- **FR-025**: Modais DEVEM atender acessibilidade básica (foco/fechamento previsíveis).

### Out of Scope

- Novos módulos de produto (nova matriz 9-box, API/SPA, aplicativo mobile).
- Exclusão física (hard-delete) de histórico de ciclo, avaliação, PDI ou auditoria.
- Mudança na fórmula de nota consolidada do líder ou na lista canônica de etapas do ciclo.
- Introdução de arquitetura cliente-separada (SPA) ou camada de API REST como superfície principal.

### Key Entities *(include if feature involves data)*

- **Avaliação**: Continua sendo o registro por colaborador/ciclo; etapa agregada não retrocede por reprovação pontual; pode ser criada mid-cycle.
- **Meta / Resultado (item de ciclo)**: Pode ser reaberto individualmente após reprovação para correção e reaprovação.
- **Área, Cargo, Escala, Competência**: Catálogos com ativação/desativação e unicidade entre ativos.
- **Colaborador / Gestor direto**: Relação hierárquica; sujeito a reatribuição em lote no offboarding.
- **Ação de PDI**: Possui prazo e status de atraso recalculável; alterações auditáveis.
- **Lembrete / Notificação agendada**: Evento deduplicável por destinatário/contexto para evitar reenvio indevido.
- **Registro de Auditoria**: Inclui ator real em aprovações administrativas e mudanças de gestor/prazo.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 0% dos colaboradores ativos com item reprovado ficam sem caminho acionável para corrigir e reaprovar (sem dead-end).
- **SC-002**: 100% dos colaboradores ativos em ciclo aberto possuem Avaliação nesse ciclo (incluindo admitidos após a abertura).
- **SC-003**: Em 100% dos casos de offboarding com liderados, a desativação só conclui após reatribuição; a reatribuição em lote cobre todos os liderados em uma operação.
- **SC-004**: Em cenários de gestor ausente, o administrador consegue concluir aprovação/reprovação pendente, e 100% dessas decisões registram o ator real na auditoria.
- **SC-005**: 0 reenvios indevidos do mesmo lembrete para o mesmo destinatário/evento na mesma janela elegível, em verificação do agendamento.
- **SC-006**: 100% das extensões de prazo de PDI para data futura a partir de estado atrasado resultam em status não-atrasado de forma coerente e auditável.
- **SC-007**: Instância de produção sobe com health check verificável e procedimento de backup documentado utilizável pela operação.
- **SC-008**: A suíte automatizada de escopo e máquina de estados cobre os fluxos desta feature e falha quando escopo ou transição são violados.
- **SC-009**: Em revisão de UX das telas críticas (listas vazias, ações parciais, modais), loading, empty state com CTA e acessibilidade básica de modal estão presentes.

## Assumptions

- Escala-alvo: ~130 colaboradores e ~6 gestores; um ciclo aberto por vez permanece como na v1.
- Esta feature endurece o MVP existente; não reabre o desenho de papéis, fórmula de nota consolidada nem a lista canônica de etapas.
- Soft-delete com unicidade entre registros ativos é o padrão para Área, Cargo, Escala e Competência; registros inativos não entram em seletores de criação de novos vínculos.
- Aprovação por administrador é exceção de governança RH, não substitui o gestor no fluxo feliz nem altera o modelo de escopo hierárquico para líderes.
- Paridade ambiente de desenvolvimento / produção no código de aplicação é preservada (mesmas regras de negócio); diferenças limitam-se a configuração operacional.
- Stack e restrições da constituição do projeto permanecem vigentes (monólito server-rendered; sem API/SPA; escopo no backend; histórico imutável).
- Deduplicação de lembretes usa chave lógica estável por destinatário + tipo de evento + referência do pendente + janela (padrão razoável na ausência de especificação mais fina).
- “Ativar/cadastrar colaborador” cobre o equivalente operacional que torna o usuário elegível ao ciclo (status ativo).
