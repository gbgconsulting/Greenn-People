# Feature Specification: Importação One-Shot do Legado Sólides — PDIs e Ações

**Feature Branch**: `014-import-pdi-acoes-legado`

**Created**: 2026-08-19

**Status**: Draft

**Input**: User description: "Importação one-shot do legado Sólides — PDIs e ações (Sprint PRD 6.5.6). Pré-condição: specs 003 e 010. Specs 011/013 NÃO são pré-requisito de FK. Fonte: backup_pdi_*.xlsx (~86). Comando único importar_pdi. Sem UI/upload. Objetivo: desligar a Sólides como arquivo de PDI."

## Clarifications

### Session 2026-08-19 (decisões fechadas — não reabrir)

- **Granularidade**: 1 linha da planilha = 1 PDI do colaborador já importado + 1 ação. A descrição da ação é a concatenação determinística dos campos Objetivo / Situação Atual / Situação Desejada **não vazios**, com separador documentado nesta spec. Não criar três ações. Não persistir PDI sem ação.
- **Responsável da ação**: sempre o dono do PDI (a pessoa resolvida da linha). Nunca o gestor hierárquico. Nunca inventar pessoa.
- **Ciclo / avaliação**: PDI no produto é independente de ciclo. Zero vínculo persistido com ciclo ou avaliação. Identificador de solicitação no dump, se existir, é no máximo órfão **informativo** no relatório.
- **Chave externa**: o export **não** traz ID Sólides de PDI. Preencher o identificador Sólides já existente no PDI com um **digest determinístico curto** da chave natural (chave canônica do nome + título normalizado + instante “Criado em”, se houver). Não persistir nome/título concatenados nesse identificador (isso seria dado pessoal no identificador). Upsert do PDI por esse identificador. A ação **não** ganha identificador Sólides: idempotência pela chave natural (PDI + descrição normalizada + prazo).
- **Status do PDI**: `finalizado` → concluído; `em_andamento` → ativo; desconhecido → conflito/skip. Sem status arquivado nesta fatia.
- **Status da ação**: PDI concluído → ação concluída (nunca atrasada). PDI ativo + prazo interpretável anterior à data da carga → atrasada. PDI ativo + prazo ≥ data da carga → pendente. Prazo ausente ou ilegível → conflito da linha (prazo é obrigatório; não inventar data).
- **Pessoa**: match **único** via chave canônica do `Nome`; identificador Sólides da pessoa se o dump trouxer. Inativo (demitido) é permitido. Ambíguo ou irresolvível → órfão. Nunca inventar colaborador.
- **Atraso**: reutilizar o recálculo de atraso **já existente** do domínio PDI **na linha importada**. Não disparar e-mail, agendamento em massa, marcação de atraso em lote nem recálculo de dashboard/aderência.
- **Parser / persistência**: parser único já usado nas fatias 010/011/013. Persistência só no domínio PDI. Datas: serial Excel e ISO.
- **Operação**: simulação (`--dry-run`); uma unidade atômica de persistência; exit 0 sucesso / 1 erro fatal; rollback se falhar.
- **Schema**: preferir zero evolução. O identificador Sólides do PDI já existe (opcional, único quando preenchido, indexado) — não alterar tipo, tamanho máximo, unicidade, opcionalidade nem política de exclusão. Sem migration, sem campo novo de PII, sem identificador Sólides na ação, sem vínculo a ciclo/avaliação. Sem apagar PDI/ação para “refazer” a carga. Persistência pelas validações de domínio existentes (sem gravação em massa que ignore validação).
- **Pré-condição**: specs 003 (chave canônica / nome de exibição) e 010 (colaboradores, inclusive inativos; identificador Sólides do PDI já no schema da 6.5.1) aplicadas no ambiente alvo. Specs 011 e 013 **não** são pré-requisito de vínculo.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Persistir PDIs e uma ação por linha (Priority: P1)

O operador técnico executa a importação one-shot do backup de PDI, em homologação/banco descartável, após simulação. Cada linha resolvível gera **um** plano de desenvolvimento do colaborador já importado na spec 010 e **uma** ação ligada a esse plano. O título vem do legado; a descrição da ação junta Objetivo, Situação Atual e Situação Desejada não vazios. O responsável da ação é o dono do PDI. O plano **não** se liga a ciclo nem a avaliação. O identificador Sólides do PDI é um digest curto da chave natural — não o nome da pessoa em claro.

**Why this priority**: É o miolo da Sprint 6.5.6. Sem isto a Sólides permanece arquivo de PDI e o produto não substitui o legado operacionalmente.

**Independent Test**: Com catálogo (003) e colaboradores (010) carregados — **sem** exigir ciclos/notas (011/013) — importar o backup de PDI e verificar: 1 PDI + 1 ação por linha resolvível; dono e responsável iguais; zero vínculo a ciclo/avaliação; identificador Sólides curto e estável; zero pessoa inventada; zero PDI persistido sem ação.

**Acceptance Scenarios**:

1. **Given** backup de PDI e colaboradores já importados, **When** o operador executa a importação, **Then** cada linha com pessoa, título, status conhecido, prazo interpretável e pelo menos um trecho de Objetivo/Situação Atual/Situação Desejada gera ou atualiza **um** PDI e **uma** ação — nunca três ações, nunca PDI órfão de ação.
2. **Given** Objetivo, Situação Atual e Situação Desejada com subconjunto preenchido, **When** a descrição da ação é montada, **Then** entram **somente** os trechos não vazios, na ordem Objetivo → Situação Atual → Situação Desejada, separados pelo separador documentado (duas quebras de linha). Trechos vazios são omitidos.
3. **Given** os três trechos vazios, **When** a linha é processada, **Then** é **conflito/skip** — não persiste PDI sem descrição de ação.
4. **Given** pessoa resolvida, **When** a ação é persistida, **Then** o responsável é **essa mesma pessoa**; **nunca** o gestor hierárquico; **nunca** uma pessoa inventada.
5. **Given** identificador de solicitação/ciclo presente ou ausente no dump, **When** o PDI é persistido, **Then** não há vínculo com ciclo nem avaliação. Se o identificador existir e não for usado, a linha **não** falha por isso; no máximo consta como informação órfã no relatório.
6. **Given** a chave natural (chave canônica do nome + título normalizado + instante “Criado em” se houver), **When** o identificador Sólides do PDI é preenchido, **Then** é um digest determinístico **curto** (cabe no campo existente de 50 caracteres), **sem** concatenar nome/título em claro. Upsert do PDI é por esse identificador.
7. **Given** status legado `finalizado`, **When** o PDI é persistido, **Then** status do PDI é concluído e o da ação é concluída (**nunca** atrasada).
8. **Given** status legado `em_andamento` e prazo interpretável **anterior** à data da carga, **When** o PDI é persistido, **Then** PDI fica ativo e a ação fica atrasada.
9. **Given** status legado `em_andamento` e prazo interpretável **igual ou posterior** à data da carga, **When** o PDI é persistido, **Then** PDI fica ativo e a ação fica pendente.
10. **Given** status legado desconhecido, **When** a linha é processada, **Then** conflito/skip; **não** usar arquivado nesta fatia.
11. **Given** prazo ausente ou ilegível, **When** a linha é processada, **Then** conflito/skip; **não** inventar data de prazo.
12. **Given** a ação sendo gravada, **When** o recálculo de atraso vigente do domínio PDI se aplica à **mesma linha**, **Then** o status resultante permanece coerente com as regras 7–9; **não** dispara e-mail, job em massa de atraso, nem recálculo de dashboard/aderência.

---

### User Story 2 - Resolver colaborador sem inventar pessoa (Priority: P1)

Cada linha aponta para um colaborador já existente (ativo ou inativo). A resolução é por match **único** da chave canônica do `Nome` (a mesma das specs 003/010); se o dump trouxer identificador Sólides da pessoa, ele pode reforçar o match. Nome ambíguo, vazio ou sem correspondente → órfão no relatório, sem criar colaborador.

**Why this priority**: PDI sem dono correto corrompe o arquivo de desenvolvimento e violaria a regra de nunca inventar usuário.

**Independent Test**: Fixtures com nome único, nome duplicado, nome ausente, demitido e identificador Sólides quando presente; verificar persistência só no match único e 100% dos demais no relatório como órfãos.

**Acceptance Scenarios**:

1. **Given** `Nome` cuja chave canônica corresponde a **exatamente uma** pessoa importada, **When** a linha é resolvida, **Then** o PDI pertence a essa pessoa (inativa permitida).
2. **Given** dump com identificador Sólides da pessoa **e** esse identificador existe no cadastro, **When** a resolução ocorre, **Then** o match por identificador prevalece se for único e coerente; conflito identificador vs nome único divergente → conflito/skip.
3. **Given** zero ou duas+ pessoas com a mesma chave canônica, **When** a linha é processada, **Then** é órfã; **nunca** inventa colaborador e **nunca** escolhe o “primeiro” em silêncio.
4. **Given** colaborador demitido (inativo) com match único, **When** o PDI é persistido, **Then** a carga **não** é bloqueada pela inatividade; a leitura posterior continua pelo escopo hierárquico **já vigente** — inatividade **não** cria atalho de visibilidade.

---

### User Story 3 - Simular, reexecutar e validar com samples anonimizados (Priority: P2)

O operador valida com simulação (zero gravação), reexecuta de forma idempotente, e a CI cobre o comportamento só com fixtures anonimizadas — nunca os backups brutos. O relatório traz totais completos e amostra mascarada. Executar a importação **não** mexe em etapa, ciclo, metas, notas, fórmula, escopo, aderência, 9-box nem telas da visão histórica (spec 012).

**Why this priority**: O backup contém dados pessoais e textos de desenvolvimento. Staging exige simulação. A fatia é persistência de arquivo de PDI, não produto novo de autorização nem ciclo operacional.

**Independent Test**: Simulação sem writes; duas execuções reais consecutivas sem duplicar PDI pela chave digest nem ação pela chave natural; suite automatizada verde só com samples; teste de ouro da denylist; regressão de etapa/escopo inalterada.

**Acceptance Scenarios**:

1. **Given** arquivo válido, **When** o operador executa com simulação, **Then** o sistema parseia, emite relatório com totais projetados e **não persiste** alterações.
2. **Given** uma importação bem-sucedida, **When** o operador reexecuta com a mesma fonte, **Then** delta nas chaves naturais (digest do PDI; PDI + descrição normalizada + prazo da ação) = 0.
3. **Given** erro fatal pré-persistência ou falha na unidade de persistência, **When** a importação aborta, **Then** exit indica falha e nenhum estado parcial inconsistente permanece (rollback atômico).
4. **Given** fixtures anonimizadas (match único, órfão, ambíguo, inativo, status desconhecido, prazo ilegível, descrição vazia, PII na fonte, 2ª run), **When** a suite roda no CI, **Then** cobre simulação, idempotência, denylist e mascaramento; **nenhum** teste lê backups brutos.
5. **Given** a suite de regressão de domínio, **When** a feature é integrada, **Then** testes de etapa/escopo/invariante de rejeição permanecem verdes **sem** alterar asserts, e o teste de ouro da denylist permanece vazio (nenhuma alteração das regras preservadas).

---

### Edge Cases

- Arquivo ausente, corrompido ou sem a planilha esperada: falha clara antes da persistência; exit de erro.
- Título ausente/vazio: conflito/skip (não inventar título).
- “Criado em” ausente: o digest usa a chave natural **sem** esse instante; duas linhas com mesmo nome+título e sem instante colidem no mesmo PDI — a 2ª é atualização/conflito conforme o restante dos campos, nunca um segundo identificador inventado.
- “Criado em” presente: entra no digest para distinguir PDIs homônimos da mesma pessoa.
- Objetivo/Situação com texto longo: persiste no registro de negócio; **nunca** aparece completo em relatório, stdout, stderr, log ou arquivo de relatório.
- PII cadastral (CPF, RG, CTPS, PIS, banco, endereço, telefone) presente na fonte: **não** importar; presença ≠ persistir.
- Pessoa inativa: persistir se match único; visibilidade posterior = escopo vigente (sem bypass).
- Identificador de solicitação no dump: não cria FK; no máximo seção informativa no relatório.
- Status `arquivado` do produto: **não** usado nesta fatia, mesmo que o legado traga valor não mapeado (esse caso é conflito).
- Reexecução: **não** apagar PDI/ação para “refazer”; upsert/skip/conflito.
- Recálculo de atraso: só na linha gravada, via regra já existente do domínio; **não** disparar marcação em massa nem e-mail.
- Relatório: totais completos; amostra mascarada (máx. 5 por seção); sem nome, e-mail, linha bruta da planilha, título/objetivo completos.
- Homologação com backups brutos: **manual**, staging/banco descartável, simulação primeiro. CI só com samples.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O sistema MUST oferecer um único comando operacional one-shot `importar_pdi` no app de PDI, reproduzível, no padrão das specs 010/011/013. MUST NOT haver interface de upload, tela nova, API remota, rota nova, papel de produto novo ou fila assíncrona nesta fatia.
- **FR-002**: O parse da planilha MUST permanecer isolado da persistência (parser único já usado nas fatias 010/011/013). A persistência MUST ocorrer somente no domínio PDI.
- **FR-003**: O sistema MUST ler a fonte única `backup_pdi_*.xlsx` (Excel real; dump de referência 2026-06-24; ~86 linhas: 67 `finalizado`, 19 `em_andamento`). Inventário e colunas: `data/legado-solides/README.md` (Decisão #22). MUST NOT importar `backup_treinamentos`.
- **FR-004**: Cada linha resolvível MUST resultar em exatamente 1 PDI + 1 ação. MUST NOT criar três ações a partir de Objetivo / Situação Atual / Situação Desejada. MUST NOT persistir PDI sem ação.
- **FR-005**: A descrição da ação MUST ser a concatenação determinística dos trechos não vazios, nesta ordem: Objetivo, Situação Atual, Situação Desejada. Separador documentado: **duas quebras de linha** (`\n\n`) entre trechos. Os três vazios → conflito/skip.
- **FR-006**: O responsável da ação MUST ser o dono do PDI (pessoa resolvida da linha). MUST NOT usar o gestor hierárquico. MUST NOT inventar colaborador.
- **FR-007**: O sistema MUST NOT criar vínculo (FK) com ciclo ou avaliação. PDI no produto é independente de ciclo. Identificador de solicitação no dump, se existir, MUST NO máximo aparecer como órfão informativo no relatório — MUST NOT bloquear linhas resolvíveis nem persistir vínculo.
- **FR-008**: Como o export não traz ID Sólides de PDI, o sistema MUST preencher o identificador Sólides **já existente** do PDI com digest determinístico **curto** (cabe no campo atual de comprimento 50) da chave natural: chave canônica do `Nome` + título normalizado + instante “Criado em” se houver. MUST NOT persistir nome/título concatenados nesse identificador (PII no identificador). O digest MUST NOT ser tratado como schema novo nem como PII em claro. Upsert do PDI MUST ser por esse identificador.
- **FR-009**: A ação MUST NOT ganhar identificador Sólides. Idempotência da ação MUST usar chave natural: PDI resolvido + descrição normalizada + prazo.
- **FR-010**: De-para de status do PDI MUST ser: `finalizado` → concluído; `em_andamento` → ativo; qualquer outro valor → conflito/skip. MUST NOT gravar arquivado nesta fatia.
- **FR-011**: De-para de status da ação MUST ser: PDI concluído → ação concluída (MUST NOT atrasada); PDI ativo e prazo interpretável < data da carga → atrasada; PDI ativo e prazo ≥ data da carga → pendente. Prazo ausente/ilegível MUST ser conflito da linha; MUST NOT inventar prazo.
- **FR-012**: Resolução de pessoa MUST ser match **único** via chave canônica do `Nome` (mesma das specs 003/010). Identificador Sólides da pessoa, se o dump trouxer, MAY reforçar o match. Inativo permitido. Ambíguo/irresolvível → órfão. MUST NOT inventar colaborador.
- **FR-013**: Ao persistir a ação, o sistema MUST reutilizar o recálculo de atraso já existente do domínio PDI **naquela linha**. MUST NOT disparar e-mail, agendamento/Beat, marcação de atraso em massa, nem recálculo de dashboard/aderência.
- **FR-014**: Datas MUST aceitar serial Excel e ISO, no mesmo contrato das fatias 010/011/013.
- **FR-015**: O comando MUST aceitar simulação (`--dry-run`: zero gravação), persistir em **uma** transação atômica, ser idempotente, emitir relatório (criados / atualizados / inalterados / conflitos / órfãos) com amostra mascarada (máx. 5 por seção) e usar exit 0 sucesso / 1 erro fatal. Totais MUST ser sempre completos. Falha MUST fazer rollback.
- **FR-016**: Persistência MUST passar pelas validações de domínio existentes (validação completa + gravação). MUST NOT usar SQL cru nem gravação em massa que ignore validação/gravação de domínio.
- **FR-017**: Vínculos protegidos contra exclusão em cascata de PDI e ação MUST permanecer intactos (`PROTECT`). MUST NOT alterar essa política para CASCADE. MUST NOT apagar PDI/ação para “refazer” a carga.
- **FR-018** *(PII / OPSEC — nível 010 FR-015 + 013 FR-018/022)*: MUST NOT importar CPF, RG, CTPS, PIS, banco, endereço, telefone — mesmo que a planilha traga. Objetivo, Situação e título persistem no registro de negócio; MUST NOT aparecer **completos** em relatório, stdout, stderr, logging, traceback tratado ou arquivo de relatório. Relatório MUST reutilizar mascaramento já existente (`mask_solides_id` / `mask_pii`). MUST NOT incluir nome, e-mail ou linha bruta da planilha. Logs de produção MUST NOT imprimir linha bruta do backup.
- **FR-019** *(schema — inegociável)*: Preferir **zero** evolução de schema. O identificador Sólides do PDI já existe: opcional, único quando preenchido, indexado — MUST NOT alterar tipo, comprimento máximo, unicidade, opcionalidade nem política de exclusão. MUST NOT criar migration, campo novo, tabela de mapa, campo de PII, FK nova, identificador Sólides na ação, nem vínculo a ciclo/avaliação.
- **FR-020** *(autorização — nível 013 FR-020 + 011 FR-017)*: A importação MUST NOT chamar nem alterar regras de visibilidade/escopo hierárquico (`get_visible_users`, mixins de objeto no escopo, módulo de escopo). Nenhuma regra nova de “quem vê PDI de quem”. Depois da carga, a leitura continua pelas telas e escopo **já existentes** do produto PDI. PDI de demitido MUST NOT ficar visível fora do escopo vigente. Operador = administrador técnico de plataforma com acesso ao ambiente; MUST NOT ser papel de produto novo nem endpoint público. Executar a importação MUST NOT mudar quem vê quem.
- **FR-021** *(denylist / teste de ouro — nível 013 FR-021 + gate 011 SC-008)*: Executar `importar_pdi` MUST NOT: avançar etapa; abrir/fechar ciclo; aprovar/reprovar meta; alterar avaliação / nota por competência / feedback / notas finais; editar o módulo de fórmula de nota; classificar 9-box; disparar cálculo de aderência; tocar urls/templates da spec 012; criar rota `/historico/`. Diff desses caminhos MUST ser vazio no merge. Gate: testes de máquina de etapa / escopo / invariante de rejeição verdes **sem** alterar asserts. Permitido: persistir PDI/ação; preencher identificador Sólides **já existente** do PDI; estender parse/datas/relatório; samples e testes desta fatia.
- **FR-022**: Testes automatizados MUST usar fixtures anonimizadas em `data/legado-solides/samples/`; MUST NOT ler `data/legado-solides/raw/` no CI. Homologação com backups brutos é **manual**, em staging/banco descartável, com simulação primeiro.
- **FR-023**: Esta fatia MUST NOT reabrir as specs 010/011/013, MUST NOT importar o catálogo extra 57 + matriz ~2.720, MUST NOT importar treinamentos, MUST NOT implementar a homologação operacional completa (6.5.7) e MUST NOT inventar 9-box/metas a partir do PDI importado.

### Key Entities

- **PDI (plano de desenvolvimento individual)**: Um por linha resolvível; pertence a colaborador já importado; título legado; status ativo ou concluído nesta fatia; identificador Sólides = digest curto da chave natural (não PII em claro); **sem** vínculo a ciclo/avaliação.
- **Ação de PDI**: Exatamente uma por PDI importado nesta fatia; descrição concatenada; prazo obrigatório; responsável = dono do PDI; status concluída / atrasada / pendente conforme regras desta spec; **sem** identificador Sólides próprio.
- **Colaborador (pessoa)**: Já persistido na spec 010; match único por chave canônica (e identificador se o dump trouxer); inativo permitido; nunca criado aqui.
- **Chave natural do PDI**: chave canônica do nome + título normalizado + instante de criação legado se houver; materializada só como digest curto no identificador Sólides existente.
- **Chave natural da ação**: PDI + descrição normalizada + prazo.
- **Relatório de carga**: Totais + amostra mascarada (máx. 5/seção); seções criados/atualizados/inalterados/conflitos/órfãos (incl. informativo de solicitação, se houver).
- **Fonte**: `backup_pdi_*.xlsx` (~86 linhas; dump 2026-06-24).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Após importação bem-sucedida do dump 2026-06-24, as ~86 linhas são processadas (persistidas, atualizadas, inalteradas, conflito ou órfão); 100% das irresolvíveis aparecem no relatório; zero colaborador inventado.
- **SC-002**: 100% das linhas resolvíveis geram exatamente 1 PDI + 1 ação; zero PDI persistido sem ação; zero linha resolvível transformada em três ações.
- **SC-003**: 100% das ações persistidas têm responsável igual ao dono do PDI; zero ação atribuída ao gestor hierárquico por esta carga.
- **SC-004**: Zero PDI importado nesta fatia com vínculo a ciclo ou avaliação.
- **SC-005**: Segunda execução consecutiva com a mesma fonte: delta 0 nas chaves naturais (digest do PDI; PDI + descrição normalizada + prazo da ação).
- **SC-006**: Modo simulação produz relatório completo com zero registros persistidos (contagem antes/depois inalterada para PDI e ações).
- **SC-007**: Suite automatizada passa no CI **sem** qualquer referência a backups brutos; cobre match único, órfão, ambíguo, inativo, status desconhecido, prazo ilegível, descrição vazia, digest curto (≠ nome concatenado), idempotência e mascaramento.
- **SC-008**: Relatório de produção: totais completos; amostra mascarada ≤ 5 itens por seção; zero dump de nome, e-mail, linha bruta, título/objetivo/situação **completos**; operador revisa totais em < 3 minutos.
- **SC-009**: Operador popula staging (após simulação obrigatória) em uma execução operacional (< 10 minutos de tempo humano, excluindo parse em hardware de referência).
- **SC-010**: Teste de ouro: executar a importação não altera etapa, escopo, fórmula, abertura/fechamento de ciclo, metas, notas/feedback, 9-box, aderência nem telas/rotas da spec 012; regressão de etapa/escopo/invariante permanece verde sem mudança de asserts.
- **SC-011**: Recorte conhecido do dump (67 finalizado / 19 em_andamento) **não** é invertido no de-para de status do PDI; status desconhecido = 100% no relatório como conflito/skip.
- **SC-012**: 100% das linhas com prazo ausente/ilegível ou descrição totalmente vazia constam como conflito; zero prazo inventado; zero PDI arquivado criado por esta fatia.

## Assumptions

- Specs **003** (chave canônica / nome de exibição) e **010** (colaboradores, inclusive inativos; identificador Sólides do PDI já no schema da 6.5.1) estão aplicadas no ambiente alvo **antes** desta fatia.
- Specs **011** e **013** **não** são pré-requisito de vínculo: a carga de PDI não depende de ciclo, avaliação, nota ou comentário já importados.
- Inventário e mapeamento coluna→domínio em `data/legado-solides/README.md` (Decisão #22) são a fonte de volumes/colunas; esta spec não duplica o inventário inteiro.
- Dump de referência: 2026-06-24. PDI: ~86 registros (67 `finalizado`, 19 `em_andamento`). Colunas esperadas conforme README: `Nome`, `Título do PDI`, `Status`, `Objetivo`, `Situação Atual`, `Situação Desejada`, `Data de Entrega`; `Criado em` entra no digest quando existir.
- Chave canônica de nomes = a mesma das specs 003/010.
- Separador da descrição da ação = duas quebras de linha entre trechos não vazios, na ordem Objetivo → Situação Atual → Situação Desejada. Trechos não recebem rótulo extra (o conteúdo legado já identifica o sentido).
- Data da carga para atraso = data local do ambiente no início da execução (não a data “Criado em” do legado).
- Digest curto: função determinística estável entre execuções; comprimento final ≤ 50; não reversível para o nome em claro a partir do relatório mascarado.
- Recálculo de atraso vigente do domínio PDI é aplicado **depois** de definir o status desta fatia, na mesma gravação da linha — não substitui as regras FR-011; não autoriza job em massa.
- Comando é operacional (administrador técnico com acesso ao ambiente), não exposto via UI. Simulação obrigatória no guia rápido; staging/banco descartável antes de produção.
- Padrões operacionais (simulação, atomicidade, relatório, idempotência, exit codes, parser isolado, mascaramento) seguem 010/011/013 salvo adaptações no plano/contrato desta feature (`import-command`, `column-mapping`, `model-allowlist`, `non-goals-denylist`, `migration-safety`).
- Constituição (gate — violação não justificada **bloqueia**): I comando + persistência nativa; biblioteca de planilha só no parser já justificada na 010; II segurança/escopo só no backend vigente — import **não** é autorização; III histórico sem cascata, sem apagar para refazer; IV domínio PDI + parser isolado; V sem reinventar regra de atraso em paralelo se o serviço existir; VI sem aderência/9-box/e-mail (volume ~86, one-shot síncrono — sem fila nesta fatia).
- Homologação operacional completa (contagens em staging com `raw/`, 6.5.7) ocorre **depois** desta fatia; aqui só o contrato de que essa homologação é manual e fora do CI.

## Out of Scope

- `backup_treinamentos`.
- Catálogo extra 57 competências + matriz ~2.720 vínculos cargo↔competência.
- Reabrir specs 010, 011 ou 013.
- 9-box, metas, aderência, e-mail, Beat, marcação de atraso em massa.
- Sprint 6.5.7 (homologação operacional depois).
- UI, upload, API remota, SPA, fila, biblioteca nova, rota nova, papel de produto novo.
- Campo de PII novo; migration; tabela de mapa; identificador Sólides na ação.
- Alterar telas, endereços ou copy da spec 012; criar rota `/historico/`.
- Nova regra de quem pode ver PDI (o escopo hierárquico vigente permanece).
- Status arquivado de PDI.
- Três ações por linha; PDI persistido sem ação; vínculo a ciclo/avaliação.

## Dependencies

- **Spec 003** (`import-catalogo-legado`): chave canônica / nome de exibição.
- **Spec 010** (`import-colaboradores-legado`): pessoas (ativas e inativas); identificador Sólides do PDI já no schema; parser/relatório/mascaramento one-shot.
- **Inventário legado** (`data/legado-solides/README.md`): colunas, volumes (~86), ordem segura (passo 7 / 6.5.6), denylist e política de PII.
- **PRD** §6.5.6; **SOLIDES.md** 6.5.6.
- **Padrão de contratos** 010/011/013: `import-command`, `column-mapping`, `model-allowlist`, `non-goals-denylist`, `migration-safety` (artefatos desta fatia no planejamento).
- **Não dependem desta fatia**: spec 011 (ciclos/cabeçalhos) e spec 013 (notas/comentários) — não são pré-requisito de vínculo.
- **Spec 012** (`gerencial-historico-legado`): não é alterada aqui.
