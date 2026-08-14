# Fixtures anonimizadas — legado Sólides (CI / pytest)

Subset mínimo OOXML para CI e pytest. **Sem PII real.** Nenhum teste deve
ler `data/legado-solides/raw/`.

| Arquivo | Feature | Papel |
|---|---|---|
| `colaboradores_min.xlsx` | 010 | Layout de colaboradores |
| `avaliacoes_crosswalk_min.xlsx` | 010 | Crosswalk `Nome Avaliado` → `Identificador Avaliado` |
| `solicitacoes_min.xlsx` | 011 | Solicitações → ciclos históricos |
| `avaliacoes_headers_min.xlsx` | 011 | Cabeçalhos de avaliação (agregação 1:1) |

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
