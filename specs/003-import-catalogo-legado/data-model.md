# Data Model: Importação One-Shot do Catálogo Legado

**Branch**: `003-import-catalogo-legado` | **Date**: 2026-07-28

**Nota**: Esta feature **não introduz models novos**. Reutiliza entidades já existentes (feature 001 + soft-delete/unicidade da 002). Este documento descreve campos tocados, regras de validação na carga e tabelas de de-para.

Modelo canônico de domínio: [apps/organization/models.py](../../apps/organization/models.py), [apps/competencies/models.py](../../apps/competencies/models.py). Contratos: [contracts/legado-domain-mapping-contract.md](./contracts/legado-domain-mapping-contract.md).

---

## Entidades persistidas (existentes)

### Cargo (`organization.Cargo`)

| Campo | Tipo | Origem na importação |
|---|---|---|
| `nome` | CharField(100) | Nome display (strip/colapso); matching por chave canônica |
| `nivel` | PositiveSmallInteger 1–6 | De-para por tokens no nome (FR-002) |
| `is_active` | bool | Sempre `True` em creates; inativos existentes **não** são reativados |

**Constraints**: `unique_cargo_nome_ativo` (nome único entre ativos).

**Estado**: create ativo | update ativo | skip+conflito se inativo com mesma chave.

### Competencia (`competencies.Competencia`)

| Campo | Tipo | Origem |
|---|---|---|
| `nome` | CharField(150) | Display da lista-competencias |
| `descricao` | TextField | Coluna `Descrição` (blank ok) |
| `tipo` | `tecnica` \| `comportamental` \| `lideranca` | Grupo legado (FR-003) |
| `escala` | FK → Escala (PROTECT) | Escala padrão 1–5 |
| `is_active` | bool | Creates `True`; inativos não reativados |

**Constraints**: `unique_competencia_nome_ativa`.

**Filtro**: só habilidades avaliáveis; KPI → exclusão; ambíguos → não mapeado (sem persistir).

### CargoCompetencia (`competencies.CargoCompetencia`)

| Campo | Tipo | Origem |
|---|---|---|
| `cargo` | FK Cargo (PROTECT) | Resolvido na carga |
| `competencia` | FK Competencia (PROTECT) | Resolvido na carga |
| `nivel_esperado` | Decimal | Tabela senioridade → esperado (FR-004) |
| `peso` | Decimal | Sempre `1` |

**Constraints**: `unique_cargo_competencia` (par único).

**Estado**: `update_or_create` por par; atualiza `nivel_esperado`/`peso` se divergirem da regra default (reporta `atualizados`).

### Escala (`competencies.Escala`)

| Campo | Valor padrão da importação |
|---|---|
| `nome` | `Escala padrão 1-5` |
| `valor_minimo` | `1` |
| `valor_maximo` | `5` |
| `rotulos_por_nivel` | `{}` ou rótulos opcionais 1..5 (não obrigatório) |
| `is_active` | `True` no create |

**Constraints**: `unique_escala_nome_ativa`. Reutilizar se ativa existir; conflito se apenas inativa (ver research R9).

---

## Entidades lógicas (não persistidas)

### Fonte Legada — lista-cargos

- Colunas: `Cargo`, `Competência` (pipe-separated).
- Produz: set de nomes de cargo + pares vista A.

### Fonte Legada — lista-competencias

- Colunas: `Competência`, `Grupo de competência`, `Descrição`, `Peso`, `Tipo de Avaliação`, `Cargo` (pipe-separated).
- Produz: metadados de competência + pares vista B.
- `Peso` / `Tipo de Avaliação` do legado: **ignorados** para persistência (peso fixo 1; tipo via grupo).

### Relatório de Carga

Artefato de saída (stdout / arquivo). Contadores e listas: `criados`, `atualizados`, `inalterados`, `excluidos_kpi`, `nao_mapeados`, `conflitos`, `divergencias`, `merged`. Schema em [import-command-contract.md](./contracts/import-command-contract.md).

---

## Tabelas de de-para

### Senioridade → `Cargo.nivel`

| Tokens no nome (após normalização) | nivel |
|---|---:|
| estagiario, estag, trainee | 1 |
| jr, junior | 2 |
| pl, pleno | 3 |
| sr, senior | 4 |
| tech lead, ux lead, qa lead, lead | 5 |
| gerente, diretor, coordenador(a), ceo, presidente, head | 6 |
| (sem sufixo) | 6 |

### `Cargo.nivel` → `nivel_esperado`

| nivel | nivel_esperado |
|------:|---------------:|
| 1 | 2 |
| 2 | 2 |
| 3 | 3 |
| 4 | 4 |
| 5 | 4 |
| 6 | 4 |

### Grupo → `Competencia.tipo`

| Grupo | tipo |
|---|---|
| Liderança | lideranca |
| Comportamento | comportamental |
| Desempenho | tecnica |

### KPI — exclusão (não persiste Competencia)

Chaves canônicas (e variantes de família por prefixo/igualdade):

- sla
- lead time discovery
- custo de nuvem por transacao
- throughput por colaborador*
- indice de incidentes*
- tempo medio de espera na esteira

### Ambíguos — `nao_mapeados` (não persiste nesta versão)

- erros de usabilidade
- oportunidade de usabilidades entregues e cm problemas resolvidos
- oportunidades entregues de modernizacao
- oportunidades tracionadas
- monitoramento continuo

---

## Relacionamentos

```text
Escala 1──* Competencia
Cargo  *──* Competencia  (via CargoCompetencia)
CargoCompetencia (cargo, competencia, nivel_esperado, peso)
```

Importação **não** cria/altera: `CustomUser`, `Avaliacao`, `AvaliacaoCompetencia`, `Meta`, `AcaoPDI`, snapshots históricos.

---

## Validação e invariantes

1. Arquivos inválidos/ausentes → nenhuma escrita.
2. Persistência em uma transação atômica.
3. Zero duplicatas ativas por nome canônico após N execuções (SC-006).
4. Soft-delete: inativo com mesma chave → conflito reportado, sem reativação.
5. Divergências entre fontes → sempre no relatório; matriz = união de pares elegíveis.
6. `solides_id` ausente → não bloqueia (FR-011).

---

## State transitions (idempotência)

```text
[parse OK]
    → resolve Escala padrão
    → para cada cargo elegível:
         ativo match → update|noop
         inativo match → conflito (skip)
         sem match → create
    → para cada competência avaliável:
         (idem)
    → para cada par união elegível:
         update_or_create vínculo
    → emitir relatório
```

Não há máquina de estados de domínio além desse fluxo de carga.
