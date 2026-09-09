# Contract: Listagem PDI com atraso (hub + tabela)

**Apps**: `pdi`  
**Views**: `PDIListView` (+ partials HTMX)

## Query params

| Param | Valores | Quem |
|---|---|---|
| `status` | (existente) todos / em andamento / concluídos / arquivados | todos |
| `q` | busca título/nome/e-mail | todos |
| `visao` | `proprias` \| `equipe` | quem `can_view_team_ownership_list` |
| `atrasadas` | `1` = só PDIs com ≥1 ação `atrasada` | todos (respeita escopo) |
| `modo` | `cards` (default) \| `tabela` | só visão equipe; ignorado/forçado cards se colaborador puro |
| `gestor` | id usuário | visão equipe |
| `area` | id área | visão equipe |
| `faixa_atraso` | `1-7` \| `8-30` \| `30+` | visão equipe |

Arquivados: filtro `atrasadas` **não** inclui arquivados salvo `status=arquivados` explícito (padrão operacional = fora).

## Contexto de linha (card e tabela)

```text
pdi, progresso, acoes_atrasadas_count, dias_atraso_max?, proximo_prazo?,
colaborador, gestor?, area?
```

## AuthZ

- Queryset base = ownership + `get_visible_users` (inalterado na regra; só annotate/filter aditivo).
- `modo=tabela` sem permissão de equipe → render cards (ou 400/redirect para cards); nunca vazar linhas fora do escopo.
- Filtros gestor/área limitados a opções **dentro** do escopo do viewer.

## HTMX

- Continua `#list-container` / partial swap.
- Toggle modo e filtros preservam demais query params (como listagens admin).

## Testes de contrato

1. Base com 2 PDIs (1 com atraso, 1 sem) → `atrasadas=1` retorna só o com atraso.
2. Contagem no card = count real.
3. Colaborador não vê PDI de outro nem filtros gestor.
4. Admin `visao=equipe&modo=tabela` vê colunas acordadas.
5. `faixa_atraso=1-7` exclui plano cujo max dias = 10.
6. PDI arquivado fora do filtro operacional de atrasados.
