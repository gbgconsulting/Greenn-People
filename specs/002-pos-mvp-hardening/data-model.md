# Data Model: Hardening Operacional Pós-MVP

**Branch**: `002-pos-mvp-hardening` | **Date**: 2026-07-14

Modelo incremental sobre o MVP. Referência completa da 001: [../001-gestao-desempenho-talentos/data-model.md](../001-gestao-desempenho-talentos/data-model.md) e [docs/data-model.md](../../docs/data-model.md).

Este documento lista **apenas alterações e entidades impactadas**.

## Convenções preservadas

- `TimeStampedModel`; código EN / labels pt-BR.
- FKs históricas: `on_delete=PROTECT`.
- Auditoria append-only (`AuditLog`).
- Um ciclo `aberto` por vez; etapas canônicas inalteradas.
- Fórmula de `nota_final_lider` inalterada.

---

## Alterações por entidade

### Avaliacao (`reviews`) — sem mudança de schema

| Aspecto | Detalhe |
|---|---|
| Unicidade | `(ciclo, usuario)` — base de idempotência mid-cycle |
| Etapa | Nunca retrocede por reprovação pontual |
| Criação mid-cycle | `get_or_create` via `ensure_avaliacao_for_user` quando colaborador ativo + ciclo aberto |
| Defaults | `etapa=input_metas` na criação mid-cycle (igual batch de abertura) |

**Estados / transições**: ver [contracts/post-rejection-contract.md](./contracts/post-rejection-contract.md) e contrato de stage da 001 (corrigido semanticamente nesta feature).

---

### Meta (`goals`) — sem novos campos; comportamento de status

| Campo | Valores | Regra pós-hardening |
|---|---|---|
| `status` | `pendente` \| `aprovada` \| `reprovada` | `reject_meta` → `reprovada`; correção chama `reopen()` → `pendente`; aprovadas irmãs intactas |
| `status_resultado` | `pendente` \| `aprovado` \| `reprovado` | `reject_resultado` → `reprovado`; correção chama `reopen_resultado()` → `pendente` |
| `progresso` | 0–100 | Editável após reprovação de resultado enquanto etapa = `aprovacao_resultados` (além de `resultados`) |

**Validação**:
- `reopen()` só se `status == reprovada`.
- `reopen_resultado()` só se `status_resultado == reprovado`.
- Avanço de etapa continua exigindo 100% aprovados + ≥1 meta (serviço `stage`).

**Auditoria**: passar a trackear `status` e `status_resultado` (ator real via `audit_actor`).

---

### Area / Cargo (`organization`)

| Campo | Mudança |
|---|---|
| `is_active` | Já existe — **remoção** = `is_active=False` (não `DELETE`) |
| `nome` | `UniqueConstraint(nome, condition=Q(is_active=True))` |

**Validação**: seletores de criação de vínculos só listam ativos; inativos permanecem para histórico.

---

### Escala / Competencia (`competencies`)

| Campo | Mudança |
|---|---|
| `is_active` | **Novo** BooleanField `default=True` |
| `nome` | `UniqueConstraint(nome, condition=Q(is_active=True))` por model |

`CargoCompetencia` e FKs históricas: `PROTECT` mantido; soft-delete não cascadeia.

---

### CustomUser (`accounts`)

| Aspecto | Mudança comportamental |
|---|---|
| Ativação / cadastro ativo | Dispara `ensure_avaliacao_for_user` se ciclo aberto |
| `line_manager` | Reatribuição em lote via serviço de offboarding |
| Desativação | Continua bloqueada se houver liderados ativos |

Sem novos campos obrigatórios.

---

### NotificacaoLog (`notifications`)

| Campo | Tipo | Notas |
|---|---|---|
| `referencia` | CharField(64) | Ex.: `avaliacao:{id}`, `acao_pdi:{id}` |
| `janela` | CharField(32) ou DateField | Ex.: data-alvo do lembrete ISO |
| (existentes) | `destinatario`, `tipo`, `status`, `erro`, `created_at` | Append-only preservado |

**Índice**: `(destinatario, tipo, referencia, janela)` para lookup de dedupe.

**Regra**: se existe log `enviado` com a mesma chave lógica, task não reenvia.

---

### AcaoPDI (`pdi`)

| Campo | Mudança comportamental |
|---|---|
| `prazo` | Tracked em auditoria |
| `status` | Se `atrasada` e novo `prazo >= hoje` → recalcular (default `pendente`); se prazo ainda passado, permanece `atrasada` |

---

### AuditLog (`audit`) — schema inalterado

Novos eventos via signals/serviço:

| Instância | Campos adicionados ao track |
|---|---|
| `Meta` | `status`, `status_resultado` |
| `AcaoPDI` | `prazo` (além de `status`) |
| `CustomUser` | `line_manager_id` (já tracked) — reassign em lote gera N entradas |

---

## Relacionamentos relevantes (inalterados topologicamente)

```text
Ciclo (1 aberto) ──< Avaliacao >── CustomUser
                      │
                      └── metas (Meta)  [status / status_resultado]

CustomUser.line_manager → CustomUser
Area / Cargo / Escala / Competencia  (is_active + unique ativos)

AcaoPDI.prazo / status
NotificacaoLog (dedupe key)
AuditLog (append-only)
```

---

## Políticas `on_delete` (sem regressão)

| Relação | Política |
|---|---|
| Avaliacao → Ciclo/User | PROTECT |
| Meta → Avaliacao/User/Objetivo | PROTECT |
| CargoCompetencia → Cargo/Competencia | PROTECT |
| Competencia → Escala | PROTECT |
| NotificacaoLog → User | PROTECT |
| Soft-delete catálogo | Sem DELETE físico; histórico preservado |

---

## State machines (resumo)

### Item meta / resultado

```text
pendente ──approve──► aprovada/aprovado
    │
    └──reject──► reprovada/reprovado ──reopen(correction)──► pendente ──approve──► ...
```

Etapa agregada: **estática** durante o loop acima.

### Offboarding gestor

```text
tem liderados ativos ──► desativação BLOQUEADA
        │
        └── reassign_direct_reports(all) ──► sem liderados ──► desativação PERMITIDA
```

Reassign parcial: desativação permanece bloqueada.
