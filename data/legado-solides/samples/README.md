# Fixtures anonimizadas — import de colaboradores (US5 / T029)

Subset mínimo OOXML de `backup_colaboradores` / `backup_avaliacoes` para CI e
pytest. **Sem PII real.** Nenhum teste deve ler `data/legado-solides/raw/`.

| Arquivo | Papel |
|---|---|
| `colaboradores_min.xlsx` | Layout de colaboradores |
| `avaliacoes_crosswalk_min.xlsx` | Crosswalk `Nome Avaliado` → `Identificador Avaliado` |

E-mails: `@example.com` (RFC 2606). CPF sentinela `000.000.000-00` (coluna
presente só para provar que PII é ignorada — **não** persistida).

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
