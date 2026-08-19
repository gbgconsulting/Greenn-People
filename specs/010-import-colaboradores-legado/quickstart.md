# Quickstart: Validação — Importação Legado Sólides (Colaboradores + Schema)

**Branch**: `010-import-colaboradores-legado` | **Date**: 2026-08-12

Guia de validação end-to-end conforme [spec.md](./spec.md). Modelo: [data-model.md](./data-model.md). Contratos: [contracts/](./contracts/).

---

## §0 — Gate de regressão (obrigatório antes de merge)

```bash
export DJANGO_SETTINGS_MODULE=config.settings.dev

# Denylist diff MUST be empty
git diff main -- \
  apps/cycles/services/stage.py \
  apps/cycles/services/cycle.py \
  apps/goals/services/approval.py \
  apps/accounts/services/scope.py \
  apps/reviews/services/evaluation.py \
  apps/dashboard/services/adherence.py

# Regressão domínio + novos testes import
pytest tests/test_stage_machine tests/test_scope tests/test_reject_stage_invariant -q
pytest tests/test_import_colaboradores_legado.py -q
```

**Esperado**: diff denylist vazio; todos os testes verdes.

Allowlist de paths permitidos: [contracts/model-allowlist.md](./contracts/model-allowlist.md).

---

## Pré-requisitos

- Python 3.x, `pip install -r requirements.txt` (inclui `openpyxl`)
- Migrations 6.5.1 aplicadas
- Catálogo spec 003 executado (recomendado):

```bash
python manage.py migrate
python manage.py importar_competencias_cargo \
  --cargos lista-cargos.xlsx \
  --competencias lista-competencias.xlsx
```

- Fontes operacionais (staging — contêm PII):
  - `data/legado-solides/raw/backup_colaboradores_20260624.xlsx`
  - `data/legado-solides/raw/backup_avaliacoes_20260624.xlsx` (crosswalk)

**CI / dev local**: usar apenas `data/legado-solides/samples/*.xlsx` (anonimizadas).

---

## Comando

```bash
# Preview sem gravar
python manage.py importar_colaboradores \
  --colaboradores data/legado-solides/samples/colaboradores_min.xlsx \
  --avaliacoes data/legado-solides/samples/avaliacoes_crosswalk_min.xlsx \
  --dry-run

# Carga real (staging — paths raw)
python manage.py importar_colaboradores \
  --colaboradores data/legado-solides/raw/backup_colaboradores_20260624.xlsx \
  --avaliacoes data/legado-solides/raw/backup_avaliacoes_20260624.xlsx \
  --report-file /tmp/relatorio-colaboradores-legado.txt
```

Contrato CLI: [contracts/import-command-contract.md](./contracts/import-command-contract.md).

---

## Cenários de validação

### C1 — Schema `solides_id` (US1 / 6.5.1)

| Passo | Ação | Esperado |
|---|---|---|
| 1 | `python manage.py migrate` | Cinco apps migrados sem erro |
| 2 | Shell: criar User/Cargo sem `solides_id` | Aceito (null) |
| 3 | Dois registros com mesmo `solides_id` non-null | IntegrityError |
| 4 | CRUD/login/ciclos existentes | Inalterados |

Ver [contracts/migration-safety.md](./contracts/migration-safety.md).

### C2 — Carga inicial colaboradores (US2 / 6.5.2)

| Passo | Ação | Esperado |
|---|---|---|
| 1 | `--dry-run` com fixture/samples | exit 0; zero writes; totais projetados |
| 2 | Carga real samples | exit 0; `usuarios_criados` > 0 |
| 3 | Conferir demitidos | `is_active=False` quando data demissão preenchida |
| 4 | Conferir e-mail confirmado | `email_confirmado_em` not null |
| 5 | Conferir áreas | Departamentos → `Area` criadas |
| 6 | Dump real (~325) | ≥99% com e-mail válido importados (SC-002) |

### C3 — Crosswalk e gestores (US2 + US3)

| Passo | Ação | Esperado |
|---|---|---|
| 1 | Com `--avaliacoes` | `solides_id_preenchidos` > 0 no relatório |
| 2 | Usuário com superior resolvível | `line_manager` correto |
| 3 | Superior inexistente | `gestor_nao_resolvido` no relatório |
| 4 | Ciclo artificial (fixture teste) | `ciclos_hierarquia` reportado; vínculo não aplicado |

Ver [contracts/solides-id-crosswalk-contract.md](./contracts/solides-id-crosswalk-contract.md).

### C4 — Idempotência e dry-run (US4)

| Passo | Ação | Esperado |
|---|---|---|
| 1 | Segunda execução mesmas fontes | delta duplicatas e-mail = 0 |
| 2 | Predominância `usuarios_inalterados` | SC-007 |
| 3 | Arquivo corrompido/ausente | exit 1; DB inalterado |

### C5 — PII / OPSEC (US5)

| Passo | Ação | Esperado |
|---|---|---|
| 1 | `pytest tests/test_import_colaboradores_legado.py` | Verde sem ler `raw/` |
| 2 | Inspecionar stdout relatório | E-mails mascarados; sem CPF |
| 3 | Shell: User importado | Sem campos CPF/RG/endereço |

### C6 — Senha unusable

| Passo | Ação | Esperado |
|---|---|---|
| 1 | Login com usuário importado sem reset | Falha autenticação |
| 2 | Admin reset password | Login ok após reset |

---

## Checagens rápidas via shell

```bash
python manage.py shell
```

```python
from apps.accounts.models import CustomUser
from apps.organization.models import Area, Cargo

print(CustomUser.objects.count())
print(CustomUser.objects.filter(is_active=False).count())  # demitidos
print(CustomUser.objects.filter(solides_id__isnull=False).count())
print(CustomUser.objects.filter(line_manager__isnull=False, is_active=True).count())
print(Area.objects.filter(is_active=True).count())

# Amostra: email confirmado na importação
u = CustomUser.objects.filter(email_confirmado_em__isnull=False).first()
assert u is not None

# KPI PII: model não tem cpf
assert not hasattr(CustomUser, 'cpf')
```

---

## Testes automatizados

```bash
pytest tests/test_import_colaboradores_legado.py -q
```

Cobertura mínima: dry-run, idempotência, demitidos inativos, hierarquia/ciclo, crosswalk parcial, migration reversível, arquivo inválido.

---

## Critérios de sucesso (smoke)

- SC-001: cinco entidades aceitam `solides_id` null
- SC-002..SC-005: contagens dump 2026-06-24 (staging)
- SC-006: dry-run zero persistência
- SC-007: reexecução sem duplicatas
- SC-008: CI sem `raw/`
- SC-009: PII ausente de logs/registros
- SC-010: operação humana < 5 min + relatório < 2 min

---

## Ordem segura de import completa (trilha 6.5)

Referência: [data/legado-solides/README.md](../../data/legado-solides/README.md)

```text
1. migrate solides_id (esta feature — 6.5.1)
2. importar_competencias_cargo (003)
3. importar_colaboradores (esta feature — 6.5.2)  ← você está aqui
4. fatias futuras: avaliações, notas, PDI...
```
