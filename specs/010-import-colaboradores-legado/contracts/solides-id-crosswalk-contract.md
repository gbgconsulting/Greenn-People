# Contract: Estratégia `solides_id` Crosswalk

**Feature**: `010-import-colaboradores-legado`  
**Fonte**: [data/legado-solides/README.md](../../../data/legado-solides/README.md) § Identificadores  
**Data**: 2026-08-12

---

## Problema

`backup_colaboradores` **não** traz coluna de ID Sólides do colaborador. Fatias futuras (6.5.4–6.5.6) precisam correlacionar usuários com `Identificador Avaliado` nos backups de avaliações/notas.

---

## Estratégia por entidade (esta fatia)

| Entidade | Fonte no legado | Estratégia 6.5.1/6.5.2 |
|---|---|---|
| **CustomUser** | Ausente em colaboradores | Crosswalk opcional + chave natural e-mail |
| **Cargo** | `Cargo ID` | Direto na importação colaboradores |
| **Competencia** | `Identificador` (habilidades) | Schema only — fatia 6.5.3 |
| **Avaliacao** | `Identificador` (avaliações) | Schema only — fatia 6.5.4 |
| **PDI** | composta / hash | Schema only — fatia 6.5.6 |

---

## Crosswalk usuário (6.5.2)

### Entrada

Arquivo `--avaliacoes` (`backup_avaliacoes_*.xlsx`).

### Algoritmo

```text
1. Para cada linha com Nome Avaliado + Identificador Avaliado:
     key = canonical_key(Nome Avaliado)
     id  = str(Identificador Avaliado).strip()
     if key empty or id empty: skip
     if key in index and index[key] != id:
         register conflito crosswalk_ambiguo(key, index[key], id)
     else:
         index[key] = id

2. Para cada colaborador parseado:
     key = canonical_key(Nome)
     if key in index:
         user.solides_id = index[key]   # se sem conflito prévio na key
     else:
         user.solides_id = null         # ok — dedupe por email
```

### Gestor (`Superior direto id`)

- Valor numérico/string do backup colaboradores.
- Fase B: `CustomUser.objects.filter(solides_id=str(superior_id)).first()`.
- Requer gestor com `solides_id` preenchido (via crosswalk ou futura fonte).
- Dump 2026-06-24: ~29/31 IDs de gestores batem com avaliações.

### Idempotência

- Reimport: atualizar `solides_id` se crosswalk resolve e valor diverge.
- Unique constraint DB rejeita duplicata de `solides_id` entre dois usuários → conflito fatal de persistência para aquela linha (reportar, não corromper par existente).

---

## Cargo `solides_id`

```text
on upsert cargo from row:
  if Cargo ID present:
    cargo.solides_id = str(Cargo ID)
  lookup order: solides_id → canonical_key(nome)
on reimport catalog 003 cargos without solides_id:
  first colaboradores import backfills solides_id when Cargo ID known
```

---

## Nullable e unicidade

- `solides_id` MAY be null em qualquer entidade.
- When non-null, MUST be unique (DB + application).
- Import MUST NOT exigir 100% preenchido (~187/325 esperado com crosswalk no dump).

---

## Chaves naturais de fallback

| Entidade | Chave natural |
|---|---|
| CustomUser | e-mail normalizado |
| Cargo | `canonical_key(nome)` entre ativos |
| Area | `nome` entre ativos |
| Competencia/Avaliacao/PDI | (fatias futuras — definir na spec respectiva) |

---

## Testes MUST validar

- Crosswalk parcial: subset com match único recebe ID.
- Nome ambíguo: dois IDs → conflito, ambos usuários sem ID atribuído por aquela key.
- Gestor resolvido por `solides_id` após fase A.
- Gestor ID inexistente → `gestor_nao_resolvido`, user sem line_manager.
- Reimport idempotente: mesmo `solides_id` não duplica usuários.
