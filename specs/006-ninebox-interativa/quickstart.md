# Quickstart: Validação — 9-box Interativa

**Branch**: `006-ninebox-interativa` | **Date**: 2026-07-31  
**Spec**: [spec.md](./spec.md) · **Plan**: [plan.md](./plan.md)

Guia de validação ponta a ponta (não é suite de implementação). Detalhes: [contracts/](./contracts/), [data-model.md](./data-model.md).

---

## Pré-requisitos

- Stack local Greenn People (venv, `migrate`, `runserver`).
- Usuários: **admin (Marina)**, **gerente** com escopo hierárquico, **colaborador** com classificação (visível e oculta).
- Ciclo com `Avaliacao.nota_final_lider` e ao menos 3 `ClassificacaoTalento` no escopo admin.
- Freeze 004 disponível (`docs/design-system.md`).

```bash
python manage.py runserver
```

---

## Slice 1 / MVP — Drawer (US1 / SC-001)

| # | Passo | Esperado |
|---|---|---|
| 1 | Login admin → `/talent/matrix/` | Grade carrega; filtros ciclo/área/cargo |
| 2 | Clicar pessoa em uma célula | Drawer lateral na **mesma página** com identidade, área/cargo, desempenho, potencial, quadrante, Visível/Oculto |
| 3 | Alterar potencial (1–3) → Salvar | Persistido; quadrante coerente; card na célula correta; **sem** full reload obrigatório; toast/sucesso |
| 4 | Toggle Liberar/Ocultar | Estado persistido no drawer + badge no card |
| 5 | Potencial inválido / forçar erro | Mensagem PT-BR; estado anterior permanece (SC-004) |
| 6 | Confirmar | Não foi obrigatório passar por `/talent/<id>/classify/` (FR-013) |
| 7 | Login gerente | Drawer abre **sem** save/toggle; POST direto → 403 |

---

## Slice 2 — Drag (US2 / SC-002)

| # | Passo | Esperado |
|---|---|---|
| 1 | Admin desktop: arrastar card para coluna de potencial diferente **mesma linha** de desempenho | Potencial atualiza; card na nova célula; desempenho inalterado |
| 2 | Soltar em célula com **desempenho incompatível** | Desempenho **não** muda; card faz **snap** para (desempenho derivado, potencial pretendido); feedback explícito |
| 3 | Simular falha de rede/403 no move | Card volta; erro visível; sem sucesso silencioso |
| 4 | Repetir para ≥ 3 pessoas | Grade coerente com DB sem full reload obrigatório entre moves |
| 5 | Viewport mobile / touch | Sem drag (ou degradado); calibração via drawer OK (SC-005) |
| 6 | Não-admin | Sem handles; POST move → 403 |

---

## Slice 3 — Leitura / a11y / empty (US3 / SC-006)

| # | Passo | Esperado |
|---|---|---|
| 1 | Gerente: matriz | Só pessoas do escopo; filtros aplicam |
| 2 | Abrir drawer | Somente leitura |
| 3 | Filtro sem resultados | Empty state claro; loading ≠ empty definitivo |
| 4 | Teclado | Abrir/fechar drawer; foco entra/sai previsível; Escape fecha |
| 5 | Células | Rótulos/texto de eixos ou quadrante além da cor |

---

## Regressão AuthZ / colaborador (SC-003, SC-007)

| # | Passo | Esperado |
|---|---|---|
| 1 | Colaborador com `visivel_ao_colaborador=False` | Sem 9-box em `/talent/mine/`; sem acesso útil à matriz |
| 2 | Liberar no drawer → colaborador | Passa a ver em mine; default continua False para novos |
| 3 | IDOR (curl POST potencial/toggle/move como gerente) | 403; zero write |
| 4 | Fórmulas | Mesmos limiares `derive_desempenho` / `calculate_quadrante` (sem mudança de código de cálculo) |
| 5 | Opcional | `scripts/validate_t070.py` — líder puro continua 403 na matriz |

---

## Checklist Success Criteria

| ID | Critério | Como verificar |
|---|---|---|
| **SC-001** | Inspecionar + potencial + toggle ≤ 1 min sem `classify` obrigatório | Slice 1 |
| **SC-002** | ≥ 3 reposicionamentos coerentes | Slice 2 |
| **SC-003** | 100% permissão/escopo/IDOR | Regressão AuthZ + testes |
| **SC-004** | Falhas honestas | Slice 1.5, 2.3 |
| **SC-005** | Mobile via drawer | Slice 2.5 |
| **SC-006** | Teclado + rótulos além da cor | Slice 3 |
| **SC-007** | Fórmulas + gate visibilidade | Regressão 4–5 |

### Validação T033 (2026-08-05)

| Camada | Resultado |
|---|---|
| `pytest tests/test_talent_matrix_authz.py` (Docker) | **29 passed** |
| `scripts/validate_t070.py` (Docker, `PYTHONPATH=/app`) | **47 PASS / 0 FAIL** (incl. C5.3b líder puro 403) |
| Inspeção de código vs slices | Endpoints/partials/JS presentes; formulários/fórmulas intactos |

| SC | Status T033 | Evidência / gap |
|---|---|---|
| SC-001 | **PASS** (HTTP + contratos) | Drawer write admin, potencial HTMX, toggle HTMX, inválido sem mutação, gerente read-only; tempo ≤1 min / “sem reload” = residual browser |
| SC-002 | **PASS** (HTTP + snap) | Move potencial-only + snap coerente nos testes; ≥3 moves live + fail-rede visual = residual browser |
| SC-003 | **PASS** | AuthZ/IDOR/escopo/líder 403 cobertos por pytest + T070 |
| SC-004 | **PASS** (parcial auto) | Potencial inválido + POST erro preservam estado no backend; revert DnD em rede/5xx = JS (residual smoke) |
| SC-005 | **PASS** (código) | Gates `pointer: coarse` / viewport estreito em `ninebox_matrix.js`; smoke touch residual |
| SC-006 | **PASS** (código + partial) | Escape/focus trap no JS; rótulos em `_cell.html`; smoke teclado residual |
| SC-007 | **PASS** | Default oculto, `mine` gate, `derive_desempenho`/`calculate_quadrante` nos testes |

**Residual browser (opcional smoke):** Slice 1 passos 1–3 toast/no-reload; Slice 2.3–2.5 drag fail/mobile; Slice 3.3–3.4 empty vs loading + teclado.

---

## OUT (não validar como entrega)

- Edição livre de desempenho; novas faixas; SPA/DRF; Chart.js/005; export; histórico visual de moves; 9-box default visível; deprecação de `classify`; redesign shell/Freeze/Impeccable; expansão da matriz a líderes puros.
