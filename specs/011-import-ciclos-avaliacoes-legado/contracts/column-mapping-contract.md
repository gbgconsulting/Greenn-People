# Contract: Mapeamento Coluna → Campo Django

**Feature**: `011-import-ciclos-avaliacoes-legado`  
**Fonte**: [data/legado-solides/README.md](../../../data/legado-solides/README.md) § Mapeamento + clarifications 2026-08-13  
**Data**: 2026-08-13

Contrato normativo coluna Sólides → domínio Greenn People para solicitações (→ `Ciclo`) e avaliações (→ cabeçalho `Avaliacao` agregado).

---

## `backup_solicitacoes_avalicaoes_*.xlsx` → `cycles.Ciclo`

### Colunas obrigatórias (parse)

| Coluna Sólides | Obrigatória | Campo Django | Regras |
|---|---|---|---|
| `Identificador` | sim | `Ciclo.solides_id` | String canônica (sem `.0` float); chave de idempotência |
| `Nome` | sim | `Ciclo.nome` | Ver § Normalização de nome |
| `Iniciada em` | sim* | `Ciclo.data_inicio` | serial Excel ou ISO via `dates.parse_legacy_date` |
| `Terminada em` | sim* | `Ciclo.data_fim` | idem |
| `Status` | não | → sempre `encerrado` | finished/draft/active/canceled (e demais) → `encerrado` |

\* Valor presente e parseável: se ausente/inválido → conflito; ciclo **não** criado (política conservadora).

### Colunas ignoradas (v1)

| Coluna | Motivo |
|---|---|
| `Criada em` | Auditoria futura; não bloqueia |

### Normalização de nome

```text
normalize_ciclo_nome(raw):
  if raw is numeric / Excel-serial-like:
    d = parse_legacy_date(raw)
    if d: return d.isoformat()          # YYYY-MM-DD estável
    else: conflito nome_serial_ambiguo; não gravar bruto sem report
  else:
    return display_name(strip(raw))     # colapsar whitespace (003)
```

### Status

```text
Ciclo.status = 'encerrado'   # SEMPRE — independente de Status Sólides
# NUNCA 'aberto'
```

### Idempotência

```text
lookup = Ciclo.objects.filter(solides_id=str(Identificador)).first()
if lookup: update nome/datas/status=encerrado se divergir → atualizado|inalterado
else: create
```

---

## `backup_avaliacoes_*.xlsx` → `reviews.Avaliacao` (cabeçalho agregado)

### Colunas obrigatórias (parse / agregação)

| Coluna Sólides | Obrigatória | Uso | Regras |
|---|---|---|---|
| `Identificador` | sim | `Avaliacao.solides_id` canônico / colapsados | String canônica |
| `Identificador Solicitação` | sim | Resolve `Ciclo.solides_id` | Órfão se ciclo ausente |
| `Identificador Avaliado` | sim | Resolve `CustomUser.solides_id` | Fallback nome se miss |
| `Nome Avaliado` | sim* | Fallback resolução + autoavaliação | `canonical_key` |
| `Nome Avaliador` | sim* | Detectar autoavaliação | Igualdade via `canonical_key` |

\* Necessárias para regra canônica (autoavaliação) e fallback de usuário; ausência → grupo pode cair em conflito/`nao_agregavel`.

### Colunas ignoradas nesta fatia

| Coluna | Motivo |
|---|---|
| `Avaiação criada em` (typo legado) | Não deriva etapa; estado terminal fixo |
| Demais colunas de metadados | Fora do cabeçalho mínimo |

### Resolução de FKs

```text
resolve_ciclo(solicitacao_id):
  Ciclo.objects.filter(solides_id=str(solicitacao_id)).first()
  # miss → orfao_ciclo; NÃO inventar Ciclo

resolve_usuario(avaliado_id, nome_avaliado):
  1. CustomUser.objects.filter(solides_id=str(avaliado_id)).first()
  2. se miss: match único por canonical_key(nome_avaliado) == canonical_key(user.nome)
  3. miss/ambíguo → orfao_usuario; NÃO inventar User
  # is_active=False NÃO bloqueia
```

### Estado persistido (fixo)

```text
etapa = 'feedback'
concluida = True
# nota_final_* intocadas / null
# sem AvaliacaoCompetencia / Feedback
```

Agregação completa: [aggregation-contract.md](./aggregation-contract.md).

---

## Datas (compartilhado com 010)

Reutilizar `apps/accounts/services/legacy_import/dates.py`:

- serial Excel (epoch 1899-12-30)
- `date`/`datetime` tipados openpyxl
- strings ISO / `fromisoformat`
- `0` / vazio → ausente

---

## Identificadores canônicos (string)

```text
canonicalize_id(value) =
  str(int(value)) se float/int integral (ex. 123.0 → "123")
  senão strip(str(value))
```

Evita duplicatas `"123"` vs `"123.0"` em `solides_id`.
