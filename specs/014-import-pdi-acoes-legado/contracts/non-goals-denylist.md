# Contract: Non-Goals / Denylist de Domínio

**Feature**: `014-import-pdi-acoes-legado`  
**Fonte**: [spec.md](../spec.md) FR-020/FR-021/FR-023 + [data/legado-solides/README.md](../../../data/legado-solides/README.md) § Denylist  
**Padrão**: espelha [spec 013](../../013-import-notas-comentarios-legado/contracts/non-goals-denylist.md)  
**Data**: 2026-08-19

### Confirmação T001 (2026-08-19)

Denylist congelada contra o monólito. Paths sob vigilância **existem** no repo e permanecem intocáveis (diff MUST be empty). Alinhado a [model-allowlist.md](./model-allowlist.md) e à seção “Escopo inválido” de `tasks.md`.

- [x] Denylist inclui explicitamente: `apps/cycles/services/stage.py`, `apps/cycles/services/cycle.py`, `apps/reviews/services/evaluation.py`, `apps/accounts/services/scope.py`
- [x] UI 012: `apps/dashboard/urls.py`, `apps/cycles/urls.py` + templates da 012; **sem** rota `/historico/`
- [x] PDI produto intocável: `apps/pdi/models.py`, `views.py`, `urls.py`, `forms.py`, `services/overdue.py`, `services/progress.py`, `tasks.py` (chamar `AcaoPDI.save()` ≠ editar `overdue.py`)
- [x] `apps/talent/` (mutators) na denylist; paths existem no repo
- [x] **Zero** migrations; **sem** nova lib; **sem** UI/DRF/Celery
- [x] Teste de ouro ratificado: executar `importar_pdi` **não** avança etapa, não abre/fecha ciclo, não aprova, não muda quem vê quem, **não edita** fórmula/`overdue.py`/`views.py`, não cria 9-box, não dispara aderência, não toca telas/rotas 012

---

## Declaração

Esta feature **persiste arquivo de PDI/ação** via comando operacional one-shot (`importar_pdi`).

**Teste de ouro (FR-021)**: executar `importar_pdi` **não** deve avançar etapa, abrir/fechar ciclo, aprovar/reprovar meta, alterar quem vê quem, editar a fórmula de nota, tocar notas/feedback, classificar 9-box, disparar recálculo de aderência, tocar urls/templates da spec 012 / criar rota `/historico/`, nem editar `overdue.py` / `progress.py` / `tasks.py` / `views.py`.

Diff dessas regras = **vazio** no merge.

**Teste de ouro II (Princípio II)**: após `importar_pdi`, usuário autenticado **fora** da hierarquia do dono recebe **404** (mesmo comportamento vigente) ao abrir detalhe/editar/apagar PDI ou ação; colaborador inativo **não** aparece na listagem de quem já não o via; asserts de `test_scope` intactos; `git diff` de `views.py` / `forms.py` / `urls.py` / `scope.py` = vazio.

FAIL se: view nova sem escopo; “esconder no frontend”; papel fixo no lugar de `line_manager`.

---

## Denylist (PROIBIDO)

| Zona | Proibição explícita |
|---|---|
| Máquina de estados | `can_advance`, `advance_stage` |
| Ciclos | `open_cycle`, `close_cycle` |
| Aprovação | `approve_*` / `reject_*` |
| Fórmulas / notas | Editar `evaluation.py`; `create_competency_lines`; mutar nota/feedback |
| Aderência / 9-box | `calcular_aderencia`; `ClassificacaoTalento` |
| AuthZ / escopo | Alterar/chamar `get_visible_users`, `ScopedObjectMixin`, `user_in_scope`, `scope.py` no **comando** para “autorizar” a carga |
| PDI produto | Editar `views.py`, `urls.py`, `forms.py`, templates pdi; simular POST CreateView |
| Atraso | Editar `overdue.py`; chamar `mark_overdue_pdi_actions` / `.delay`; editar `tasks.py` |
| Progresso | Editar/chamar `progress.py` / `calculate_pdi_progress` no import |
| UI spec 012 | `dashboard/urls.py`, `cycles/urls.py`, templates da 012; rota `/historico/` |
| Talent | Qualquer mutator em `apps/talent/` |
| Schema | Migration; `AddField`; `solides_id` em `AcaoPDI`; FK ciclo/avaliação |
| Stack | Views upload, DRF, Celery tasks novas, lib nova |
| Persistência | Raw SQL / `bulk_create` bypass `save`; RunPython; apagar PDI para refazer |
| CI | Ler `data/legado-solides/raw/` |

### Paths sob vigilância (diff MUST be empty)

```text
apps/cycles/services/stage.py
apps/cycles/services/cycle.py
apps/goals/services/approval.py
apps/accounts/services/scope.py
apps/reviews/services/evaluation.py
apps/dashboard/services/adherence.py
apps/dashboard/urls.py
apps/cycles/urls.py
apps/pdi/models.py
apps/pdi/views.py
apps/pdi/urls.py
apps/pdi/forms.py
apps/pdi/services/overdue.py
apps/pdi/services/progress.py
apps/pdi/tasks.py
apps/talent/
```

Qualquer `*/migrations/*` — diff MUST be empty (nenhuma migration nova).

Templates da 012 (qualquer path sob `templates/` tocado pela spec 012) — diff MUST be empty nesta fatia.

**Não alterar asserts** de `tests/test_stage_machine`, `tests/test_scope`, `tests/test_reject_stage_invariant`.

---

## Permitido (contraste)

| Ação | Escopo |
|---|---|
| ORM create `PDI` / `AcaoPDI` | 1+1; digest em `PDI.solides_id`; `full_clean`+`save` |
| Estender parse/dates/report da 010/011/013 | openpyxl só no parser |
| Pacote `pdi/services/legacy_import/` + `importar_pdi` | domínio + CLI fino |
| Relatório CLI mascarado + samples + testes desta fatia | stdout / `--report-file` |

---

## Gate de regressão (obrigatório)

Antes de merge:

```bash
# Diff denylist = vazio (NÃO usar `apps/pdi` inteiro — allowlist cria files novos)
git diff development -- \
  apps/cycles/services/stage.py \
  apps/cycles/services/cycle.py \
  apps/goals/services/approval.py \
  apps/accounts/services/scope.py \
  apps/reviews/services/evaluation.py \
  apps/dashboard/services/adherence.py \
  apps/dashboard/urls.py \
  apps/cycles/urls.py \
  apps/pdi/models.py \
  apps/pdi/views.py \
  apps/pdi/urls.py \
  apps/pdi/forms.py \
  apps/pdi/services/overdue.py \
  apps/pdi/services/progress.py \
  apps/pdi/tasks.py \
  apps/talent

# Nenhuma migration no PR
git diff development -- '**/migrations/**'

pytest tests/test_stage_machine tests/test_scope tests/test_reject_stage_invariant -q
pytest tests/test_import_pdi_legado.py -q
```

Qualquer diff não justificado em path da denylist = **FAIL**.

---

## Checklist de revisão de PR

- [ ] Nenhum arquivo denylist alterado (`overdue.py` / `tasks.py` / `views.py` / `models.py` inclusive)
- [ ] `scope.py` / urls 012 / templates 012 / talent intocados
- [ ] Sem chamada a open/close/advance/approve/`mark_overdue_pdi_actions`/`calcular_aderencia`/`get_visible_users` no command
- [ ] Persistência só ORM `full_clean`+`save` (hook de atraso via `save`)
- [ ] Sem UI/DRF/Celery/lib nova/migration
- [ ] Testes CI não referenciam `raw/`
- [ ] Relatório sem dump completo de PII (título/objetivo/nome/e-mail)
- [ ] Digest ≠ concatenação em claro; sem `solides_id` na ação
- [ ] Asserts de stage/scope/reject_stage_invariant **não** alterados
