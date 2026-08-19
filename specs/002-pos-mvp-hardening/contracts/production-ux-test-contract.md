# Contract: Prontidão de produção, testes e polish HTMX

**Apps**: `config`, `core`, templates, `tests/`

## Health

```http
GET /health/   # ou /healthz/
→ 200 application/json (ou text/plain)
{
  "status": "ok",
  "database": "ok"
}
```

Falha de DB → 503. Sem autenticação (usar network policy / não expor dados sensíveis).

## Static + backup

| Item | Contrato |
|---|---|
| `STATIC_ROOT` | Definido em settings de produção; `collectstatic` no checklist de deploy |
| Serving | WhiteNoise **ou** reverse-proxy — documentar a opção escolhida em `docs/ops/` |
| Backup | `docs/ops/backup.md`: frequência mínima, retenção mínima, comando/procedimento PostgreSQL aplicável |

## Testes automatizados (mínimo)

Suíte `tests/` deve falhar se:

1. Usuário acessa `DetailView` fora de `get_visible_users`.
2. `advance_stage` com pré-condição inválida.
3. Reprovação altera `Avaliacao.etapa`.
4. Reopen/correção não restaura caminho acionável (status incoerente).
5. Mid-cycle cria duplicata.
6. Admin approve sem AuditLog do ator (quando aplicável).

Comando esperado (quickstart): `pytest` (ou `python -m pytest`).

## HTMX / a11y

| Padrão | Contrato |
|---|---|
| Loading | Elementos com `hx-*` longos usam `hx-indicator` + indicador visível até swap |
| Empty | Listas críticas (metas, ações PDI, catálogos) com empty state + CTA se permissão |
| Modal | `role="dialog"` `aria-modal="true"`; Escape fecha; foco inicial; restore no trigger |

Sem Alpine/React; JS mínimo permitido.
