# Contract: Badge de pendências do líder

**Feature**: `008-cycle-guidance-ux`  
**Fonte**: [spec.md](../spec.md) FR-006  
**Tipo**: Contagem de apresentação — **não** inventa elegibilidade.

---

## Forma

```text
badge.total = count(aprovacoes_elegiveis)
            + count(avaliacoes_elegiveis)
            + count(feedbacks_elegiveis)
```

UI: **um único** badge/total na navegação do líder (`nav_link` + `nav_menu`).  
Breakdown interno permitido só para testes/debug — não três badges na nav.

Sem pendências: omitir badge **ou** exibir zero (sem alarme falso).

---

## Reuso obrigatório de elegibilidade

Cada parcela MUST espelhar predicados **já usados** nas superfícies operacionais:

| Fonte | Predicado / superfície de referência (reuso) | O que NÃO fazer |
|-------|-----------------------------------------------|-----------------|
| Aprovações | Itens em que `meta_approval_actionable(avaliacao, meta, lider)` seria True (mesma etapa + status + approver) | Contar “todas pendentes” sem checar etapa/approver |
| Avaliações | Avaliações no ciclo aberto, no `get_visible_users(lider)`, etapa `avaliacao`, onde o líder é o ator esperado (mesma regra que já leva ao `leader_assessment`) | Contar fora do escopo / etapa errada |
| Feedbacks | Avaliações onde o líder já poderia criar/conduzir feedback pelas regras atuais (`feedback_create_allowed` + etapa `feedback` conforme produto hoje) | Inventar “feedback pendente” por outro critério |

Escopo: sempre ⊆ hierarquia atual (`get_visible_users`) — **sem alterar** `apps/accounts/services/scope.py`.

---

## Onde vive

- Preferência: funções read-only em `apps/reviews/services/guidance.py` ou sibling `pending_counts.py`
- Exposição: `context_processors` e/ou context do layout — leitura por request autenticado de líder
- Template: `nav_link.html` aceita `badge_count` opcional; `nav_menu.html` passa o total — **sem** reordenar grupos

---

## Navegação IA (FR-013)

Permitido: adicionar contagem visual ao item existente (ex. “Painel do time”).  
Proibido: criar seção nova, mover itens entre Governança/Cadastros/Sistema, renomear grupos.

---

## Testes

- Fixture líder com N aprovações + M avaliações + K feedbacks elegíveis ⇒ `total == N+M+K`
- Usuário fora do escopo **não** entra na soma
- Predicado alterado “só para o badge” = falha deste contrato
