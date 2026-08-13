# Research: Importação One-Shot do Legado Sólides — Ciclos e Cabeçalhos de Avaliação

**Branch**: `011-import-ciclos-avaliacoes-legado` | **Date**: 2026-08-13

Pesquisa consolidada a partir de [spec.md](./spec.md) (clarifications 2026-08-13 **fechadas**), [data/legado-solides/README.md](../../data/legado-solides/README.md), specs [010](../010-import-colaboradores-legado/) e [003](../003-import-catalogo-legado/), constituição (I–VI) e models atuais (`Ciclo` sem `solides_id`; `Avaliacao` já com `solides_id` + `unique_together (ciclo, usuario)`).

**Zero `NEEDS CLARIFICATION` residual** sobre as 5 decisões clarificadas — research **implementa**, não re-debate.

---

## Decisões clarificadas (obrigatórias — não reabrir)

| # | Decisão | Implementação |
|---|---|---|
| 1 | `Ciclo.solides_id` **aditivo** = `Identificador` da solicitação (padrão 010) | Migration única; lookup FK nas avaliações |
| 2 | Agregação **1** `Avaliacao` por `(ciclo, avaliado)`; N linhas avaliador×avaliado colapsam | [aggregation-contract.md](./contracts/aggregation-contract.md) |
| 3 | `Avaliacao.solides_id` = linha canônica (autoavaliação se `Nome Avaliador`=`Nome Avaliado`; senão menor `Identificador`); IDs colapsados no relatório | Handoff 6.5.5 |
| 4 | Persistência **direta** `etapa=feedback` + `concluida=True` — **sem** stage/open/close/approval | ORM `save`/`full_clean` apenas |
| 5 | **Todos** status Sólides (`finished`/`draft`/`active`/`canceled`) → `Ciclo.status=encerrado`; **nunca** abrir | FR-005/FR-006 |

---

## R1 — openpyxl: reuso, sem nova biblioteca (Princípio I)

- **Decision**: **Não** adicionar nova dependência. Continuar usando `openpyxl` **somente** em `apps/accounts/services/legacy_import/parse_xlsx.py` (estender parsers de solicitações e avaliações-cabeçalho). Nenhum módulo de domínio importa openpyxl diretamente.
- **Rationale**: Já justificado e presente na 010; backups são OOXML real; FR-003.
- **Alternatives considered**:
  - Nova lib (pandas/xlrd) — rejeitada: complexidade desnecessária.
  - Segundo `parse_xlsx` em `cycles` — rejeitada: parsers divergentes.

---

## R2 — Onde vive o código (estender 010 vs pasta paralela)

- **Decision**:
  1. **Estender** `apps/accounts/services/legacy_import/` para parse compartilhado (`parse_xlsx`, `dates`, `report`) e reutilizar `crosswalk`/`canonical_key` no fallback de usuário.
  2. Criar **`apps/cycles/services/legacy_import/`** para agregação, resolução Ciclo/User e `importer` de domínio (ciclos + cabeçalhos).
  3. Management command fino em `apps/cycles/management/commands/importar_ciclos_avaliacoes.py`.
  4. **Não** reimplementar `importar_colaboradores`.
- **Rationale**: Princípio IV (Ciclo pertence a `cycles`) + evitar dois parsers (Complexity Tracking). Avaliação persiste via ORM `reviews.Avaliacao` sem migration em `reviews`.
- **Alternatives considered**:
  - Tudo em `accounts/legacy_import` — rejeitado: acopla domínio de ciclo/avaliação histórica a accounts.
  - Pasta paralela completa com parser próprio — rejeitada: duplicação openpyxl/dates/report.

---

## R3 — Superfície CLI: um comando, duas fases

- **Decision**:

```bash
python manage.py importar_ciclos_avaliacoes \
  --solicitacoes PATH \
  --avaliacoes PATH \
  [--report-file PATH] \
  [--dry-run]
```

Fases **sempre** nesta ordem, dentro do mesmo fluxo (e mesma `transaction.atomic()` no modo persist):

1. Parse + upsert ciclos (`solicitacoes`)
2. Agregar + upsert cabeçalhos (`avaliacoes`)

Espelha 010 (`--colaboradores` + arquivo secundário). Ambos os paths são **obrigatórios** nesta fatia (ordem segura exige ciclos antes de FKs; operador que quiser só ciclos em staging pode passar fixture vazia de avaliações **não** é suportado — preferir dry-run parcial via implementação se necessário, mas contrato: ambos obrigatórios).

- **Rationale**: FR-002; reuso operacional 010; atomicidade FR-014; ordem README passo 4→5.
- **Alternatives considered**:
  - Dois commands (`importar_ciclos` + `importar_avaliacoes`) — rejeitado: pior DX vs 010; risco de pular fase 1; dois relatórios.
  - Só ciclos no command e avaliações depois — rejeitado: fatia única 6.5.4 + pré-requisito.

Detalhe: [contracts/import-command-contract.md](./contracts/import-command-contract.md).

---

## R4 — Migration `Ciclo.solides_id` (única alteração de schema)

- **Decision**: Campo idêntico ao padrão 010:

```python
solides_id = models.CharField(
    'ID Sólides',
    max_length=50,
    blank=True,
    null=True,
    unique=True,
    db_index=True,
)
```

**Uma** migration em `apps/cycles` apenas. Valor = `Identificador` da solicitação (string canônica, sem `.0` de float). Sem Match por nome/datas; sem tabela crosswalk externa.

- **Rationale**: Clarification #1; FR-001; `Avaliacao.solides_id` já existe (010).
- **Alternatives considered**:
  - Match só por nome/datas — **descartado** na clarification.
  - Crosswalk externo separado — **descartado**.
  - Alterar campos existentes de Ciclo — **proibido**.

Detalhe: [contracts/migration-safety.md](./contracts/migration-safety.md).

---

## R5 — Política de status → sempre encerrado

- **Decision**: Mapeamento fixo:

| Status Sólides | `Ciclo.status` |
|---|---|
| `finished` | `encerrado` |
| `canceled` | `encerrado` |
| `draft` | `encerrado` |
| `active` | `encerrado` |
| (qualquer outro conhecido/desconhecido) | `encerrado` + reportar `status_legado_desconhecido` (não-fatal) |

**Nunca** gravar `aberto`. Import **não** chama `open_cycle` / `close_cycle`. Ciclo aberto vigente do fluxo normal permanece intacto (só-um-aberto continua válido porque novos são todos `encerrado`).

- **Rationale**: Clarification #5; FR-005/FR-006; SC-002.
- **Alternatives considered**:
  - Pular draft/active/canceled — **descartado**.
  - `active` → abrir ciclo — **descartado** (violaria só-um-aberto e denylist).

---

## R6 — Nome serial Excel → rótulo legível

- **Decision**: Reutilizar `dates.parse_legacy_date`. Se `Nome` for numérico/serial Excel interpretável como data → persistir rótulo ISO `YYYY-MM-DD` (ou `strftime` estável documentado). Caso contrário: `display_name()` / strip + colapsar whitespace. Falha de normalização ambígua → conflito; **não** gravar número bruto sem registro no relatório.
- **Rationale**: Spec Assumptions + FR-003; volume baixo (~57).
- **Alternatives considered**:
  - Manter `46113.0` bruto — rejeitado (ilegível).
  - Locale pt-BR `DD/MM/YYYY` — aceitável se consistente; default do contrato = ISO para estabilidade em testes.

---

## R7 — Datas ausentes/inválidas (conservador)

- **Decision**: Exigir **ambas** `Iniciada em` e `Terminada em` parseáveis. Ausência/invalidade → conflito `datas_ausentes_ou_invalidas`; **não criar** ciclo. Continuação parcial das demais linhas permitida (não-fatal por linha); falha fatal só para arquivo/colunas/args/transaction.
- **Rationale**: Spec Edge Cases + Assumptions; volume ~57.
- **Alternatives considered**:
  - Default datas inventadas — rejeitado.
  - Abort atômico em qualquer data faltante — rejeitado (operador perde lote inteiro por 1 linha).

---

## R8 — Agregação e linha canônica

- **Decision**: Algoritmo normativo em [aggregation-contract.md](./contracts/aggregation-contract.md):

```text
group_key = (Identificador Solicitação, Identificador Avaliado)
canonical_id =
  se ∃ linha com Nome Avaliador ≈ Nome Avaliado (canonical_key):
    menor Identificador entre as linhas de autoavaliação do grupo
  senão:
    menor Identificador do grupo (numérico se todos numéricos; senão lexicográfico estável)
collapsed_ids = todos Identificadores do grupo − {canonical_id}
→ 1 Avaliacao(ciclo, usuario) com solides_id=canonical_id
```

Relatório: `grupos_agregados`, amostra mascarada de `ids_colapsados` (handoff 6.5.5).

- **Rationale**: Clarifications #2 e #3; FR-007/FR-009; `unique_together (ciclo, usuario)`.
- **Alternatives considered**:
  - Uma Avaliação por linha — **descartado**.
  - Só autoavaliação — **descartado**.
  - Hash composto / `solides_id` nulo — **descartado**.

---

## R9 — Resolução de usuário (solides_id + fallback 010)

- **Decision**:

```text
1. Primário: CustomUser.objects.filter(solides_id=Identificador Avaliado).first()
2. Fallback (só se passo 1 falhar):
   - Match único CustomUser por canonical_key(Nome Avaliado) == canonical_key(user.nome)
   - Se ambíguo ou zero matches → órfão no relatório; NÃO inventar user
3. Usuário inativo (demitido 010): PERMITIDO vincular cabeçalho histórico
```

Quando o fallback aplica: **apenas** se o Identificador Avaliado não resolve por `solides_id` (usuário sem crosswalk na 010 ou ID ausente no dump de colaboradores). Não sobrescrever `solides_id` do user nesta fatia (isso é escopo 010).

- **Rationale**: FR-008/FR-011; SC-004.
- **Alternatives considered**:
  - Só solides_id sem fallback — rejeitado: perde cobertura dos sem crosswalk.
  - Criar user órfão — **proibido**.

---

## R10 — Persistência terminal sem máquina de estados

- **Decision**: Na criação/atualização de `Avaliacao` histórica:

```text
etapa = Avaliacao.Etapa.FEEDBACK
concluida = True
nota_final_lider = NÃO TOCAR (deixar null / inalterado)
nota_final_autoavaliacao = NÃO TOCAR
# NÃO chamar: advance_stage, can_advance, open_cycle, close_cycle,
#             approve_*, reject_*, calcular_*
```

Ciclo: `status=encerrado` via atribuição ORM + `full_clean()`/`save()`.

- **Rationale**: Clarification #4; FR-010/FR-012/FR-017; Princípio V.
- **Alternatives considered**:
  - Derivar etapa por status Sólides — **descartado**.
  - Etapa inicial + advance — **descartado**.

---

## R11 — Idempotência

- **Decision**:
  - **Ciclo**: lookup por `solides_id`; create ou update `nome`/`data_inicio`/`data_fim`/`status=encerrado`; nunca duplicar.
  - **Avaliação**: lookup por `(ciclo, usuario)` **e** validar `solides_id` canônico; se outro registro já usa o canônico → conflito; se mesmo `(ciclo, usuario)` → atualizar campos permitidos (`etapa`, `concluida`, `solides_id` se vazio ou igual); não reabrir ciclo.
- **Rationale**: FR-015; SC-006.
- **Alternatives considered**:
  - Sempre delete+recreate — rejeitado: risco em FKs futuras 6.5.5.

---

## R12 — Relatório, dry-run, atomicidade, exit codes

- **Decision**: Espelhar 010/003:
  - `--dry-run`: parse + agregação + totais projetados; **zero** writes.
  - Persist: `transaction.atomic()`; falha → rollback completo; exit `1`.
  - Exit `0` sucesso (conflitos/órfãos não-fatais ok); `1` erro fatal.
  - Relatório: `criados` / `atualizados` / `inalterados` / `conflitos` / `orfaos` + `grupos_agregados` + amostra `ids_colapsados` mascarada.
- **Rationale**: FR-013/FR-014/FR-016; SC-005/SC-010.

---

## R13 — Ordem operacional e pré-condições

- **Decision**:

```text
003 catálogo → 010 colaboradores (+ solides_id users/Avaliação schema)
  → migrate Ciclo.solides_id (esta feature)
  → importar_ciclos_avaliacoes
  → (futuro) notas/comentários 6.5.5
```

Pré-condição dura: 010 aplicada (users com `solides_id` quando crosswalk existiu; `Avaliacao.solides_id` no schema). Catálogo 003 recomendado (não bloqueia cabeçalho; bloqueia notas futuras).

- **Rationale**: README ordem segura; Dependencies da spec.

---

## R14 — Gate denylist e testes

- **Decision**:
  - `git diff` denylist vazio (`stage.py`, `cycle.py`, `approval.py`, `scope.py`, `evaluation.py`, `adherence.py`).
  - pytest: stage/scope/reject_stage_invariant + `test_import_ciclos_avaliacoes_legado.py`.
  - Samples: solicitações (serial nome, active/canceled) + avaliações (multi-avaliador, órfão); **nunca** `raw/` no CI.
- **Rationale**: FR-019/FR-017; SC-007/SC-008.

---

## Resolução de Technical Context

| Item | Resolução |
|---|---|
| Parser XLSX | openpyxl existente (010) — R1 |
| Layout código | parse em accounts; domínio em cycles — R2 |
| CLI | um comando duas fases — R3 |
| Schema | só `Ciclo.solides_id` — R4 |
| Status | todos → encerrado — R5 |
| Nome serial | dates.py → rótulo — R6 |
| Datas | ambas obrigatórias — R7 |
| Agregação | 1:1 + canônico — R8 |
| User resolve | solides_id → fallback nome — R9 |
| Estado | feedback+concluida direto — R10 |
| Idempotência | por solides_id / (ciclo,usuario) — R11 |
| Relatório/dry-run | padrão 010 — R12 |

**Nenhum NEEDS CLARIFICATION residual.**
