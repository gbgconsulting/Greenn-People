# Contract: Fluxo pós-reprovação (FR-026 completo)

**Apps**: `goals`, `cycles`, `reviews`  
**Corrige**: wording do [stage-machine-contract da 001](../../001-gestao-desempenho-talentos/contracts/stage-machine-contract.md) (reprovação **não** zera imediatamente para `pendente`).

## Serviços

```python
# apps/goals/services/approval.py
def reject_meta(meta, approver) -> Meta:
    """status → reprovada. NÃO altera Avaliacao.etapa. NÃO chama reopen()."""

def reject_resultado(meta, approver) -> Meta:
    """status_resultado → reprovado. NÃO altera Avaliacao.etapa."""

# apps/goals/models.py (já existentes — passar a ser usados)
Meta.reopen()            # reprovada → pendente
Meta.reopen_resultado()  # reprovado → pendente
```

## Elegibilidade de correção (UI + forms)

| Item | Condição para editar/corrigir | Ao salvar correção |
|---|---|---|
| Meta | `status=reprovada` e etapa `aprovacao_metas` (e permissão colaborador/dono) | `reopen()` + persistir conteúdo |
| Resultado | `status_resultado=reprovado` e etapa `aprovacao_resultados` | permitir update de progresso; `reopen_resultado()` |

Itens `aprovada`/`aprovado` na mesma etapa **não** reabrem.

## Invariantes

1. `reject_*` e `reopen*` **nunca** chamam `advance_stage` nem decrementam etapa.
2. `can_advance` / avanço só quando 100% dos itens da etapa estão aprovados e há ≥1 meta (regra canônica).
3. Ciclo `encerrado`: rejeitar correções e aprovações.
4. Tela da Avaliação DEVE expor próximo passo acionável (corrigir / reenviar / reaprovar) — sem dead-end.

## Contratos de teste

- Reprovar 1 de N metas → etapa permanece; N−1 aprovadas intactas; a reprovada voltável a pendente via correção.
- Resultado reprovado → colaborador atualiza progresso → status_resultado pendente → gestor reaprova.
- Após todas aprovadas → `advance_stage` sucede.
