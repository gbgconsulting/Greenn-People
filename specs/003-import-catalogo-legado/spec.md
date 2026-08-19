# Feature Specification: Importação One-Shot do Catálogo Legado de Cargos e Competências

**Feature Branch**: `003-import-catalogo-legado`

**Created**: 2026-07-28

**Status**: Draft

**Input**: User description: "Importação one-shot (management command) do catálogo legado de cargos e competências para o Greenn People, usando os arquivos lista-cargos.xlsx e lista-competencias.xlsx (na prática CSV com extensão .xlsx) como fonte. Esta feat cobre a fatia de catálogo + vínculos cargo↔competência da Sprint 6.5.3 do PRD (importar_competencias_cargo); fora de escopo: import de colaboradores, avaliações históricas, notas, comentários e PDIs."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Carregar catálogo de cargos e competências (Priority: P1)

O operador de RH (ou administrador técnico) executa o comando de importação apontando para os arquivos legados de cargos e competências. Ao final, o sistema possui o catálogo de cargos ativos (com senioridade correta) e o catálogo de competências avaliáveis (com tipo e escala padrão), prontos para uso nos fluxos já existentes de gestão de competências.

**Why this priority**: Sem o catálogo base, não há perfil esperado por cargo nem base para ciclos futuros de avaliação. É o pré-requisito de toda a Sprint 6.5.3 nesta fatia.

**Independent Test**: Executar a importação em ambiente limpo (ou com catálogo vazio) e verificar que cargos e competências avaliáveis aparecem no CRUD existente com nomes normalizados, tipos corretos e escala 1–5 associada.

**Acceptance Scenarios**:

1. **Given** os arquivos legados de cargos e competências disponíveis e um catálogo vazio (ou sem os registros equivalentes), **When** o operador executa o comando de importação, **Then** todos os cargos do legado são criados com senioridade (`nivel`) derivada das regras de de-para por nome, e todas as competências avaliáveis são criadas com tipo mapeado do grupo legado e escala padrão 1–5.
2. **Given** um cargo legado cujo nome contém indicador de senioridade (ex.: JR, PL, SR, Lead, Gerente), **When** a importação processa esse cargo, **Then** o `nivel` gravado corresponde à tabela de de-para acordada (1=Estagiário … 6=Principal).
3. **Given** um cargo legado sem sufixo de senioridade, **When** a importação processa esse cargo, **Then** o `nivel` gravado é 6 (Principal), conforme regra do legado para funções sem divisão de senioridade.
4. **Given** uma competência cujo grupo legado é Liderança, Comportamento ou Desempenho (e que seja habilidade avaliável), **When** a importação a processa, **Then** o tipo no sistema é respectivamente `lideranca`, `comportamental` ou `tecnica`.

---

### User Story 2 - Montar perfil esperado cargo↔competência (Priority: P1)

Após (ou juntamente com) o carregamento do catálogo, o sistema cria os vínculos entre cada cargo e suas competências esperadas, com peso e nível esperado coerentes com a senioridade do cargo, de modo que o RH possa revisar e ajustar finamente via CRUD existente.

**Why this priority**: O valor de negócio da Sprint é ter o perfil esperado por cargo pronto; catálogo sem vínculos não habilita ciclos de avaliação por competência.

**Independent Test**: Após a importação, escolher um cargo conhecido do legado e confirmar que as competências listadas nas duas fontes (matriz de cargos e lista por competência) estão vinculadas com `peso=1` e `nivel_esperado` conforme a senioridade do cargo.

**Acceptance Scenarios**:

1. **Given** um cargo importado com senioridade conhecida, **When** os vínculos cargo↔competência são criados, **Then** cada vínculo tem `peso=1` e `nivel_esperado` derivado da senioridade: Estagiário→2, Júnior→2, Pleno→3, Sênior→4, Especialista→4, Principal→4.
2. **Given** as duas fontes legadas (lista de competências com cargos associados e lista de cargos com competências separadas por pipe), **When** a importação conclui o parse, **Then** a matriz de vínculos resultante das duas vistas é a mesma (mesmos pares cargo↔competência após normalização).
3. **Given** vínculos criados pela importação, **When** o RH acessa o CRUD existente de perfil por cargo (US-14), **Then** pode ajustar `nivel_esperado` e `peso` sem depender de nova importação.

---

### User Story 3 - Separar competências de KPIs operacionais (Priority: P2)

Durante a importação, itens do legado que são métricas/KPIs operacionais (e não habilidades avaliáveis) são excluídos da matriz de competências e listados em um relatório claro, evitando misturar Meta/acompanhamento com competências.

**Why this priority**: Alinha o catálogo ao modelo de domínio (RF-10/RF-14/RF-15 e Decisão #1 do PRD); misturar KPIs como competência corrompe avaliações futuras.

**Independent Test**: Incluir no arquivo legado itens tipicamente operacionais (ex.: SLA, Lead time, Throughput) e verificar que não viram competência ativa e que aparecem no relatório de excluídos/não mapeados.

**Acceptance Scenarios**:

1. **Given** itens legados reconhecidos como operacionais/métricas (ex.: SLA, Lead time discovery, Custo de nuvem, Throughput, Índice de incidentes), **When** a importação roda, **Then** esses itens NÃO são criados como competência no catálogo e constam no relatório de exclusão com motivo identificável.
2. **Given** competências reais (comportamentais, liderança e técnicas/comportamento de entrega), **When** a importação roda, **Then** são importadas normalmente como competência avaliável.
3. **Given** a importação concluída, **When** o operador consulta o relatório de carga, **Then** consegue distinguir criados/atualizados, excluídos (KPI/meta) e não mapeados/conflitos.

---

### User Story 4 - Reexecutar importação de forma segura (Priority: P2)

O operador pode reexecutar o mesmo comando com as mesmas fontes sem duplicar registros ativos; o sistema atualiza o que for cabível ou reporta conflitos de forma clara, respeitando soft-delete/`is_active` do catálogo atual.

**Why this priority**: Import one-shot precisa ser reproduzível em staging/produção e após correções pontuais nos arquivos; duplicatas quebram o catálogo.

**Independent Test**: Rodar o comando duas vezes com os mesmos arquivos e confirmar contagens estáveis de ativos (sem duplicata) e relatório indicando atualizações/sem mudança/conflitos.

**Acceptance Scenarios**:

1. **Given** uma importação já concluída com sucesso, **When** o operador reexecuta o comando com as mesmas fontes, **Then** não são criados registros ativos duplicados de cargo, competência ou vínculo cargo↔competência.
2. **Given** um registro do catálogo marcado como inativo (`is_active=false`), **When** a reimportação encontra o equivalente no legado, **Then** o comportamento respeita a política de soft-delete documentada (não reativa silenciosamente sem registro no relatório, ou atualiza conforme regra explícita de idempotência — ver Assumptions).
3. **Given** um conflito semântico (ex.: mesmo nome normalizado com atributos incompatíveis), **When** a importação detecta o conflito, **Then** o relatório descreve o conflito de forma acionável e a carga dos demais itens não fica silenciosamente corrompida.

---

### Edge Cases

- Arquivo ausente, ilegível ou com encoding/separador inesperado: o comando falha de forma clara antes de gravar mudanças parciais inconsistentes, ou aborta com relatório de erro.
- Competência listada em uma fonte e ausente na outra (após normalização): reportar como divergência entre fontes; a matriz final deve privilegiar a união consistente ou a regra documentada de reconciliação (ver Assumptions).
- Nome de cargo/competência com espaços extras, capitalização ou acentuação inconsistente: normalização determinística produz a mesma chave canônica.
- Duplicatas semânticas no legado (mesmo conceito com grafias levemente diferentes): consolidar em um único registro ativo conforme regras de normalização documentadas; reportar merges.
- Cargo ou competência apenas em uma das listas: criar o registro e reportar a origem; vínculos só existem quando ambas as pontas estão resolvidas.
- `solides_id` ausente nos arquivos: não bloqueia a importação.
- Itens ambíguos entre competência e KPI (não listados explicitamente como exemplo operacional): aplicar a lista de exclusão documentada; o que não estiver na lista de exclusão e for habilidade avaliável importa; o restante ambíguo vai para “não mapeado” no relatório para decisão humana posterior.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O sistema MUST oferecer um comando de importação one-shot, reproduzível e documentado, que lê as fontes `lista-cargos` e `lista-competencias` (arquivos com extensão `.xlsx` cujo conteúdo, na prática, é CSV) e carrega o catálogo de cargos, competências e vínculos cargo↔competência — sem interface de upload/admin.
- **FR-002**: O sistema MUST criar ou atualizar Cargos com `nome`, `nivel` (senioridade 1–6) e `is_active`, derivando `nivel` pelas regras de de-para por tokens no nome: Estagiário/Estag→1; JR/Júnior→2; PL/Pleno→3; SR/Sênior→4; Lead/Tech Lead/UX Lead/QA Lead→5 (Especialista); Gerente/Diretor/Coordenador/CEO/Presidente→6 (Principal); sem sufixo de senioridade→6 (Principal).
- **FR-003**: O sistema MUST criar ou atualizar Competências avaliáveis com `nome`, `descricao`, `tipo` (`tecnica` | `comportamental` | `lideranca`), escala padrão 1–5 e `is_active`, mapeando Grupo legado: Liderança→`lideranca`, Comportamento→`comportamental`, Desempenho→`tecnica` (quando for competência real).
- **FR-004**: O sistema MUST criar ou atualizar vínculos CargoCompetencia com `peso=1` e `nivel_esperado` derivado da senioridade do cargo na escala de avaliação 1–5: nivel 1→2, 2→2, 3→3, 4→4, 5→4, 6→4.
- **FR-005**: O sistema MUST garantir que as duas fontes, após parse e normalização, produzam a mesma matriz de pares cargo↔competência; divergências MUST ser reportadas.
- **FR-006**: O sistema MUST importar como Competência apenas habilidades avaliáveis (comportamentais, liderança e técnicas/comportamento de entrega) e MUST excluir da matriz itens operacionais/métricas do legado (candidatos a Meta/acompanhamento), gerando relatório do que foi excluído ou não mapeado.
- **FR-007**: O sistema MUST aplicar normalização determinística e documentada de nomes (espaços, acentos, capitalização e duplicatas semânticas óbvias) antes de criar/atualizar registros e vínculos.
- **FR-008**: O sistema MUST ser idempotente: reexecutar o comando NÃO MUST duplicar registros ativos; MUST atualizar atributos quando apropriado ou reportar conflitos de forma clara, respeitando `is_active`/soft-delete do catálogo atual.
- **FR-009**: O sistema MUST produzir um relatório de carga ao final (criados, atualizados, inalterados, excluídos como KPI/meta, não mapeados, conflitos e divergências entre fontes).
- **FR-010**: O sistema MUST criar ou reutilizar uma Escala padrão 1–5 para as competências importadas.
- **FR-011**: A ausência de identificador Sólides (`solides_id`) nos arquivos NÃO MUST bloquear a importação.
- **FR-012**: Esta feature MUST NOT importar colaboradores, hierarquia, avaliações históricas, notas, comentários ou PDIs; MUST NOT alterar o fluxo de avaliação/cálculo de notas; MUST NOT incluir UI de import.

### Key Entities

- **Cargo**: Posição organizacional no catálogo (`nome`, senioridade `nivel` 1–6, `is_active`). Origem principal: lista de cargos e referências na lista de competências.
- **Competencia**: Habilidade avaliável (`nome`, `descricao`, `tipo`, escala associada, `is_active`). Origem: lista de competências, após filtro de exclusão de KPIs.
- **CargoCompetencia**: Vínculo de perfil esperado (`cargo`, `competencia`, `nivel_esperado`, `peso`). Produzido pela reconciliação das duas fontes.
- **Escala**: Escala reutilizável de avaliação; a importação usa/cria a escala padrão 1–5.
- **Fonte Legada (lista-competencias)**: Catálogo com descrição, grupo e lista de cargos associados por competência.
- **Fonte Legada (lista-cargos)**: Matriz cargo → competências (lista pipe-separated).
- **Relatório de Carga**: Artefato de saída da execução com totais e detalhes de exclusões, conflitos e divergências.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Após uma execução bem-sucedida, 100% dos cargos presentes nas fontes legadas (após normalização) existem no catálogo com senioridade correta segundo a tabela de de-para acordada.
- **SC-002**: Após uma execução bem-sucedida, 100% das competências avaliáveis elegíveis (não excluídas como KPI/meta) existem no catálogo com tipo mapeado e escala 1–5.
- **SC-003**: 100% dos vínculos CargoCompetencia criados pela importação têm `peso=1` e `nivel_esperado` coerente com a senioridade do cargo (tabela Estagiário/Júnior→2, Pleno→3, Sênior/Especialista/Principal→4).
- **SC-004**: As duas fontes produzem a mesma matriz de vínculos após parse; qualquer divergência aparece no relatório (zero divergências silenciosas).
- **SC-005**: 100% dos itens classificados como KPI/operacional na lista de exclusão documentada NÃO aparecem como competência ativa no catálogo e constam no relatório de exclusão.
- **SC-006**: Uma segunda execução com as mesmas fontes não aumenta a contagem de registros ativos duplicados de Cargo, Competência ou CargoCompetencia (delta de duplicatas = 0).
- **SC-007**: O operador obtém, ao final de cada execução, um relatório legível com totais de criados/atualizados/inalterados/excluídos/não mapeados/conflitos em menos de 1 minuto de revisão para um catálogo do tamanho legado típico.
- **SC-008**: O RH consegue, imediatamente após a importação, visualizar e ajustar o perfil esperado por cargo no CRUD existente, sem nova carga, para preparar ciclos futuros.

## Assumptions

- Os arquivos `lista-cargos.xlsx` e `lista-competencias.xlsx` estão disponíveis no ambiente de execução (caminho configurável ou convencional) e, apesar da extensão, o conteúdo é tabular tipo CSV parseável de forma determinística.
- A lista de exclusão de KPIs/operacionais será documentada no comando/relatório com base nos exemplos do PRD/legado (SLA, Lead time discovery, Custo de nuvem, Throughput, Índice de incidentes e equivalentes); itens ambíguos não listados vão para “não mapeado” para decisão humana, sem bloquear o restante da carga.
- Em reimportação, registros inativos (`is_active=false`) com o mesmo nome canônico NÃO são reativados automaticamente; o conflito/estado é reportado para ação manual (evita reverter soft-delete silencioso).
- Atualização de atributos em registros ativos existentes (ex.: descrição, tipo, nivel_esperado, peso) é permitida e refletida no relatório como “atualizado” quando houver diferença.
- Divergências entre as duas fontes após normalização são reportadas; a matriz gravada privilegia a união dos pares válidos presentes em pelo menos uma fonte somente quando ambas as pontas (cargo e competência) já estão resolvidas como elegíveis — pares inválidos/excluídos não entram.
- Ajuste fino de `nivel_esperado` e `peso` após a carga é responsabilidade do RH via CRUD existente (US-14); a importação aplica apenas as regras default fechadas nesta spec.
- Escala padrão 1–5: se já existir uma escala equivalente no sistema, ela é reutilizada; caso contrário, é criada uma vez e reutilizada nas competências importadas.
- Esta fatia cobre apenas catálogo + vínculos da Sprint 6.5.3 (`importar_competencias_cargo`); demais fatias do PRD (colaboradores, avaliações, notas, PDI) permanecem fora de escopo.
- O comando é operacional (executado por administrador técnico/RH com acesso ao ambiente), não por usuário final via UI.
- Conformidade com a constituição do projeto: não altera histórico de avaliações; `peso`/`nivel_esperado` em avaliações futuras continuam sendo snapshot no momento da criação da avaliação (imutabilidade do histórico preservada).
