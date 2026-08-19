# Quickstart: Validação da Feature

**Branch**: `001-gestao-desempenho-talentos` | **Date**: 2026-07-09

Guia para validar end-to-end que a feature funciona conforme [spec.md](./spec.md). Detalhes de modelo em [data-model.md](./data-model.md); contratos em [contracts/](./contracts/).

## Pré-requisitos

- Python 3.11+ (recomendado)
- Redis em execução (para Celery; opcional em validações manuais sem notificações)
- Tailwind CLI standalone (para rebuild de CSS)

## Setup inicial

```bash
# Na raiz do repositório
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt

# Após Sprint 0 completa (config/settings split)
set DJANGO_SETTINGS_MODULE=config.settings.dev
python manage.py migrate
python manage.py createsuperuser   # primeiro admin

# Tailwind (quando configurado)
tailwindcss -i static/src/input.css -o static/css/tailwind.css --watch

# Celery (terminal separado, quando configurado)
celery -A config worker -l info
celery -A config beat -l info
```

## Cenários de validação

### Cenário 1 — Colaborador vê expectativas e registra desempenho (US1 / P1)

**Pré-condição**: Admin criou Área, Cargo, Competências com escala, vinculou `CargoCompetencia`; ciclo aberto; colaborador com cargo/área/gestor.

| Passo | Ação | Resultado esperado |
|---|---|---|
| 1 | Login como colaborador | Dashboard pessoal |
| 2 | Acessar página de expectativas | Lista competências + nível esperado + metas ligadas a objetivos |
| 3 | Cadastrar meta no ciclo | Meta com `status=pendente` |
| 4 | (Após aprovação líder) Registrar progresso na etapa `resultados` | `Meta.progresso` salvo |
| 5 | Realizar autoavaliação na etapa `avaliacao` | `nota_autoavaliacao` por competência registrada |

**Colaborador sem cargo**: página informa vínculo pendente (FR-005 edge case).

---

### Cenário 2 — Líder avalia equipe com escopo (US2 / P1)

**Pré-condição**: Líder com liderados diretos; metas submetidas.

| Passo | Ação | Resultado esperado |
|---|---|---|
| 1 | Login como líder | Seção "Time" visível |
| 2 | Aprovar/reprovar metas do liderado | Status atualizado; reprovação reabre só aquela meta |
| 3 | Aprovar resultados | Etapa avança quando 100% aprovado |
| 4 | Avaliar competências | `nota_final_lider` calculada (ver [calculation-contract.md](./contracts/calculation-contract.md)) |
| 5 | Acessar URL de avaliação de colaborador fora do escopo | 403/404 genérico; auditoria se registro existe |

---

### Cenário 3 — PDI colaborador e líder (US3 / P2)

| Passo | Ação | Resultado esperado |
|---|---|---|
| 1 | Colaborador cria PDI com ação | PDI visível no dashboard |
| 2 | Líder cria ação no PDI do liderado | Ação aparece para colaborador |
| 3 | Atualizar status da ação | `updated_at` alterado; histórico em auditoria |

*Independente do ciclo estar aberto (FR-012).*

---

### Cenário 4 — RH centraliza ciclos e aderência (US4 / P2)

| Passo | Ação | Resultado esperado |
|---|---|---|
| 1 | Admin abre ciclo | `Avaliacao` criada para todos `is_active=True` |
| 2 | Admin consulta painel aderência | Lê `AderenciaSnapshot` (não recalcula síncrono) |
| 3 | Admin encerra ciclo | Nenhuma etapa avança; incompletas marcadas |
| 4 | RH consulta lacunas por área/cargo | Agregação dentro do escopo admin |

---

### Cenário 5 — Matriz 9-box (US5 / P3)

| Passo | Ação | Resultado esperado |
|---|---|---|
| 1 | Admin define potencial manual | `ClassificacaoTalento.potencial` salvo |
| 2 | Sistema deriva desempenho | De `nota_final_lider` normalizada |
| 3 | Gestor filtra por área | Apenas escopo hierárquico |
| 4 | Colaborador sem visibilidade liberada | Não vê classificação |

---

## Validações de conformidade constitucional

| Check | Como validar |
|---|---|
| Escopo backend | Tentar IDOR em PDI/avaliação/9-box (Cenário 2, passo 5) |
| Snapshots | Alterar peso em `CargoCompetencia` após avaliação; recalcular — nota inalterada |
| Append-only audit | Tentar editar/deletar `AuditLog` no admin — bloqueado |
| Performance | Dashboard admin < 2s com snapshot pré-calculado |
| Paginação | Listagens com > 20 itens exibem paginação |

## Comandos úteis pós-implementação

```bash
python manage.py check
python manage.py migrate --check
ruff check apps/
pytest tests/ -v                    # sprints finais
```

## Referências

- [scope-contract.md](./contracts/scope-contract.md) — regras de visibilidade
- [routes-contract.md](./contracts/routes-contract.md) — mapa de URLs
- [stage-machine-contract.md](./contracts/stage-machine-contract.md) — transições de etapa
- [calculation-contract.md](./contracts/calculation-contract.md) — fórmulas de nota e 9-box
