# Contract: Backend-authoritative AuthZ & Scope (018)

**Gate constitucional**: Princípio II — segurança e escopo **sempre no backend**; UI **nunca** decide elegibilidade, abertura, alerta ou visibilidade.

## Regra de ouro

| Camada | Pode | Não pode |
|---|---|---|
| **Backend** (services, tasks, views, queryset) | Calcular marco, abrir coorte, alertar, matricular, filtrar governança | Confiar em flag de template/JS como autorização |
| **Template / HTMX** | Ocultar links de governança para não-admin | Ser a única barreira; “esconder = seguro” |
| **E-mail / link** | Apontar para URL de governança | Expandir AuthZ ao abrir |
| **Celery** | Usar `is_admin` / hierarquia reais no envio | Disparar lote a partir de session de usuário anônimo |

**Teste de ouro**: manipular URL de governança / ids de run / query de período **não** vaza fila organizacional para líder/colaborador. Esconder botão ≠ controle de acesso. HTTP **não** é o processador autoritativo do lote do mês (mesmo que exista reprocesso admin idempotente).

## Matriz por superfície

| Superfície | Resolução no backend | UI só apresenta |
|---|---|---|
| Task Beat abertura | Serviço `auto_cohort` + predicados; sem user UI | — |
| Governança global (entrantes/sem data/alertas/falhas) | `AdminCyclesMixin` / `RequiresAdminMixin` (`is_admin`) | Lista/KPIs |
| Abrir ciclo manual 015 | `open_cycle` + corte; AuthZ admin | Form |
| Avaliações no ciclo | `get_visible_users` / ScopedObjectMixin intactos | Listagens existentes |
| Alerta e-mail “ciclo ainda aberto” | Destinatários = admins ativos no task | — |
| Multi-open seletor | Queryset de abertos no server; default documentado | Options renderizadas |
| Enrollment | Predicado + `ciclo` explícito no caminho auto | — |

## Lógica de negócio (nunca no front)

- Cálculo de próximo marco futuro / 1º dia útil
- Elegibilidade automática e FR-008
- Criação idempotente da coorte
- Contagens de governança
- Decisão de emitir alerta vs matricular
- “Pode ver governança automática”

Template pode espelhar flags **já calculadas** no context (`can_manage_cycles`, contagens, status do run).

## Anti-padrões (rejeitar no review)

1. Calcular elegíveis no Alpine/JS a partir de payload completo.
2. Endpoint público de “rodar automático agora” sem admin + sem idempotência.
3. Líder acessando `/cycles/auto/...` via URL direta → deve 403.
4. Confiar que `origem=automatico` no GET autoriza mutação.
5. Task que e-maila qualquer `is_staff` sem `is_admin`.
6. UI que “bloqueia” lote por alerta enquanto o backend seguiria (ou o inverso: UI libera e backend deveria negar matrícula FR-008).

## Testes mínimos de segurança

- Não-admin GET governança → 403.
- Não-admin POST reprocesso (se existir) → 403.
- Líder não vê lista nominativa org de “sem admissão”.
- Admin vê contagens coerentes com eventos persistidos.
- Dois runs no mesmo dia → sem duplicar ciclo/avaliações; dedupe de e-mail.

## Relação

- Visual: ocultar ≠ autorizar — [ui-visual-consistency.md](./ui-visual-consistency.md)
- Abertura: [auto-cohort-open-contract.md](./auto-cohort-open-contract.md)
- Elegibilidade: [marco-eligibility-contract.md](./marco-eligibility-contract.md)
