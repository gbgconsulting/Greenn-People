# Fixtures anonimizadas — legado Sólides (CI / pytest)

Subset mínimo OOXML para CI e pytest. **Sem PII real.** Nenhum teste deve
ler `data/legado-solides/raw/`.

| Arquivo | Feature | Papel |
|---|---|---|
| `colaboradores_min.xlsx` | 010 | Layout de colaboradores |
| `avaliacoes_crosswalk_min.xlsx` | 010 | Crosswalk `Nome Avaliado` → `Identificador Avaliado` |
| `solicitacoes_min.xlsx` | 011 | Solicitações → ciclos históricos |
| `avaliacoes_headers_min.xlsx` | 011 | Cabeçalhos de avaliação (agregação 1:1) — **reusado** como mapa 013 |
| `notas_min.xlsx` | 013 | Notas por competência (auto/líder, IDs colapsados, conflitos) |
| `comentarios_min.xlsx` | 013 | Comentários qualitativos (líder/auto, autor órfão, serial Excel) |

E-mails: `@example.com` (RFC 2606). CPF sentinela `000.000.000-00` (coluna
presente só para provar que PII é ignorada — **não** persistida). Nomes de
fixture alinhados ao crosswalk 010 (`Gestor Alpha`/`100`, `Ana Silva`/`101`,
`Bruno Costa`/`102`, `Carla Dias`/`103`).

## `colaboradores_min.xlsx`

Planilha ativa `sheet1`. Colunas de domínio + `CPF` / `Unidade` (ignoradas).

| Nome | Subset |
|---|---|
| Gestor Alpha | Ativo; e-mail empresarial; **sem superior** (topo); crosswalk `100` |
| Ana Silva | Ativo; e-mail empresarial; superior `100`; crosswalk `101` |
| Bruno Costa | Ativo; só `E-mail` (2ª preferência); superior `100`; crosswalk `102` |
| Carla Dias | Demitida **serial Excel** `45446.0`; **sem superior**; crosswalk `103` |
| Diego Alves | Demitido **ISO** `2024-06-01`; só e-mail pessoal (3ª); superior `100` |
| Fernanda Lima | Ativa; **sem superior**; **sem** linha no crosswalk (parcial) |
| Nome Ambiguo | Ativo; mesmo nome com dois IDs no crosswalk (não recebe `solides_id`) |
| Elena Sem Email | Sem e-mail nas três colunas → `nao_importavel` |

## `avaliacoes_crosswalk_min.xlsx`

| Nome Avaliado | Identificador Avaliado | Nota |
|---|---|---|
| Gestor Alpha | 100 | match único (gestor resolvível) |
| Ana Silva | 101 | match único |
| Bruno Costa | 102 | match único |
| Carla Dias | 103 | match único |
| Diego Alves | 104 | match único |
| Nome Ambiguo | 900 | conflito com a linha seguinte |
| Nome Ambiguo | 901 | `crosswalk_ambiguo` |

Fernanda Lima e Elena Sem Email **não** aparecem aqui (crosswalk parcial).

## `solicitacoes_min.xlsx` (011 / T020)

Planilha `sheet1`. Colunas: `Identificador`, `Nome`, `Iniciada em`,
`Terminada em`, `Status` (+ `Criada em` ignorada).

| ID | Nome | Datas | Status | Nota |
|---|---|---|---|---|
| 10 | Ciclo Finished Alpha | ISO | finished | Base multi-avaliador |
| 20 | Ciclo Draft Beta | serial Excel | draft | Cabeçalho simples |
| 30 | Ciclo Active Gamma | ISO + serial | active | → sempre `encerrado` |
| 40 | Ciclo Canceled Delta | serial + ISO | canceled | → sempre `encerrado` |
| 50 | `46113.0` (serial) | serial | finished | Nome → rótulo ISO `2026-04-01` |
| 60 | Ciclo Sem Datas | ausentes | finished | Conflito `datas_ausentes_ou_invalidas` |

## `avaliacoes_headers_min.xlsx` (011 / T020)

Planilha `sheet1`. Colunas obrigatórias + `Avaiação criada em` (typo legado,
ignorada).

| Grupo | Solicitação | Avaliado | Linhas | Canônico / órfão |
|---|---|---|---|---|
| Multi **com** auto | 10 | Ana Silva `101` | 1001 (auto), 1002, 1003 | canônico `1001`; colapsados `1002`,`1003` |
| Multi **sem** auto | 10 | Bruno Costa `102` | 2001, 2003, 2005 | canônico `min_id`=`2001` |
| Simples | 20 | Gestor Alpha `100` | 3001 | 1:1 |
| Órfão usuário | 10 | `99999` / Usuario Orfao Fixture | 4001 | `orfaos_usuario` |
| Solicitação órfã | `999` (ausente) | Ana Silva `101` | 5001 | `orfaos_ciclo` |
| 1:1 canceled | 40 | Carla Dias `103` | 6001 | ciclo canceled no sample |

## `notas_min.xlsx` (013 / T017)

Planilha `sheet1`. Colunas obrigatórias do dump de notas (**sem** coluna de
nível) + `CPF` / `E-mail` sentinela (ignorados — **não** persistidos). Mapa
de IDs = `avaliacoes_headers_min.xlsx` (011). **Proibido** `raw/`.

| ID linha | Avaliação | Avaliador → avaliado | Habilidade | Subset |
|---|---|---|---|---|
| 8001 | `1001` canônico | Ana Silva → Ana Silva (auto) | `HAB10` Comunicacao Fixture | auto + canônico; Fator `1`; Nota `3` |
| 8002 | `1003` colapsado | Gestor Alpha → Ana Silva | `HAB10` | líder unívoco do mesmo par |
| 8003 | `1002` colapsado | Bruno Costa → Ana Silva | `HAB11` Colaboracao Fixture | ID colapsado sem conflito de líder |
| 8004 | `88888` | Gestor Alpha → Ana Silva | `HAB10` | órfão (sem canônico nem mapa) |
| 8005 | `1002` colapsado | Bruno Costa → Ana Silva | `HAB12` Lideranca Fixture | dois líderes divergentes (nota `4`) |
| 8006 | `1003` colapsado | Gestor Alpha → Ana Silva | `HAB12` | dois líderes divergentes (nota `5`) |
| 8007 | `3001` | Ana Silva → Gestor Alpha | `HAB10` | Fator válido `1.5` |
| 8008 | `3001` | Ana Silva → Gestor Alpha | `HAB11` | Fator inválido `0` |
| 8009 | `6001` | Gestor Alpha → Carla Dias | `HAB10` | Nota `9` fora da escala 1–5 |
| 8010 | `1001` | Ana Silva → Ana Silva (auto) | `99001` Habilidade Extra Fixture | extra não-KPI |
| 8011 | `1001` | Ana Silva → Ana Silva (auto) | `99002` `SLA` | nome KPI 003 → `orfaos_competencia` |
| 8012 | `1001` | Ana Silva → Ana Silva (auto) | `99003` Erros de usabilidade | nome ambíguo 003 → `orfaos_competencia` |

## `comentarios_min.xlsx` (013 / T017)

Planilha `sheet1`. Colunas obrigatórias + `Identificador Solicitação` /
`Identificador Avaliado` / `CPF` / `E-mail` (ignorados). Textos são fixture
— persistidos em `Feedback.conteudo`, **nunca** no relatório mascarado.

| Avaliação | Avaliador | Tipo | `Criado em` | Subset |
|---|---|---|---|---|
| `1001` | Gestor Alpha `100` | líder | serial `45446.5` (fração de dia) | ciência preenchida |
| `1001` | Gestor Alpha `100` | líder | serial `45447` | 2º texto (N por avaliação) |
| `1001` | Ana Silva `101` | auto | ISO `2024-06-03T09:15:00` | `ciente_em` null |
| `1001` | `88888` / Ninguem Desconhecido Fixture | — | serial `45446.5` | `orfaos_autor` (não inventa User) |
| `1002` colapsado | Bruno Costa `102` | líder | serial `45323.25` | mesma canônica `1001` |
