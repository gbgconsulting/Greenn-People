# Research: 008-cycle-guidance-ux

**Branch**: `008-cycle-guidance-ux`  
**Date**: 2026-08-07  
**Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md)

Todas as ambiguidades de Technical Context foram resolvidas. **Nenhum** `NEEDS CLARIFICATION` restante. Models/migrations **não** são necessários.

---

## R1 — Onde vive o serviço de guidance (leitura)

**Decision**: `apps/reviews/services/guidance.py` (módulo novo, puro leitura).

**Rationale**:
- `Avaliacao.etapa` e `build_fr005_context` já pertencem a `apps/reviews`
- Mapa etapa→orientação da spec é centrado em Avaliação + papel no contexto
- Evita acoplar `core` a domínio de ciclo além de templates compartilhados

**Alternatives considered**:
- `apps/core/services/guidance.py` — bom para UI genérica, mas acoplaria core ao enum de etapas de reviews
- Split core + reviews — overhead desnecessário para v1 desta feature
- Context só em templates (`{% if avaliacao.etapa == ... %}`) — duplica mapa, dificulta testes unitários do contrato

**Constraints no módulo**:
- Funções puras / queries de leitura apenas
- **PROIBIDO** importar/chamar `advance_stage`, `approve_*`, `calcular_nota_*`, mutators
- Retorno tipado (dataclass / TypedDict) alinhado a [contracts/guidance-derivation.md](./contracts/guidance-derivation.md)

---

## R2 — Models / migrations: necessidade mínima?

**Decision**: **Zero** models e **zero** migrations.

**Rationale**: Orientação é 100% derivada de estado já persistido (`Ciclo.status`, `Avaliacao.etapa`, `Meta.status*`, `Feedback.ciente_em`, vínculo área/cargo, `CargoCompetencia`). Nada a persistir como “regra de guidance”.

**Alternatives considered**:
- Model `GuidanceHint` / tabela de copy — overkill; copy vive no mapa estático do serviço (+ spec)
- Field `proximo_passo` em Avaliacao — viola FR-013 / denylist; desalinha se etapa muda sem sync

---

## R3 — Contrato etapa → orientação (derivação)

**Decision**: Função canônica `resolve_next_step(user, *, role_context) -> NextStepGuidance` produzindo:

```text
{ title, body, cta_label, cta_url_name, cta_kwargs, blocked_reason }
```

Fonte da etapa: `Avaliacao.etapa` vigente (ou estados especiais: sem ciclo / vínculo pendente / concluída). Destinos: **somente** URL names já existentes (confirmados no código):

`dashboard:personal`, `dashboard:team`, `goals:meta_list`, `reviews:self_assessment`, `reviews:leader_assessment`, `reviews:feedback_create`, `reviews:feedback_list`, `reviews:feedback_acknowledge`, `reviews:detail`

**Rationale**: Congela FR-001a; testável unitariamente; UI só renderiza; **zero write** de etapa/status.

**Alternatives considered**:
- Hardcode só nos templates — frágil, sem teste de mapa
- Endpoint JSON de guidance — viola “sem rotas de domínio novas” / overkill HTMX

**Nota implementação**: `cta_url_name` + `cta_kwargs` resolvidos com `{% url %}` / `reverse` na view ou template; ausência de CTA (`cta_url_name is None`) coberta por estados especiais e `blocked_reason`.

---

## R4 — Stepper compartilhado

**Decision**: Partial `templates/components/stage_stepper.html` incluso em Meu painel e `avaliacao_detail`. Estados visuais: `concluida | atual | futura | bloqueada`, derivados **somente** do progresso real (etapa atual + regras de bloqueio **já** refletidas no estado — ex. dependência de aprovação = etapa ainda não avançada / flags existentes). Stepper **não** decide se pode avançar.

**Rationale**: FR-002 exige partial shared; reutiliza Freeze (badge/button) sem extensão tipográfica (FR-014).

**Alternatives considered**:
- Componente JS interativo — fora do stack; risco de AuthZ no front
- Dois markups separados painel/detalhe — diverge e viola FR-002

**Mobile**: compactar para números/rótulos curtos (SC-006); desktop é aceite primário.

---

## R5 — Badge de pendências do líder (soma única)

**Decision**: Um total = aprovações elegíveis + avaliações elegíveis + feedbacks elegíveis, com predicados **iguais** aos já usados nas superfícies (`meta_approval_actionable` / filtros equivalentes; avaliações no escopo em etapa `avaliacao` onde o líder atua; feedbacks onde `feedback_create_allowed` / ausência de feedback líder conforme regra atual). Escopo via `get_visible_users` **sem alterar** AuthZ.

Local provável: helper no mesmo `guidance.py` (ou `pending_counts.py` sibling read-only) + exposição via `context_processors` ou context do layout — **apresentação only**.

**Rationale**: FR-006 / clarificação Session: um único badge; sem inventar elegibilidade; sem redesenhar grupos nav.

**Alternatives considered**:
- Três badges separados — rejeitado pela clarificação (soma única)
- Reusar KPI de aderência (`dashboard/services/adherence.py`) — mede prazo histórico de ações já feitas, **não** fila de pendências atuais; inadequado
- Contagem ad-hoc por status sem checar etapa — inventaria elegibilidade falsa (denylist)

**Sem pendências**: badge omitido ou zero (sem alarme).

---

## R6 — Checklist RH pré-abertura

**Decision**: Superfície **somente avisória** em `ciclo_list` (+ reuso de `user_pending` para usuários sem área/cargo). Bloqueadores: (1) usuários ativos sem área/cargo; (2) cargos sem competências/pesos. Links para correção. **Não** disable / soft-lock do botão Abrir; `open_cycle` / `CicloOpenView` mantêm comportamento vigente.

**Rationale**: FR-011 / FR-012 / SC-002; clarificação Session.

**Alternatives considered**:
- Soft-disable Abrir se blockers — **fora de escopo** (FR-013)
- Nova rota `/cycles/preflight/` — desnecessária; enriquecer listagem existente

---

## R7 — Coerência com hint pós-reprovação (FR-007)

**Decision**: Manter `_proximo_passo_pos_reprovacao` em `goals/views.py` como fonte de verdade do hint de metas; o bloco Meu painel / hub deve usar copy compatível (mesma ação corretiva) e **não** contradizer.

**Rationale**: Spec + testes em `test_production_ux.py` já cobrem o helper.

**Alternatives considered**: Mover helper para `guidance.py` agora — opcional refactor mínimo se reduzir duplicação; **não** alterar predicados de elegibilidade de correção.

---

## R8 — US3 (ações longas) sem mudar regras

**Decision**:
- Leader assessment: progress “faltam N notas” = contagem de linhas sem `nota_lider` (leitura do formset/queryset)
- Sticky do colaborador: markup sticky no template
- Save feedback: messaging já existente / confirm visual
- Feedback ciente: hierarquia CTA + menos hops **via copy/links existentes**, sem mudar `can_acknowledge_feedback`

**Rationale**: FR-008–010; ouro: desligar UI = mesmas regras.

---

## R9 — Strategy de testes

**Decision**:
1. Unitários novos: mapa etapa×papel→CTA/destino; estados especiais; soma do badge contra fixtures com predicados conhecidos
2. **Não** alterar asserts de negócio dos testes de stage/scope; apenas garantir PASS contínuo na CI/local
3. Sem suite visual obrigatória; quickstart por persona cobre SC-001–SC-006

**Rationale**: SC-002; FR-015.

---

## R10 — Agent context update

**Decision**: Script `update-agent-context` **não existe** neste repositório (`.specify/scripts` só PowerShell de feature setup). Atualização de contexto de agente: **skip** documentado; artefactos em `specs/008-cycle-guidance-ux/` são a fonte de verdade.

---

## Resumo de decisões fechadas

| Tema | Decisão |
|------|----------|
| Home do serviço | `apps/reviews/services/guidance.py` |
| Schema | nenhum |
| Stepper | `templates/components/stage_stepper.html` |
| Próximo passo | `templates/components/next_step.html` |
| Badge | soma 3 fontes elegíveis existentes |
| Checklist RH | aviso + links; Abrir intacto |
| Rotas | nenhuma de domínio nova |
| Tests | mapping unitário + regressão stage/scope |
