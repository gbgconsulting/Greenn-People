# Contract: Backend-authoritative AuthZ & Scope (017)

**Gate constitucional**: Princípio II — segurança e escopo **sempre no backend**; UI **nunca** decide autorização; templates/HTMX/JS **nunca** calculam regra de negócio de quem vê/muta.

## Regra de ouro

| Camada | Pode | Não pode |
|---|---|---|
| **Backend** (views, services, tasks, queryset) | Resolver escopo, filtrar, rejeitar, contar, concluir, notificar | Confiar em param de URL/UI como prova de permissão |
| **Template / HTMX** | Ocultar controles para UX (esconder toggle tabela, CTA) | Ser a única barreira; filtrar “no cliente”; confiar que param `modo`/`atrasadas` implica direito |
| **E-mail / link** | Apontar para URL com filtros | Expandir AuthZ: ao abrir, a view revalida escopo do usuário autenticado |
| **Celery tasks** | Usar hierarquia/`is_admin` reais no momento do envio | Enviar para “lista fixa” sem checar ativo/papel |

**Teste de ouro**: manipular query string (`visao=equipe`, `modo=tabela`, `gestor=`, `atrasadas=1`, pk de outro PDI) **não** vaza dados nem executa mutação fora do escopo. Esconder botão no HTML **não** é controle de acesso.

## Matriz por superfície (obrigatória na implementação)

| Superfície | US | Resolução no backend | UI só apresenta |
|---|---|---|---|
| Hub listagem / filtro atrasadas | US1 | `get_queryset` = ownership + `get_visible_users` + annotate/filter server-side | Chips/links montam query; resultado vem do servidor |
| Toggle Cards \| Tabela | US3 | Se `not can_view_team_ownership_list`: forçar cards / ignorar `modo=tabela` no **view** | Esconde toggle |
| Filtros gestor / área / faixa | US3 | Opções e predicados limitados ao escopo; IDs fora do escopo → ignorados ou 404/lista vazia segura | `<select>` só com opções já filtradas pelo backend |
| Detalhe / board / concluir | US6 | `ScopedObjectMixin` (ou equivalente) em get_object; `complete_pdi` revalida pré-condições no **serviço** | CTA oculto se inelegível; POST sem elegibilidade → rejeição |
| Arquivar / mutar ação | (existente) | Predicados atuais + block arquivado no backend | — |
| KPI dashboard | US5 | Contagem via serviço/queryset scoped ao user da request | Card mostra número; link não autoriza |
| Alerta atraso (e-mail) | US2 | Destinatários = dono + `line_manager` resolvidos no task; skip inativo/arquivado | — |
| Digest admin | US4 | Só `is_admin` ativo; agregação org no task; não-admin nunca entra no loop | — |
| Link do digest/alerta | US2/4 | View de destino reaplica escopo do user logado (SC-005) | — |

## Lógica de negócio (nunca no front)

Deve viver em **service/view/task**, não em template/`{% if %}` como única verdade:

- Contagem de atrasadas / `dias_atraso_max` / faixa
- Elegibilidade `complete_pdi` (100% concluídas + ativo)
- Marcação `atrasada` e disparo de e-mail
- Dedupe `already_sent`
- “Pode ver visão equipe / tabela”

Template pode espelhar flags **já calculadas no context** (`can_complete`, `show_table_toggle`, `acoes_atrasadas_count`) — flags vindas do backend.

## Anti-padrões (rejeitar no review)

1. Filtrar cards/tabela só com Alpine/JS a partir de payload completo da org.
2. Confiar em `request.GET['visao']=='equipe'` sem `can_view_team_ownership_list`.
3. CTA “Concluir” só escondido; POST sem checagem no serviço.
4. Opções de filtro gestor/área com todos os users do banco.
5. Contagem do KPI no template loopando objetos já entregues sem escopo.
6. Task de digest que e-maila qualquer staff sem `is_admin`.

## Testes mínimos de segurança (por fatia)

- Colaborador + `?visao=equipe&modo=tabela&atrasadas=1` → sem dados de terceiros.
- Líder + `gestor=<id fora do escopo>` → vazio ou ignore; sem leak.
- POST concluir em PDI fora do escopo → 403/404 (mesmo padrão ScopedObjectMixin).
- User não-admin não recebe digest; link do digest como colaborador não mostra org inteira.
- Dois runs do job atraso no mesmo dia → sem bypass de dedupe (não é AuthZ, mas integridade do canal).

## Relação com outros contratos

- Listagem: [pdi-overdue-list.md](./pdi-overdue-list.md) §AuthZ  
- Notificações: [pdi-overdue-notifications.md](./pdi-overdue-notifications.md)  
- Lifecycle: [pdi-complete-lifecycle.md](./pdi-complete-lifecycle.md) §AuthZ  
- Visual: [ui-visual-consistency.md](./ui-visual-consistency.md) — ocultar ≠ autorizar
