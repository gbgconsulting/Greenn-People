# Contract: Abertura de ciclo com corte “Admitidos até”

**Feature**: `015-cycle-admission-cutoff`  
**Apps**: `cycles`  
**Fonte**: FR-001, FR-002, FR-013, FR-014, FR-019; US1; [research.md](../research.md) R2/R4

---

## Gate sem data

| Condição | Resultado |
|---|---|
| POST Abrir / `open_cycle` **sem** `admitidos_ate` resolvido | `CycleMissingCutoffError` |
| Status do ciclo | **permanece** não-aberto (`encerrado` se era encerrado) |
| Avaliações novas | **zero** |
| UX | `messages.error` visível (texto claro: informe “Admitidos até”) |

Exceção canônica: `apps.cycles.exceptions.CycleMissingCutoffError(CycleError)`.

---

## Gate com data D

| Passo | Comportamento |
|---|---|
| Persistência | `ciclo.admitidos_ate = D` (date calendário) |
| Status | `aberto` |
| Matrícula | somente elegíveis via `ensure_avaliacao_for_user` |
| Um ciclo aberto | regra vigente **intacta** (`CycleAlreadyOpenError`) |
| Reenvio em ciclo já aberto | erro existente; não duplica Avaliações |

`admitidos_ate` é **independente** de `data_inicio` / `data_fim`.

---

## Mensagem de sucesso

**MUST NOT** afirmar matrícula de “todos os ativos” nem equivalente genérico atual:

```text
# VIGENTE (a substituir) — CicloOpenView
'Ciclo "{nome}" aberto. Avaliações criadas para colaboradores ativos.'
```

**MUST** refletir que a matrícula seguiu o critério de elegibilidade do corte  
(ex.: “Avaliacoes criadas conforme elegibilidade (admitidos até …)” e/ou incluir contagem de elegíveis matriculados se barato).

---

## AuthZ

| Ator | Abrir |
|---|---|
| Admin (`is_admin`, `AdminCyclesMixin`) | permitido |
| Líder / colaborador / anônimo | mesma negação vigente (403 / login) |

Sem papel novo. POST sem permissão = mesmo 403 de hoje.

---

## Checklist 008

Permanece **avisório**. Única trava **nova** = ausência de `admitidos_ate`  
(além de “só um aberto” / “já aberto”).

---

## Superfícies

| Path | Papel |
|---|---|
| `CicloOpenView.post` | lê `admitidos_ate` do POST; chama `open_cycle`; mensagens |
| `templates/cycles/ciclo_list*.html` (e/ou form auxiliar) | input date + botão Abrir |
| `apps/cycles/services/cycle.py::open_cycle` | gate + persistência + batch |

---

## Contrato de teste

| ID | Cenário | Esperado |
|---|---|---|
| T-open-1 | Base controlada + D | 1 Avaliacao por elegível; 0 demais |
| T-open-2 | Sem D | erro; status não aberto; 0 Avaliações |
| T-open-3 | Sucesso | mensagem sem “todos os ativos” / “colaboradores ativos” genérico |
| T-open-4 | Já existe aberto | `CycleAlreadyOpenError` intacto |
| T-open-5 | Reabrir mesmo ciclo aberto | erro existente; sem duplicar |
