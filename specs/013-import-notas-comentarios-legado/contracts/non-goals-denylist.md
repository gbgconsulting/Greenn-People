# Contract: Non-Goals / Denylist de Domínio

**Feature**: `013-import-notas-comentarios-legado`  
**Fonte**: [spec.md](../spec.md) FR-020/FR-021/FR-023 + [data/legado-solides/README.md](../../../data/legado-solides/README.md) § Denylist  
**Padrão**: espelha [spec 011](../../011-import-ciclos-avaliacoes-legado/contracts/non-goals-denylist.md)  
**Data**: 2026-08-18

### Confirmação T001 (2026-08-18)

Denylist congelada contra o monólito. Paths sob vigilância **existem** no repo e permanecem intocáveis (diff MUST be empty). Alinhado a [model-allowlist.md](./model-allowlist.md) e à seção “Escopo inválido” de `tasks.md`.

- [x] Denylist inclui explicitamente: `apps/cycles/services/stage.py`, `apps/cycles/services/cycle.py`, `apps/reviews/services/evaluation.py` (**diff vazio** — chamar ≠ editar), `apps/accounts/services/scope.py`
- [x] UI 012: `apps/dashboard/urls.py`, `apps/cycles/urls.py` + templates da 012; **sem** rota `/historico/`
- [x] `apps/pdi/` e `apps/talent/` (mutators) na denylist; paths existem no repo
- [x] **Zero** migrations; **sem** nova lib; **sem** UI/DRF/Celery
- [x] Teste de ouro ratificado: executar `importar_notas_comentarios` **não** avança etapa, não abre/fecha ciclo, não aprova, não muda quem vê quem, **não edita** a fórmula, não cria PDI/9-box, não dispara aderência, não toca telas/rotas 012

---

## Declaração

Esta feature **persiste histórico** de notas por competência e feedback qualitativo via comando operacional one-shot.

**Teste de ouro (FR-021)**: executar `importar_notas_comentarios` **não** deve avançar etapa, abrir/fechar ciclo, aprovar/reprovar itens, alterar quem vê quem, **alterar** a fórmula de nota, criar PDI, classificar 9-box, disparar recálculo de aderência, nem alterar telas/rotas da visão histórica (spec 012) / criar rota dedicada de histórico.

Diff dessas regras = **vazio** no merge.

---

## Denylist (PROIBIDO)

| Zona | Proibição explícita |
|---|---|
| Máquina de estados | `can_advance`, `advance_stage`; mutar `Avaliacao.etapa` / `concluida` da 011 |
| Ciclos (serviços) | `open_cycle`, `close_cycle` e qualquer mutação comportamental em `cycle.py` |
| Aprovação / reprovação | `approve_*` / `reject_*` |
| Fórmulas | **Editar** `evaluation.py`; reimplementar normalização; chamar `create_competency_lines` |
| Aderência / 9-box | `calcular_aderencia`; `ClassificacaoTalento` a partir da nota importada |
| AuthZ / escopo | Alterar/chamar `get_visible_users`, `ScopedObjectMixin`, `scope.py` para “liberar” nota |
| Snapshots | Mutar snapshots já persistidos; ler `CargoCompetencia` vigente como passado |
| PDI / talent | Qualquer mutator em `apps/pdi`, `apps/talent` |
| UI spec 012 | `dashboard/urls.py`, `cycles/urls.py`, templates da 012; rota `/historico/` |
| Schema | Migration; `AddField`; campo de PII novo |
| Mapa | Tabela persistida de `ids_colapsados` |
| Stack | Views upload, DRF, Celery tasks novas, lib nova |
| Persistência | Raw SQL / `bulk_create` bypass `clean`/`save`; RunPython de domínio |
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
apps/pdi/
apps/talent/
```

Templates da 012 (qualquer path sob `templates/` tocado pela spec 012) — diff MUST be empty nesta fatia.

**Não alterar asserts** de `tests/test_stage_machine`, `tests/test_scope`, `tests/test_reject_stage_invariant`.

---

## Permitido (contraste)

| Ação | Escopo |
|---|---|
| ORM create/update `AvaliacaoCompetencia` | Snapshots 1ª save; upsert `(avaliacao, competencia)` |
| ORM create `Feedback` | Append-only; `ciente_em` em líder histórico |
| ORM create `Competencia` mínima | Só FK de nota + filtro 003 |
| **Chamar** `calcular_nota_final_lider` / `calcular_nota_final_autoavaliacao` | Persiste `nota_final_*` **sem** editar `evaluation.py` |
| Estender parse/dates/report da 010/011 | openpyxl só no parser |
| IMPORTAR `aggregate.py` da 011 | Memória; não copiar |
| Relatório CLI mascarado + samples + testes desta fatia | stdout / `--report-file` |

---

## Gate de regressão (obrigatório)

Antes de merge:

```bash
# Diff denylist = vazio
git diff main -- \
  apps/cycles/services/stage.py \
  apps/cycles/services/cycle.py \
  apps/goals/services/approval.py \
  apps/accounts/services/scope.py \
  apps/reviews/services/evaluation.py \
  apps/dashboard/services/adherence.py \
  apps/dashboard/urls.py \
  apps/cycles/urls.py \
  apps/pdi \
  apps/talent

pytest tests/test_stage_machine tests/test_scope tests/test_reject_stage_invariant -q
pytest tests/test_import_notas_comentarios_legado.py -q
```

Qualquer diff não justificado em path da denylist = **FAIL**.

---

## Checklist de revisão de PR

- [ ] Nenhum arquivo denylist alterado (`evaluation.py` inclusive — diff vazio)
- [ ] `scope.py` / urls 012 / templates 012 / pdi / talent intocados
- [ ] Sem chamada a open/close/advance/approve/`create_competency_lines`/`calcular_aderencia`
- [ ] **Há** chamada a `calcular_nota_final_*`
- [ ] Sem UI/DRF/Celery/lib nova/migration
- [ ] Testes CI não referenciam `raw/`
- [ ] Relatório sem dump completo de PII (comentário/nome/e-mail)
- [ ] Zero 2ª `Avaliacao`; `etapa`/`concluida` 011 intactas
- [ ] Asserts de stage/scope/reject_stage_invariant **não** alterados
