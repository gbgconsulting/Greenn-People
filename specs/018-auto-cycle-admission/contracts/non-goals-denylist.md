# Contract: Non-goals / denylist (018)

**Refs**: FR-019, FR-020; Clarifications 2026-09-09

## Proibido nesta feature

| Item | Motivo |
|---|---|
| Opção B (lote único sem ritmo por admissão) | Decisão fechada |
| Recuperar marcos atrasados / backfill de ciclos passados | Bootstrap essencial |
| Feriados estaduais/municipais | Escopo nacional |
| Matrícula de inativo / sem `data_entrada` | FR-003/004 |
| Bloquear lote por alerta de ciclo aberto | FR-007 |
| Papel RH novo / `is_rh` | FR-019; RH = `is_admin` |
| DRF / SPA / app Django nova | Constituição I/IV |
| Lib externa de feriados (nesta fatia) | Princípio I — módulo puro |
| Segunda identidade visual do automático | Diretrizes + contrato UI |
| Alterar machine de etapas / fórmulas / 9-box / PDI / hierarquia | FR-019 |
| Apagar Avaliação por mudança de `data_entrada` | FR-017 / Princípio III |
| Reprocessar ciclos encerrados | FR-018 |
| Processar lote do mês só porque RH abriu a tela | FR-021 / Princípio VI |
| Manter “só um aberto” | FR-010 (quebra deliberada) |

## Diff vazio de comportamento esperado (salvo multi-open necessário)

Paths que **não** devem mudar regra de negócio além do estritamente necessário à coexistência de N abertos / chamadas com `ciclo=` explícito:

- `apps/cycles/services/stage.py`
- `apps/goals/services/approval.py`
- `apps/reviews/services/evaluation.py` (exceto resolução de ciclo ambíguo)
- `apps/dashboard/services/adherence.py` (já multi-open-aware no daily)
- `apps/accounts/services/scope.py`
- `apps/talent/`
- `apps/pdi/` (exceto se consumir `get_open_ciclo` — ajustar só honestidade multi-open)

## Allowlist de mudança multi-open

Documentada em [multi-open-ciclo-contract.md](./multi-open-ciclo-contract.md). Qualquer consumidor de `get_open_ciclo()` deve ser revisado na implementação (tasks.md).

## Smoke checklist (T031)

| Item | Status | Evidência |
|---|---|---|
| Stage / `can_advance` intactos | ✅ | `test_denylist_stage_surface_intacta` |
| Approval / fórmulas metas | ✅ | `test_denylist_approval_surface_intacta` |
| Escopo hierárquico | ✅ | `test_denylist_scope_hierarquico_intacta` |
| 9-box limiares 0.33/0.66 | ✅ | `test_denylist_talent_formulas_limiares_intactos` |
| PDI app; sem app nova / DRF | ✅ | `test_denylist_pdi_app_presente_sem_papel_novo` |
| Sem `is_rh` (RH = `is_admin`) | ✅ | `test_denylist_sem_papel_rh_is_rh` |
| Sem lib feriados / DRF em deps | ✅ | `test_denylist_sem_lib_feriados_nem_drf` |
| Feriado municipal fora | ✅ | `test_denylist_feriado_municipal_fora_do_calendario` |
| Opção A (não B) | ✅ | `test_denylist_opcao_a_ritmo_admissao_nao_opcao_b` |
| Zero backfill de marcos | ✅ | `test_denylist_bootstrap_nao_recupera_marco_passado` |
| HTTP governança só lê | ✅ | `test_denylist_governanca_http_somente_leitura` |
| Paths denylist existem | ✅ | `test_denylist_paths_contrato_existem` |
| Inativo / sem `data_entrada` fora | ✅ | `test_denylist_inativo_e_sem_data_fora_do_automatico` |

Suite: `tests/test_auto_denylist_smoke.py` — **13 passed**.
