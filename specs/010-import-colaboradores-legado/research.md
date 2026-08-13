# Research: Importação One-Shot do Legado Sólides — Colaboradores e Schema

**Branch**: `010-import-colaboradores-legado` | **Date**: 2026-08-12

Pesquisa consolidada a partir de [spec.md](./spec.md), [data/legado-solides/README.md](../../data/legado-solides/README.md), [spec 003](../003-import-catalogo-legado/), constituição (Princípios II e III em destaque), PRD §6.5.1/6.5.2 e Decisões #21/#22. Todos os `NEEDS CLARIFICATION` do Technical Context foram resolvidos.

---

## R1 — openpyxl restrito ao parse XLSX (Princípio I)

- **Decision**: Adicionar `openpyxl` a `requirements.txt`. Usar **somente** em `apps/accounts/services/legacy_import/parse_xlsx.py` para ler planilhas OOXML (`backup_colaboradores`, `backup_avaliacoes`). Nenhum outro módulo importa openpyxl. Sem pandas, sem xlrd.
- **Rationale**: `file data/legado-solides/raw/*.xlsx` → "Microsoft Excel 2007+"; stdlib `csv` falha. Contraste com spec 003 (CSV disfarçado). FR-002.
- **Alternatives considered**:
  - Exportar manualmente para CSV — rejeitado: perde fidelidade operacional e serial Excel de datas.
  - pandas — rejeitado: dependência pesada além do necessário.
  - Converter offline para CSV no repo — rejeitado: duplica fonte e PII.

---

## R2 — Superfície CLI (`importar_colaboradores`)

- **Decision**:

```bash
python manage.py importar_colaboradores \
  --colaboradores PATH \
  [--avaliacoes PATH] \
  [--report-file PATH] \
  [--dry-run]
```

Lógica em `apps/accounts/services/legacy_import/`; comando valida args, chama serviço, imprime relatório. Sem DRF, sem UI, sem Celery.

- **Rationale**: FR-002/FR-003/FR-011; alinhado PRD 6.5.2 e padrão 003.
- **Alternatives considered**:
  - Comando em `core` — rejeitado: domínio de colaboradores pertence a `accounts` (Princípio IV).
  - Admin upload — rejeitado (fora de escopo).

---

## R3 — Migration `solides_id` (6.5.1)

- **Decision**: Campo idêntico em cinco models:

```python
solides_id = models.CharField(
    max_length=50, blank=True, null=True, unique=True, db_index=True
)
```

**Uma migration por app** (`accounts`, `organization`, `competencies`, `reviews`, `pdi`). Sem alterar tipo/nullable/unique de campos existentes; sem novos campos PII. Detalhes: [contracts/migration-safety.md](./contracts/migration-safety.md).

- **Rationale**: PRD 6.5.1; FR-001; nullable — import não exige 100% preenchido.
- **Alternatives considered**:
  - Migration única consolidada — rejeitada: viola modularidade por app.
  - `solides_id` obrigatório — rejeitado: crosswalk parcial (~187/325).

---

## R4 — Persistência via ORM (`save()` / `clean()`)

- **Decision**: Toda escrita MUST chamar `model.full_clean()` + `model.save()` (ou `CustomUser.objects.create_user()` que normaliza e-mail). **Proibido** raw SQL / `bulk_create` / `update()` que bypass validação. Hierarquia: `CustomUser.clean()` já valida aciclicidade de `line_manager` (RF-04.1).
- **Rationale**: Spec + constituição III; evita ciclos silenciosos.
- **Alternatives considered**:
  - `bulk_create(ignore_conflicts=True)` — rejeitado: bypass `clean()`.
  - Atualizar `line_manager_id` via SQL — rejeitado.

---

## R5 — Ordem de persistência

- **Decision**: Dentro de um único `transaction.atomic()`:

```text
Fase A (entidades base):
  1. Area      — get_or_create por nome (Departamento)
  2. Cargo      — resolve por solides_id ou canonical_key; create se faltante (até 8 casos)
  3. CustomUser — create/update por e-mail; crosswalk solides_id; is_active; email_confirmado_em

Fase B (hierarquia — 2ª passada):
  4. line_manager — mapear Superior direto id → CustomUser.solides_id
                    full_clean + save por usuário; ciclos → reportar, não aplicar vínculo inválido
```

- **Rationale**: FR-007/FR-008/FR-009; FKs resolvidas antes de gestor; README ordem de import.
- **Alternatives considered**:
  - Gestor na mesma passada — rejeitado: superior pode aparecer depois no arquivo.
  - Ordem User antes Cargo — rejeitado: FK `cargo` obrigatória quando preenchida.

---

## R6 — Estratégia de e-mail e Decisão #21

- **Decision**:
  - Ordem: `E-mail empresarial` → `E-mail` → `E-mail pessoal`; `strip` + colapsar whitespace; `CustomUserManager.normalize_email()`.
  - `email_confirmado_em = timezone.now()` na criação/atualização importada (primeira carga e reimport).
  - Import **não** valida domínio `@greenn.com.br`; `RegisterForm.ALLOWED_EMAIL_DOMAIN` permanece intacto para cadastro autônomo.
- **Rationale**: FR-004/FR-005/FR-019; PRD RF-02.1 Decisão #21.
- **Alternatives considered**:
  - Enviar link de confirmação — rejeitado (Decisão #21).
  - Relaxar denylist globalmente — rejeitado: só bypass no path de import.

---

## R7 — Senha na importação

- **Decision**: Novos usuários recebem `set_unusable_password()` — login bloqueado até reset administrativo. Documentar no quickstart: operador dispara "reset password" via admin ou `createsuperuser`-style flow. **Nunca** senha hardcoded ou temporária fixa no código.
- **Rationale**: Segurança; alinhado a usuários sem credencial conhecida.
- **Alternatives considered**:
  - Senha temporária única por env — fora de escopo (sem e-mail massivo).
  - Forçar reset token em lote — alternativa operacional pós-import, não no comando.

---

## R8 — Crosswalk `solides_id` para usuários

- **Decision**: Arquivo `--avaliacoes` opcional. Construir índice `canonical_key(Nome Avaliado)` → `Identificador Avaliado` (string). Para cada colaborador, se match único → preencher `solides_id`. Ambiguidade (mesmo nome, IDs distintos) → conflito, **não** atribuir silenciosamente. Sem match → `solides_id` null; dedupe por e-mail.
- **Rationale**: README § Identificadores; FR-003; ~187 matches esperados no dump.
- **Alternatives considered**:
  - Gerar hash determinístico de e-mail — rejeitado: não correlaciona com backups futuros.
  - Exigir crosswalk — rejeitado: import deve completar sem ele.

Ver [contracts/solides-id-crosswalk-contract.md](./contracts/solides-id-crosswalk-contract.md).

---

## R9 — `solides_id` em Cargo na importação de colaboradores

- **Decision**: Coluna `Cargo ID` → `Cargo.solides_id` no create/update de cargo. Lookup: `Cargo.objects.filter(solides_id=...).first()`; fallback `canonical_key(nome)` entre ativos. Cargos da spec 003 sem `solides_id` preenchido: atualizar `solides_id` quando `Cargo ID` presente no backup.
- **Rationale**: FR-008; README mapeamento.
- **Alternatives considered**:
  - Só nome — rejeitado: perde rastreabilidade para fatias 6.5.4+.

---

## R10 — Datas (serial Excel + ISO)

- **Decision**: Parser em `dates.py`:
  - Float/int serial Excel (ex. `45446.0`) → `datetime.date` via epoch 1899-12-30 (compat openpyxl).
  - Strings ISO (`YYYY-MM-DD`) → parse direto.
  - Vazio / `0` / `None` → ausência de demissão → `is_active=True`.
- **Rationale**: README § Datas; edge cases spec.
- **Alternatives considered**:
  - Ignorar serial — rejeitado: 198 demitidos dependem de parse correto.

---

## R11 — `is_active` e demitidos

- **Decision**: `Data demissão` preenchida e ≠ zero/vazio → `is_active=False`. Caso contrário `True`. Gestor demitido pode ser `line_manager` de ativo (estrutura histórica). `_validate_deactivation_without_active_reports` pode bloquear desativação se liderados ativos — import deve processar gestores **antes** de desativar subordinados ou usar ordem: criar todos ativos primeiro, depois aplicar demissões, depois hierarquia. **Ordem refinada**:

```text
3a. CustomUser — upsert com is_active derivado de demissão (demitidos inativos desde o início)
4.  line_manager — vínculos (gestores demitidos permitidos)
```

Se `clean()` bloquear desativação por liderados ativos: na fase de upsert, demitidos com liderados ativos → reportar conflito `desativacao_bloqueada_liderados` e manter ativo **ou** aplicar gestor antes — **decisão**: fase B atribui gestores; demitidos nunca têm liderados ativos no legado (198 demitidos). Se edge case ocorrer, reportar e pular desativação.

- **Rationale**: FR-006; `CustomUser._validate_deactivation_without_active_reports`.
- **Alternatives considered**:
  - `update(is_active=False)` bypass — rejeitado (R4).

---

## R12 — Idempotência

- **Decision**: Chave natural = e-mail normalizado. Lookup: `CustomUser.objects.filter(email=...)`. Reexecução: update campos divergentes (`nome`, `cargo`, `area`, `is_active`, `solides_id`, `email_confirmado_em`); reportar `criados`/`atualizados`/`inalterados`. Colisão de e-mail no backup (duas linhas) → conflito; linha posterior não sobrescreve.
- **Rationale**: FR-013; Assumptions spec.
- **Alternatives considered**:
  - Upsert por `solides_id` only — rejeitado: muitos null.

---

## R13 — Transação, dry-run e exit codes

- **Decision**: Espelhar spec 003:
  1. Parse+validate (sem DB) — erro fatal → exit 1.
  2. `--dry-run`: fase 1 + totais projetados, zero commit.
  3. Persist: `transaction.atomic()` — exceção → rollback, exit 1.
  4. Conflitos não-fatais (sem e-mail, crosswalk ambíguo, gestor não resolvido) → relatório; exit 0 se persist ok.
- **Rationale**: FR-011/FR-012/FR-014.
- **Alternatives considered**: idem 003.

---

## R14 — PII / OPSEC

- **Decision**:
  - `raw/` contém PII — **proibido** em CI.
  - Fixtures anonimizadas em `data/legado-solides/samples/` (subset: ativos, demitidos, sem superior, crosswalk parcial, datas serial+ISO).
  - Relatório: totais + amostra mascarada (`j***@example.com`, CPF nunca logado).
  - Função `mask_email()` / `mask_pii()` em `report.py`.
- **Rationale**: FR-015/FR-020; README § Segurança.
- **Alternatives considered**:
  - Log linha completa em debug — rejeitado.

---

## R15 — Reuso da spec 003

- **Decision**: Import read-only de `canonical_key`, `display_name` de `apps/competencies/services/catalog_import/normalize.py`. **Não** reimplementar catálogo CSV. Assumir `importar_competencias_cargo` executado antes (README ordem passo 2).
- **Rationale**: FR-018; Decisão #22 ordem de import.
- **Alternatives considered**:
  - Duplicar normalize — rejeitado.

---

## R16 — Denylist de domínio (Princípios II, III, V)

- **Decision**: Import **MUST NOT** alterar arquivos listados em [contracts/non-goals-denylist.md](./contracts/non-goals-denylist.md). Gate de regressão: `git diff` denylist vazio (exceto allowlist). pytest: `test_stage_machine`, `test_scope`, `test_reject_stage_invariant` verdes.
- **Rationale**: FR-016/FR-017; constituição II/III/V.
- **Alternatives considered**: N/A — non-negotiable.

---

## R17 — Testes

- **Decision**: `tests/test_import_colaboradores_legado.py` cobrindo: dry-run, idempotência, demitidos inativos, hierarquia + ciclo reportado, crosswalk parcial, arquivo inválido, migration reversível (smoke), denylist diff vazio.
- **Rationale**: US5; SC-008.
- **Alternatives considered**: smoke manual only — rejeitado.

---

## Outcomes

Todos os `NEEDS CLARIFICATION` resolvidos. Nenhum gate de constituição violado sem registro em Complexity Tracking (openpyxl justificado). Próximo: [data-model.md](./data-model.md), [contracts/](./contracts/), [quickstart.md](./quickstart.md).
