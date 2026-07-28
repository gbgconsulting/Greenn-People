# Contract: Mapeamento Legado → Domínio

**Feature**: `003-import-catalogo-legado`  
**Data**: 2026-07-28

Contrato normativo dos de-paras usados pelo importador. Implementação e testes MUST aderir a estas tabelas. Detalhe de entidades: [../data-model.md](../data-model.md). CLI: [import-command-contract.md](./import-command-contract.md).

---

## 1. Normalização de nomes

```text
display_name(s) = collapse_whitespace(strip(s))
canonical_key(s) = casefold(strip_accents(NFKD(display_name(s))))
```

- Matching e idempotência usam `canonical_key`.
- Persistência usa `display_name` (preferência de fonte: competências ← lista-competencias; cargos ← lista-cargos).
- Dois nomes com a mesma chave → um registro; reportar `merged`.

---

## 2. Listas pipe-separated

```text
split_pipe(s) = [display_name(p) for p in s.split('|') if display_name(p)]
```

Aplicar em:

- `lista-cargos.Competência`
- `lista-competencias.Cargo`

---

## 3. Senioridade → `Cargo.nivel`

Avaliar na ordem; **primeira** regra que casar com token delimitado no nome canônico vence.

| Prioridade | Padrões (sobre canonical_key / tokens) | nivel | Label |
|-----------:|----------------------------------------|------:|-------|
| 1 | `estagiario`, `estag`, `trainee` | 1 | Estagiário |
| 2 | `jr`, `junior` | 2 | Júnior |
| 3 | `pl`, `pleno` | 3 | Pleno |
| 4 | `sr`, `senior` | 4 | Sênior |
| 5 | `tech lead`, `ux lead`, `qa lead`, `lead` | 5 | Especialista |
| 6 | `gerente`, `diretor`, `coordenador`, `coordenadora`, `ceo`, `presidente`, `head` | 6 | Principal |
| 7 | default (sem sufixo) | 6 | Principal |

Tokens de 1–2 caracteres (`jr`, `pl`, `sr`) MUST usar boundary (não substring de outra palavra).

---

## 4. `Cargo.nivel` → `CargoCompetencia.nivel_esperado`

| nivel | nivel_esperado |
|------:|---------------:|
| 1 | 2 |
| 2 | 2 |
| 3 | 3 |
| 4 | 4 |
| 5 | 4 |
| 6 | 4 |

`peso` MUST ser `1` (`Decimal('1')` / `1.00`).

---

## 5. Grupo legado → `Competencia.tipo`

| Grupo de competência (display; match casefold) | tipo |
|---|---|
| Liderança | `lideranca` |
| Comportamento | `comportamental` |
| Desempenho | `tecnica` |

Qualquer outro grupo → `nao_mapeados` (`motivo=grupo_desconhecido`); não cria competência.

Colunas legadas `Peso` e `Tipo de Avaliação` **MUST NOT** definir `Competencia.tipo` nem `CargoCompetencia.peso`.

---

## 6. Classificação de itens de competência

Ordem de avaliação por item de `lista-competencias`:

1. Se `canonical_key(nome)` ∈ KPI (igualdade ou família documentada) → `excluidos_kpi` (`motivo=kpi_operacional`).
2. Senão se ∈ ambíguos documentados → `nao_mapeados` (`motivo=ambiguo`).
3. Senão se grupo mapeável → candidata a importação (`avaliavel`).
4. Senão → `nao_mapeados`.

### 6.1 KPI — exclusão obrigatória

| Nome legado (exemplos) | Chave / família |
|---|---|
| SLA | `sla` |
| Lead time discovery | `lead time discovery` |
| Custo de nuvem por transação | `custo de nuvem por transacao` |
| Throughput por Colaborador | `throughput por colaborador` (+ sufixos) |
| Throughput por colaborador - Arquiteto | idem família |
| Índice de incidentes | `indice de incidentes` (+ sufixos) |
| Índice de incidentes - QA Lead | idem família |
| Tempo médio de espera na esteira | `tempo medio de espera na esteira` |

Família: match se `canonical_key` é igual **ou** começa com a chave base + separador (` - `, ` -`, espaço).

### 6.2 Ambíguos — não importar nesta versão

| Nome legado |
|---|
| Erros de usabilidade |
| Oportunidade de usabilidades entregues e cm problemas resolvidos |
| Oportunidades entregues de modernização |
| Oportunidades tracionadas |
| Monitoramento contínuo |

---

## 7. Escala padrão

| Atributo | Valor |
|---|---|
| `nome` | `Escala padrão 1-5` |
| `valor_minimo` | 1 |
| `valor_maximo` | 5 |

Lookup: escala **ativa** com esse nome → reutilizar. Só inativa → conflito fatal (`escala_inativa`).

---

## 8. Reconciliação de matriz

```text
pares_A = from lista-cargos
pares_B = from lista-competencias
pares_A', pares_B' = filter(competencia avaliável resolvível)
divergencias = symmetric_difference(pares_A', pares_B')  # report
matriz = union(pares_A', pares_B') where cargo resolvido AND competencia resolvida
```

Divergências MUST aparecer no relatório (SC-004). Pares com competência KPI/ambígua NÃO entram na matriz.

---

## 9. Soft-delete / idempotência

| Situação | Comportamento | Relatório |
|---|---|---|
| Ativo com mesma `canonical_key` | update campos se diferir | `atualizados` / `inalterados` |
| Inativo com mesma chave | não reativar; não criar ativo duplicado | `conflitos` / `inativo_existente` |
| Sem match | create `is_active=True` | `criados` |
| Reexecução idêntica | sem novos ativos duplicados | SC-006 |

---

## 10. Fora de escopo deste contrato

- Criação de Metas a partir de KPI excluídos
- `solides_id`
- Users, avaliações, PDI, UI
