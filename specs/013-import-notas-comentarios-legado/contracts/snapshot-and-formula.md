# Contract: Snapshots Write-Once e Fórmula de Nota Final

**Feature**: `013-import-notas-comentarios-legado`  
**Fonte**: spec FR-009/FR-010/FR-011; clarifications 2026-08-18 (#2); RF-19.2; RF-15.1  
**Data**: 2026-08-18

---

## 1. Write-once (`AvaliacaoCompetencia.save`)

Campos snapshot: `peso_utilizado`, `nivel_esperado_utilizado`.

O model vigente **já** levanta `ValidationError` se a 2ª `save()` tentar alterá-los. O importador MUST respeitar isso:

| Run | Fonte vs persistido | Ação | Relatório |
|---|---|---|---|
| 1ª | — | Preencher snapshots na create | `notas_criadas` |
| 2ª | iguais | **Não** reatribuir snapshots; pode atualizar `nota_*` | `inalterado` ou `atualizado` (se nota mudou) |
| 2ª | divergem | **Não** reescrever snapshots; **não** apagar a linha; **não** apagar `Avaliacao` 011 | `conflito` `snapshot_divergente` |
| 2ª | `ValidationError` write-once | Capturar; linha permanece | `conflito` (não mascarar como sucesso) |

---

## 2. Fonte de `peso_utilizado`

```text
peso_utilizado ← Decimal(Fator no Momento)
ausente / não-numérico / ≤ 0 → conflito fator_invalido; NÃO persistir a linha
NÃO assumir peso 1
NÃO ler CargoCompetencia.peso
```

---

## 3. Fonte de `nivel_esperado_utilizado`

Dump 2026-06-24 de notas **não possui coluna** de nível (clarification #2).

```text
nivel_esperado_utilizado ← nivel_esperado_for(avaliacao.usuario.cargo.nivel)

tabela 003 (mapping.py, READ-ONLY):
  1→2, 2→2, 3→3, 4→4, 5→4, 6→4

cargo None / nivel ausente / ValueError → skip/conflito nivel_irresolvivel
NUNCA ler CargoCompetencia.nivel_esperado (perfil vigente, mutável)
```

Cargo do **avaliado** (não do avaliador).

---

## 4. PROIBIDO `create_competency_lines`

`apps/reviews/services/evaluation.py::create_competency_lines` copia peso/nível de `CargoCompetencia` **atual**. Isso mentiria o passado (FR-010 / RF-19.2).

Linhas existem **porque o legado trouxe a nota**, não porque o cargo atual lista a competência.

O importador MUST criar `AvaliacaoCompetencia` diretamente via ORM com os snapshots deste contrato.

---

## 5. MUST CALL `calcular_nota_final_*`

Após o upsert das linhas do **grupo** (todas as competências de uma `Avaliacao` no lote):

```text
from apps.reviews.services.evaluation import (
    calcular_nota_final_lider,
    calcular_nota_final_autoavaliacao,
)
from apps.reviews.exceptions import CalculationError

try:
    calcular_nota_final_lider(avaliacao)
except CalculationError:
    report conflito_calculo_lider   # NÃO inventar média

try:
    result = calcular_nota_final_autoavaliacao(avaliacao)
    # None = contrato vigente: nenhuma linha com auto → não inventar
except CalculationError:
    report conflito_calculo_auto
```

As funções vigentes **já persistem** `Avaliacao.nota_final_lider` / `nota_final_autoavaliacao`. O importador não reimplementa `normalize_score` nem a média ponderada.

`CalculationError` conhecido do produto: peso total zero, linha sem `nota_lider`, competência sem escala, amplitude de escala zero.

---

## 6. MUST NOT edit `evaluation.py`

```text
git diff <base> -- apps/reviews/services/evaluation.py
# MUST be empty
```

Chamar não é editar. Teste de ouro FR-021 inclui este path na denylist.

---

## 7. Demais módulos de cálculo / estado intocáveis

- `apps/cycles/services/stage.py`
- `apps/cycles/services/cycle.py` (`open_cycle` / `close_cycle`)
- `apps/goals/services/approval.py`
- `apps/dashboard/services/adherence.py`
- `Avaliacao.etapa` / `Avaliacao.concluida` (011)

---

## 8. Invariantes de teste

1. 1ª save preenche peso do Fator e nível da tabela 003.
2. 2ª run: snapshots **bit-a-bit** estáveis (SC-005).
3. Fixture com `CargoCompetencia` vigente **divergente** do Fator/tabela 003 → linha histórica **não** copia o vigente.
4. `create_competency_lines` **não** é chamado (spy/mock assert).
5. `evaluation.py` diff vazio; `calcular_nota_final_lider` **é** chamado quando há linhas com líder.
6. `CalculationError` → conflito; `nota_final_*` não inventada.
