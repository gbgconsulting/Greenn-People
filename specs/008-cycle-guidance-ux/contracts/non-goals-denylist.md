# Contract: Non-Goals / Denylist de lógica (FR-013)

**Feature**: `008-cycle-guidance-ux`  
**Fonte**: [spec.md](../spec.md) FR-013 + invariante do plano  
**Uso**: Qualquer PR/task que viole este contrato = **fora de escopo** / rejeitar.

**Status T001 (2026-08-07)**: ✅ Confirmado — denylist de domínio espelha FR-013 / plan; paths sob vigilância existem no repo e permanecem intocáveis em comportamento. Permitido apenas UI + context/serviço de leitura (ver [path-allowlist.md](./path-allowlist.md)).

---

## Declaração

Esta feature é **SOMENTE** apresentação/orientação (guidance UX).

**Teste de ouro**: desligar CSS e/ou o bloco de guidance **não** deve mudar nenhum resultado de negócio (avanço, aprovação, nota, AuthZ, abertura de ciclo).

---

## Denylist (PROIBIDO)

| Zona | Proibição explícita |
|------|---------------------|
| Regras de negócio / domínio | Alterar ou “aperfeiçoar” lógica porque “UX pede” |
| Máquina de estados | `can_advance`, `advance_stage`, ordem de etapas, bloqueio de avanço |
| Aprovação / reprovação | `approve_*` / `reject_*`, reabertura, mid-cycle, offboarding |
| Fórmulas | `nota_final`, normalização, aderência, 9-box, desempenho/potencial |
| AuthZ / escopo | Alterar `get_visible_users`, `ScopedObjectMixin`, permissões, “quem pode” |
| Persistência de regra | Models, migrations, campos novos que guardem regra/etapa/hint obrigatório |
| URLs / contratos de domínio | Novas rotas de negócio ou mudança de contrato de endpoints existentes |
| Semântica de fluxo | Feedback/ciente, status PDI, política de abertura de ciclo |
| Navegação IA | Reorganizar/renomear grupos Governança / Cadastros / Sistema |
| Auth surfaces | Redesign login / `base_auth` |

### Paths de código sob vigilância (não modificar comportamento)

- `apps/cycles/services/stage.py`
- `apps/cycles/services/cycle.py` (`open_cycle` comportamento)
- `apps/goals/services/approval.py`
- `apps/accounts/services/scope.py` (alteração)
- Cálculos mutadores em `apps/reviews/services/evaluation.py` (`calcular_nota_*`, etc.)
- `apps/*/models.py`, `**/migrations/**`
- `apps/*/urls.py` — **nenhuma** URL de domínio nova

---

## Allowlist funcional (PERMITIDO)

| Tipo | Exemplos |
|------|----------|
| Copy / hierarquia visual | CTA primário vs secundário; linguagem humana |
| Stepper / badges | Contagem visual; estados de UI do stepper |
| Serviço de LEITURA | `apps/reviews/services/guidance.py` (+ pending count read-only) |
| Context builders | `get_context_data` nas views existentes |
| Templates / components | `next_step.html`, `stage_stepper.html`, ajustes de detalhe |
| CSS mínimo | Classes do stepper em `input.css` se necessário |
| Contagens | Reuso de queries/predicados de elegibilidade **já vigentes** |

---

## Regra de rejeição

Se a solução proposta:

1. Exige mudar predicado de elegibilidade, ou  
2. Exige trava nova de abertura, ou  
3. Exige migration / campo novo de regra, ou  
4. Muda resultado de teste de stage/scope,

→ **REJEITAR**. Documentar no PR/task: “fora de escopo 008 / FR-013”.
