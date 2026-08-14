# Contract: Agregação de Avaliações (1:1 ciclo/usuário + linha canônica)

**Feature**: `011-import-ciclos-avaliacoes-legado`  
**Fonte**: Clarifications 2026-08-13 (#2, #3); FR-007/FR-009; `Avaliacao.unique_together (ciclo, usuario)`  
**Data**: 2026-08-13  
**Handoff**: IDs colapsados alimentam a fatia **6.5.5** (notas que apontam a Identificadores não canônicos)

---

## Problema

O Sólides exporta **N linhas** por combinação avaliador × avaliado na mesma solicitação.  
O Greenn People admite **no máximo uma** `Avaliacao` por `(ciclo, usuario)`.

---

## Chave de agregação

```text
group_key = (
  canonicalize_id(Identificador Solicitação),
  canonicalize_id(Identificador Avaliado),
)
```

Todas as linhas com o mesmo `group_key` colapsam em **uma** `Avaliacao`.

---

## Algoritmo (normativo)

```text
1. Parse todas as linhas de backup_avaliacoes_*.xlsx
2. Descartar/reportar linhas sem Identificador, Identificador Solicitação ou Identificador Avaliado
3. Group by group_key
4. Para cada grupo G:

   auto_rows = { row in G | canonical_key(Nome Avaliador) == canonical_key(Nome Avaliado)
                            and ambos não-vazios }

   if auto_rows:
     canonical_id = min_id({ row.Identificador for row in auto_rows })
   else:
     canonical_id = min_id({ row.Identificador for row in G })

   collapsed_ids = sorted_unique({ row.Identificador for row in G } - { canonical_id })

   ciclo   = resolve_ciclo(G.solicitacao_id)
   usuario = resolve_usuario(G.avaliado_id, G.any_nome_avaliado)

   if not ciclo:   report orfao_ciclo; skip persist
   if not usuario: report orfao_usuario; skip persist

   upsert Avaliacao(
     ciclo=ciclo,
     usuario=usuario,
     solides_id=canonical_id,
     etapa=feedback,
     concluida=True,
   )

   report grupos_agregados += 1
   if collapsed_ids: report amostra ids_colapsados (mascarada)
```

### `min_id` (ordem total estável)

```text
min_id(ids):
  if all ids parseiam como int:
    return str(min(int(id) for id in ids))
  else:
    return min(ids)   # lexicográfico Unicode estável
```

Entre múltiplas linhas de autoavaliação, aplica-se o mesmo `min_id` no subconjunto auto.

### Igualdade de nomes (autoavaliação)

```text
is_auto(row) =
  canonical_key(Nome Avaliador) == canonical_key(Nome Avaliado)
  and canonical_key(Nome Avaliado) != ""
```

Reutilizar `canonical_key` da spec 003 (mesmo da 010).

---

## Upsert e conflitos de unicidade

| Situação | Ação |
|---|---|
| Não existe Avaliacao `(ciclo, usuario)` e `solides_id` canônico livre | Create |
| Existe `(ciclo, usuario)` com mesmo `solides_id` (ou null→canônico) | Update `etapa`/`concluida`/`solides_id`; report atualizado/inalterado |
| Existe `(ciclo, usuario)` com **outro** `solides_id` non-null | Conflito `solides_id_divergente`; não sobrescrever silenciosamente |
| Canônico já usado por **outra** Avaliacao | Conflito `solides_id_avaliacao_em_uso`; não sobrescrever |

---

## Relatório → handoff 6.5.5

Cada grupo com `len(G) > 1` MUST aparecer (amostra mascarada) com:

| Campo | Uso futuro |
|---|---|
| `canonical` | FK alvo das notas que usam ID canônico |
| `colapsados` | Mapear `Identificador Avaliação` em `backup_notas_*` → avaliação canônica |
| `n_linhas` | Cardinalidade do grupo |

Produção: **máx. 5** amostras por seção; totais sempre completos. Sem dump PII (nomes completos em massa).

---

## Invariantes verificáveis em teste

1. N linhas multi-avaliador → **1** Avaliacao no DB para o par.
2. Grupo com autoavaliação → `solides_id` ∈ IDs das linhas auto; e = `min_id` desse subconjunto.
3. Grupo sem autoavaliação → `solides_id` = `min_id` de todos.
4. `collapsed_ids` no relatório = todos − canônico.
5. Reexecução → delta contagem Avaliacao por `(ciclo, usuario)` = 0.

---

## Explicitamente descartado (clarifications)

- Uma Avaliação por linha Sólides
- Importar somente autoavaliações
- Hash composto como `solides_id`
- `solides_id` nulo nesta fatia
