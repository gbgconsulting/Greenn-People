# Contract: Preview de contagens do corte

**Feature**: `015-cycle-admission-cutoff`  
**Apps**: `cycles`  
**Fonte**: FR-011, FR-012, US2; [research.md](../research.md) R5  
**Constituição**: II (AuthZ no backend; sem vazar PII)

---

## Contagens (exatamente 3)

Dado `admitidos_ate = D` (date):

| Chave | Definição (somente `is_active=True`) |
|---|---|
| `elegiveis` | `data_entrada IS NOT NULL` ∧ `data_entrada ≤ D` |
| `excluidos_admissao_posterior` | `data_entrada IS NOT NULL` ∧ `data_entrada > D` |
| `sem_data_entrada` | `data_entrada IS NULL` |

Inativos **não** entram nas três contagens.

Implementação: agregações ORM no serviço (`preview_admission_counts(D)`), **não** loop no template que renderize pessoas.

---

## AuthZ

| Ator | Preview |
|---|---|
| Admin de ciclos (`AdminCyclesMixin` / `RequiresAdminMixin`) | OK |
| Líder | **403** (mesmo gate) |
| Colaborador | **403** |
| Anônimo | redirect login |
| Rota pública sem auth | **PROIBIDO** |

Preview e gravação/abertura compartilham o **mesmo** gate. Sem papel novo.

---

## Proibições de payload

- MUST NOT expor lista nominativa de exclusões (nomes, e-mails, IDs, PKs de user).
- MUST NOT retornar JSON autenticado via DRF.
- Partial HTMX / HTML com **números** + labels apenas.

---

## UX

- Informativo; **não** exige confirmação em duas etapas além do POST Abrir já existente.
- Preferência: HTMX parcial ao informar/alterar a data no fluxo de abertura.
- Se D ausente: UI indica que o preview precisa da data (sem inventar contagens).

---

## Superfícies sugeridas

| Item | Notas |
|---|---|
| View | Ex. `CicloOpenPreviewView(AdminCyclesMixin, …)` GET/POST HTMX |
| URL | Sob namespace `cycles:`; **não** pública |
| Template partial | 3 números; sem tabela de usuários |
| Serviço | `apps/cycles/services/eligibility.py` (ou `preview.py`) |

---

## Contrato de teste

| Cenário | Esperado |
|---|---|
| Admin + base conhecida + D | 3 contagens batem com a regra |
| Líder GET/POST preview | 403 |
| Colaborador | 403 |
| Resposta HTML | sem e-mails/nomes de excluídos |
| Após preview, POST Abrir | sem step extra obrigatório |
