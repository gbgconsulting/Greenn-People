# Contract: Máquina de Estados do Ciclo

**Apps**: `cycles` (transições), `reviews` (model `Avaliacao`), `goals` (model `Meta`)

## Interface de serviço

```python
# apps/cycles/services/stage.py

ETAPAS = (
    'input_metas',
    'aprovacao_metas',
    'resultados',
    'aprovacao_resultados',
    'avaliacao',
    'feedback',
)

def can_advance(avaliacao: Avaliacao) -> tuple[bool, str]:
    """Retorna (ok, motivo) para avançar etapa."""

def advance_stage(avaliacao: Avaliacao, actor: CustomUser) -> Avaliacao:
    """Avança etapa se pré-condições satisfeitas; levanta StageTransitionError."""

def is_cycle_closed(avaliacao: Avaliacao) -> bool:
    """True se ciclo.status == 'encerrado'."""
```

## Pré-condições por transição

| De | Para | Pré-condição |
|---|---|---|
| `input_metas` | `aprovacao_metas` | ≥1 meta criada pelo colaborador |
| `aprovacao_metas` | `resultados` | ≥1 meta E 100% com `status=aprovada` |
| `resultados` | `aprovacao_resultados` | Todas metas aprovadas têm `progresso` registrado |
| `aprovacao_resultados` | `avaliacao` | 100% com `status_resultado=aprovado` |
| `avaliacao` | `feedback` | Autoavaliação completa em todas as linhas; todas `AvaliacaoCompetencia` com `nota_lider`; `nota_final_lider` calculada |
| `feedback` | (concluída) | Feedback líder registrado; `ciente_em` preenchido |

## Regras invariantes

1. **Nunca retroceder** `etapa` por reprovação de meta/resultado individual.
2. Reprovação altera apenas `Meta.status` ou `Meta.status_resultado` para `pendente`.
3. Ciclo encerrado → `advance_stage` levanta `CycleClosedError`.
4. Zero metas **não** satisfaz avanço de `aprovacao_metas` → `resultados`.
5. Bloqueio para `avaliacao`: cargo deve ter ≥1 `CargoCompetencia` com Σpeso > 0.

## Side effects na transição para `avaliacao`

```python
# apps/reviews/services/evaluation.py
create_competency_lines(avaliacao)  # copia snapshots write-once
```

## Aprovação de metas/resultados

```python
# apps/goals/services/approval.py

def approve_meta(meta: Meta, approver: CustomUser) -> Meta: ...
def reject_meta(meta: Meta, approver: CustomUser) -> Meta:
    # status → reprovada; depois → pendente (reabertura)
```

**Aprovador válido**: `line_manager` do colaborador OU `is_admin` se `line_manager` nulo.

## Eventos de auditoria

Toda transição de `etapa` gera `AuditLog` com `campo='etapa'`, valor anterior/novo.
