# Contract: Path allowlist / denylist

**Feature**: `008-cycle-guidance-ux`  
**Fonte**: [plan.md](../plan.md) + [non-goals-denylist.md](./non-goals-denylist.md)  
**Uso**: Antes de editar qualquer arquivo, confirmar path na **allowlist**. Diff em path da **denylist** (comportamento de domínio) = falha de aceite.

**Status T001 (2026-08-07)**: ✅ Confirmado contra o monólito — UI + context read-only apenas; denylist de domínio intocável. Paths existentes conferidos no repo; paths **Novo** são scaffold desta feature. Alinhado a [non-goals-denylist.md](./non-goals-denylist.md) e à seção Source Code do [plan.md](../plan.md).

---

## Allowlist (permitido)

### Serviço de leitura

| Path | Notas |
|------|-------|
| `apps/reviews/services/guidance.py` | **Novo** — mapa etapa→orientação; stepper DTO; helpers read-only |
| `apps/reviews/services/pending_counts.py` | Opcional — se separado do guidance; só contagem |
| `apps/core/context_processors.py` | Expor badge/total líder (leitura); sem AuthZ nova |

### Views — só context / apresentação

| Path | Notas |
|------|-------|
| `apps/dashboard/views.py` | `PersonalDashboardView` (+ team se preciso) — context guidance |
| `apps/reviews/views.py` | Detail / self / leader / feedback — context, progress UI flags |
| `apps/goals/views.py` | Alinhar hint FR-007 **sem** mudar predicados de approval |
| `apps/cycles/views.py` | Context checklist avisório na listagem |
| `apps/organization/views.py` | Context/links na superfície pending (se US4) |

### Templates / components

| Path | Notas |
|------|-------|
| `templates/components/next_step.html` | **Novo** |
| `templates/components/stage_stepper.html` | **Novo** |
| `templates/components/nav_link.html` | Slot `badge_count` (apresentação) |
| `templates/components/nav_menu.html` | Exibir badge; **proibido** reordenar/renomear grupos IA |
| `templates/dashboard/personal.html` | US1 |
| `templates/reviews/avaliacao_detail.html` | US1/US2 hub CTA |
| `templates/reviews/self_assessment.html` | US3 |
| `templates/reviews/leader_assessment.html` | US3 |
| `templates/reviews/feedback_list.html` | US3 |
| `templates/reviews/feedback_list_partial.html` | US3 |
| `templates/reviews/feedback_form.html` | US3 |
| `templates/goals/meta_list.html` | FR-007 coerência (se necessário) |
| `templates/goals/meta_list_partial.html` | idem |
| `templates/goals/partials/meta_row.html` | idem |
| `templates/cycles/ciclo_list.html` | US4 |
| `templates/cycles/ciclo_list_partial.html` | US4 |
| `templates/organization/user_pending_list.html` | US4 — confirmado no repo |
| `templates/organization/user_pending_list_partial.html` | US4 — confirmado no repo |

### CSS

| Path | Notas |
|------|-------|
| `static/src/input.css` | **Somente** classes mínimas do stepper |
| `static/css/tailwind.css` | Via rebuild CLI |

### Tests

| Path | Notas |
|------|-------|
| `tests/test_guidance_mapping.py` | **Novo** — mapa etapa→ação |
| `tests/test_leader_pending_count.py` | **Novo** — soma pendências |
| Outros `tests/test_*.py` | **Somente** garantir PASS; sem mudar asserts de negócio salvo bugfix puro de apresentação |

### Artefatos da feature

Tudo sob `specs/008-cycle-guidance-ux/` — docs da feature.

---

## Denylist (proibido — comportamento / domínio)

| Path / padrão | Motivo |
|---------------|--------|
| `apps/*/models.py` | Schema / regra persistida |
| `**/migrations/**` | Schema |
| `apps/*/urls.py` | URLs de domínio novas / contrato |
| `apps/cycles/services/stage.py` | Máquina de estados |
| `apps/cycles/services/cycle.py` | Abertura/fechamento — comportamento |
| `apps/goals/services/approval.py` | Aprovação |
| `apps/accounts/services/scope.py` | Alterar AuthZ/escopo |
| Mutators / fórmulas em `apps/reviews/services/evaluation.py` | Cálculo |
| `templates/accounts/**` | Login / auth polish |
| Redesign IA em `nav_menu.html` (grupos/ordem labels Governança/Cadastros/Sistema) | FR-013 |
| Novas libs front / Chart / SPA | Stack |

### Zona cinza (permitido só com cuidado)

| Path | Regra |
|------|-------|
| `apps/reviews/forms.py` | **Não** alterar `feedback_create_allowed` / `can_acknowledge_feedback` predicados; só se view precisar de helper de **contagem** que **chama** os existentes |
| `apps/goals/forms.py` | **Não** alterar `meta_approval_actionable` / `is_meta_approver`; reutilizar |

---

## Checklist de revisão de diff

- [x] Nenhum arquivo em denylist de comportamento
  - Confirmado T038 (2026-08-08): `git diff development...WORKDIR` vazio em `stage.py` / `cycle.py` / `approval.py` / `scope.py` / `evaluation.py` / `apps/*/models.py` / `apps/*/migrations/` / `apps/*/urls.py`.
- [x] Nenhum `CreateView`/`urlpatterns` de domínio novo
- [x] Nenhum `migrations/`
- [x] Services novos são importáveis e **não** chamam advance/approve/cálculo
- [x] `nav_menu.html`: diff limitado a badge/count, sem reordenação de grupos
  - Confirmado T037 (2026-08-08): `git diff development...HEAD -- templates/components/nav_menu.html` = apenas `badge_count=leader_pending_badge.total` no item “Painel do time”. Ordem de seções/labels idêntica a `development` (Colaborador → Líder → Gerente → Governança → Cadastros → Sistema).
- Gate T038 (2026-08-08): pytest stage/scope/reprovação + guidance/pending = **95 passed**.
