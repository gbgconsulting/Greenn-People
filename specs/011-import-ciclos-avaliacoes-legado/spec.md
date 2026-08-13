# Feature Specification: Importação One-Shot do Legado Sólides — Ciclos Históricos e Cabeçalhos de Avaliação

**Feature Branch**: `011-import-ciclos-avaliacoes-legado`

**Created**: 2026-08-13

**Status**: Draft

**Input**: User description: "Importação one-shot do legado Sólides — ciclos históricos e cabeçalhos de avaliação (Sprint 6.5.4 + pré-requisito solicitações→Ciclo). Specs 003 e 010 concluídas. Fatia (4) solicitações → Ciclo encerrado + (5) cabeçalhos Avaliacao. Fontes: backup_solicitacoes_* (~57) e backup_avaliacoes_* (~1.925). Sem isso, notas/comentários (6.5.5) não têm FK."

## Clarifications

### Session 2026-08-13

- Q: Chave externa do Ciclo para correlacionar solicitação Sólides → A: Adicionar `solides_id` em `Ciclo` (aditivo, nullable, único quando preenchido, indexado); valor = `Identificador` da solicitação (padrão 010). Descarta match só por nome/datas e crosswalk externo separado.
- Q: Agregação de N linhas Sólides (avaliador×avaliado) em Avaliações GP → A: 1 `Avaliacao` por `(ciclo, avaliado/usuario)`; N linhas do mesmo par colapsam. Descarta uma avaliação por linha e filtro só-autoavaliação.
- Q: Qual `Identificador` Sólides vira `Avaliacao.solides_id` no grupo agregado → A: Linha canônica = autoavaliação (`Nome Avaliador` = `Nome Avaliado`) se existir; senão o menor `Identificador` estável do grupo. IDs colapsados no relatório para 6.5.5.
- Q: Estado histórico `etapa`/`concluida` sem máquina de estados → A: Persistir direto `etapa=feedback` + `concluida=True`; sem `stage`, abertura/fechamento de ciclo ou aprovação. Derivação por status Sólides e etapa inicial **descartadas**.
- Q: Política para solicitações `draft`/`active`/`canceled` → A: Importar **todos** os status como `Ciclo` **encerrado** (nunca abrir ciclo ativo). Pular draft/active/canceled **descartado**.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Importar solicitações como ciclos históricos encerrados (Priority: P1)

O operador técnico executa a importação apontando para o backup de solicitações Sólides. Ao final, cada solicitação elegível existe como ciclo histórico no Greenn People, com nome normalizado, datas de início/fim interpretadas do legado, status sempre encerrado, e identificador externo Sólides que permite correlacionar a solicitação de origem nas fatias seguintes.

**Why this priority**: Sem ciclos resolvíveis, cabeçalhos de avaliação e notas futuras não têm âncora de FK. É o pré-requisito imediato da Sprint 6.5.4 e da ordem segura do inventário legado (passo 4).

**Independent Test**: Com colaboradores já importados (spec 010) e backup de solicitações disponível, executar a importação de ciclos e verificar contagem (~57 no dump 2026-06-24), status 100% encerrado, nomes legíveis e reexecução sem duplicar pelo identificador da solicitação.

**Acceptance Scenarios**:

1. **Given** o backup de solicitações disponível, **When** o operador executa a importação de ciclos, **Then** cada solicitação com identificador válido é criada ou atualizada como ciclo com nome normalizado, `data_inicio`/`data_fim` interpretadas (serial Excel ou ISO) e status **encerrado**.
2. **Given** solicitações com status legado `finished`, `canceled`, `draft` ou `active`, **When** a importação as processa, **Then** **todas** ficam com status encerrado — nenhum ciclo ativo é aberto nesta fatia.
3. **Given** um nome de solicitação representado como serial Excel (ex.: `46113.0`), **When** o parser normaliza o nome, **Then** o ciclo persiste um rótulo legível (não o número bruto serial), conforme regra documentada no contrato/assumptions.
4. **Given** a evolução de schema desta feature, **When** um ciclo é criado pela importação, **Then** o identificador da solicitação Sólides é gravado em `solides_id` do ciclo (opcional, único quando preenchido, indexado), alinhado ao padrão da spec 010.
5. **Given** já existe um ciclo aberto no ambiente (fluxo normal da aplicação), **When** a importação grava apenas ciclos encerrados, **Then** a regra “só um ciclo aberto” permanece válida — a importação não cria segundo aberto nem encerra o ciclo aberto vigente.

---

### User Story 2 - Importar cabeçalhos de avaliação agregados 1:1 (ciclo, usuário) (Priority: P1)

O operador executa a importação do backup de avaliações. O sistema resolve o ciclo pelo identificador da solicitação e o colaborador pelo identificador Sólides do avaliado (ou crosswalk nome/e-mail da 010). Como o Greenn People admite **uma** avaliação por pessoa/ciclo e o Sólides exporta N linhas (avaliador × avaliado), a importação **agrega** por (solicitação, avaliado), criando ou atualizando um único cabeçalho por pessoa no ciclo, em estado histórico terminal, sem avançar máquina de estados.

**Why this priority**: É o núcleo da Sprint 6.5.4 e o pré-requisito de FK para notas/comentários (6.5.5). Sem agregação correta, a unicidade `(ciclo, usuario)` é violada ou o histórico fica incompleto.

**Independent Test**: Após ciclos importados e usuários com `solides_id` quando disponível, importar cabeçalhos e verificar: zero duplicata `(ciclo, usuario)`; avaliados sem usuário resolvido no relatório; `solides_id` da avaliação determinístico e único; etapa terminal sem chamar serviços de avanço/abertura/fechamento de ciclo.

**Acceptance Scenarios**:

1. **Given** backup de avaliações e ciclos já importados com `solides_id` da solicitação, **When** a importação processa as linhas, **Then** resolve o ciclo via Identificador Solicitação e o usuário via Identificador Avaliado (`solides_id`) ou, se necessário, crosswalk nome/e-mail herdado da 010.
2. **Given** N linhas Sólides para o mesmo (solicitação, avaliado) com avaliadores distintos, **When** a importação agrega, **Then** existe exatamente **uma** Avaliação no Greenn People para aquele `(ciclo, usuario)` — não uma por linha de avaliador.
3. **Given** o grupo agregado, **When** o `solides_id` da Avaliação é definido, **Then** o valor é determinístico e único (linha canônica: preferir autoavaliação quando `Nome Avaliador` = `Nome Avaliado`; senão o menor Identificador do grupo), documentado no contrato; conflitos de unicidade aparecem no relatório.
4. **Given** uma Avaliação histórica importada, **When** a persistência conclui, **Then** o estado é terminal (`etapa=feedback` e `concluida=True`) **sem** invocar avanço de etapa, abertura ou fechamento de ciclo.
5. **Given** um avaliado cujo Identificador Avaliado não resolve para usuário importado, **When** a linha/grupo é processado, **Then** o caso entra no relatório como conflito/não resolvido e **nenhum** usuário é inventado.
6. **Given** esta fatia, **When** a importação termina, **Then** notas finais e linhas de competência **não** são preenchidas (reservadas à 6.5.5).

---

### User Story 3 - Simular, reexecutar e testar com samples anonimizados (Priority: P2)

O operador valida a carga com `--dry-run` (zero gravações), reexecuta de forma idempotente após correções, e a CI cobre o comportamento com fixtures anonimizadas em `data/legado-solides/samples/` — nunca `raw/`.

**Why this priority**: Backups contêm PII; staging exige dry-run e idempotência; CI não pode depender de `raw/`. Espelha o padrão operacional das specs 003 e 010.

**Independent Test**: Dry-run sem writes; duas execuções reais consecutivas sem duplicar Ciclo/Avaliação; suite automatizada verde só com samples; gate de regressão stage/scope/invariantes intacto.

**Acceptance Scenarios**:

1. **Given** arquivos válidos, **When** o operador executa com `--dry-run`, **Then** o sistema parseia, emite relatório com totais projetados e **não persiste** alterações.
2. **Given** uma importação bem-sucedida, **When** o operador reexecuta com as mesmas fontes, **Then** não duplica Ciclo pelo identificador da solicitação nem Avaliação por `(ciclo, usuario)` / `solides_id`.
3. **Given** erro fatal pré-persistência ou falha na transação, **When** a importação aborta, **Then** exit code indica falha e nenhum estado parcial inconsistente permanece (rollback atômico).
4. **Given** fixtures anonimizadas representativas (serial Excel em nomes/datas, multi-avaliador por avaliado, órfão sem usuário, solicitação active/canceled), **When** a suite roda no CI, **Then** cobre dry-run, agregação, idempotência e denylist; nenhum teste lê `raw/`.
5. **Given** a suite de regressão de domínio, **When** a feature é integrada, **Then** testes de stage/scope/invariante de rejeição de etapa permanecem verdes e a denylist de mutação de serviços de domínio permanece vazia.

---

### Edge Cases

- Arquivo de solicitações ou avaliações ausente, corrompido ou sem planilha/`sheet1` esperada: falha clara antes da persistência; exit de erro.
- Solicitação sem Identificador: não importável; reportar; não bloquear silenciosamente o restante quando política de continuação parcial estiver documentada — preferir aborto atômico se o contrato exigir consistência total da fatia.
- Datas ausentes ou inválidas em `Iniciada em` / `Terminada em`: reportar conflito; política default — exigir ambas para criar ciclo (volume baixo; operador corrige fonte).
- Nome serial Excel vs. texto: normalizar para rótulo legível; se normalização falhar, reportar e não gravar nome bruto ambíguo sem registro no relatório.
- Solicitação `active`, `draft` ou `canceled` no legado: **sempre** importar como encerrado (histórico); nunca abrir; não pular por status.
- Múltiplas linhas de avaliação para o mesmo avaliado/ciclo: agregar; listar Identificadores colapsados no relatório (amostra mascarada) para apoiar a fatia 6.5.5.
- Conflito de `solides_id` canônico já usado por outra Avaliação: reportar; não sobrescrever silenciosamente.
- Avaliado demitido (usuário inativo na 010): cabeçalho histórico **permitido** se o usuário existir; inatividade não bloqueia o vínculo.
- Ciclo referenciado em avaliações mas ausente no backup de solicitações: reportar órfão; não inventar ciclo.
- Reexecução alterando nome/datas do ciclo ou estado terminal da Avaliação: atualizar campos permitidos e reportar como atualizado; não reabrir ciclo.
- Relatório em produção: totais + amostra mascarada de exceções; **sem** dump completo de PII (nomes/e-mails em massa).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O sistema MUST adicionar campo identificador externo Sólides (`solides_id`) no Ciclo — opcional, único quando preenchido, indexado — via evolução de schema **aditiva** apenas (sem alterar campos existentes do Ciclo). Justificativa: alinhamento à spec 010, resolução determinística de FK nas avaliações e nas fatias 6.5.5+, e reexecução idempotente por chave legado.
- **FR-002**: O sistema MUST oferecer comando(s) de importação one-shot reproduzível(is) que leem `backup_solicitacoes_avalicaoes_*` e `backup_avaliacoes_*` (Excel OOXML real) e persistem ciclos históricos e cabeçalhos de Avaliação — sem interface de upload, UI, API REST ou fila assíncrona nesta fatia.
- **FR-003**: O parser MUST residir isolado da persistência (padrão 003/010: biblioteca de planilha apenas no parser) e MUST aceitar datas/nomes em serial Excel e strings ISO conforme inventário legado.
- **FR-004**: O sistema MUST mapear Identificador da solicitação → `Ciclo.solides_id` e persistir `nome`, `data_inicio`, `data_fim` normalizados.
- **FR-005**: O sistema MUST gravar **todo** ciclo importado com status encerrado, independentemente do status Sólides (`finished` / `canceled` / `draft` / `active`).
- **FR-006**: O sistema MUST NOT abrir ciclo ativo nesta fatia e MUST NOT violar a regra de negócio “no máximo um ciclo aberto”.
- **FR-007**: O sistema MUST agregar linhas de `backup_avaliacoes_*` pela chave lógica (Identificador Solicitação, Identificador Avaliado), produzindo no máximo uma Avaliação por `(ciclo, usuario)`.
- **FR-008**: O sistema MUST resolver Ciclo via `solides_id` = Identificador Solicitação e CustomUser via `solides_id` = Identificador Avaliado, com fallback ao crosswalk nome/e-mail da spec 010 quando documentado e disponível.
- **FR-009**: O sistema MUST definir `Avaliacao.solides_id` de forma determinística e única por grupo agregado (linha canônica: autoavaliação se existir; senão menor Identificador do grupo) e MUST reportar conflitos de unicidade e Identificadores colapsados (amostra mascarada).
- **FR-010**: O sistema MUST persistir Avaliações históricas em estado terminal (`etapa=feedback` e `concluida=True`) **sem** chamar serviços de avanço de etapa, abertura ou fechamento de ciclo, aprovação, fórmulas ou escopo.
- **FR-011**: O sistema MUST NOT inventar usuários nem ciclos; órfãos e não resolvidos MUST aparecer no relatório.
- **FR-012**: O sistema MUST NOT preencher notas finais nem linhas de competência nesta fatia.
- **FR-013**: O sistema MUST aceitar `--dry-run`: parse completo, relatório com totais projetados, zero persistência.
- **FR-014**: O sistema MUST persistir alterações reais em transação atômica — falha implica rollback completo.
- **FR-015**: O sistema MUST ser idempotente: reexecução MUST NOT duplicar Ciclo por `solides_id` da solicitação nem Avaliação por `(ciclo, usuario)` / `solides_id` canônico.
- **FR-016**: O sistema MUST emitir relatório estruturado (criados, atualizados, inalterados, conflitos, não resolvidos / órfãos, grupos agregados) com amostra mascarada e MUST usar exit code 0 sucesso / 1 erro fatal — alinhado às specs 003/010.
- **FR-017**: O sistema MUST NOT alterar AuthZ, inventar métricas, mutar serviços denylist (`stage`, abertura/fechamento de ciclo, approval, evaluation, adherence, scope) nem simular POSTs de ciclo.
- **FR-018**: Persistência MUST respeitar validações de domínio existentes (`save`/`clean`) e FKs com proteção de exclusão intactas.
- **FR-019**: Testes automatizados MUST usar fixtures anonimizadas em `data/legado-solides/samples/`; MUST NOT depender de `data/legado-solides/raw/` no CI.
- **FR-020**: O sistema MUST NOT importar notas, comentários, PDI, treinamentos, nem estender o catálogo das 57 habilidades extras nesta fatia (salvo se estritamente necessário para `solides_id` de Competência — preferir deferir à spec seguinte de notas/catálogo).

### Key Entities

- **Ciclo (histórico)**: Representa uma solicitação Sólides encerrada; atributos relevantes: nome, datas, status sempre encerrado, `solides_id` = Identificador da solicitação.
- **Avaliação (cabeçalho)**: Uma por pessoa/ciclo; agrega N linhas avaliador×avaliado do legado; estado terminal; `solides_id` canônico determinístico; sem notas nesta fatia.
- **Colaborador (CustomUser)**: Já importado na 010; resolvido por `solides_id` do avaliado ou crosswalk.
- **Solicitação legada**: Fonte (~57 linhas); status finished/canceled/draft/active → todos encerrados no GP.
- **Linha de avaliação legada**: Fonte (~1.925 linhas); chave de agregação (solicitação, avaliado).
- **Relatório de carga**: Totais, órfãos, conflitos, IDs colapsados (amostra mascarada); sem dump completo de PII.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Após a evolução aditiva de schema, 100% dos ciclos importados podem carregar `solides_id` da solicitação sem regressão nos fluxos existentes de ciclo (abrir/encerrar manual permanece intacto).
- **SC-002**: Após importação bem-sucedida do dump 2026-06-24, 100% das solicitações elegíveis (~57) existem como ciclos **encerrados**; zero ciclos abertos criados pela importação.
- **SC-003**: Após importação de cabeçalhos, 100% das Avaliações criadas respeitam unicidade `(ciclo, usuario)` — nenhuma duplicata por multi-avaliador no legado.
- **SC-004**: ≥95% dos grupos (solicitação, avaliado) cujo Identificador Avaliado resolve para usuário importado geram Avaliação; 100% dos não resolvidos aparecem no relatório (zero usuário inventado).
- **SC-005**: Modo `--dry-run` produz relatório completo com zero registros persistidos (contagem antes/depois inalterada para Ciclo e Avaliação).
- **SC-006**: Segunda execução consecutiva com as mesmas fontes não aumenta contagem de Ciclos distintos por `solides_id` nem de Avaliações distintas por `(ciclo, usuario)` (delta duplicatas = 0).
- **SC-007**: Suite de testes automatizados passa em CI sem acesso a `raw/`; cobre dry-run, agregação multi-avaliador, órfãos, idempotência e status sempre encerrado.
- **SC-008**: Gate de regressão: testes de stage/scope/invariante de rejeição de etapa permanecem verdes; diff da denylist de serviços de domínio permanece vazio.
- **SC-009**: Operador consegue popular staging com ciclos + cabeçalhos do dump em uma execução operacional (< 10 minutos de tempo humano, excluindo parse em hardware de referência) e revisar o relatório em < 3 minutos.
- **SC-010**: Relatório de produção não contém dump completo de PII; apenas totais e amostra mascarada de exceções.

## Assumptions

- Specs **003** (catálogo) e **010** (colaboradores + `solides_id` em entidades já previstas, inclusive Avaliação) estão aplicadas no ambiente alvo antes desta fatia; catálogo completo não bloqueia cabeçalhos, mas é necessário antes das notas (6.5.5).
- Inventário e mapeamentos em `data/legado-solides/README.md` (Decisão #22) são a fonte de colunas/volumes; esta spec não duplica o inventário inteiro.
- **Decisão de chave de Ciclo** (clarificada 2026-08-13): migration aditiva de `solides_id` em Ciclo (= `Identificador` da solicitação); alinhada à 010. Match só por nome/datas e tabela de crosswalk separada **descartados**.
- Dump de referência: 2026-06-24 — ~57 solicitações (50 finished, 1 active, 3 draft, 3 canceled) e ~1.925 linhas de avaliação. **Política de status** (clarificada 2026-08-13): finished/draft/active/canceled → **todos** viram ciclo encerrado; zero ciclo aberto pela importação.
- Normalização de nome serial Excel: converter serial de data Excel para representação de data legível (mesmo critério de datas) quando o campo Nome for numérico/serial; caso contrário, strip/colapsar whitespace.
- Datas inválidas/ausentes em solicitações: conflito reportado; ciclo não criado até correção da fonte (conservador para volume ~57).
- **Agregação** (clarificada 2026-08-13): uma Avaliação por (solicitação/ciclo, avaliado); N linhas avaliador×avaliado colapsam; lista de Identificadores colapsados fica no relatório para a fatia 6.5.5 resolver notas que apontam a IDs não canônicos. Uma avaliação por linha Sólides e import só de autoavaliação **descartados**.
- **Linha canônica para `Avaliacao.solides_id`** (clarificada 2026-08-13): autoavaliação (`Nome Avaliador` = `Nome Avaliado`) se existir no grupo; senão o menor Identificador numérico/lexicográfico estável do grupo. Hash composto e `solides_id` nulo nesta fatia **descartados**.
- Avaliado inativo (demitido) pode receber cabeçalho histórico se o usuário existir.
- **Estado terminal histórico** (clarificado 2026-08-13): `etapa=feedback` + `concluida=True` por persistência direta, sem passar pela máquina de estados (`stage`), abertura/fechamento de ciclo ou aprovação — coerente com ciclo encerrado e pré-requisito de leitura histórica.
- Comando(s) são operacionais (admin técnico / RH com acesso ao ambiente), não expostos via UI.
- Padrões operacionais (dry-run, atomicidade, relatório, idempotência, exit codes, parser de planilha isolado da persistência) seguem 003/010 salvo adaptações no plano/contrato desta feature.
- Constituição: importação persiste histórico; não simula POSTs de ciclo; PROTECT e imutabilidade de regras de cálculo/AuthZ permanecem intactos.

## Out of Scope

- Importação de notas (`importar_notas`), comentários, PDI e treinamentos.
- Extensão do catálogo das 57 habilidades extras (`backup_habilidades*`), salvo necessidade estrita deferida preferencialmente à próxima spec de notas.
- Interface de usuário, API remota ou processamento assíncrono desta carga.
- Mutação de `stage`, abertura/fechamento de ciclo, `approval`, `evaluation`, `adherence`, `scope` e AuthZ.
- Abrir ciclo ativo; inventar métricas; POST de ciclo.
- Importar comentários ou PII além do necessário ao cabeçalho histórico.
- Preencher `nota_final_*` ou `AvaliacaoCompetencia` nesta fatia.

## Dependencies

- **Spec 010** (`import-colaboradores-legado`): usuários com `solides_id` quando o crosswalk existiu; demitidos/ativos corretos; `Avaliacao.solides_id` já no schema.
- **Spec 003** (`import-catalogo-legado`): catálogo preferencialmente carregado (não bloqueia cabeçalho; bloqueia notas futuras).
- **Inventário legado** (`data/legado-solides/README.md`): colunas, volumes, ordem segura, denylist e política de PII.
- **PRD Sprint 6.5.4** e pré-requisito solicitações → Ciclo na ordem segura do README.
