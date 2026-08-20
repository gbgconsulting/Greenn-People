# Research: Elegibilidade de Ciclo por “Admitidos até”

**Branch**: `015-cycle-admission-cutoff` | **Date**: 2026-08-20

Pesquisa consolidada a partir de [spec.md](./spec.md) (Clarifications Session **2026-08-20 fechadas**), constituição I–VI, código âncora (`Ciclo`, `open_cycle`, `ensure_avaliacao_for_user`, `data_entrada`, legacy 010) e contratos a estender (002 mid-cycle, 008 checklist avisório).

**Zero `NEEDS CLARIFICATION` residual.** Clarifications 2026-08-20 **MUST NOT** ser reabertas. Stack preenchida no [plan.md](./plan.md).

---

## Decisões clarificadas (obrigatórias — não reabrir)

| # | Decisão | Research |
|---|---|---|
| Critério | 1 data de corte **por ciclo**; independente de `data_inicio`/`data_fim`; sem M2M | R1 |
| Momento | Obrigatório na **ABERTURA**; sem data → não abre, 0 Avaliações | R2, R4 |
| Elegível | ativo ∧ `data_entrada` NOT NULL ∧ `data_entrada ≤ admitidos_ate` (inclusivo) | R3 |
| Mid-cycle | Mesma regra em `ensure_avaliacao_for_user` | R3, R-mid |
| Snapshot | Avaliacao existente permanece; elegibilidade só cria | R3 |
| Histórico | `admitidos_ate=NULL` válido; sem reprocessar | R1, R-hist |
| Schema | 1 AddField aditivo; reutilizar `data_entrada`; zero AlterField | R1 |
| AuthZ | Mesmo admin de ciclos; sem papel novo; scope intacto | R-authz |
| Preview | 3 contagens agregadas; sem lista nominativa | R5 |
| Backfill | Comando novo; dry-run; só NULL; match 010 | R6 |
| Checklist 008 | Continua avisório | R-checklist |
| Stack | DTL+HTMX; sem DRF/SPA/Celery novo para o corte | R-stack |

---

## R1 — Nome canônico do campo: `Ciclo.admitidos_ate`

- **Decision**: `admitidos_ate = models.DateField('admitidos até', null=True, blank=True)` em `apps/cycles/models.py`. **Uma** migration `AddField` aditiva. Opcional no armazenamento (ciclos 011/arquivo). Obrigatório **somente** na regra de negócio de abertura (`open_cycle`).
- **Rationale**: Spec + decisão fechada do usuário; nome pt-BR alinhado a `data_inicio`/`data_fim`; independente do período informativo; NULL = histórico válido (FR-007).
- **Alternatives considered**:
  - Reutilizar `data_inicio` como corte — **proibido** (FR-002; clarifications).
  - `cutoff_date` / `admission_cutoff` em inglês — rejeitado: modelo vigente usa labels pt.
  - Campo obrigatório no DB (`null=False`) — rejeitado: quebraria ciclos 011/arquivo e import.
  - M2M / tabela de participantes — **proibido** (FR-010).

Detalhe: [data-model.md](./data-model.md), [migration-safety.md](./contracts/migration-safety.md).

---

## R2 — Onde capturar `admitidos_ate` (POST de abrir, não create+open forçado)

- **Decision**:
  1. **Fonte autoritativa da gravação no fluxo operacional**: POST de abertura (`CicloOpenView` → `open_cycle`). O POST inclui `admitidos_ate` (date input no formulário “Abrir” da listagem / superfície admin já existente).
  2. `open_cycle` **persiste** `admitidos_ate` no ciclo **antes** de mudar `status` para `aberto` (mesmo `transaction.atomic`), valida presença, depois cria Avaliações só para elegíveis.
  3. `CicloForm` (create/update) **pode** expor o campo como opcional para pré-preencher antes de abrir, mas **não** é gate no `save` do form — o gate permanece em `open_cycle`. Default de implementação: priorizar o campo no fluxo de Abrir; incluir no form de edição se DX simples (mesmo `DateInput`).
- **Rationale**: Hoje create ≠ open (`CicloForm` só `nome`/`data_inicio`/`data_fim`; status via Abrir). Forçar corte no create quebraria cadastro de ciclo “rascunho” encerrado e ciclos importados. Spec: momento = ABERTURA.
- **Alternatives considered**:
  - Só no `CicloCreateView` com create+open atômico — rejeitado: muda UX vigente; ciclos podem existir encerrados sem abrir.
  - Endpoint separado “salvar corte” sem abrir — desnecessário; preview não exige persistir antes do POST de abrir (pode calcular com date do input).
  - Wizard 2 steps — rejeitado: spec diz preview informativo sem etapa extra além do POST Abrir.

---

## R3 — Predicado único: `user_eligible_for_ciclo(user, ciclo) -> bool`

- **Decision**: Módulo fino `apps/cycles/services/eligibility.py` (ou equivalente sob `cycles/services/`):

```python
def user_eligible_for_ciclo(user: CustomUser, ciclo: Ciclo) -> bool:
    """Elegível para criar Avaliacao neste ciclo (abertura e mid-cycle)."""
    if not getattr(user, 'is_active', False):
        return False
    if ciclo.admitidos_ate is None:
        return False  # fail-closed: sem corte não matricula (open_cycle falha antes)
    entrada = getattr(user, 'data_entrada', None)
    if entrada is None:
        return False
    return entrada <= ciclo.admitidos_ate  # date, inclusivo
```

Usado por:
- `open_cycle` (após gate + persistência do corte; batch só se elegível, via `ensure`)
- `ensure_avaliacao_for_user` (além de ativo + ciclo aberto)

**Invariantes**:
- `NULL data_entrada` ⇒ **não elegível** (nunca).
- `NULL admitidos_ate` no predicado ⇒ `False` (fail-closed). Em ciclo **encerrado** histórico, `ensure` já no-op por status; `open_cycle` **nunca** chama ensure sem corte (levanta exceção antes).
- Inclusivo: `data_entrada == admitidos_ate` ⇒ elegível.
- Já existe Avaliacao ⇒ `ensure` retorna existente (**não** remove).

- **Rationale**: FR-003…FR-006, FR-015, FR-024; um único lugar evita divergência abertura vs mid-cycle.
- **Alternatives considered**:
  - Duplicar filtro em `open_cycle` e `ensure` — rejeitado (drift).
  - Colocar predicado em `reviews` — aceitável se imports; preferência `cycles` porque o corte é atributo do Ciclo (Princípio IV). `enrollment` importa de `cycles.services.eligibility` (já depende de `Ciclo`).
  - QuerySet manager mágico — overkill; função pura + filtros ORM no preview.

Detalhe: [eligibility-predicate-contract.md](./contracts/eligibility-predicate-contract.md).

---

## R4 — `open_cycle`: gate, exceção, ordem atômica

- **Decision**:
  1. Nova exceção de domínio: `CycleMissingCutoffError(CycleError)` em `apps/cycles/exceptions.py`.
  2. Assinatura preferida: `open_cycle(ciclo: Ciclo, *, admitidos_ate: date | None = None) -> Ciclo`. Se `admitidos_ate` passado, grava em `locked`; senão usa `locked.admitidos_ate` já persistido. Se após isso ainda `None` → `CycleMissingCutoffError`; status **não** vira aberto; **zero** Avaliacao.
  3. Ordem no `atomic`: lock → checks um-aberto / já-aberto → **exigir corte** → `locked.admitidos_ate = …` → `status=aberto` → `save` → iterator ativos → `ensure_avaliacao_for_user` (predicado dentro do ensure).
  4. `CicloOpenView`: ler date do POST; catch `CycleMissingCutoffError` → `messages.error` visível; success message **sem** “todos os ativos” / “colaboradores ativos” genérico — ex.: refletir matrícula conforme elegibilidade do corte (contagem opcional no texto se barato).
  5. Regra “só um aberto” **intacta** (`CycleAlreadyOpenError`).

- **Rationale**: FR-001, FR-013, FR-014; código atual abre todos os `is_active=True` sem corte.
- **Alternatives considered**:
  - ValidationError genérico no model `clean` ao abrir — menos claro na view; preferir exceção de domínio espelhando `CycleAlreadyOpenError`.
  - Filtrar no `open_cycle` sem mudar `ensure` — **proibido** (mid-cycle furaria a regra).

Detalhe: [open-cycle-cutoff-contract.md](./contracts/open-cycle-cutoff-contract.md).

---

## R5 — Preview: HTMX parcial na superfície admin + 3 contagens

- **Decision**:
  - **Superfície**: no fluxo de listagem/abertura que o admin já usa (`templates/cycles/ciclo_list*.html` e/ou detalhe), campo date “Admitidos até” + região de preview.
  - **Estratégia preferida**: endpoint HTMX (GET ou POST) sob `AdminCyclesMixin`, ex. `cycles:ciclo_open_preview` no mesmo `pk` do ciclo, recebendo `admitidos_ate` e devolvendo partial com **apenas**:
    1. `elegiveis` — ativos com `data_entrada ≤ D`
    2. `excluidos_admissao_posterior` — ativos com `data_entrada > D`
    3. `sem_data_entrada` — ativos com `data_entrada IS NULL`
  - Função de serviço: `preview_admission_counts(admitidos_ate: date) -> NamedTuple` (agrega sobre `CustomUser.objects.filter(is_active=True)`). **Não** precisa do ciclo persistido para contar (corte vem do input); se D ausente, partial mostra estado “informe a data” sem números enganosos.
  - **AuthZ**: idêntico a Abrir (`AdminCyclesMixin` / `RequiresAdminMixin`). Líder/colaborador → 403. Anônimo → login redirect. **MUST NOT** rota pública. **MUST NOT** serializar lista de usuários/e-mails/nomes.
  - Preview **informativo**; não adiciona step de confirmação além do POST Abrir.

- **Rationale**: US2; Constituição II; FR-011/FR-012.
- **Alternatives considered**:
  - Só recompute no POST Abrir sem preview — rejeitado (US2 P1).
  - Contagens no template com loop Python de usuários — rejeitado (lento + risco de vazar PII no HTML).
  - JSON/DRF — **proibido** (Princípio I).
  - Mesmo POST page full reload a cada keyup — pior UX; HTMX parcial é o padrão do monólito.

Detalhe: [preview-counts-contract.md](./contracts/preview-counts-contract.md).

---

## R6 — Backfill: comando novo sob `accounts` (não mutar importer 010 full)

- **Decision**:
  - Command: `python manage.py backfill_data_entrada --colaboradores PATH [--dry-run] [--report-file PATH]`
  - Pacote: `apps/accounts/services/admission_backfill/` (`resolve.py` + `importer.py`) + `apps/accounts/management/commands/backfill_data_entrada.py`
  - Fonte: `backup_colaboradores_*.xlsx`, coluna **“Data admissão”**. Parse via `dates.parse_legacy_date` (serial Excel + ISO já aceitos).
  - Leitura XLSX: estender `parse_xlsx` **mínimo** (ex. campo opcional em `ColaboradorRow` **ou** parser dedicado `parse_colaboradores_admission_xlsx` no mesmo módulo) — **preferir** não alterar o caminho de persistência do `importar_colaboradores` / `importer.py` 010.
  - Match pessoa: **mesma chave natural da 010** — `email` (`email__iexact` / e-mail empresarial) e, se necessário, `solides_id` complementar (`canonicalize_id` do Identificador). **NÃO** inventar User.
  - Só preenche `data_entrada` quando `NULL`/vazio; **NÃO** sobrescreve; **NÃO** toca nome/email/área/cargo/gestor/`is_active`.
  - **NÃO** chama `open_cycle` / `close_cycle` / `ensure_avaliacao_for_user` / `advance_stage`.
  - Dry-run: zero writes; relatório com totais + amostra mascarada (`report.py` / `mask_email` / `mask_pii` padrão 010).
  - Persist: `transaction.atomic`; idempotente (2ª run delta 0).

- **Rationale**: US4; FR-016/017/018; decisão explícita de módulo novo vs mutar 010.
- **Alternatives considered**:
  - Flag no `importar_colaboradores` — rejeitado (reabre allowlist 010; risco de side-effects).
  - UI upload — **proibido**.
  - Match só por nome — rejeitado (ambiguidade; 010 usa e-mail/solides_id).

Detalhe: [admission-backfill-command-contract.md](./contracts/admission-backfill-command-contract.md).

---

## R-mid — Atualização do contrato mid-cycle (002)

- **Decision**: **Estender** (não substituir) `specs/002-pos-mvp-hardening/contracts/mid-cycle-enrollment-contract.md`:
  - Após checagens de ativo + ciclo aberto, aplicar `user_eligible_for_ciclo`.
  - Inelegível → `None` (no-op).
  - Abertura: deixa de dizer “todos ativos”; passa a “ativos elegíveis pelo corte”.
  - Pontos de invocação (RegisterForm / UserUpdateForm reativação) **inalterados** — só o comportamento interno do ensure muda.
- **Rationale**: FR-005; evita drift documental.
- **Alternatives considered**: Contrato 015 só e abandonar 002 — rejeitado; 002 continua sendo a referência de enrollment mid-cycle.

---

## R-tests — Política de testes que quebram “todos os ativos”

- **Decision**:
  1. `tests/conftest.py::ciclo_aberto`: antes de `open_cycle`, setar `admitidos_ate` (ex. `date.today()` ou data ≥ `data_entrada` dos fixtures) **e** garantir que usuários fixture usados na suíte tenham `data_entrada` preenchida quando o teste espera Avaliacao.
  2. Qualquer teste que chama `open_cycle` direto deve passar/gravar corte.
  3. Atualizar `test_mid_cycle_enrollment.py` e qualquer assert de mensagem/contagem “todos ativos”.
  4. Novos testes cobrem inelegíveis (sem data / data > D) e gate sem corte.
  5. **Não** alterar asserts de negócio de stage/scope/fórmula/rejeição — só fixtures se `open_cycle` passar a exigir corte.
- **Rationale**: SC-009; conftest hoje chama `open_cycle` sem corte → quebraria 100% da suíte após o gate.

---

## R-authz — Mesmo gate admin; scope intocado

- **Decision**: `AdminCyclesMixin` = `LoginRequiredMixin` + `RequiresAdminMixin` (`is_admin=True`). Preview e Abrir usam o mesmo mixin. **Zero** mudança em `get_visible_users`, `ScopedObjectMixin`, `line_manager`. Inelegível simplesmente não tem Avaliacao — leitura permanece como hoje.
- **Rationale**: FR-012, FR-020; Constituição II.
- **Alternatives considered**: Papel “RH” novo — **proibido**. Preview para líder — **proibido**.

---

## R-audit — Rastreabilidade sem AuditLog paralelo

- **Decision**: `Ciclo` **não** está em `apps/audit/signals.py` hoje. Nesta feature: **não** inventar trilha paralela nem obrigar wiring de AuditLog para Ciclo. Conformidade FR-021 = `admitidos_ate` **persistido e legível no ciclo após abertura** (campo no model + admin/detail). Mudanças de `data_entrada` no User continuam sob o que o produto já audita (hoje `USER_TRACKED_FIELDS` **não** inclui `data_entrada` — **não** expandir nesta feature salvo necessidade futura explícita).
- **Rationale**: “usar trilha existente **se** Ciclo já for auditado”; não é. Spec pede rastreável no ciclo.
- **Alternatives considered**: Adicionar Ciclo ao audit signals só por esta feature — rejeitado (escopo; inventa superfície nova sem pedido).

---

## R-checklist — 008 permanece avisório

- **Decision**: `build_rh_pre_open_checklist` / contract 008 **intactos**. Única trava **nova** de abertura = ausência de `admitidos_ate`. Pessoas sem data **não** bloqueiam abertura — só não entram (preview mostra contagem).
- **Rationale**: FR-019; clarifications.

---

## R-hist — Ciclos 011 / imports

- **Decision**: Imports 010/011/013/014 **não** passam a exigir `admitidos_ate` nem a chamar `open_cycle`. Ciclos 011 continuam `encerrado` com `admitidos_ate=NULL`. Zero backfill do corte em ciclos históricos. Zero criação/remoção de Avaliacao por reprocessar elegibilidade.
- **Rationale**: FR-008, FR-018; US5.

---

## R-stack — UI mínima; RegisterForm

- **Decision**: Preferir DTL + HTMX + forms Django. Sem SPA, DRF, lib nova. `RegisterForm`: **não** tornar `data_entrada` obrigatória (default). RH preenche no cadastro admin (`UserUpdateForm` já tem o campo).
- **Rationale**: Non-goals do usuário; Constituição I.

---

## Resolvido: zero NEEDS CLARIFICATION

Todas as ambiguidades de Technical Context foram fechadas pelas decisões Session 2026-08-20 + este research. Pronto para Phase 1 (`data-model.md`, `contracts/`, `quickstart.md`).
