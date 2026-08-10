# Contract: Checklist RH pré-abertura (somente avisório)

**Feature**: `008-cycle-guidance-ux`  
**Fonte**: [spec.md](../spec.md) FR-011, FR-012, SC-002  
**Tipo**: Superfície informativa — **não** é gate de abertura.

---

## Declaração

O checklist operacional de RH:

1. **Lista** bloqueadores conhecidos com links de correção  
2. **NÃO** desabilita, soft-disable, esconde ou altera a política do controle **Abrir**  
3. Abertura continua 100% pela regra **já existente** (`CicloOpenView` / `open_cycle`)

Se a regra vigente **permite** abrir com pendências, isso permanece — blockers ficam evidentes para decisão consciente.

Qualquer proposta de trava nova = **fora de escopo** ([non-goals-denylist.md](./non-goals-denylist.md)).

---

## Bloqueadores (escopo deste contrato)

| kind | Condição (leitura) | Correção (URL existente) |
|------|--------------------|---------------------------|
| `user_missing_area_cargo` | Usuários ativos sem área e/ou cargo | Superfície `organization:user_pending` (ou equivalente já existente) |
| `cargo_missing_competencies` | Cargos ativos sem competências/pesos configurados | Fluxo de cadastro de cargo/competências **já existente** |

Não amplia para import em massa, novos cadastros, ou validators de abertura.

---

## Superfícies

| Path | Papel |
|------|-------|
| `templates/cycles/ciclo_list.html` (+ partial) | Checklist próximo ao fluxo/lista de ciclos |
| `templates/organization/user_pending*.html` | Já lista pending de vínculo; pode reforçar link no checklist |

---

## Aceite

| Cenário | Esperado |
|---------|----------|
| Com blockers | Lista escaneável + links |
| Sem blockers | Mensagem clara de ausência de pendências nesse escopo |
| POST Abrir | Mesmo resultado que antes da feature (teste de regressão / comparação manual) |

---

## Proibições no código

- Alterar assinatura/comportamento de `open_cycle`
- Condicionar `CicloOpenView` ao checklist
- Migration “ciclo.require_clean_catalog”
- Mensagem que afirme que abrir está “bloqueado pelo sistema” se a regra ainda permite
