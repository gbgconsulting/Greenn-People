# Contract: Cálculos de Nota e 9-Box

**Apps**: `reviews`, `competencies`, `talent`

## Nota final do líder

```python
# apps/reviews/services/evaluation.py

def normalize_score(nota: Decimal, escala: Escala) -> Decimal:
    """(nota - valor_minimo) / (valor_maximo - valor_minimo)"""

def calcular_nota_final_lider(avaliacao: Avaliacao) -> Decimal:
    """
    nota_final = Σ(normalize(nota_lider) × peso_utilizado) / Σ(peso_utilizado)
    Usa APENAS peso_utilizado (snapshot), nunca CargoCompetencia.peso atual.
    Levanta CalculationError se Σpeso_utilizado == 0.
    """
```

### Entradas

| Campo | Origem |
|---|---|
| `nota_lider` | `AvaliacaoCompetencia` |
| `peso_utilizado` | Snapshot write-once |
| `valor_minimo/maximo` | `Competencia.escala` |

### Saída

- Persistida em `Avaliacao.nota_final_lider`
- Idempotente: recalcular com mesmos inputs → mesmo resultado (SC-004)

## Nota final autoavaliação (referência)

```python
def calcular_nota_final_autoavaliacao(avaliacao: Avaliacao) -> Decimal | None:
    """Mesma fórmula usando nota_autoavaliacao; opcional."""
```

## Classificação 9-box

```python
# apps/talent/services/classification.py

def derive_desempenho(nota_final_lider: Decimal) -> int:
    """
    nota_normalizada 0-1 a partir de nota_final_lider
    < 0.33 → 1 (baixo)
    0.33–0.66 → 2 (médio)
    > 0.66 → 3 (alto)
    """

def calculate_quadrante(desempenho: int, potencial: int) -> str:
    """Retorna um dos 9 quadrantes: baixo_baixo, baixo_medio, ... alto_alto."""

def upsert_classification(usuario, ciclo, potencial: int, admin: CustomUser) -> ClassificacaoTalento:
    """potencial manual (1-3); desempenho e quadrante derivados."""
```

### Tabela de quadrantes

| desempenho ↓ / potencial → | 1 | 2 | 3 |
|---|---|---|---|
| 1 | baixo_baixo | baixo_medio | baixo_alto |
| 2 | medio_baixo | medio_medio | medio_alto |
| 3 | alto_baixo | alto_medio | alto_alto |

## Aderência de liderança (assíncrono)

```python
# apps/dashboard/tasks.py

@shared_task
def calculate_adherence_snapshot(lider_id: int, ciclo_id: int) -> None:
    """
    Calcula percentual de ações no prazo do líder.
    Atribui cada ação ao autor real (AuditLog/autor_id), NÃO ao line_manager atual.
    Persiste em AderenciaSnapshot.
    """
```

**Trigger**: abertura de ciclo, encerramento de etapa relevante, schedule diário Celery Beat.

## Progresso PDI

```python
# apps/pdi/services/progress.py

def calculate_pdi_progress(pdi: PDI) -> Decimal:
    """% ações com status=concluida sobre total."""
```
