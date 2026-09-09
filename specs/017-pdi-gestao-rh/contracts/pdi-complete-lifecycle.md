# Contract: Lifecycle — concluir PDI

**App**: `pdi`  
**Serviço**: extensão de `apps/pdi/services/lifecycle.py`

## complete_pdi(pdi) → pdi

**Pré-condições**:
- `pdi.status == ativo`
- Existe ≥1 ação e **todas** com `status == concluida`

**Efeito**: `pdi.status = concluido` (persistido).

**Rejeições** (feedback claro na UI):
- Status ≠ ativo (inclui arquivado/concluído)
- Qualquer ação não concluída
- Sem ações (plano vazio não conclui)

## Board grouping

```text
_group_acoes:
  atrasadas  ← status == atrasada
  andamento  ← em_andamento (sem misturar atrasada)
  proximas   ← pendente (ou regra já existente de “próximas”)
  concluidas ← concluida
```

## AuthZ

Mesmo escopo de mutação já usado para ações/arquivo: viewer no escopo do **dono** (`ScopedObjectMixin` / predicados existentes). Sem permissão nova.

## UI

- CTA “Concluir plano” só quando pré-condições verdadeiras.
- Estilo: secundário/outline (contrato visual).
- Após sucesso: PDI aparece no filtro Concluídos do hub.

## Testes

1. 100% concluídas + ativo → `concluido`.
2. 1 pendente → rejeita, status permanece ativo.
3. Arquivado → rejeita.
4. Board lista ação atrasada só na coluna Atrasadas.
