# Data Model: Importação Legado Sólides — Ciclos Históricos e Cabeçalhos de Avaliação

**Branch**: `011-import-ciclos-avaliacoes-legado` | **Date**: 2026-08-13

**Nota**: Esta fatia introduz **apenas** `Ciclo.solides_id` (migration aditiva) e **persiste** ciclos históricos + cabeçalhos `Avaliacao` agregados. `Avaliacao.solides_id` já existe (spec 010). Sem notas, competências, Feedback ou PDI.

Models canônicos: [apps/cycles/models.py](../../apps/cycles/models.py), [apps/reviews/models.py](../../apps/reviews/models.py), [apps/accounts/models.py](../../apps/accounts/models.py).

Contratos: [contracts/model-allowlist.md](./contracts/model-allowlist.md), [contracts/migration-safety.md](./contracts/migration-safety.md), [contracts/aggregation-contract.md](./contracts/aggregation-contract.md), [contracts/column-mapping-contract.md](./contracts/column-mapping-contract.md).

---

## Regras estritas de models / migrations

### PERMITIDO (esta fatia)

| Alteração | Escopo |
|---|---|
| Adicionar `Ciclo.solides_id` | Única alteração de schema |
| Definição do campo | `CharField(max_length=50, blank=True, null=True, unique=True, db_index=True)` |
| Persistência ORM `Ciclo` | `nome`, `data_inicio`, `data_fim`, `status=encerrado`, `solides_id` |
| Persistência ORM `Avaliacao` | `ciclo`, `usuario`, `etapa=feedback`, `concluida=True`, `solides_id` canônico |
| Extensão parse/dates/report 010 | Módulos irmãos no mesmo padrão |
| Samples + testes | `data/legado-solides/samples/`, `tests/test_import_ciclos_avaliacoes_legado.py` |

### PROIBIDO

| Proibição | Motivo |
|---|---|
| Alterar tipo/constraints/`on_delete` de campos existentes Ciclo/Avaliacao | Integridade histórica (III) |
| Chamar `open_cycle`, `close_cycle`, `advance_stage`, `can_advance`, `approve_*`, `reject_*`, `calcular_*` | Clarification #4; Princípio V |
| Preencher `nota_final_*`, `AvaliacaoCompetencia`, `Feedback`, `PDI` | FR-012/FR-020; escopo 6.5.5+ |
| Inventar `CustomUser` ou `Ciclo` órfão | FR-011 |
| `RunPython` mutando domínio; raw SQL bypass `clean`/`save` | migration-safety |
| Usar `raw/` no CI | FR-019 |

### Persistência obrigatória

- Toda escrita MUST chamar `full_clean()` + `save()`.
- `Ciclo._validate_single_open()` permanece: como import só grava `encerrado`, não conflita com ciclo aberto vigente.

---

## Entidade: Ciclo (histórico)

**Model**: `cycles.Ciclo`  
**Fonte**: `backup_solicitacoes_avalicaoes_*.xlsx` (~57)

### Campo novo (migration)

| Campo | Tipo | Regras |
|---|---|---|
| `solides_id` | CharField(50), null, blank, unique, db_index | = `Identificador` da solicitação (string canônica) |

### Campos persistidos pela importação

| Campo | Origem | Regras |
|---|---|---|
| `nome` | `Nome` | Normalizar serial Excel → rótulo legível (ISO); senão strip/display_name |
| `data_inicio` | `Iniciada em` | serial Excel ou ISO via `dates.parse_legacy_date`; **obrigatória** |
| `data_fim` | `Terminada em` | idem; **obrigatória** |
| `status` | `Status` Sólides | **Sempre** `encerrado` (finished/draft/active/canceled) |
| `solides_id` | `Identificador` | Chave de idempotência |

### Campos existentes intocados na definição

`TimeStampedModel` (`created_at`, `updated_at`); choices `Status.ABERTO`/`ENCERRADO`; validação só-um-aberto — **sem alteração de schema**.

### Validação / estado

| Regra | Comportamento |
|---|---|
| Sem `Identificador` | Não importável; conflito |
| Datas ausentes/inválidas | Conflito; **não criar** ciclo |
| Status legado qualquer | → `encerrado` |
| Reexecução mesmo `solides_id` | Update campos permitidos; não duplicar |
| Ciclo aberto vigente no ambiente | Intact; import não abre nem encerra o vigente |

### Relacionamentos

- `Avaliacao.ciclo` → `Ciclo` (`on_delete=PROTECT`) — cabeçalhos desta fatia.

---

## Entidade: Avaliação (cabeçalho histórico)

**Model**: `reviews.Avaliacao`  
**Fonte**: `backup_avaliacoes_*.xlsx` (~1.925 linhas → N grupos)  
**Schema**: `solides_id` **já existe** (010) — sem migration em `reviews` nesta fatia.

### Campos persistidos pela importação

| Campo | Origem / regra | Notas |
|---|---|---|
| `ciclo` | Resolve `Ciclo.solides_id` = `Identificador Solicitação` | Órfão se ciclo ausente |
| `usuario` | Resolve `CustomUser.solides_id` = `Identificador Avaliado`; fallback nome (R9) | Órfão se não resolve; inativo ok |
| `etapa` | Constante `feedback` | Persistência direta |
| `concluida` | Constante `True` | Persistência direta |
| `solides_id` | Identificador canônico do grupo (aggregation-contract) | Unique global |

### Campos explicitamente NÃO preenchidos

| Campo | Motivo |
|---|---|
| `nota_final_lider` | Fatia 6.5.5 |
| `nota_final_autoavaliacao` | Fatia 6.5.5 |
| Linhas `AvaliacaoCompetencia` | Fatia 6.5.5 |
| `Feedback` | Fatia 6.5.5 |

### Constraints existentes (intocados)

- `unique_together = [('ciclo', 'usuario')]` — **força** agregação 1:1
- `solides_id` unique nullable
- FKs `PROTECT`

### Agregação (resumo)

```text
Entrada: N linhas (avaliador × avaliado) por (solicitação, avaliado)
Saída: 1 Avaliacao(ciclo, usuario)
solides_id = canônico (autoavaliação preferida; senão min ID)
ids_colapsados → relatório (amostra mascarada) para 6.5.5
```

Detalhe normativo: [contracts/aggregation-contract.md](./contracts/aggregation-contract.md).

### Transições de estado

| De | Para | Como |
|---|---|---|
| (inexistente) | `etapa=feedback`, `concluida=True` | Create ORM direto |
| Qualquer estado prévio do mesmo `(ciclo,usuario)` importado | `feedback` + `concluida=True` | Update ORM (reexecução) |
| — | — | **Proibido** usar `advance_stage` / open-close |

Não há máquina de estados nesta fatia — apenas escrita de campos permitidos.

---

## Entidade: Colaborador (CustomUser) — read-only nesta fatia

| Uso | Regra |
|---|---|
| Lookup primário | `solides_id` = Identificador Avaliado |
| Fallback | `canonical_key(Nome Avaliado)` → match único em `nome` |
| Inativo | Permitido (histórico) |
| Create | **Proibido** |

Populado pela spec 010. Esta feature **não** altera schema de `CustomUser`.

---

## Entidades fonte (não persistidas como models)

### Solicitação legada

| Atributo | Coluna | Destino |
|---|---|---|
| id | `Identificador` | `Ciclo.solides_id` |
| nome | `Nome` | `Ciclo.nome` |
| datas | `Iniciada em` / `Terminada em` | `data_inicio` / `data_fim` |
| status | `Status` | sempre `encerrado` |

### Linha de avaliação legada

| Atributo | Coluna | Uso |
|---|---|---|
| id linha | `Identificador` | canônico / colapsado |
| solicitação | `Identificador Solicitação` | FK ciclo |
| avaliado | `Identificador Avaliado` | FK usuario |
| nomes | `Nome Avaliador` / `Nome Avaliado` | detectar autoavaliação |

---

## Relatório de carga (artefato operacional)

Não é model Django. Contadores estáveis:

| Contador | Significado |
|---|---|
| `ciclos_criados` / `atualizados` / `inalterados` | Fase 1 |
| `avaliacoes_criadas` / `atualizadas` / `inalteradas` | Fase 2 |
| `grupos_agregados` | Quantidade de grupos (solicitação, avaliado) processados |
| `conflitos` | Datas, unicidade solides_id, canônico já usado, etc. |
| `orfaos` | Ciclo ou usuário não resolvido |
| `ids_colapsados` (amostra) | Handoff 6.5.5 — mascarados |

---

## Diagrama de relacionamentos (pós-import)

```text
Ciclo (solides_id = Identificador solicitação, status=encerrado)
  └── Avaliacao* (unique ciclo+usuario; solides_id canônico;
                  etapa=feedback; concluida=True)
        └── usuario → CustomUser (solides_id = Identificador Avaliado)
        └── (futuro 6.5.5) AvaliacaoCompetencia / Feedback
```

---

## Ordem de persistência (dentro de `transaction.atomic`)

```text
0. Pré: migrate Ciclo.solides_id; 010 aplicada
1. Upsert Ciclo por solides_id (todos encerrados)
2. Agregar linhas avaliações → grupos
3. Por grupo: resolve ciclo + usuario → upsert Avaliacao
```

Falha em qualquer passo da transação → rollback completo.
