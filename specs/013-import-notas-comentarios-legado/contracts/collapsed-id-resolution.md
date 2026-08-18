# Contract: Resolução de IDs Colapsados (consumo da 011)

**Feature**: `013-import-notas-comentarios-legado`  
**Data**: 2026-08-18  
**Normativo (NÃO reabrir)**: [specs/011-import-ciclos-avaliacoes-legado/contracts/aggregation-contract.md](../../011-import-ciclos-avaliacoes-legado/contracts/aggregation-contract.md)

Esta fatia **só CONSOME** o algoritmo da 011. **Proibido** segundo algoritmo, cópia de `aggregate.py`, tabela persistida ou PII extra (FR-003).

---

## Problema

O dump de notas/comentários referencia `Identificador Avaliação` que pode ser:

1. O `Avaliacao.solides_id` **canônico** gravado na 011, ou
2. Um ID **colapsado** do mesmo grupo 1:1 `(ciclo, usuario)`, ou
3. Um ID sem canônico nem mapa → órfão.

Os IDs colapsados **não** estão no banco.

---

## Insumo

`--avaliacoes` = mesmo `backup_avaliacoes_*` usado na 011 (cabeçalhos, ~1.925 linhas).

```text
rows   = parse_avaliacoes_headers_xlsx(path).rows
groups = aggregate_avaliacao_headers(rows)   # IMPORTAR cycles/.../aggregate.py
```

Funções/tipos a reutilizar (não reimplementar): `aggregate_avaliacao_headers`, `AggregatedAvaliacaoGroup`, `min_id`, `is_autoavaliacao`, `canonical_id`, `collapsed_ids`, `group_key`.

---

## Mapa em memória

```text
mapa: dict[str, str]  # legado_id → canonical_id

para cada group in groups:
  mapa[group.canonical_id] = group.canonical_id
  para cada cid in group.collapsed_ids:
    mapa[cid] = group.canonical_id
```

Default = memória. **PROIBIDO** persistir model/tabela de mapa.

`--avaliacoes` **NÃO** reimporta cabeçalhos (zero `Avaliacao.save` oriundo deste arquivo).

---

## Resolução `Identificador Avaliação`

```text
id = canonicalize_id(Identificador Avaliação)

1. Avaliacao.objects.filter(solides_id=id).first()
2. senão:
     canonical = mapa.get(id)
     se canonical: Avaliacao.objects.filter(solides_id=canonical).first()
3. senão: orfaos_avaliacao; skip
```

**NUNCA** inventar `Avaliacao`, `Ciclo` ou `User`.  
**NUNCA** `get_or_create(ciclo=..., usuario=...)`.  
**NUNCA** novo `unique_together`.

Relatório: incrementar `ids_colapsados_resolvidos` quando o passo (2) for o que resolveu.

---

## Invariantes verificáveis em teste

| Caso | Esperado |
|---|---|
| ID **canônico** | Match direto; nota/feedback na mesma `Avaliacao` 011 |
| ID **colapsado** | Resolve para a avaliação canônica do grupo; **zero** 2ª `Avaliacao` |
| ID **órfão** (sem canônico nem mapa) | `orfaos_avaliacao`; zero `Avaliacao`/`Ciclo`/`User` inventados |
| Reexecução | Delta de `Avaliacao` por `(ciclo, usuario)` = **0** |

Estes quatro casos MUST existir em `tests/test_import_notas_comentarios_legado.py` com samples (nunca `raw/`).

---

## Explicitamente descartado

- Copiar `aggregate.py` para `reviews/`
- Reabrir clarifications da 011 (auto vs `min_id`, unique `(ciclo, usuario)`)
- Arquivo/relatório truncado da 011 como mapa completo (amostra máx. 5 é insuficiente)
- Persistir `ids_colapsados` como PII/tabela
