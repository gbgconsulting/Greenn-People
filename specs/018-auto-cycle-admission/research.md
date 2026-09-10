# Research: Abertura Automática de Ciclos por Admissão

**Branch**: `018-auto-cycle-admission` | **Date**: 2026-09-09

Pesquisa consolidada a partir de [spec.md](./spec.md) (Clarifications Session **2026-09-09 fechadas**), constituição I–VI, diretrizes visuais Greenn People, código âncora (`Ciclo`, `open_cycle`, `ensure_avaliacao_for_user`, `get_open_ciclo`, Celery Beat, PDI 017) e contratos 015 a preservar.

**Zero `NEEDS CLARIFICATION` residual.** Clarifications 2026-09-09 **MUST NOT** ser reabertas.

---

## Decisões clarificadas (obrigatórias — não reabrir)

| # | Decisão | Research |
|---|---|---|
| Modelo | Opção A — ritmo pela admissão; **coorte do mês** (1 ciclo / mês de marco) | R1 |
| Marco | Mês de admissão + múltiplos de 6; abertura no **1º dia útil** do mês | R2, R3 |
| Feriados | Brasil **nacional** apenas | R3 |
| Prazo | `data_fim` = ativação + **20** dias corridos | R4 |
| Sem admissão | Fora do automático | R2 |
| Bootstrap | Só **próximo marco futuro**; zero atrasados | R5 |
| Ciclo ainda aberto | Alerta RH; **não** bloqueia lote; **não** matricula a pessoa (FR-008) | R6 |
| Multi-open | Permitir N ciclos `aberto` (quebra 015) | R7 |
| Manual 015 | Permanece; caminho adicional | R8 |
| AuthZ / escopo | Backend only; RH = `is_admin` de ciclos | R9 |
| Lote | Celery Beat diário; HTTP não processa | R10 |
| Visual | Reuso shell/listagens; contrato UI | R11 |

---

## R1 — Forma do ciclo: coorte do mês (não 1 ciclo/pessoa)

- **Decision**: No 1º dia útil do mês M, se houver ≥1 elegível cujo próximo marco futuro é M, criar **exatamente um** `Ciclo` automático da coorte M e matricular todos os elegíveis (ex.: 10 → os 10). Nome operacional legível RH (ex.: “Avaliação automática — Jul/2026”).
- **Rationale**: Spec FR-001; governança simples; idempotência por coorte/mês.
- **Alternatives considered**:
  - Um ciclo por pessoa — rejeitado (clarifications; governança explode).
  - Opção B (lote único sem ritmo por admissão) — **proibido** (FR-020).

---

## R2 — Predicado de elegibilidade automática + relação com 015

- **Decision**:
  - **Manual (015)**: `user_eligible_for_ciclo` intacto — ativo ∧ `data_entrada` ∧ `data_entrada ≤ admitidos_ate`.
  - **Automático**: predicado separado `user_eligible_for_auto_marco(user, *, ano, mes, hoje)` / serviço de lote:
    1. `user.is_active`
    2. `data_entrada` NOT NULL
    3. `next_future_marco(data_entrada, hoje).year/month == (ano, mes)`
    4. Não bloqueado por FR-008 (possui **qualquer** ciclo com `status=aberto` no momento do marco) → gera alerta, **não** matricula
  - Ciclos automáticos **não** usam `admitidos_ate` como predicado de matrícula do lote (campo pode ficar NULL ou espelhar fim informativo — ver data-model; abertura manual continua exigindo corte).
  - Mid-cycle `ensure_avaliacao_for_user(user, ciclo=auto)`: elegível só se ainda no predicado da coorte daquele ciclo **e** janela/idempotência permitir; **nunca** recupera marco passado.
- **Rationale**: FR-001…FR-008, FR-011, FR-017; evita misturar corte 015 com ritmo de admissão.
- **Alternatives considered**:
  - Reusar `admitidos_ate` = último dia do mês do marco — rejeitado: confunde caminho manual e automaticidade do predicado.
  - Matricular quem tem ciclo aberto — rejeitado (default FR-008 fechado).

Detalhe: [marco-eligibility-contract.md](./contracts/marco-eligibility-contract.md).

---

## R3 — 1º dia útil + feriados Brasil nacional (sem lib nova)

- **Decision**: Módulo puro `apps/core/calendar_br.py` (ou `apps/cycles/services/business_days.py` se preferir colocalizar — preferência **core** por reuso):
  - Lista/algoritmo de feriados **nacionais** (fixos + móveis via Páscoa gregoriana).
  - `is_business_day(d) -> bool` (seg–sex ∧ ¬feriado nacional).
  - `first_business_day_of_month(year, month) -> date`.
  - Task diária: se `hoje != first_business_day_of_month(hoje.year, hoje.month)` → no-op de abertura (ainda pode registrar “rodou / não era dia”).
- **Rationale**: Spec Assumptions + Princípio I (sem dependência nova). Zero utilitário existente no repo (exploração 2026-09-09).
- **Alternatives considered**:
  - Pacote `holidays` / `workalendar` — rejeitado nesta feature (complexidade/deps); reabrir só se manutenção do algoritmo ficar cara.
  - Só seg–sex ignorando feriados — rejeitado (clarifications).
  - Feriados estaduais/municipais — **fora** (FR-020).

---

## R4 — Prazo 20 dias corridos

- **Decision**: Na ativação do ciclo automático, `data_inicio = hoje` (dia útil da abertura), `data_fim = data_inicio + timedelta(days=20)`. Help text / copy RH: prazo de conclusão da avaliação; encerramento em massa na `data_fim` pode ser assistido (como hoje o encerramento é manual) — governança evidencia atraso (rose) quando ultrapassado.
- **Rationale**: FR-006; alinhável a lembretes existentes que já olham `ciclo.data_fim`.
- **Alternatives considered**: 20 dias úteis — rejeitado (spec: corridos). Auto-close hard no Beat — opcional futuro; não bloqueia esta feature se atraso estiver visível.

---

## R5 — Bootstrap legado (ESSENCIAL)

- **Decision**: `next_future_marco(data_entrada, ref_date)` retorna o menor mês de marco **≥ mês(ref_date)** na série `mês(admissão) + 6k`. **Nunca** materializa k passados. Go-live no meio do mês após o 1º dia útil: aquele mês **não** abre “atrasado”; espera o próximo marco futuro de cada pessoa (e o próximo 1º dia útil correspondente).
- **Rationale**: Clarifications + FR-005; SC-002.
- **Alternatives considered**: Backfill de marcos 2022–2026 — **proibido**. Abrir mês corrente se go-live após 1º dia útil — **proibido**.

---

## R6 — Alerta de ciclo ainda aberto (não-bloqueio)

- **Decision**:
  1. Antes/durante o lote, para cada candidato elegível por marco que já participa de **algum** ciclo `aberto`: emitir evento de alerta (persistido + e-mail aos `is_admin` ativos, padrão digest PDI) identificando pessoa + ciclo(s) aberto(s).
  2. **Não** abortar/adiar criação da coorte nem matrícula dos demais.
  3. A pessoa em alerta **não** recebe Avaliação no novo ciclo automático daquele marco.
  4. Idempotência: reexecução no mesmo dia não reenvia spam (dedupe `NotificacaoLog` por destinatário+tipo+referência+janela).
- **Rationale**: FR-007, FR-008, FR-016.
- **Alternatives considered**: Bloquear lote — rejeitado. Matricular mesmo assim — rejeitado pelo default fechado FR-008.

---

## R7 — Múltiplos ciclos abertos (impacto mapeado)

- **Decision**: Remover invariante “no máximo um `aberto`”:
  - Apagar/`no-op` `Ciclo._validate_single_open` em `clean`/`save`.
  - `open_cycle` manual **não** levanta `CycleAlreadyOpenError` por existência de outro aberto (pode manter erro se tentar reabrir o **mesmo** ciclo).
  - Copy UI `ciclo_list.html` (“Só um ciclo…”) → texto multi-open honesto.
  - Introduzir `get_open_ciclos() -> QuerySet/list` ordenado por `-data_inicio`.
  - `get_open_ciclo()` passa a significar **default operacional** = primeiro de `get_open_ciclos()` (mais recente por `data_inicio`) — documentar como convenção, não “único”.
  - `grouped_ciclo_options`: grupo `operacional` = **todos** os abertos (não truncar em 1).
  - Context processor `ciclo_aberto`: expor default + lista (`ciclos_abertos`) para topbar/badge não mentir.
  - `ensure_avaliacao_for_user` **sem** `ciclo=`: **deixar de escolher silenciosamente** um aberto ambíguo para criação nova — preferência: exigir `ciclo` explícito em caminhos de escrita; mid-cycle organization forms devem passar o ciclo alvo (manual aberto mais recente **com corte**, ou política documentada). Caminho automático **sempre** passa o ciclo da coorte.
  - Aderência daily já itera todos os abertos — manter.
- **Rationale**: FR-010; exploração mostrou validação em modelo + `open_cycle` + UI + helpers singulars.
- **Alternatives considered**: Manter um aberto e enfileirar meses — contradiz “alerta não bloqueia”. Ciclo “guarda-chuva” único — não é Opção A.

Detalhe: [multi-open-ciclo-contract.md](./contracts/multi-open-ciclo-contract.md).

---

## R8 — Compatibilidade com abertura manual 015

- **Decision**: `open_cycle(..., admitidos_ate=)` permanece; pode coexistir com ciclo(s) automático(s) aberto(s). Checklist 008 continua avisório. Imports/histórico 011+ intactos.
- **Rationale**: FR-011, FR-018, SC-009.
- **Alternatives considered**: Desligar manual — rejeitado. Forçar fechar auto antes de manual — rejeitado (seria bloqueio).

---

## R9 — AuthZ e escopo

- **Decision**: Governança global = mesmo gate `AdminCyclesMixin` / `RequiresAdminMixin` / `user.is_admin`. Zero papel novo. Visibilidade de avaliações para líder/colaborador continua `get_visible_users` / `ScopedObjectMixin`. Tasks de e-mail só para admins ativos. UI esconder ≠ autorizar.
- **Rationale**: Constitution II; FR-012…FR-014; precedente 015/017.
- **Alternatives considered**: Papel `is_rh` — rejeitado (FR-019).

---

## R10 — Rotina assíncrona (Princípio VI)

- **Decision**: `apps.cycles.tasks.run_auto_cycle_admission_daily` no Beat (ex.: 00:30, após overdue PDI). Orquestra: calendário → elegíveis → alertas → `open_auto_cohort` idempotente → auditoria. Endpoint HTTP admin, se existir, **só** consulta governança / no máximo “reprocessar idempotente” com AuthZ — **não** é o disparo primário do marco.
- **Rationale**: FR-021; Constitution VI.
- **Alternatives considered**: Abrir na view de lista de ciclos — rejeitado. Management command only sem Beat — insuficiente para produção contínua (command pode existir para ops/teste).

Detalhe: [auto-cohort-open-contract.md](./contracts/auto-cohort-open-contract.md).

---

## R11 — UX / consistência visual

- **Decision**: Governança do automático vive sob **Ciclos** (Governança & Cadastros): mesma tipografia (Fraunces h1 + Source Sans 3), Lush Professional, `rounded-lg`, filter bar/`<details>`, badges pastel, empty states guiados, um CTA primário soberano (ex.: “Ver pendências sem admissão” ou “Abrir ciclo manual” conforme viewport — ver contrato). Semântica: slate = neutro/espera; amber = atenção (alerta ciclo aberto, pendência cadastro); rose = prazo 20d estourado ou falha real da rotina; emerald = brand/sucesso/CTA.
- **Rationale**: Diretrizes canônicas + Freeze v2 + precedente 017 `ui-visual-consistency.md`.
- **Alternatives considered**: Dashboard analitico novo / SPA — rejeitado. Cards gamificados de “streak de marco” — rejeitado.

---

## R12 — Observabilidade / auditoria

- **Decision**:
  - `write_audit_log` na criação/abertura automática do ciclo (Ciclo **não** está nos signals atuais).
  - Eventos de governança persistidos (modelo leve de run/evento **ou** reuso `NotificacaoLog` + AuditLog — preferência: **AutoCycleRun** + **AutoCycleEvent** append-oriented para RH ler em linguagem de negócio; AuditLog para trilha técnica).
  - Falha parcial: marca run como `parcial`/`falha`; reexecução idempotente não duplica ciclo/avaliações.
- **Rationale**: FR-015, FR-016, Constitution III.
- **Alternatives considered**: Só logs de aplicação — rejeitado (RH não governa por log técnico).

---

## Best practices (stack)

| Tema | Prática adotada |
|---|---|
| Idempotência de lote | Unique constraint em chave de coorte (`origem=automatico` + `marco_competencia`) + `get_or_create` / select_for_update |
| Celery | `@shared_task` nome estável + Beat; work no task, não na request |
| E-mail RH | Dedupe `already_sent`; template `emails/base.html` |
| Testes de calendário | Datas fixas + feriados conhecidos (ex.: 1º jan, carnaval derivado) |
| Multi-open | Testes de regressão em `get_open_ciclo`, seletor, enrollment |

---

## Resolução de unknowns

Todos os itens do Technical Context estavam preenchíveis a partir das clarifications + código. **Nenhum NEEDS CLARIFICATION** restante.
