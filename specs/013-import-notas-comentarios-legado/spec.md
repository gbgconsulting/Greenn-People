# Feature Specification: Importação One-Shot do Legado Sólides — Notas por Competência e Comentários Qualitativos

**Feature Branch**: `013-import-notas-comentarios-legado`

**Created**: 2026-08-18

**Status**: Draft

**Input**: User description: "Importação one-shot do legado Sólides — notas por competência e comentários/feedback qualitativo (Sprint PRD 6.5.5). Specs 003, 010 e 011 já aplicadas. Fontes: backup_notas_avaliacoes_* (~7.360; escala 1–5; ~2.213 auto / ~5.147 líder) e backup_comentarios_avaliacoes_* (~1.494). Dump 2026-06-24. Handoff obrigatório da 011: ids_colapsados. Sem esta fatia o histórico da 012 permanece empty sem_nota."

## Clarifications

### Session 2026-08-18 (defaults explícitos na especificação)

- Q: As 57 habilidades extras do backup de habilidades entram nesta fatia? → A: Somente competência **estritamente necessária como vínculo de uma nota** e que passe o filtro de KPI/ambíguos da spec 003. Não é sprint de catálogo completo; a matriz de ~2.720 vínculos cargo↔competência **não** entra. Habilidade sem evidência de nota → órfão no relatório, sem inventar competência.
- Q: De onde vem o nível esperado histórico se o dump de notas **não traz coluna** de nível? → A: Derivar da tabela documentada do catálogo 003 (senioridade do cargo do avaliado → nível esperado). **Nunca** ler o perfil cargo↔competência vigente (mutável) como se fosse o passado. Se cargo/senioridade não resolvem → conflito/skip da linha.
- Q: Comentários históricos do líder devem ficar pendentes de ciência? → A: Não. Preencher ciência com o instante legado do comentário (ou equivalente de criação) para não reabrir pendência em ciclo já encerrado. A etapa/conclusão da 011 **não** são alteradas.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Persistir notas históricas, snapshots e nota final (Priority: P1)

O operador técnico executa a importação one-shot das notas do legado, em ambiente de homologação/banco descartável, após simulação. Cada linha de nota resolve a avaliação já importada na spec 011 (incluindo identificadores que foram colapsados na agregação 1:1) e a competência correspondente. Autoavaliação e nota de líder ocupam campos distintos, sem inversão. Peso e nível esperado ficam congelados como retrato do passado. Quando há notas de líder suficientes, a nota final da avaliação é preenchida **pela mesma fórmula já usada no produto** — sem reinventar média e sem copiar o perfil de cargo atual.

**Why this priority**: É o miolo da Sprint 6.5.5. Sem notas, o histórico gerencial da spec 012 permanece “sem nota” (pipeline/conclusão sem desempenho). É o que permite desligar a Sólides como arquivo de nota.

**Independent Test**: Com catálogo (003), colaboradores (010) e ciclos/cabeçalhos (011) já carregados, importar o backup de notas e verificar: linhas de competência ligadas às avaliações canônicas; auto vs líder corretos; snapshots estáveis na reexecução; notas finais preenchidas só via fórmula vigente; identificadores colapsados da 011 resolvem para a mesma avaliação; zero segunda avaliação por pessoa/ciclo.

**Acceptance Scenarios**:

1. **Given** backups de notas e cabeçalhos da 011 disponíveis e avaliações históricas já persistidas, **When** o operador executa a fase de notas, **Then** cada linha com avaliação e competência resolvíveis gera ou atualiza uma linha de nota por competência ligada à **avaliação canônica** do grupo — nunca uma segunda avaliação para o mesmo (ciclo, pessoa).
2. **Given** `Nome Avaliador` e `Nome Avaliado` com a mesma chave canônica (ambos não-vazios), **When** a nota é persistida, **Then** o valor vai **somente** para autoavaliação; **Given** nomes distintos (ou um vazio), **Then** vai **somente** para nota de líder. Nunca inverter; nunca copiar líder na auto ou vice-versa.
3. **Given** N avaliadores Sólides na mesma competência da mesma pessoa/ciclo, **When** a importação colapsa, **Then** existe uma única linha de competência na avaliação canônica: auto preenche autoavaliação; demais líderes preenchem nota de líder.
4. **Given** dois “líderes” com notas **divergentes** na mesma competência da mesma avaliação, **When** a carga detecta a divergência, **Then** registra **conflito** — não inventa média e não cria segunda avaliação.
5. **Given** primeira gravação de uma linha, **When** o snapshot é preenchido, **Then** o peso utilizado vem do **Fator no Momento** legado e o nível esperado utilizado vem da política histórica desta spec (coluna legado se existir; senão tabela 003 de senioridade do cargo do avaliado). **Nunca** usa o perfil cargo↔competência **atual** como se fosse o passado.
6. **Given** uma linha já persistida, **When** o operador reexecuta a importação, **Then** peso e nível esperado **já gravados não mudam** (write-once); a reexecução reporta inalterado ou conflito se a fonte divergir, sem reescrever o retrato.
7. **Given** uma avaliação histórica com linhas suficientes de nota de líder, **When** a fase de notas conclui o grupo, **Then** a nota final de líder é preenchida **reusando a fórmula vigente** (normalização pela escala da competência, ponderação pelos pesos congelados da linha histórica). Falha de cálculo (peso total zero, linha sem nota de líder, competência sem escala) → conflito no relatório, **sem** média inventada.
8. **Given** linhas com autoavaliação preenchida quando couber o cálculo, **When** a fórmula vigente de autoavaliação se aplica, **Then** a nota final de autoavaliação é preenchida pelo mesmo contrato; ausência de auto em todas as linhas **não** inventa valor.
9. **Given** um `Identificador Avaliação` que **não** é o identificador canônico gravado na 011, **When** esse ID consta como colapsado do mesmo grupo, **Then** a nota é gravada na avaliação canônica do grupo; **Given** ID sem canônico nem mapa, **Then** a linha é órfã — não inventa avaliação, ciclo ou pessoa.
10. **Given** um ciclo **aberto operacional** no ambiente (fluxo normal), **When** uma nota apontaria para avaliação desse ciclo, **Then** a linha é conflito/skip. Histórico legado ≠ operação vigente.

---

### User Story 2 - Persistir comentários / feedback qualitativo (Priority: P1)

Na mesma execução (fase seguinte às notas, mesma unidade de persistência), o operador importa o backup de comentários. Cada comentário liga-se à **mesma avaliação canônica** da US1 (incluindo IDs colapsados). O autor é pessoa já importada; o tipo (colaborador vs líder) segue auto vs não-auto. Vários comentários por avaliação são válidos. Comentários de líder em ciclo encerrado não reabrem “pendência de ciência”.

**Why this priority**: Completa o desligamento da Sólides como arquivo de feedback qualitativo. Sem isto, RH/líder/colaborador veem nota sem o texto da conversa histórica.

**Independent Test**: Após (ou juntamente com) notas, importar comentários e verificar: vínculo à avaliação canônica; autor resolvido sem inventar pessoa; tipo coerente; reexecução sem duplicar pela chave natural; ciência preenchida em comentário de líder; conteúdo persistido no produto, sem vazar texto completo no relatório.

**Acceptance Scenarios**:

1. **Given** backup de comentários e avaliações canônicas da 011, **When** a fase de comentários processa as linhas, **Then** cada comentário com avaliação e autor resolvíveis é persistido como feedback qualitativo na avaliação canônica (mesmo mapa de IDs colapsados da US1).
2. **Given** `Identificador Avaliador` correspondente a colaborador importado, **When** o autor é resolvido, **Then** o feedback aponta para essa pessoa; fallback: nome único pela mesma chave canônica das specs 003/010/011. Autor não resolvido → órfão; **nunca** inventa usuário.
3. **Given** avaliador e avaliado com a mesma chave canônica (ambos não-vazios), **When** o tipo é inferido, **Then** o feedback é de **colaborador**; caso contrário, de **líder**.
4. **Given** vários comentários para a mesma avaliação, **When** a carga conclui, **Then** todos os resolvíveis existem (N por avaliação é válido; sem unicidade que descarte o segundo texto distinto).
5. **Given** um comentário de **líder** histórico, **When** é persistido, **Then** a ciência (`ciente_em`) é preenchida com o instante legado (`Criado em` ou equivalente de criação) para não reabrir pendência em ciclo morto. Etapa e flag de concluída da 011 **permanecem intactas**.
6. **Given** reexecução com as mesmas fontes, **When** a chave natural estável coincide (avaliação canônica + autor + tipo + conteúdo normalizado + data se houver), **Then** não duplica; **não** reescreve em silêncio o conteúdo de feedback alheio.

---

### User Story 3 - Simular, reexecutar e validar com samples anonimizados (Priority: P2)

O operador valida com simulação (zero gravação), reexecuta de forma idempotente, e a CI cobre o comportamento só com fixtures anonimizadas — nunca os backups brutos com PII. O relatório traz totais completos e amostra mascarada. Executar a importação **não** mexe em regras de etapa, escopo, fórmula, abertura/fechamento de ciclo, PDI, 9-box nem telas/rotas da visão histórica (spec 012).

**Why this priority**: Backups contêm CPF, comentários nominais e outros dados pessoais. Staging exige simulação obrigatória. A fatia é persistência histórica, não um produto novo de autorização nem um ciclo operacional.

**Independent Test**: Simulação sem writes; duas execuções reais consecutivas sem duplicar linhas de competência nem feedbacks pela chave natural; snapshots 100% estáveis na segunda run; suite automatizada verde só com samples; teste de ouro da denylist de domínio.

**Acceptance Scenarios**:

1. **Given** arquivos válidos, **When** o operador executa com simulação (`--dry-run`), **Then** o sistema parseia, emite relatório com totais projetados e **não persiste** alterações.
2. **Given** uma importação bem-sucedida, **When** o operador reexecuta com as mesmas fontes, **Then** delta de duplicatas nas chaves naturais = 0; snapshots já persistidos inalterados; feedbacks não duplicados.
3. **Given** erro fatal pré-persistência ou falha na unidade de persistência, **When** a importação aborta, **Then** exit indica falha e nenhum estado parcial inconsistente permanece (rollback atômico das duas fases).
4. **Given** fixtures anonimizadas representativas (ID colapsado, órfão de avaliação/competência/autor, conflito de duas notas de líder, snapshot write-once, habilidade extra vs órfão, ciclo aberto, PII presente na fonte), **When** a suite roda no CI, **Then** cobre simulação, idempotência, denylist e mascaramento; **nenhum** teste lê backups brutos (`raw/`).
5. **Given** a suite de regressão de domínio, **When** a feature é integrada, **Then** testes de etapa/escopo/invariante de rejeição permanecem verdes e o teste de ouro da denylist permanece vazio (nenhuma alteração das regras preservadas).

---

### Edge Cases

- Arquivo de notas ou comentários ausente, corrompido ou sem planilha esperada: falha clara antes da persistência; exit de erro.
- `Identificador Avaliação` igual ao canônico da 011: match direto.
- `Identificador Avaliação` colapsado na 011: resolve para a avaliação canônica do grupo via mapa reconstruído em memória pelo **mesmo algoritmo determinístico** da 011; **não** reabre agregação nem cria segunda avaliação.
- ID de avaliação sem canônico e sem entrada no mapa: órfão; não inventa avaliação/ciclo/pessoa.
- `Identificador Habilidade` presente no catálogo 003 (43 competências): resolve por identificador Sólides da competência.
- Habilidade extra (fora das 43) referenciada por nota e aprovada no filtro KPI da 003: cria/resolve competência **somente** como vínculo necessário daquela nota; não importa a matriz cargo↔competência.
- Habilidade extra filtrada como KPI/ambíguo, ou sem evidência de nota: órfão no relatório; não inventa competência.
- Nota fora da escala da competência: conflito; **não** recorta (clip) em silêncio.
- Fator no Momento ausente ou inválido: conflito da linha; não inventa peso.
- Nível esperado: dump 2026-06-24 de notas **não possui coluna** de nível; derivar da tabela 003 (senioridade do cargo do avaliado). Cargo/senioridade irresolvíveis → conflito/skip.
- Duas notas de líder divergentes na mesma (avaliação, competência): conflito; sem média; sem segunda avaliação.
- Reexecução tentando mudar peso/nível já persistidos: write-once prevalece; reportar; não apagar avaliação da 011 para “refazer”.
- Ciclo alvo aberto (operação vigente): conflito/skip; não misturar histórico com operação.
- Avaliado/autor inativo (demitido na 010): permitido se a pessoa existir; inatividade não bloqueia histórico.
- Comentário cujo identificador de avaliação é colapsado: mesma resolução da US1.
- Autor de comentário não resolvido: órfão; não inventa usuário.
- Comentário de colaborador (auto): tipo colaborador; ciência do líder não se aplica da mesma forma — não preencher ciência de líder em feedback de colaborador.
- Relatório: totais completos; amostra mascarada (máx. 5 por seção); **sem** dump de comentário completo, nome ou e-mail; logs **não** imprimem linha bruta da planilha.
- PII cadastral (CPF, RG, banco, endereço): não importar (já fora na 010); presença na fonte não vaza para relatório/CI.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O sistema MUST oferecer comando operacional one-shot, reproduzível, com **duas fases na mesma unidade de persistência** (notas → comentários), no padrão das specs 003/010/011. Dois comandos separados só se o plano justificar; o default é um comando. Sem interface de upload, tela nova, API remota ou fila assíncrona nesta fatia.
- **FR-002**: O parse das planilhas MUST permanecer isolado da persistência de domínio (parser único já usado nas fatias 010/011); a persistência de nota/feedback MUST permanecer no domínio de avaliações.
- **FR-003**: O sistema MUST ler `backup_notas_avaliacoes_*` e `backup_comentarios_avaliacoes_*` (Excel real). MUST reconstruir em memória o mapa de identificadores colapsados da 011 a partir do **mesmo algoritmo** de agregação (reexecutável, determinístico) sobre o backup de cabeçalhos já usado na 011. MUST NOT persistir tabela extra de mapa nem PII adicional por omissão — default = memória; tabela só se o plano provar que arquivo/relatório da 011 é insuficiente.
- **FR-004**: O sistema MUST resolver `Identificador Avaliação` nesta ordem: (a) match com o identificador Sólides **canônico** da avaliação; (b) senão, mapa `ids_colapsados` → canônico; (c) senão, órfão. MUST NOT inventar avaliação, ciclo ou pessoa. MUST NOT reabrir a agregação 1:1 da 011 nem criar segunda avaliação por (ciclo, usuário).
- **FR-005**: O sistema MUST resolver `Identificador Habilidade` para competência via identificador Sólides (spec 010). O catálogo das 43 competências da spec 003 é pré-condição. As 57 habilidades extras MUST entrar **somente** se forem vínculo estritamente necessário de uma nota **e** passarem o filtro KPI/ambíguos da 003 (reutilizar mapeamento e chave canônica). MUST NOT importar a matriz de ~2.720 vínculos cargo↔competência como produto desta fatia. Órfãos de habilidade MUST ir ao relatório.
- **FR-006**: O sistema MUST persistir linhas históricas de nota por competência ligadas à avaliação já importada (011) e à competência resolvível. A unicidade (avaliação, competência) MUST permanecer intacta; idempotência = upsert dessa chave.
- **FR-007**: O sistema MUST separar a nota: se `Nome Avaliador` ≈ `Nome Avaliado` (mesma chave canônica das specs 003/010/011, ambos não-vazios) → autoavaliação; senão → nota de líder. MUST NOT inverter nem copiar um campo no outro.
- **FR-008**: Notas de N avaliadores Sólides no mesmo (ciclo, pessoa, competência) MUST colapsar na **mesma** linha. Dois líderes com valores divergentes MUST gerar conflito — MUST NOT inventar média e MUST NOT criar segunda avaliação.
- **FR-009**: Snapshots de peso e nível esperado MUST ser write-once (constituição III / RF-19.2). Peso utilizado ← `Fator no Momento` (ausente/inválido → conflito da linha, sem inventar). Nível esperado utilizado ← valor legado se a coluna existir; no dump 2026-06-24 **não existe coluna** → derivar da tabela 003 (senioridade do cargo do avaliado → nível esperado). MUST NOT ler o perfil cargo↔competência **atual** como passado. Primeira gravação permitida; reexecução MUST NOT alterar snapshots já persistidos.
- **FR-010**: O sistema MUST NOT criar linhas de competência a partir do perfil de cargo **vigente** (isso retrataria o presente e mentiria o passado). Linhas existem porque o legado trouxe a nota, não porque o cargo atual lista a competência.
- **FR-011**: Após linhas com nota de líder suficientes, o sistema MUST preencher a nota final de líder (e a de autoavaliação quando couber) **reusando a fórmula já existente** — normalização `(nota − mínimo) / (máximo − mínimo)` ponderada pelo peso utilizado da linha histórica (RF-15.1). MUST NOT reimplementar a fórmula nem alterar o módulo de cálculo. Falha de cálculo MUST ir ao relatório como conflito, sem média inventada.
- **FR-012**: O sistema MUST persistir feedback qualitativo na mesma avaliação canônica. Autor MUST resolver por `Identificador Avaliador` → identificador Sólides da pessoa (fallback: nome único via chave canônica). Tipo colaborador vs líder MUST ser inferido por auto vs não-auto / papel do autor. MUST NOT inventar usuário.
- **FR-013**: N comentários por avaliação são válidos. Idempotência MUST usar chave natural estável: avaliação canônica + autor + tipo + normalização/hash do conteúdo + data se houver. Reexecução MUST NOT duplicar nem reescrever em silêncio feedback alheio (append-only de conteúdo).
- **FR-014**: Comentário de líder histórico MUST ter ciência preenchida com o instante legado (`Criado em` ou equivalente de criação). MUST NOT deixar ciência nula em massa nesse recorte sem avaliar o indicador de conclusão. MUST NOT alterar etapa nem o flag de concluída gravados na 011. MUST NOT avançar etapa, abrir/fechar ciclo nem aprovar/reprovar meta.
- **FR-015**: Nota fora da escala da competência MUST ser conflito (sem recorte silencioso). Vínculos protegidos contra exclusão em cascata MUST permanecer intactos; órfão de avaliação/competência/pessoa → skip + relatório, nunca inventar.
- **FR-016**: Ciclos alvo são os **encerrados** da 011. MUST NOT persistir nota em ciclo aberto operacional: conflito/skip. Histórico ≠ operação.
- **FR-017**: O comando MUST aceitar simulação (`--dry-run`: zero gravação), persistir em transação atômica, ser idempotente, emitir relatório (criados / atualizados / inalterados / conflitos / órfãos) com amostra mascarada (máx. 5 por seção) e usar exit 0 sucesso / 1 erro fatal — alinhado a 003/010/011. Totais MUST ser sempre completos.
- **FR-018**: Relatório e logs MUST NOT despejar comentário completo, nome, e-mail nem linha bruta da planilha. O conteúdo do comentário **no registro de negócio** é dado da avaliação; o risco a controlar é relatório/CI, não omitir o campo de conteúdo na persistência.
- **FR-019**: Preferir **zero** evolução de schema. MUST NOT alterar tipo, opcionalidade, unicidade ou política de exclusão de campos existentes. MUST NOT criar campo de PII novo. MUST NOT importar CPF, RG, dados bancários ou endereço.
- **FR-020**: A importação MUST NOT chamar nem alterar regras de visibilidade/escopo hierárquico. Nenhuma regra de autorização nova. Após persistir, a leitura continua pelas telas e escopo já existentes. O operador é de plataforma, não um papel de produto novo.
- **FR-021**: **Teste de ouro (denylist de domínio)**: executar a importação MUST NOT avançar etapa, abrir/fechar ciclo, aprovar/reprovar itens, alterar quem vê quem, alterar a fórmula de nota, criar PDI, classificar 9-box, disparar recálculo de aderência, nem alterar telas/rotas da visão histórica (spec 012) / criar rota dedicada de histórico. Diff dessas regras = vazio no merge. Permitido: persistir notas/feedback históricos, preencher notas finais **chamando** a fórmula vigente sem editá-la, estender parser/relatório, samples e testes desta fatia.
- **FR-022**: Testes automatizados MUST usar fixtures anonimizadas em `data/legado-solides/samples/`; MUST NOT depender de `data/legado-solides/raw/` no CI. Homologação com backups brutos é manual, em staging/banco descartável, com simulação primeiro.
- **FR-023**: Esta fatia MUST NOT importar PDI nem treinamentos (6.5.6), MUST NOT inventar classificação de talento a partir da nota importada, e MUST deixar aderência/9-box ausentes até processo operacional próprio.

### Key Entities

- **Avaliação (cabeçalho, 011)**: Uma por (ciclo, pessoa); identificador Sólides canônico; IDs colapsados só no mapa em memória. Esta fatia **não** cria nem duplica avaliação.
- **Linha de nota por competência**: Autoavaliação e/ou nota de líder na mesma linha; peso e nível esperado são retrato write-once; unicidade (avaliação, competência).
- **Competência**: Catálogo 003 (43) como base; extras só sob demanda de FK de nota + filtro KPI.
- **Feedback qualitativo**: Comentário ligado à avaliação canônica; autor resolvido; tipo colaborador/líder; N por avaliação; ciência preenchida em líder histórico.
- **Mapa de IDs colapsados**: Derivado do algoritmo da 011; traduz identificador não canônico → avaliação canônica; não é tabela de PII persistida por default.
- **Nota final**: Resultado da fórmula vigente sobre as linhas históricas; não é média inventada pelo importador.
- **Relatório de carga**: Totais + amostra mascarada; seções de criados/atualizados/inalterados/conflitos/órfãos (incl. ID colapsado, habilidade extra, ciclo aberto).
- **Fontes**: Backup de notas (~7.360 linhas; escala 1–5; ~2.213 auto / ~5.147 líder) e backup de comentários (~1.494); dump 2026-06-24. Backup de cabeçalhos da 011 como insumo do mapa. Backup de habilidades apenas se necessário para FK de nota.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Após importação bem-sucedida do dump 2026-06-24, as ~7.360 linhas de nota elegíveis são processadas (persistidas, atualizadas, inalteradas, conflito ou órfão); 100% das não resolvidas aparecem no relatório; zero avaliação/ciclo/pessoa inventados.
- **SC-002**: Entre as notas cujo par avaliador/avaliado resolve, a separação auto vs líder respeita a regra de nomes: o recorte conhecido do dump (~2.213 auto / ~5.147 líder) **não é invertido**; auditoria amostral não encontra auto copiada no campo de líder nem o inverso.
- **SC-003**: Zero duplicata da chave (avaliação, competência) após a carga; N avaliadores Sólides no mesmo par colapsam em uma linha.
- **SC-004**: 100% das avaliações com linhas suficientes de nota de líder recebem nota final pela fórmula vigente **ou** constam como conflito de cálculo (peso zero / linha sem líder / sem escala) — zero média inventada. Autoavaliação final só quando o contrato vigente se aplica.
- **SC-005**: Segunda execução consecutiva com as mesmas fontes: delta de duplicatas = 0; **100%** dos snapshots já persistidos permanecem bit-a-bit estáveis (peso e nível esperado).
- **SC-006**: 100% dos `Identificador Avaliação` que existem no mapa de colapsados da 011 resolvem para a avaliação canônica; 100% dos demais irresolvíveis são órfãos; zero segunda avaliação por (ciclo, pessoa) criada por esta fatia.
- **SC-007**: Comentários do dump (~1.494) são processados; reexecução não duplica pela chave natural; 100% dos feedbacks de líder históricos persistidos têm ciência preenchida quando a data legado é interpretável (senão conflito explícito, não nulo em massa).
- **SC-008**: Modo simulação produz relatório completo com zero registros persistidos (contagem antes/depois inalterada para linhas de competência, feedbacks e notas finais).
- **SC-009**: Suite automatizada passa no CI **sem** qualquer referência a backups brutos (`raw/`); cobre ID colapsado, órfão, conflito de dois líderes, write-once na 2ª run, habilidade extra vs órfão, ciclo aberto e mascaramento de PII no relatório.
- **SC-010**: Relatório de produção: totais completos; amostra mascarada ≤ 5 itens por seção; zero dump de comentário completo, nome ou e-mail; operador revisa totais em < 3 minutos.
- **SC-011**: Operador popula staging (após simulação obrigatória) em uma execução operacional (< 10 minutos de tempo humano, excluindo parse em hardware de referência).
- **SC-012**: Zero nota persistida em ciclo aberto operacional; 100% desses casos no relatório como conflito/skip.
- **SC-013**: Teste de ouro: executar a importação não altera etapa, escopo, fórmula, abertura/fechamento de ciclo, PDI, 9-box nem telas/rotas da spec 012; regressão de etapa/escopo/invariante permanece verde.
- **SC-014**: Habilidades extras: somente as exigidas como vínculo de nota e aprovadas no filtro 003 entram; a matriz ~2.720 **não** é carregada; órfãos de habilidade = 100% visíveis no relatório.

## Assumptions

- Specs **003** (catálogo 43 competências + filtro KPI + chave canônica + tabela senioridade→nível esperado), **010** (colaboradores + identificadores Sólides) e **011** (ciclos encerrados + cabeçalhos 1:1 + handoff `ids_colapsados`) estão aplicadas no ambiente alvo **antes** desta fatia.
- Inventário e mapeamento coluna→domínio em `data/legado-solides/README.md` (Decisão #22) são a fonte de volumes/colunas; esta spec não duplica o inventário inteiro.
- Dump de referência: 2026-06-24. Notas: ~7.360 linhas (escala 1–5; ~2.213 auto / ~5.147 líder). Comentários: ~1.494. Colunas de notas confirmadas na inspeção de cabeçalho: Identificador, Identificador Avaliação, Nome Avaliador, Nome Avaliado, Identificador Habilidade, habilidade, Fator no Momento, Nota — **sem** coluna de nível esperado. Colunas de comentários: Identificador Solicitação, Nome Solicitação, Identificador (avaliação), Identificador Avaliador, Nome Avaliador, Identificador Avaliado, Nome Avaliado, Comentário, Criado em.
- **Handoff 011**: o mapa de IDs colapsados é reconstruído em memória pelo algoritmo canônico da 011 (autoavaliação se existir no grupo; senão menor identificador estável; colapsados = demais). Arquivo/relatório da 011 não precisa ser persistido como tabela; o backup de cabeçalhos é insumo de resolução, **não** de reimportação de cabeçalhos.
- Chave canônica de nomes = a mesma das specs 003/010/011 (normalização determinística). Igualdade de autoavaliação exige ambos os nomes não-vazios.
- Fator no Momento ausente/inválido: conflito (não assume peso 1 em silêncio). Peso 1 só existiria se o legado o trouxesse.
- Nível esperado histórico: tabela 003 (`Cargo.nivel` 1→2, 2→2, 3→3, 4→4, 5→4, 6→4) aplicada ao cargo do **avaliado** já importado — é o retrato do catálogo original, **não** o vínculo cargo↔competência que o RH possa ter editado depois.
- Fórmula de nota final = RF-15.1 já vigente (média ponderada de notas normalizadas pela escala, só com peso congelado). O importador **chama** esse contrato; não o reescreve.
- Avaliação da 011 permanece `etapa=feedback` e `concluida=True`; esta fatia não mexe em etapa, não chama avanço de etapa, não abre/fecha ciclo, não aprova/reprova meta.
- Ciência em feedback de líder histórico evita falso positivo de “pendência de ciência” em ciclo morto, coerente com `concluida=True` da 011 e com o indicador de conclusão.
- Comando(s) são operacionais (administrador técnico com acesso ao ambiente), não expostos via UI. Simulação obrigatória no guia rápido; staging/banco descartável antes de produção.
- Padrões operacionais (simulação, atomicidade, relatório, idempotência, exit codes, parser isolado) seguem 003/010/011 salvo adaptações no plano/contrato desta feature.
- Constituição (gate — violação não justificada **bloqueia**): I comando+persistência nativa, sem API/SPA/lib nova/UI de upload/fila desta fatia (biblioteca de planilha já justificada na 010, só no parser); II import não altera escopo/autorização; III histórico imutável, snapshots write-once, sem cascata, sem apagar avaliação 011 para refazer; IV persistência de nota/feedback no domínio de avaliações, parse no parser único; V nota final só via fórmula vigente e peso histórico — sem criar linhas a partir do perfil atual; VI sem disparar recálculo de aderência nem inventar 9-box.
- A spec 012 continua responsável pela leitura gerencial; esta fatia **alimenta** o desempenho que hoje aparece como empty/`sem_nota`, sem redesenhar painéis.

## Out of Scope

- Sprint 6.5.6 — PDI / `backup_pdi` / `backup_treinamentos`.
- Reabrir a spec 011 (agregação, identificador de ciclo, etapa/concluída).
- Extensão completa do catálogo 57 + 2.720 vínculos como feature própria.
- Interface, API remota, fila/tarefas novas, upload, dashboard novo, tendência pessoal nova.
- Recalcular aderência; classificar 9-box; mudar máquina de estados.
- Simular envios de ciclo; abrir ciclo ativo.
- Nova biblioteca de dependências do projeto.
- Alterar telas, endereços ou copy da spec 012; criar rota dedicada `/historico/`.
- Campo de PII novo; importar CPF/RG/banco/endereço.
- Nova regra de quem pode ver nota/feedback (o escopo hierárquico vigente permanece).

## Dependencies

- **Spec 003** (`import-catalogo-legado`): 43 competências, chave canônica, filtro KPI/ambíguos, tabela senioridade → nível esperado.
- **Spec 010** (`import-colaboradores-legado`): pessoas com identificador Sólides quando o crosswalk existiu; competências com identificador; parser/relatório one-shot.
- **Spec 011** (`import-ciclos-avaliacoes-legado`): ciclos encerrados; uma avaliação por (ciclo, pessoa); identificador canônico; contrato de agregação e lista de IDs colapsados para esta fatia.
- **Spec 012** (`gerencial-historico-legado`): consome notas/feedback **depois** desta carga; não é alterada aqui (empty honesto hoje; desempenho passa a existir quando a 013 persistir).
- **Inventário legado** (`data/legado-solides/README.md`): colunas, volumes, ordem segura (passos 6→7), denylist e política de PII.
- **PRD** §6.5.5, RF-15.1 (fórmula da nota final) e RF-19.2 (snapshots write-once).
