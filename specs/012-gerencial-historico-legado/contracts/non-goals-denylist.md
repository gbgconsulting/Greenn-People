# Contract: Non-Goals / Denylist de lógica (FR-018)

**Feature**: `012-gerencial-historico-legado`  
**Fonte**: [spec.md](../spec.md) FR-018 + invariante do plano  
**Uso**: Qualquer PR/task que viole este contrato = **fora de escopo** / rejeitar.

### Confirmação T001 (2026-08-14)

- [x] Denylist inclui explicitamente: `apps/cycles/services/stage.py`, `apps/cycles/services/cycle.py`, `apps/dashboard/services/adherence.py` (`compute_adherence` / fórmula), `apps/accounts/services/scope.py`
- [x] Teste de ouro ratificado: desligar CSS/charts/toggle **não** muda etapa, aprovação, notas, visible, open/close nem snapshots
- [x] Permitido permanece leitura/apresentação + `visao=historico` nas URLs já existentes (sem rota nova)
- [x] Espelho de paths sob vigilância alinhado à allowlist e ao “Escopo inválido” de `tasks.md`

---

## Declaração

Esta feature é **apresentação gerencial + composição leve de dados já autorizados** (default operacional, densidade, empty honesto, modo histórico de etapa/conclusão).

**Teste de ouro**: desligar CSS/charts/toggle **não** deve mudar avanço de etapa, aprovação, notas, conjunto de usuários visíveis, política de abrir/fechar ciclo, nem snapshots.

---

## Denylist (PROIBIDO)

| Zona | Proibição explícita |
|------|---------------------|
| Máquina de estados | `apps/cycles/services/stage.py` — `can_advance`, `advance_stage`, ordem/semântica |
| Abrir / fechar ciclo | `apps/cycles/services/cycle.py` (`open_cycle` / `close_cycle`); views open/close |
| Aprovação | `apps/goals/services/approval.py` |
| Avaliação / fórmulas de nota | Mutators em `apps/reviews/services/evaluation.py`; `nota_final_lider`; 6.5.5 notas/comentários |
| Aderência (fórmula) | `apps/dashboard/services/adherence.py` (`compute_adherence`); nova task Celery de % |
| AuthZ / escopo | `apps/accounts/services/scope.py`; `get_visible_users`; `ScopedObjectMixin` |
| Snapshots write-once | Mutar `peso_utilizado` / `nivel_esperado_utilizado` / política append-only |
| Schema de nota | Models/migrations de nota, competência avaliada, PDI |
| PDI / 9-box | Apps `pdi` / drag 9-box / classificação |
| Métricas inventadas | Saúde do ciclo, nota final temporal, média de % como score novo |
| Stack | SPA, DRF, lib nova de gráfico, Chart ≠ 4.5.1, plugin npm |
| Rotas | Página/seção dedicada de “histórico / evolução” |
| Shell / auth | Reabrir nav IA, login, Freeze A/B/C de paleta/shell |
| Fixtures | `data/legado-solides/raw/` no CI |

### Paths sob vigilância (diff de comportamento = falha)

- `apps/cycles/services/stage.py`
- `apps/cycles/services/cycle.py`
- `apps/goals/services/approval.py`
- `apps/accounts/services/scope.py`
- Mutators em `apps/reviews/services/evaluation.py`
- `apps/dashboard/services/adherence.py` (fórmula / `compute_adherence`)
- `apps/dashboard/tasks.py` (salvo evidência de peso documentada)
- `apps/pdi/**`
- Migrations novas de domínio / nota

---

## Permitido (leitura / apresentação)

- Context de views dashboard/ciclo: default aberto, empty, `?ciclo=`, `?visao=historico`
- Helpers em `chart_payloads.py` (Top-N + Outros) e builder de tendência de etapa (recebe `visible`)
- `structure.py` só para aplicar densidade na cobertura já composta (receber `visible`)
- Templates/partials de dashboard e ciclo (lista/detalhe) + `_chart_block` + `dashboard_charts.js` (leveza; sem lib nova)
- Seletor agrupado / copy de KPI / empty_state
- `docs/design-system.md` + `static/src/input.css` se o Freeze D exigir token
- Testes de superfície + regressão stage/scope/reject **sem** mudar regras de domínio
