# Contract: Superfície de governança RH (automático)

**Refs**: FR-015, FR-016, FR-022; US4; [ui-visual-consistency.md](./ui-visual-consistency.md); [backend-scope-authz.md](./backend-scope-authz.md)

## Objetivo

Em ≤5 minutos (SC-007) / idealmente <3s de escaneamento visual, admin responde:

1. Quem **entrou** no lote do período?
2. Quem ficou de fora por **falta de admissão**?
3. Quem gerou **alerta de ciclo ainda aberto**?
4. Houve **falha** operacional da rotina?

## AuthZ

- Somente `is_admin` (`RequiresAdminMixin`).
- Líder/colaborador: 403 / sem link na nav.

## Dados mínimos (backend)

| Bloco | Fonte | Semântica visual |
|---|---|---|
| KPIs do período | agregações `AutoCycleRun` / events | emerald sucesso; amber alertas/pendências; rose falhas/atraso 20d |
| Entrantes | events `matricula` (+ join user) | lista/tabela |
| Sem admissão | contagem/ativos sem `data_entrada` (+ event) | amber pendência cadastro |
| Alertas ciclo aberto | events `alerta_ciclo_aberto` | amber atenção |
| Falhas | events `falha` / run status | rose |
| Runs | `AutoCycleRun` | histórico operacional |

## UX

- Shell Ciclos; ver contrato visual.
- Um CTA primário soberano na viewport.
- Empty states guiados.
- Copy RH (FR-022): sem jargão de Celery/stack na UI principal.

## Fora de escopo da superfície

- Analytics de desempenho / ninebox.
- Edição em massa de `data_entrada` (usa cadastro usuários existente).
- Disparo HTTP como substituto do Beat (reprocesso idempotente admin, se existir, é secundário e AuthZ-bound).
