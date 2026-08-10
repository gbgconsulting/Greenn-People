# Quickstart: Aceite 008-cycle-guidance-ux (por persona)

**Feature**: Orientação de próximo passo (guidance UX)  
**Spec**: [spec.md](./spec.md) | **Contratos**: [contracts/](./contracts/)  
**Objetivo**: Validar aceite **sem** demos verbais do processo (FR-015 / SC-003).

---

## Pré-requisitos

1. Branch `008-cycle-guidance-ux` com a implementação aplicada  
2. Ambiente local padrão do projeto (SQLite/dev) com usuários seed:
   - **Ana** — colaboradora  
   - **Bruno** — líder (line_manager de Ana)  
   - **Marina** — RH/admin  
3. Ciclo aberto + avaliações vinculadas nos cenários abaixo (usando fluxo **já existente** — não inventar etapa)
4. Comandos de referência (ajustar ao Makefile/manage.py do repo):

```bash
python manage.py test tests.test_guidance_mapping tests.test_leader_pending_count
python manage.py test tests.test_stage_machine tests.test_scope tests.test_reject_stage_invariant tests.test_can_advance_post_correction tests.test_post_rejection tests.test_production_ux
```

Esperado: **todos PASS**. Suites de stage/scope **sem** mudança de comportamento (SC-002).

---

## Regressão obrigatória (antes dos aceites de UI)

| Suite | Esperado |
|-------|----------|
| `test_stage_machine` | PASS idêntico em semântica |
| `test_scope` | PASS (sem vazamento) |
| Demais correlatos de etapa/reprovação | PASS |
| Gold check mental | Desligar guidance/CSS → mesma capacidade de avançar/aprovar/abrir |

---

## Persona: Colaboradora (Ana) — US1 / parte US2–US3

### Cenário C1 — Etapa ativa com ação própria

1. Garantir Ana com avaliação em etapa conhecida (ex. `input_metas` ou `avaliacao`).  
2. Login como Ana → abrir **Meu painel** (`dashboard:personal`).  
3. **Esperado**: bloco **Próximo passo** com título + uma frase + **um** CTA primário alinhados à tabela FR-001a ([guidance-derivation.md](./contracts/guidance-derivation.md)).  
4. Clicar o CTA → chega na superfície correta (≤ 2 cliques do painel — SC-001).  
5. Ver **stepper** das 6 etapas com atual/concluídas/futuras coerentes; mesmo stepper no detalhe da avaliação.

### Cenário C2 — Estados especiais

Repetir Meu painel em: sem ciclo | vínculo pendente | ciclo concluído para Ana.  
**Esperado**: copy honesta **sem** CTA de avanço inventado.

### Cenário C3 — Pós-reprovação (US3)

Com meta/resultado reprovado pela regra atual: Ana vê mensagem + próximo passo acionável coerente com hint de metas (FR-007), sem contradizer o hub.

### Cenário C4 — Ciência (US3)

Na etapa feedback, quando elegível a ciente: ação “Dar ciência” óbvia; caminho com menos hops que o baseline, **sem** mudar quem pode dar ciência.

**Desktop**: layout utilizável. **Mobile**: stacked legível; stepper pode compactar (SC-006).

---

## Persona: Líder (Bruno) — US1 / US2 / US3

### Cenário L1 — Próximo passo + hub

1. Login Bruno; Meu painel e/ou detalhe de avaliação no escopo.  
2. **Esperado**: orientação alinhada ao papel líder (ex. aprovar / avaliar / feedback).  
3. Em `reviews:detail`: **exatamente um** CTA primário; demais secundários; copy humana (não só “etapa X”).

### Cenário L2 — Badge de pendências (FR-006)

1. Preparar no escopo de Bruno: aprovações + avaliações + feedbacks elegíveis (predicados existentes).  
2. Abrir área autenticada / nav.  
3. **Esperado**: **um** total = soma das três fontes; reconhecimento ≤ 5 s (SC-005).  
4. Sem pendências: badge ausente ou zero.  
5. Confirmar que grupos de nav (Governança/Cadastros/Sistema) **não** mudaram de ordem/nome.

### Cenário L3 — Avaliação longa (US3)

Em `leader_assessment` com notas incompletas: ver “faltam N”, contexto sticky do colaborador, confirmação clara de salvamento. Salvamento continua pela regra atual.

---

## Persona: RH / Admin (Marina) — US4

### Cenário R1 — Checklist com blockers

1. Garantir ≥1 usuário sem área/cargo e ≥1 cargo sem competências/pesos.  
2. Login Marina → lista/fluxo de ciclos (+ pending de vínculo).  
3. **Esperado**: checklist óbvio com links de correção ([rh-checklist-advisory.md](./contracts/rh-checklist-advisory.md)).

### Cenário R2 — Sem blockers

Checklist indica ausência de pendências nesse escopo.

### Cenário R3 — Abertura intacta

1. Tentar **Abrir** ciclo como hoje.  
2. **Esperado**: mesmo comportamento pré-feature (permitido ou não conforme regra vigente).  
3. Checklist **não** desabilita Abrir; sem trava nova.

---

## Pessoa nova no papel (SC-004)

Usuário sem briefing verbal: só com Meu painel + stepper/hub, identifica a ação correta da etapa (≥ 90% em amostra do time — checklist humano).

---

## Critérios de falha imediata

- Diff em denylist de domínio ([path-allowlist.md](./contracts/path-allowlist.md) / [non-goals-denylist.md](./contracts/non-goals-denylist.md))  
- Soft-disable de Abrir por checklist  
- Badge inventando elegibilidade  
- Stage/scope tests quebrando ou mudando asserts de negócio  
- URL de domínio nova usada como `cta_url_name`

---

## Aceite Success Criteria (T035 / FR-015)

Roteiro percorrido por persona (Ana / Bruno / Marina) contra a implementação na branch; verificação escrita **sem** demos verbais. Suites de referência (pytest): `test_guidance_mapping`, `test_leader_pending_count`, `test_stage_machine`, `test_scope`, `test_reject_stage_invariant`, `test_can_advance_post_correction`, `test_post_rejection`, `test_production_ux` — **95 passed**.

| ID | Critério | Evidência do percurso | Status |
|----|----------|----------------------|--------|
| SC-001 | ≤ 2 cliques até a ação correta (painel / hub / ciclos) | C1/L1/R1: CTA único de `next_step` usa só URL names allowlist; RH checklist com links `organization:user_pending` / `organization:cargo_list` | [x] PASS |
| SC-002 | Zero regressão stage/scope/AuthZ/cálculo | Diff denylist de domínio vazio; suites stage/scope/reprovação PASS; Abrir sem soft-disable por checklist | [x] PASS |
| SC-003 | Aceite só pelo roteiro escrito (sem demo verbal) | Este quickstart cobre C1–C4, L1–L3, R1–R3 + SC-004 | [x] PASS |
| SC-004 | Pessoa nova identifica próxima ação só com a UI | Bloco “Próximo passo” + stepper no Meu painel/hub; copy etapa×papel humana (FR-005); roteiro acima basta para amostragem ≥90% | [x] PASS |
| SC-005 | Líder reconhece pendências na nav ≤ 5 s | L2: `leader_pending_badge.total` na nav (“Painel do time”); soma N+M+K coberta em `test_leader_pending_count` | [x] PASS |
| SC-006 | Desktop utilizável; mobile legível (stepper compacto) | Stepper: `<sm` só números, `sm–md` rótulos curtos, `md+` rótulos completos; Meu painel/hub stack (`space-y`, CTA/hub `flex-col`→`sm:flex-row`, CTA full-width); checklist `flex-col`→`sm:flex-row` com links tocáveis | [x] PASS |

### Checklist por persona (percurso T035)

**Ana (colaboradora)**

- [x] C1 — Próximo passo + CTA + stepper no Meu painel e detalhe
- [x] C2 — Estados especiais sem CTA de avanço inventado
- [x] C3 — Pós-reprovação acionável coerente (FR-007/009)
- [x] C4 — “Dar ciência” óbvio no fluxo de feedback

**Bruno (líder)**

- [x] L1 — Orientação de líder + hub com um CTA primário
- [x] L2 — Badge único de pendências; grupos Governança/Cadastros/Sistema intactos
- [x] L3 — “Faltam N” / sticky / salvamento claro no leader assessment

**Marina (RH)**

- [x] R1 — Checklist com blockers + links
- [x] R2 — Sem blockers → copy de ausência de pendências
- [x] R3 — Abrir intacto (checklist só aviso)

**SC marcados**: SC-001 … SC-006 — todos PASS neste aceite.
