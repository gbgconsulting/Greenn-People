# Data Model: 008-cycle-guidance-ux (apresentação)

**Feature**: Orientação de próximo passo (guidance UX)  
**Importante**: Este documento descreve **entidades de apresentação / DTO de leitura**.  
**Zero** models Django novos. **Zero** migrations.

---

## Relação com o domínio existente (somente leitura)

```text
Ciclo (existente)
  └── Avaliacao (existente) ── etapa: input_metas … feedback
        ├── Meta (status / status_resultado)     → hints / contagem aprovações
        ├── AvaliacaoCompetencia (notas)         → “faltam N”
        └── Feedback (ciente_em)                 → ciência / contagem feedbacks

CustomUser (área, cargo, line_manager)          → vínculo / escopo (sem alterar AuthZ)
CargoCompetencia                                 → blocker RH (cargo sem pesos)
```

Guidance **não** cria FKs nem espelha estado; apenas **lê** e deriva DTO.

---

## Entidade de apresentação: `NextStepGuidance`

| Campo | Tipo | Regra |
|-------|------|--------|
| `title` | str | Obrigatório; linguagem humana (FR-005) |
| `body` | str | Uma frase curta |
| `cta_label` | str \| None | None quando sem CTA de avanço |
| `cta_url_name` | str \| None | Nome de rota **já existente** ou None |
| `cta_kwargs` | dict | Kwargs para `reverse` (ex. `{'pk': avaliacao.pk}`); default `{}` |
| `blocked_reason` | str \| None | Explica ausência de CTA / espera (ex. aguardando líder) |

**Validação**:
- Se `cta_url_name` é None → `cta_label` deve ser None (ou não renderizar botão)
- `cta_url_name` MUST estar na allowlist de rotas do contrato de derivação
- Derivação NEVER escreve `Avaliacao.etapa` / status de Meta / `ciente_em`

**Fonte de mapeamento**: tabela FR-001a em [spec.md](./spec.md); formalizada em [contracts/guidance-derivation.md](./contracts/guidance-derivation.md).

---

## Entidade de apresentação: `StageStepperState`

| Campo | Tipo | Regra |
|-------|------|--------|
| `stages` | list[`StageStep`] | Exactamente as 6 etapas do enum `Avaliacao.Etapa` (ordem canônica) |

### `StageStep`

| Campo | Tipo | Valores |
|-------|------|---------|
| `key` | str | Valor de `Avaliacao.Etapa` |
| `label` | str | Rótulo humano curto |
| `state` | str | `concluida` \| `atual` \| `futura` \| `bloqueada` |

**Regras de marcação (apresentação)**:
- Etapas com índice menor que a etapa atual → `concluida` (salvo caso especial concluída total)
- Etapa corrente → `atual`
- Etapas futuras → `futura`
- `bloqueada` **somente** quando o produto já comunica bloqueio/impedimento visual distinto sem inventar regra (ex. superfície já trata como não-acionável / espera); NÃO chamar `can_advance` para **mutar** estado — pode **ler** resultado de predicados existentes se já expostos, sem alterar máquina

**Transições**: nenhuma — o stepper não possui máquina própria.

---

## Entidade de apresentação: `LeaderPendingBadge`

| Campo | Tipo | Regra |
|-------|------|--------|
| `total` | int ≥ 0 | Soma: aprovações + avaliações + feedbacks elegíveis |
| `aprovacoes` | int ≥ 0 | Breakdown opcional (debug/test); UI exibe só total |
| `avaliacoes` | int ≥ 0 | idem |
| `feedbacks` | int ≥ 0 | idem |

**Validação**:
- `total == aprovacoes + avaliacoes + feedbacks`
- Cada parcela usa **as mesmas** regras de elegibilidade já vigentes (ver [contracts/leader-pending-badge.md](./contracts/leader-pending-badge.md))
- Escopo ⊆ `get_visible_users(viewer)` (reuso, sem alterar serviço)

**Não é** entidade de negócio persistida.

---

## Entidade de apresentação: `RhPreOpenChecklist`

| Campo | Tipo | Regra |
|-------|------|--------|
| `items` | list[`RhBlockerItem`] | Pode ser vazia (“sem pendências operacionais”) |
| `advisory_only` | bool | Sempre `True` nesta feature |

### `RhBlockerItem`

| Campo | Tipo | Exemplos |
|-------|------|----------|
| `kind` | str | `user_missing_area_cargo` \| `cargo_missing_competencies` |
| `label` | str | Mensagem escaneável |
| `count` | int \| None | Quando agrega vários |
| `fix_url_name` | str | Rota **existente** (ex. `organization:user_pending`, cadastro de cargo/competências) |
| `fix_kwargs` | dict | Opcional |

**Estado vs abertura**: checklist **não** altera `Ciclo.status` nem capacidade de POST em `cycles:ciclo_open`. Ver [contracts/rh-checklist-advisory.md](./contracts/rh-checklist-advisory.md).

---

## Estados especiais (não-etapa)

| Estado | Quando | Efeito no `NextStepGuidance` |
|--------|--------|------------------------------|
| Sem ciclo aberto | `get_open_ciclo()` is None | Sem CTA de avanço; copy FR-001a |
| Vínculo / avaliação pendente | FR-005 `vinculo_pendente` ou sem `Avaliacao` no ciclo | Sem inventar etapa; CTA fraco opcional `dashboard:personal` |
| Ciclo/avaliação concluída para o usuário | avaliação concluída / sem próxima ação | CTA opcional `reviews:detail` |

---

## Out of scope (persistência)

- Qualquer `models.Model` novo
- Alteração de `choices` de `Avaliacao.Etapa`
- Campos cached de “próximo passo” na Avaliacao
- Logs de auditoria de “viu guidance” (não pedido)
