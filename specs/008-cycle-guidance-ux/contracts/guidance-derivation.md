# Contract: Derivação etapa → orientação (read-only)

**Feature**: `008-cycle-guidance-ux`  
**Fonte**: [spec.md](../spec.md) FR-001a  
**Tipo**: Contrato de UI / DTO — **não** é API REST; **não** há write de etapa/status.

---

## Invariante

```text
orientação = f(estado_já_existente, papel_no_contexto)
f NÃO escreve Avaliacao.etapa | Meta.status* | Feedback.ciente_em | Ciclo.status
```

Desligar o renderer do guidance ⇒ mesmos POST/resultados de negócio.

---

## Shape do DTO

```python
{
  "title": str,
  "body": str,
  "cta_label": str | None,
  "cta_url_name": str | None,   # django URL name já existente
  "cta_kwargs": dict,           # default {}
  "blocked_reason": str | None,
}
```

Alias documental: `NextStepGuidance` ([data-model.md](../data-model.md)).

---

## Allowlist de destinos (`cta_url_name`)

| url name | Confirmado no repo |
|----------|--------------------|
| `dashboard:personal` | sim |
| `dashboard:team` | sim |
| `goals:meta_list` | sim |
| `reviews:self_assessment` | sim |
| `reviews:leader_assessment` | sim |
| `reviews:feedback_create` | sim |
| `reviews:feedback_list` | sim |
| `reviews:feedback_acknowledge` | sim |
| `reviews:detail` | sim |

Qualquer outro `cta_url_name` = **violação** do contrato (exige URL nova ou fora do mapa).

---

## Tabela canônica (derivação)

Copy pode ser polida se preservar **mesmo significado e destino**.

| Estado / etapa | Papel no contexto | Título | Frase (body) | cta_label | cta_url_name |
|----------------|-------------------|--------|--------------|-----------|--------------|
| Sem ciclo aberto | qualquer | Sem ciclo em andamento | Não há ciclo de desempenho aberto no momento. | — | — |
| Vínculo / avaliação pendente | colaborador | Avaliação ainda não vinculada | Seu vínculo ao ciclo ainda não está pronto; acompanhe com o RH se necessário. | — ou Ver painel | `dashboard:personal` ou — |
| `input_metas` | colaborador (dono) | Defina suas metas | Cadastre e ajuste as metas deste ciclo antes de enviar para aprovação. | Ir para metas | `goals:meta_list` |
| `input_metas` | líder (escopo) | Aguardando metas do time | Os colaboradores do seu escopo ainda estão na etapa de metas. | Ver time / metas | `goals:meta_list` ou `dashboard:team` |
| `aprovacao_metas` | líder (ator) | Aprove as metas | Revise e aprove ou reprove as metas pendentes no seu escopo. | Revisar metas | `goals:meta_list` |
| `aprovacao_metas` | colaborador (dono) | Metas em aprovação | Aguarde a decisão do líder; se houver reprovação, corrija e reenvie. | Ver metas | `goals:meta_list` |
| `resultados` | colaborador (dono) | Atualize os resultados | Informe o progresso/resultados das metas deste ciclo. | Atualizar resultados | `goals:meta_list` |
| `resultados` | líder (escopo) | Aguardando resultados | O time ainda registra resultados das metas. | Ver metas do time | `goals:meta_list` |
| `aprovacao_resultados` | líder (ator) | Aprove os resultados | Revise e aprove ou reprove os resultados pendentes. | Revisar resultados | `goals:meta_list` |
| `aprovacao_resultados` | colaborador (dono) | Resultados em aprovação | Aguarde a decisão do líder; se houver reprovação, corrija o progresso e reenvie. | Ver resultados | `goals:meta_list` |
| `avaliacao` | colaborador (dono) | Faça a autoavaliação | Preencha as notas das competências na sua avaliação. | Autoavaliar | `reviews:self_assessment` |
| `avaliacao` | líder (ator) | Avalie o colaborador | Preencha as notas de competências do liderado nesta etapa. | Avaliar | `reviews:leader_assessment` |
| `feedback` | líder (ator) | Registre o feedback | Conduza o feedback da avaliação quando elegível pelas regras atuais. | Ir ao feedback | `reviews:feedback_create` ou `reviews:feedback_list` |
| `feedback` | colaborador (ciente) | Confirme ciência do feedback | Leia o feedback e registre ciência quando a regra atual permitir. | Dar ciência | `reviews:feedback_acknowledge` |
| Ciclo / avaliação concluída | qualquer | Ciclo concluído para você | Não há próxima ação de etapa nesta avaliação. | Ver avaliação | `reviews:detail` |
| Hub (qualquer etapa com ação) | ator elegível | (mesma linha da etapa) | (mesma) | (mesmo CTA; hierarquia FR-004) | Hub = `reviews:detail`; CTA primário = destino da linha |

`cta_kwargs`: tipicamente `{'pk': avaliacao.pk}` para rotas de reviews; vazio para listas.

Quando o papel atual **não** é o ator da ação: preencher `blocked_reason` / copy de espera; **não** inventar avanço.

---

## Stepper (companheiro)

Partial: `templates/components/stage_stepper.html`  
DTO: `StageStepperState` ([data-model.md](../data-model.md))  
Estados visuais: `concluida | atual | futura | bloqueada` — **marcação**, não motor de avanço.

---

## Hub CTA hierarchy (FR-004)

No `avaliacao_detail`:

1. Exactamente **um** controle com variante/estilo **primário**, alinhado a `NextStepGuidance` do ator atual
2. Demais ações: secundárias / terciárias
3. Ação “Avançar etapa” (se já existir) permanece sob as regras atuais de `can_advance` — guidance **não** libera avanço; no máximo clarifica copy

---

## Zero write (checklist de implementação)

- [ ] `guidance.py` sem `.save()` em entidades de ciclo/avaliação/meta/feedback
- [ ] Sem chamar `advance_stage` / `approve_*` / `calcular_nota_*`
- [ ] Sem `transaction.atomic` de domínio no guidance
- [ ] Views só passam DTO no context
- [ ] Testes de stage/scope continuam PASS sem alterar asserts de negócio
