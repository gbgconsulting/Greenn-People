# Data Model: Elegibilidade por “Admitidos até”

**Feature**: `015-cycle-admission-cutoff`  
**Date**: 2026-08-20  
**Fonte**: [spec.md](./spec.md) Key Entities + FR-007…FR-010; [research.md](./research.md) R1/R3

---

## Entidades

### Ciclo (`apps.cycles.models.Ciclo`)

| Campo | Tipo | Null | Notas |
|---|---|---|---|
| `nome` | CharField(100) | no | vigente |
| `data_inicio` | DateField | no | **NÃO** é o corte |
| `data_fim` | DateField | no | informativo; encerramento manual |
| `status` | CharField | no | `aberto` \| `encerrado`; no máx. um `aberto` |
| `solides_id` | CharField(50) | yes | import 011; intacto |
| **`admitidos_ate`** | **DateField** | **yes** | **NOVO** — corte “Admitidos até”; opcional no DB |

**Migration**: uma `AddField` aditiva. Sem `AlterField` em outros campos. Sem `RunPython`.

**Invariantes**:
- `admitidos_ate = NULL` em ciclo **encerrado**/importado ⇒ **válido**; sem reprocessar elegibilidade.
- Abertura operacional nova ⇒ regra de negócio exige `admitidos_ate` **não nulo** (`open_cycle`); caso contrário falha e status permanece não-aberto.
- Independente de `data_inicio` / `data_fim` (podem divergir).

**Relacionamentos**: intactos (`Avaliacao.ciclo` FK existente; PROTECT vigente). **Zero** M2M de participantes. **Zero** FK nova.

---

### CustomUser.data_entrada (`apps.accounts.models.CustomUser`)

| Campo | Tipo | Null | Notas |
|---|---|---|---|
| `data_entrada` | DateField | yes | **INTACTO** — reutilizar; base da elegibilidade |

**Proibições**:
- ZERO segundo campo de admissão.
- ZERO `AlterField` (tipo / null / unique / blank).
- Pode permanecer vazia (legado / auto-cadastro) ⇒ pessoa **não elegível** até preencher.

**Backfill (US4)**: preenche somente quando `NULL`; não sobrescreve.

---

### Avaliação (`apps.reviews.models.Avaliacao`)

Matrícula do colaborador no ciclo. Schema **sem mudança** nesta feature.

**Invariantes de criação** (comportamento):
- Criada apenas se elegível (abertura batch ou mid-cycle `ensure`).
- No máximo 1 por `(ciclo, usuario)` (`get_or_create` vigente).
- **Snapshot**: uma vez criada, **permanece** mesmo se `data_entrada` mudar depois (inclusive para > corte ou NULL). Elegibilidade **nunca** apaga / desfaz etapa / fecha Avaliação.

---

## Elegibilidade (regra de domínio — não é tabela)

```text
elegível(user, ciclo) ⇔
  user.is_active
  ∧ user.data_entrada IS NOT NULL
  ∧ ciclo.admitidos_ate IS NOT NULL
  ∧ user.data_entrada <= ciclo.admitidos_ate   # date, inclusivo
```

| Caso | Elegível? |
|---|---|
| Ativo, entrada ≤ D | sim |
| Ativo, entrada = D | sim (inclusivo) |
| Ativo, entrada > D | não |
| Ativo, `data_entrada` NULL | **não** |
| Inativo (qualquer data) | não |
| `admitidos_ate` NULL (predicado) | não (fail-closed); `open_cycle` falha antes |

**Escopo de leitura**: inelegível simplesmente **não tem** Avaliacao naquele ciclo. `get_visible_users` / hierarquia **não** mudam.

---

## Estados do ciclo

```text
[encerrado, admitidos_ate=NULL]  --create-->  [encerrado, admitidos_ate=?]
        |                                              |
        | open sem corte                               | open com D
        v                                              v
   ERRO (status intacto, 0 Avaliações)     [aberto, admitidos_ate=D]
                                                   |
                                                   | close_cycle (intacto)
                                                   v
                                          [encerrado, admitidos_ate=D]
```

- Ciclos 011: nascem/permanecem `encerrado` com `admitidos_ate=NULL`.
- `close_cycle`: **DIFF VAZIO** de regra de negócio (apenas o campo pode já estar preenchido).

---

## Preview (agregados — não entidade persistida)

Não há model. Contagens derivadas no serviço de preview:

| Contagem | Definição |
|---|---|
| elegíveis | `is_active` ∧ `data_entrada ≤ D` |
| exclusão por data posterior | `is_active` ∧ `data_entrada > D` |
| sem data | `is_active` ∧ `data_entrada IS NULL` |

Inativos **não** entram em nenhuma das três (contrato de preview foca ativos).

---

## Diagrama (schema)

```text
CustomUser                         Ciclo
───────────                        ─────
data_entrada (Date?, intacto)      admitidos_ate (Date?, NOVO)
is_active                          status (aberto|encerrado)
                                   data_inicio / data_fim (≠ corte)

            Avaliacao
            ─────────
            (ciclo, usuario) unique
            criação ← elegibilidade
            remoção ← NUNCA por mudança de data_entrada
```

---

## FR cobertos

FR-002, FR-007, FR-008, FR-009, FR-010, FR-006 (snapshot), FR-003/004 (critério).
