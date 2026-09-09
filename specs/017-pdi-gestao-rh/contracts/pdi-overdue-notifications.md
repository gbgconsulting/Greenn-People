# Contract: Notificações de atraso PDI + digest RH

**Apps**: `notifications`, `pdi`  
**Base**: estende [reminders-pdi-contract](../../002-pos-mvp-hardening/contracts/reminders-pdi-contract.md) sem alterar `lembrete_pdi`.

## Tipos e chaves

| Tipo | `referencia` | `janela` | Quando |
|---|---|---|---|
| `atraso_pdi` | `acao_pdi:{id}` | data ISO do evento de marcação | ação passa a `atrasada` |
| `digest_pdi_atrasos` | `org:pdi_atrasos` | `YYYY-Www` (semana ISO) | Beat semanal |

`lembrete_pdi` permanece preventivo (prazo = hoje+N) só para o dono.

## Fluxo atraso pontual

```text
mark_overdue_pdi_actions
  → para cada ação recém-marcada atrasada (ou elegível na passagem):
       destinatários = {dono} ∪ {line_manager(dono) se ativo e ≠ dono}
       para cada dest:
         if already_sent(...): skip
         if não elegível (arquivado/concluída/user inativo): skip
         send email + NotificacaoLog enviado|falha
```

Reprocessamento no mesmo dia com mesmo `(dest, tipo, ref, janela)` → 0 reenvios.

## Fluxo digest

```text
se count(ações atrasadas em PDI não arquivado) == 0: exit (silêncio)
senão: para cada admin ativo:
  if already_sent(semana): skip
  send resumo (totais + top áreas/gestores) + CTA listagem filtrada
```

## Conteúdo mínimo

**Atraso pontual**: identificação da ação/PDI, prazo, link para detalhe do PDI.  
**Digest**: nº PDIs com atraso, nº ações atrasadas, top focos, link `/pdi/?visao=equipe&atrasadas=1` (modo tabela opcional no CTA).

## Testes de contrato

1. Marcação atrasada → 1 e-mail dono + 1 gestor (se houver); 2ª run mesmo dia → 0.
2. Sem gestor → só dono; sem falha.
3. PDI arquivado → 0 e-mails atraso.
4. Digest com atrasos → 1 por admin/semana; sem atrasos → 0.
5. Não-admin não recebe digest.
6. `lembrete_pdi` preventivo continua independente (não confundir tipos).
