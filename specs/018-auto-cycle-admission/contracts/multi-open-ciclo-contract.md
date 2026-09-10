# Contract: Múltiplos ciclos abertos (quebra deliberada 015)

**Refs**: FR-010, FR-011, FR-019; Assumptions do spec; [research.md](../research.md) R7

## Mudança de regra

| Antes (015) | Depois (018) |
|---|---|
| No máximo um `Ciclo` com `status=aberto` | **N** ciclos `aberto` permitidos |
| `CycleAlreadyOpenError` ao abrir segundo | **Não** bloquear abertura por existência de outro aberto |
| Copy UI “Só um ciclo…” | Copy honesta de convivência |
| `get_open_ciclo()` = o único | = **default** (mais recente por `-data_inicio`) entre abertos |
| `grouped_ciclo_options.operacional` ≤ 1 | = **lista completa** de abertos |

## MUST alterar

1. `Ciclo._validate_single_open` — remover da validação de save/clean.
2. `open_cycle` — remover check que levanta `CycleAlreadyOpenError` por “outro aberto” (manter proteção de reabrir o mesmo se aplicável).
3. Templates de ciclos — copy + badges de origem.
4. `get_open_ciclos()` novo helper canônico.
5. Context processor / topbar badge / `_ciclo_selector` — refletir N abertos.
6. `ensure_avaliacao_for_user` sem `ciclo=` — **não** criar Avaliação “no aberto errado”; caminhos de escrita passam `ciclo` explícito (auto sempre; mid-cycle organization alinhado).
7. Testes 015 que assertam `CycleAlreadyOpenError` por segundo aberto — atualizar para nova regra (manual + auto convivendo = SC-009).

## MUST NOT

- Inventar status novo (`pausado`, etc.) nesta feature.
- Fechar automaticamente o ciclo anterior para “abrir espaço”.
- Fazer alerta FR-008 virar bloqueio global de `open_cycle` manual.
- Mentir no UI que só existe um vigente quando N>1.

## Default operacional (convenção)

```text
get_open_ciclos() = Ciclo.objects.filter(status=aberto).order_by('-data_inicio', 'nome')
get_open_ciclo()  = first(get_open_ciclos()) or None
```

Dashboards que precisam de um único ciclo para chart usam o default **ou** `?ciclo=` explícito (padrão 012). Documentar empty `operacional` se zero abertos — sem fallback silencioso para encerrado.

## Regressão mínima

- Abrir manual com auto aberto → sucesso (com corte 015).
- Abrir segunda coorte em mês seguinte com anterior ainda aberto → sucesso.
- Seletor lista ambos.
- Enrollment auto usa FK do ciclo da coorte.
- Aderência daily continua iterando todos os abertos.
