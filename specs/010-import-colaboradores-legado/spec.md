# Feature Specification: Importação One-Shot do Legado Sólides — Colaboradores e Schema de Identificadores

**Feature Branch**: `010-import-colaboradores-legado`

**Created**: 2026-08-12

**Status**: Draft

**Input**: User description: "Importação one-shot do legado Sólides — fatia colaboradores + schema (Sprint 6.5.1 + 6.5.2). Após o redesign visual 009, popular o Greenn People com dados reais da Sólides. Inventário e mapeamento coluna→domínio em data/legado-solides/README.md (Decisão #22). Catálogo cargos/competências já existe na spec 003; esta feature NÃO reimplementa o catálogo CSV da 003. Fontes XLSX real (backup_colaboradores, crosswalk via backup_avaliacoes). Dump 2026-06-24: ~325 colaboradores (127 ativos / 198 demitidos)."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Preparar schema para rastreabilidade legado (Priority: P1)

O operador técnico (ou administrador de plataforma) aplica a evolução de schema que adiciona um identificador externo Sólides (`solides_id`) nas entidades que participarão das fatias futuras de importação histórica: colaboradores, cargos, competências, avaliações e PDIs. O campo é opcional, único quando preenchido e indexado, permitindo correlacionar registros do Greenn People com o sistema de origem sem alterar regras de negócio existentes.

**Why this priority**: Sem o identificador externo, importações subsequentes (avaliações, notas, PDI) não conseguem resolver FKs de forma confiável. É pré-requisito da Sprint 6.5.1 e base para toda a trilha de importação.

**Independent Test**: Aplicar a evolução de schema em ambiente limpo e verificar que as entidades listadas aceitam `solides_id` nulo ou único, sem quebrar fluxos existentes de CRUD, escopo ou cálculos.

**Acceptance Scenarios**:

1. **Given** um ambiente com schema atualizado, **When** um registro de colaborador, cargo, competência, avaliação ou PDI é criado sem identificador Sólides, **Then** a operação é aceita com `solides_id` vazio.
2. **Given** dois registros distintos da mesma entidade, **When** ambos recebem o mesmo `solides_id` não nulo, **Then** o sistema rejeita a duplicata (unicidade).
3. **Given** o schema atualizado, **When** fluxos existentes (login, CRUD de catálogo, ciclos, avaliações) são exercitados sem preencher `solides_id`, **Then** comportamento permanece inalterado — nenhuma regra de stage, approval, fórmulas, escopo ou autorização é modificada.

---

### User Story 2 - Carregar colaboradores e estrutura organizacional (Priority: P1)

O operador de RH executa o comando de importação apontando para o backup de colaboradores Sólides (formato Excel real) e, opcionalmente, para o arquivo de avaliações usado como crosswalk de identificadores. Ao final, o sistema possui colaboradores com e-mail, área (departamento), cargo, status ativo/inativo coerente com demissão, e-mail considerado confirmado na importação, e identificador Sólides quando resolvível — prontos para uso nos fluxos de gestão de pessoas e hierarquia.

**Why this priority**: É a primeira fatia de maior valor de negócio após o catálogo (003): popular a plataforma com ~325 pessoas reais (127 ativas) para demonstrações, homologação e preparação de importações históricas.

**Independent Test**: Executar a importação em ambiente limpo (após catálogo 003) e verificar contagens esperadas, e-mails únicos, demitidos inativos, áreas criadas a partir de departamentos, cargos resolvidos, e relatório de carga completo.

**Acceptance Scenarios**:

1. **Given** o backup de colaboradores disponível e catálogo de cargos já carregado (spec 003), **When** o operador executa a importação, **Then** todos os colaboradores elegíveis são criados ou atualizados com nome normalizado, e-mail conforme ordem de preferência (empresarial → corporativo principal → pessoal), área derivada do departamento, cargo resolvido por identificador ou nome canônico, e e-mail marcado como confirmado no momento da importação (Decisão #21 — sem envio de link).
2. **Given** um colaborador com data de demissão preenchida, **When** a importação o processa, **Then** o registro fica inativo (`is_active=false`).
3. **Given** um colaborador sem data de demissão, **When** a importação o processa, **Then** o registro fica ativo (`is_active=true`).
4. **Given** um departamento ainda inexistente no sistema, **When** a importação encontra colaboradores daquele departamento, **Then** a área correspondente é criada ou reutilizada pelo nome do departamento (coluna Unidade ignorada por estar vazia no dump).
5. **Given** um cargo referenciado apenas no backup de colaboradores (até 8 casos conhecidos fora de `lista-cargos`), **When** a importação não encontra o cargo no catálogo existente, **Then** o cargo é criado ou obtido a partir do identificador/nome legado, preferindo chave canônica da spec 003 quando aplicável.
6. **Given** o arquivo de avaliações como crosswalk, **When** o nome do colaborador coincide com um avaliado no backup de avaliações, **Then** o `solides_id` do colaborador é preenchido com o identificador avaliado correspondente (~187 matches esperados no dump 2026-06-24).
7. **Given** um colaborador sem match no crosswalk, **When** a importação o conclui, **Then** `solides_id` permanece vazio e a chave natural de deduplicação é o e-mail.
8. **Given** colaboradores com e-mail em domínios diversos (incluindo pessoais), **When** a importação roda, **Then** a carga **não** exige domínio `@greenn.com.br` (Decisão #21); a denylist de domínio existente para cadastro normal permanece intacta para fluxos fora da importação.

---

### User Story 3 - Resolver hierarquia de gestores (Priority: P1)

Após todos os colaboradores estarem persistidos, a importação resolve a relação de gestor direto (`line_manager`) usando o identificador Sólides do superior informado no backup, em segunda fase, validando que a hierarquia resultante é acíclica (RF-04.1).

**Why this priority**: Escopo hierárquico e visibilidade de dados dependem de `line_manager` correto; importar pessoas sem gestor quebra dashboards e autorização por hierarquia.

**Independent Test**: Após importação completa, verificar que colaboradores com `Superior direto id` válido apontam para o gestor correto; ciclos detectados são reportados sem corromper a carga dos demais.

**Acceptance Scenarios**:

1. **Given** todos os colaboradores importados com seus identificadores Sólides resolvidos, **When** a fase de hierarquia processa vínculos de superior direto, **Then** cada colaborador com ID de superior válido no legado recebe `line_manager` apontando para o colaborador correspondente (~29/31 IDs de gestores batem com avaliações no dump).
2. **Given** um superior cujo identificador Sólides não existe entre os colaboradores importados, **When** a fase de hierarquia tenta resolver o vínculo, **Then** o colaborador permanece sem gestor e o caso consta no relatório como não resolvido.
3. **Given** uma cadeia de gestores que formaria ciclo, **When** a validação de aciclicidade (RF-04.1) detecta o ciclo, **Then** o vínculo conflitante não é aplicado silenciosamente e o relatório descreve o ciclo de forma acionável.

---

### User Story 4 - Simular e reexecutar importação com segurança (Priority: P2)

O operador pode executar a importação em modo simulação (`--dry-run`) para validar parse, totais projetados e conflitos sem gravar alterações, e reexecutar a importação real de forma idempotente após correções — espelhando os padrões operacionais da spec 003.

**Why this priority**: Backups contêm PII; staging exige dry-run e idempotência antes de produção. Reexecução segura é obrigatória para homologação iterativa.

**Independent Test**: Rodar dry-run (zero writes), depois duas execuções reais consecutivas e confirmar que a segunda não duplica e-mails nem colaboradores ativos.

**Acceptance Scenarios**:

1. **Given** arquivos válidos, **When** o operador executa com `--dry-run`, **Then** o sistema parseia as fontes, emite relatório com totais projetados (criados/atualizados/inalterados/conflitos/não resolvidos) e **não persiste** nenhuma alteração no banco.
2. **Given** uma importação já concluída com sucesso, **When** o operador reexecuta com as mesmas fontes, **Then** não são criados colaboradores duplicados pelo mesmo e-mail; atualizações são reportadas quando atributos divergem.
3. **Given** erro fatal antes da persistência (arquivo ausente, formato ilegível, colunas obrigatórias ausentes), **When** a importação aborta, **Then** exit code indica falha e nenhum dado parcial inconsistente permanece gravado.
4. **Given** execução bem-sucedida (real ou dry-run), **When** o operador consulta o relatório, **Then** consegue revisar totais e exceções em menos de 2 minutos para o volume típico (~325 colaboradores).

---

### User Story 5 - Validar importação com dados anonimizados (Priority: P2)

Desenvolvedores e CI executam testes automatizados usando fixtures mínimas anonimizadas que representam o layout real dos backups, sem depender dos arquivos `raw/` (que contêm PII e não devem rodar no CI).

**Why this priority**: Garante regressão segura e conformidade com política de segurança documentada no inventário legado.

**Independent Test**: Suite de testes passa em CI usando apenas fixtures em diretório de amostras; nenhum teste referencia `data/legado-solides/raw/`.

**Acceptance Scenarios**:

1. **Given** fixtures anonimizadas com subset representativo (ativos, demitidos, sem superior, crosswalk parcial, datas em serial Excel e ISO), **When** a suite de testes roda, **Then** cobre dry-run, idempotência, demitidos inativos, resolução de hierarquia e denylist intacta.
2. **Given** o pipeline de CI, **When** testes de importação executam, **Then** nenhum arquivo de `raw/` é lido ou exigido.

---

### Edge Cases

- Arquivo de colaboradores ausente, corrompido ou sem planilha esperada: falha clara antes de persistência; exit de erro.
- Colaborador sem nenhum e-mail nas três colunas: reportar como não importável; não bloquear silenciosamente os demais.
- E-mails duplicados no backup (mesmo endereço em linhas distintas): reportar conflito; política de resolução documentada em Assumptions.
- Datas em serial Excel (ex.: `45446.0`) vs. strings ISO: parser aceita ambos para data de demissão/admissão.
- Cargo ID presente mas nome divergente do catálogo 003: preferir match por identificador; conflito de nome reportado.
- Superior direto apontando para colaborador demitido: vínculo permitido (gestor histórico) ou reportado conforme regra de negócio — demitidos permanecem inativos mas referenciáveis.
- Colaborador ativo sem superior (15 ativos no dump): importar sem `line_manager`; constar no relatório como topo ou dado incompleto.
- Crosswalk ambíguo (mesmo nome, identificadores distintos): reportar conflito; não atribuir `solides_id` silenciosamente.
- Reimportação alterando status ativo (readmissão simulada por remoção de data demissão no arquivo): atualizar `is_active` e reportar como atualizado.
- Campos sensíveis presentes no backup (CPF, RG, banco, endereço, telefone): **nunca** importados; presença no arquivo não deve vazar para logs completos em produção.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O sistema MUST adicionar campo identificador externo Sólides (`solides_id`) — opcional, único quando preenchido, indexado — nas entidades Colaborador (usuário), Cargo, Competência, Avaliação e PDI, conforme Sprint 6.5.1 (somente schema nesta fatia; demais entidades ficam prontas para fatias futuras).
- **FR-002**: O sistema MUST oferecer um comando de importação one-shot reproduzível que lê o backup de colaboradores Sólides (Excel OOXML real, não CSV) e carrega colaboradores, áreas e vínculos cargo/área — sem interface de upload.
- **FR-003**: O comando MUST aceitar arquivo auxiliar de avaliações Sólides como crosswalk opcional para resolver `solides_id` de colaboradores via correspondência Nome → Identificador Avaliado.
- **FR-004**: O sistema MUST resolver e-mail do colaborador pela ordem de preferência: E-mail empresarial → E-mail → E-mail pessoal; normalizar (strip, colapsar whitespace).
- **FR-005**: O sistema MUST marcar e-mail como confirmado no momento da importação (Decisão #21), sem exigir fluxo de confirmação por link.
- **FR-006**: O sistema MUST definir colaborador como inativo quando data de demissão estiver preenchida e diferente de zero/vazio; caso contrário, ativo.
- **FR-007**: O sistema MUST criar ou obter Área a partir do nome do Departamento legado; MUST ignorar coluna Unidade quando vazia.
- **FR-008**: O sistema MUST resolver Cargo por identificador Sólides do cargo ou, na ausência, por nome canônico alinhado à spec 003; MUST criar cargo faltante quando referenciado apenas no backup de colaboradores.
- **FR-009**: O sistema MUST executar resolução de gestor direto (`line_manager`) em segunda fase, após persistência de todos os colaboradores, mapeando Superior direto id → colaborador com mesmo `solides_id`.
- **FR-010**: O sistema MUST validar aciclicidade da hierarquia resultante (RF-04.1) e reportar ciclos sem aplicar vínculos inválidos silenciosamente.
- **FR-011**: O sistema MUST aceitar `--dry-run`: parse completo, relatório com totais projetados, zero persistência.
- **FR-012**: O sistema MUST persistir alterações reais dentro de transação atômica — falha rollback completo, sem estado parcial inconsistente.
- **FR-013**: O sistema MUST ser idempotente por chave natural de e-mail (e `solides_id` quando presente): reexecução MUST NOT duplicar colaboradores.
- **FR-014**: O sistema MUST emitir relatório final estruturado (criados, atualizados, inalterados, conflitos, não resolvidos, demitidos, sem gestor, ciclos detectados) e MUST usar exit code 0 para sucesso e 1 para erro fatal pré-persistência ou falha de persistência — alinhado ao contrato da spec 003.
- **FR-015**: O sistema MUST NOT importar PII além do necessário: CPF, RG, CTPS, PIS, dados bancários, endereço e telefone MUST permanecer fora do modelo importado.
- **FR-016**: O sistema MUST NOT alterar regras de stage, approval, fórmulas de nota/aderência, escopo (`scope`) ou autorização durante a importação.
- **FR-017**: O sistema MUST NOT importar avaliações, notas, comentários, PDI, treinamentos ou solicitações de ciclo nesta fatia.
- **FR-018**: O sistema MUST NOT reimplementar o catálogo CSV da spec 003 (`importar_competencias_cargo`); MUST assumir catálogo pré-existente ou criar apenas cargos faltantes referenciados por colaboradores.
- **FR-019**: O sistema MUST NOT exigir domínio `@greenn.com.br` para colaboradores importados; a denylist de domínio para cadastro normal MUST permanecer aplicável apenas aos fluxos fora da importação legado.
- **FR-020**: Testes automatizados MUST usar fixtures anonimizadas dedicadas; MUST NOT depender de arquivos em `data/legado-solides/raw/` no CI.

### Key Entities

- **Colaborador (CustomUser)**: Pessoa no sistema; atributos relevantes à importação: nome, e-mail (único), confirmado em, ativo/inativo, cargo, área, gestor direto, identificador Sólides opcional.
- **Área**: Unidade organizacional derivada do Departamento legado; criada/obtida por nome.
- **Cargo**: Posição no catálogo; já existente via spec 003 ou criada na importação; identificador Sólides opcional.
- **Identificador Sólides (`solides_id`)**: Chave externa para correlação com backups; nullable, único, indexado em Colaborador, Cargo, Competência, Avaliação e PDI.
- **Backup Colaboradores**: Fonte primária Excel (~325 linhas no dump 2026-06-24); contém dados cadastrais, departamento, cargo, demissão, superior.
- **Backup Avaliações (crosswalk)**: Fonte auxiliar para mapear Nome → Identificador Avaliado quando colaboradores não trazem ID próprio.
- **Relatório de Carga**: Saída operacional com totais, exceções e conflitos da execução.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Após evolução de schema, 100% das cinco entidades alvo (Colaborador, Cargo, Competência, Avaliação, PDI) aceitam registro com `solides_id` vazio sem regressão nos fluxos existentes.
- **SC-002**: Após importação bem-sucedida do dump 2026-06-24, ≥99% dos colaboradores com e-mail válido (~325) existem no sistema sem duplicata de e-mail.
- **SC-003**: 100% dos colaboradores com data de demissão preenchida no legado aparecem como inativos; 100% sem demissão aparecem como ativos.
- **SC-004**: ≥95% dos colaboradores com Superior direto id resolvível no legado (~260 com ID; ~29/31 gestores válidos) recebem gestor correto; 100% dos ciclos hierárquicos detectados aparecem no relatório (zero ciclos silenciosos).
- **SC-005**: Colaboradores com match no crosswalk (~187 no dump) têm `solides_id` preenchido; demais permanecem com identificador vazio sem falha da importação.
- **SC-006**: Modo `--dry-run` produz relatório completo com zero registros persistidos (verificável por contagem antes/depois).
- **SC-007**: Segunda execução consecutiva com mesmas fontes não aumenta contagem de colaboradores distintos por e-mail (delta duplicatas = 0).
- **SC-008**: Suite de testes automatizados passa em CI sem acesso a `raw/`; cobertura inclui dry-run, idempotência, demitidos inativos e validação de hierarquia.
- **SC-009**: Nenhum campo de PII proibido (CPF, RG, banco, endereço) aparece em registros importados ou em logs de produção com linha completa do backup.
- **SC-010**: Operador consegue popular ambiente de staging com colaboradores reais em uma única execução (< 5 minutos de tempo operacional humano, excluindo tempo de parse em hardware de referência) e revisar relatório em < 2 minutos.

## Assumptions

- Inventário, mapeamento coluna→domínio e estatísticas do dump estão documentados em `data/legado-solides/README.md` (Decisão #22 cumprida) e servem como referência operacional; esta spec não duplica todo o inventário.
- Catálogo de cargos e competências da spec 003 (`importar_competencias_cargo`) foi executado previamente ou será executado antes da importação de colaboradores na ordem segura documentada no README legado.
- Formato real dos backups é Microsoft Excel 2007+ (OOXML), uma planilha por arquivo — distinto dos arquivos CSV disfarçados de `.xlsx` da spec 003.
- Chave natural de deduplicação de colaboradores é o e-mail normalizado; `solides_id` complementa quando disponível via crosswalk.
- Colisão de e-mail no backup (duas linhas, mesmo e-mail): tratar como conflito reportado; a linha posterior não sobrescreve silenciosamente — operador resolve manualmente (volume esperado baixo ou zero no dump atual).
- Gestor demitido pode permanecer referenciado como `line_manager` de subordinados ativos (estrutura histórica); gestor importado como inativo.
- Data de admissão é informativa no legado; não bloqueia importação se ausente ou em formato serial Excel.
- Competência e Avaliação recebem apenas o campo `solides_id` nesta fatia; importação de conteúdo histórico dessas entidades fica para specs futuras (6.5.4–6.5.6).
- Comando é operacional (administrador técnico / RH com acesso ao ambiente), não exposto via UI.
- Fixtures anonimizadas serão mantidas em diretório dedicado (ex.: `data/legado-solides/samples/`) criado na fase de implementação.
- Padrões operacionais (dry-run, transação atômica, relatório, idempotência, exit codes) seguem o contrato da spec 003 salvo adaptações documentadas no plano desta feature.
- Conformidade com a constituição: importação persiste histórico organizacional; não simula POSTs de ciclo; não altera imutabilidade de avaliações existentes; escopo hierárquico passa a funcionar quando gestores estiverem resolvidos.

## Out of Scope

- Importação de avaliações, notas, comentários, PDI, treinamentos ou solicitações de ciclo.
- Extensão do catálogo via `backup_habilidades*` (Sprint 6.5.3 extensão — spec/comando separado).
- Interface de usuário para upload ou monitoramento de importação.
- Alteração de stage, approval, fórmulas de nota/aderência, escopo ou regras de autorização.
- Obrigatoriedade de domínio `@greenn.com.br` para registros importados.
- Importação de PII sensível além de nome e e-mail necessários ao cadastro.

## Dependencies

- **Spec 003** (`import-catalogo-legado`): catálogo base de cargos/competências e regras de `canonical_key`, senioridade e normalização de nomes.
- **Inventário legado** (`data/legado-solides/README.md`): mapeamentos, ordem de importação, denylist de alterações e política de PII.
- **PRD Sprint 6.5.1 / 6.5.2**: requisitos de schema e colaboradores; Decisões #21 (e-mail confirmado na importação) e #22 (inventário documentado).
