# Data Model: Importação Legado Sólides — Colaboradores e Schema `solides_id`

**Branch**: `010-import-colaboradores-legado` | **Date**: 2026-08-12

**Nota**: Esta feature introduz **apenas** o campo `solides_id` (migration aditiva) em cinco entidades existentes e popula `Area`, `Cargo` (faltantes) e `CustomUser` via import. Competência, Avaliação e PDI recebem somente o campo schema nesta fatia — **sem import de conteúdo**.

Modelos canônicos: [apps/accounts/models.py](../../apps/accounts/models.py), [apps/organization/models.py](../../apps/organization/models.py), [apps/competencies/models.py](../../apps/competencies/models.py), [apps/reviews/models.py](../../apps/reviews/models.py), [apps/pdi/models.py](../../apps/pdi/models.py).

Contratos: [contracts/model-allowlist.md](./contracts/model-allowlist.md), [contracts/migration-safety.md](./contracts/migration-safety.md), [contracts/column-mapping-contract.md](./contracts/column-mapping-contract.md).

---

## Regras estritas de models / migrations

### PERMITIDO (esta fatia)

| Alteração | Escopo |
|---|---|
| Adicionar `solides_id` | `CustomUser`, `Cargo`, `Competencia`, `Avaliacao`, `PDI` |
| Definição do campo | `CharField(max_length=50, blank=True, null=True, unique=True, db_index=True)` |
| Migrations | Aditivas, uma por app (ver migration-safety) |

### PROIBIDO

| Proibição | Motivo |
|---|---|
| Alterar tipo/nullable/unique de campos existentes | Integridade histórica |
| Remover constraints / alterar `on_delete` | Princípio III |
| Novos campos PII (CPF, RG, banco, endereço, telefone) | FR-015 / OPSEC |
| Alterar semântica de `UserManager` além de set na importação | Decisão #21 escopo limitado |
| Raw SQL / bulk bypass de validação | RF-04.1 aciclicidade |
| Preencher `solides_id` em Competência/Avaliacao/PDI via import colaboradores | Fora de escopo 6.5.2 |

### Persistência obrigatória

- Import MUST chamar `full_clean()` + `save()` (ou `create_user()` para novos usuários).
- `CustomUser.clean()` valida aciclicidade de `line_manager` (RF-04.1).

---

## Entidades com migration (6.5.1)

### CustomUser (`accounts.CustomUser`)

| Campo novo | Tipo | Regras |
|---|---|---|
| `solides_id` | CharField(50), null, blank, unique, db_index | Preenchido via crosswalk avaliações quando match único; nullable |

| Campo importado | Origem | Regras |
|---|---|---|
| `nome` | `Nome` | `display_name()` |
| `email` | E-mail empresarial → E-mail → E-mail pessoal | único; `normalize_email()` |
| `email_confirmado_em` | import | `timezone.now()` (Decisão #21) |
| `is_active` | `Data demissão` | preenchida ≠ zero → `False` |
| `cargo` | `Cargo` / `Cargo ID` | FK resolve (abaixo) |
| `area` | `Departamento` | FK Area resolve (abaixo) |
| `line_manager` | `Superior direto id` | 2ª fase; via `solides_id` do gestor |
| `password` | — | `set_unusable_password()` em creates |

**Constraints existentes**: `email` unique; indexes em `line_manager`, `area`, `is_active`.

**Invariantes import**:
- E-mail único globalmente.
- Demitidos `is_active=False`.
- Hierarquia acíclica após fase B.
- Desativação respeita `_validate_deactivation_without_active_reports` (edge → conflito no relatório).

### Cargo (`organization.Cargo`)

| Campo novo | Tipo | Regras |
|---|---|---|
| `solides_id` | CharField(50), null, blank, unique, db_index | De `Cargo ID` no backup colaboradores |

| Campo importado | Origem | Regras |
|---|---|---|
| `nome` | `Cargo` | display; match `canonical_key` |
| `nivel` | inferido do nome | reuso tabela senioridade 003 se create |
| `is_active` | — | `True` em creates |

**Lookup**: `solides_id` → `canonical_key(nome)` entre ativos → create faltante (até 8 casos conhecidos).

### Competencia (`competencies.Competencia`)

| Campo novo | Tipo | Nesta fatia |
|---|---|---|
| `solides_id` | CharField(50), null, blank, unique, db_index | **Schema only** — sem import de conteúdo |

### Avaliacao (`reviews.Avaliacao`)

| Campo novo | Tipo | Nesta fatia |
|---|---|---|
| `solides_id` | CharField(50), null, blank, unique, db_index | **Schema only** — import MUST NOT alterar `etapa`, `concluida`, `nota_final_*` |

### PDI (`pdi.PDI`)

| Campo novo | Tipo | Nesta fatia |
|---|---|---|
| `solides_id` | CharField(50), null, blank, unique, db_index | **Schema only** |

---

## Entidades persistidas pelo import (6.5.2)

### Area (`organization.Area`)

| Campo | Origem | Regras |
|---|---|---|
| `nome` | `Departamento` | `get_or_create` por nome display entre ativos |
| `parent` | — | null (Unidade ignorada — vazia no dump) |
| `is_active` | — | `True` |

**Constraints**: `unique_area_nome_ativa`.

### Cargo — ver acima (create/update na resolução de FK de usuário)

### CustomUser — ver acima

---

## Entidades lógicas (não persistidas como novos models)

### Backup Colaboradores

- Formato: OOXML, planilha `sheet1` (ou primeira planilha).
- ~325 linhas (dump 2026-06-24).
- Colunas: ver [column-mapping-contract.md](./contracts/column-mapping-contract.md).

### Backup Avaliações (crosswalk)

- Opcional; colunas mínimas: `Nome Avaliado`, `Identificador Avaliado`.
- Produz índice Nome → ID Sólides.

### Relatório de Carga

Artefato stdout/arquivo. Contadores + listas mascaradas. Schema: [import-command-contract.md](./contracts/import-command-contract.md).

---

## Ordem de persistência

```text
transaction.atomic():
  1. Area         — get_or_create( nome=Departamento )
  2. Cargo        — resolve/create por solides_id ou canonical_key
  3. CustomUser   — upsert por email; solides_id; is_active; email_confirmado_em; FKs
  4. line_manager — 2ª passada: Superior direto id → solides_id → full_clean + save
```

Nenhuma escrita em `Avaliacao`, `AvaliacaoCompetencia`, `Ciclo`, `Meta`, `PDI` conteúdo.

---

## Relacionamentos tocados

```text
Area 1──* CustomUser
Cargo 1──* CustomUser
CustomUser *──1 CustomUser (line_manager, SET_NULL)
```

Import **não altera**: `CargoCompetencia`, `Avaliacao`, snapshots, `Ciclo`.

---

## State transitions (idempotência)

```text
[parse OK]
  → build crosswalk (opcional)
  → para cada linha colaborador:
       resolver email → skip se ausente (nao_importavel)
       resolver Area, Cargo
       upsert CustomUser (email key)
  → fase hierarquia:
       para cada Superior direto id:
         resolver gestor por solides_id
         tentar full_clean + save
         ciclo → conflito, não aplicar
  → emitir relatório
```

---

## Validação e invariantes

1. Arquivo colaboradores inválido → zero writes; exit 1.
2. Persistência em transação atômica.
3. Reexecução: delta duplicatas e-mail = 0 (SC-007).
4. `solides_id` nullable — ausência não falha import.
5. PII proibida nunca persistida.
6. Denylist de domínio intacta pós-import.
