# Contract: Lembretes deduplicados e PDI (atraso)

**Apps**: `notifications`, `pdi`, `audit`

## Dedupe de lembretes

```python
# NotificacaoLog — chave lógica
# (destinatario_id, tipo, referencia, janela)

def already_sent(destinatario, tipo, referencia: str, janela: str) -> bool:
    return NotificacaoLog.objects.filter(
        destinatario=destinatario,
        tipo=tipo,
        referencia=referencia,
        janela=janela,
        status=NotificacaoLog.Status.ENVIADO,
    ).exists()
```

| Tipo | `referencia` sugerida | `janela` |
|---|---|---|
| `lembrete_etapa` | `avaliacao:{id}` ou `ciclo:{id}:user:{id}` | data alvo ISO do disparo |
| `lembrete_pdi` | `acao_pdi:{id}` | data alvo ISO |

**Task**: se `already_sent` → skip; se elegibilidade do pendente cessou → skip; após envio bem-sucedido → criar log `enviado`; falha → log `falha` (permite retry).

## Recálculo de atraso PDI

```python
# ao alterar AcaoPDI.prazo
def recalculate_overdue_status(acao: AcaoPDI, today: date) -> None:
    if acao.status == AcaoPDI.Status.ATRASADA and acao.prazo >= today:
        acao.status = AcaoPDI.Status.PENDENTE
    elif acao.prazo < today and acao.status in (PENDENTE, EM_ANDAMENTO):
        # opcional no save; job diário cobre — mínimo da spec: extensão futura limpa atraso
        pass
```

**Auditoria**: track `prazo` e `status` → AuditLog com antigo/novo.

## Contratos de teste

- Job de lembrete 2× no mesmo dia/chave → 1 e-mail / 1 log `enviado`.
- Pendente resolvido antes do job → 0 envios.
- `atrasada` + prazo futuro → status não-atrasado + audit de prazo/status.
- Prazo ainda passado → permanece atrasada.
