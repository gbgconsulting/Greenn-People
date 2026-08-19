# Quickstart: Validação — Hardening Operacional Pós-MVP

**Branch**: `002-pos-mvp-hardening` | **Date**: 2026-07-14

Guia de validação end-to-end conforme [spec.md](./spec.md). Modelo: [data-model.md](./data-model.md). Contratos: [contracts/](./contracts/).

## Pré-requisitos

- Python 3.x, Redis (para validar lembretes Celery), PostgreSQL opcional (prod-like)
- Dependências: `pip install -r requirements.txt` (+ `pytest` / `pytest-django` quando adicionados)
- App já migrada do MVP (`python manage.py migrate`)

```bash
export DJANGO_SETTINGS_MODULE=config.settings.dev
python manage.py migrate
# opcional
celery -A config worker -l info
celery -A config beat -l info
```

## Cenários de validação

### C1 — Pós-reprovação de meta sem retroceder etapa (US1 / P1)

**Pré**: Avaliação em `aprovacao_metas`; ≥2 metas, uma aprovável.

| Passo | Ação | Esperado |
|---|---|---|
| 1 | Gestor reprova meta A | `status=reprovada`; `Avaliacao.etapa` inalterada; meta B aprovada intacta |
| 2 | Colaborador corrige e salva A | `reopen` → `pendente`; CTA claro |
| 3 | Gestor reaprova A | Com 100% aprovadas, avanço para `resultados` permitido |

Ver [post-rejection-contract.md](./contracts/post-rejection-contract.md).

### C2 — Pós-reprovação de resultado (US1 / P1)

**Pré**: Etapa `aprovacao_resultados`; um resultado reprovado.

| Passo | Ação | Esperado |
|---|---|---|
| 1 | Colaborador atualiza progresso do item | Edição permitida; após save `status_resultado=pendente` |
| 2 | Gestor reaprova | Só aquele item; demais aprovados intactos |
| 3 | 100% aprovados | Avanço de etapa possível |

### C3 — Avaliação mid-cycle (US2 / P1)

**Pré**: Ciclo `aberto`.

| Passo | Ação | Esperado |
|---|---|---|
| 1 | Cadastrar/ativar colaborador ativo | 1 `Avaliacao` no ciclo (`input_metas`) |
| 2 | Reativar/editar sem mudança | Sem duplicata |
| 3 | Repetir sem ciclo aberto | Nenhuma Avaliação criada |

### C4 — Catálogos + offboarding (US3 / P2)

| Passo | Ação | Esperado |
|---|---|---|
| 1 | “Excluir” Área/Cargo/Escala/Competência em uso | Soft-delete (`is_active=False`); histórico ok |
| 2 | Criar ativo com nome duplicado | Rejeitado |
| 3 | Desativar gestor com liderados | Bloqueado |
| 4 | Reatribuir em lote → desativar | Liderados no novo gestor; desativação ok; AuditLog |

### C5 — Aprovação por admin (US4 / P2)

| Passo | Ação | Esperado |
|---|---|---|
| 1 | Admin aprova meta com gestor presente | Status aprovado; AuditLog.actor = admin |
| 2 | Líder fora do escopo tenta ver/aprovar | 403/negado |

### C6 — Lembretes e PDI (US5 / P3)

| Passo | Ação | Esperado |
|---|---|---|
| 1 | Rodar task de lembrete 2× mesma janela | 1 envio efetivo |
| 2 | Estender prazo de ação `atrasada` para futuro | Status deixa de ser atrasada; audit de prazo |

### C7 — Produção, testes e UX (US6 / P3)

| Passo | Ação | Esperado |
|---|---|---|
| 1 | `GET /health/` | 200 com DB ok |
| 2 | Seguir [docs/ops/backup.md](../../docs/ops/backup.md) | Procedimento aplicável |
| 3 | `pytest` (suíte escopo/stage) | Casos inválidos falham; válidos passam |
| 4 | UI: ação HTMX / lista vazia / modal | Loading, empty+CTA, Escape/foco |

## Comandos úteis

```bash
# Suíte focada (após implementação)
pytest tests/ -q

# Smoke legado (referência MVP)
python scripts/validate_t070.py

# Static prod-like
export DJANGO_SETTINGS_MODULE=config.settings.prod
python manage.py collectstatic --noinput
```

## Critérios de aceite rápidos

- [x] SC-001–SC-004 (P1/P2 operacionais)
- [x] SC-005–SC-006 (lembretes/PDI)
- [x] SC-007–SC-009 (prod/testes/UX)

## Validação automatizada (T042)

```bash
# Cenários C1–C7 (rollback; não persiste dados)
PYTHONPATH=. python scripts/validate_quickstart_c1_c7.py

# Suíte (inclui cobertura dedicada C6/C7)
pytest tests/ -q
```
