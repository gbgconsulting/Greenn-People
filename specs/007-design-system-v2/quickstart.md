# Quickstart: Validação — Design System v2

**Branch**: `007-design-system-v2` | **Date**: 2026-08-06  
**Spec**: [spec.md](./spec.md) · **Plan**: [plan.md](./plan.md)

Guia de validação ponta a ponta (não é suite de implementação). Contratos: [contracts/](./contracts/).

---

## Pré-requisitos

- Stack local do Greenn People (venv, `migrate`, `runserver`).
- Usuários: **admin**, **líder** (time), **colaborador**; admin com acesso à matriz 9-box.
- Dados suficientes para charts populados + um cenário empty; classificação 9-box para drag.
- Tailwind rebuild após mudanças em `input.css` (comando usual do projeto).
- Scaffold de evidência: [evidence/before-after/](./evidence/before-after/).

```bash
python manage.py runserver
# Após editar static/src/input.css — rebuild Tailwind CLI conforme README/Makefile do repo
```

---

## 0 — Captura before (antes de implementar)

1. Em branch limpa / estado atual, capturar screenshots dos 5–8 pilotos (ver README da pasta evidence).
2. Capturar **login** como prova de isolamento (não conta para SC-001 de “melhoria”).
3. Nomes: `NN-<slug>-before.png`.

---

## 1 — Tipografia + isolamento auth (US1 / SC-002 / SC-005)

| # | Passo | Esperado |
|---|---|---|
| 1 | Login → abrir dashboard admin | Hierarquia display vs UI perceptível |
| 2 | Abrir team + uma lista | Mesma hierarquia |
| 3 | Abrir `/accounts/login/` (ou rota de login) | Visual **igual** ao before |
| 4 | `git diff templates/accounts/base_auth.html templates/accounts/login.html` | Vazio |
| 5 | DevTools no login | Sem classe `app-shell`; fonte efetiva Inter |

---

## 2 — Components (US2)

| # | Passo | Esperado |
|---|---|---|
| 1 | Dashboards + lista ciclos/avaliações + PDI/form | Buttons primary/secondary/outlined/loading com ritmo refinado |
| 2 | KPI / table-frame / empty | Densidade v2; empty honesto e acionável |
| 3 | CTAs existentes | Continuam submetendo / HTMX como antes |

---

## 3 — Charts polish (US3) + regressão 005

| # | Passo | Esperado |
|---|---|---|
| 1 | `/dashboard/admin/` com dados | Eixos/legendas/tooltips/grid/radius/altura refinados |
| 2 | Empty de um chart | Sem fake data; polish visual do empty |
| 3 | Labels textuais + Status Triad | Presentes além da cor |
| 4 | Diff `apps/dashboard/` (services/payloads/urls) | Sem mudança de negócio |

Detalhes: [chart-visual-polish.md](./contracts/chart-visual-polish.md).

---

## 4 — Ninebox polish (US4) + regressão 006

| # | Passo | Esperado |
|---|---|---|
| 1 | Admin → matriz | Grade/cards/empty alinhados ao v2 |
| 2 | Abrir drawer | Visual polido; payload/URL HTMX iguais |
| 3 | Drag potencial autorizado | Feedback visual refinado; persistência só potencial |
| 4 | Gerente / líder (conforme 006) | AuthZ inalterada |

Detalhes: [ninebox-visual-only.md](./contracts/ninebox-visual-only.md).

---

## 5 — Scan before/after (US5 / SC-001 / SC-005)

| # | Passo | Esperado |
|---|---|---|
| 1 | Capturar `*-after.png` nos mesmos pilotos | 5–8 pares |
| 2 | Revisor externo: ≤ 10 s/tela | Distingue melhoria em ≥ 5 (nenhuma é login) |
| 3 | Tipografia citada | ≥ 3 superfícies (revisor único) ou ≥ 80% dos revisores |

---

## 6 — Freeze v2 + checklist OUT

| # | Passo | Esperado |
|---|---|---|
| 1 | Ler `docs/design-system.md` | Status Freeze v2; tipografia, botões, cards, charts, ninebox |
| 2 | Preencher [out-checklist.md](./contracts/out-checklist.md) | Todos críticos ☑ |
| 3 | Scan deps | Sem Alpine/React/Sortable/nova chart lib |

---

## Critérios de falha imediata

- Qualquer alteração visual/comportamental em login/`base_auth`
- Regressão funcional nos happy paths 005 ou 006
- Nova rota/model/lib de front
- Redesign de grupos de navegação Admin
