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
