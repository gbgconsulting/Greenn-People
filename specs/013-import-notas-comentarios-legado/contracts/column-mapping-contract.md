# Contract: Mapeamento Coluna → Campo Django

**Feature**: `013-import-notas-comentarios-legado`  
**Fonte**: [spec.md](../spec.md) Assumptions; [data/legado-solides/README.md](../../../data/legado-solides/README.md) § notas/comentários  
**Data**: 2026-08-18

Contrato normativo coluna Sólides → domínio Greenn People para notas (`AvaliacaoCompetencia`) e comentários (`Feedback`). Cabeçalhos (`--avaliacoes`) reusam o parser **já existente** da 011 — esta fatia **não** redefine essas colunas.

---

## `backup_notas_avaliacoes_*.xlsx` → `reviews.AvaliacaoCompetencia`

Dump 2026-06-24: ~7.360 linhas; escala 1–5; ~2.213 auto / ~5.147 líder. **Sem** coluna de nível esperado.

### Colunas obrigatórias (parse)

| Coluna Sólides | Obrigatória | Uso | Regras |
|---|---|---|---|
| `Identificador` | sim | rastreio de linha no relatório | String canônica; **não** vira PK Django |
| `Identificador Avaliação` | sim | Resolve `Avaliacao` (canônico / mapa / órfão) | `canonicalize_id` |
| `Nome Avaliador` | sim* | `is_auto` via `canonical_key` | Ambos não-vazios + iguais → auto |
| `Nome Avaliado` | sim* | `is_auto` | Idem |
| `Identificador Habilidade` | sim | Resolve `Competencia.solides_id` | Extra sob R11 |
| `habilidade` | sim* | Nome para filtro KPI + create extra | `display_name` / `canonical_key` no filtro |
| `Fator no Momento` | sim* | `peso_utilizado` | Ausente/inválido/≤0 → conflito; **não** assumir 1 |
| `Nota` | sim | `nota_autoavaliacao` **ou** `nota_lider` | Fora da escala → conflito; sem clip |

\* Necessárias para a regra de negócio; ausência → conflito/`nao_importavel` da linha (não-fatal).

### Colunas **ausentes** neste dump (não parsear / não inventar)

| Coluna | Destino | Política |
|---|---|---|
| (nível esperado) | `nivel_esperado_utilizado` | Derivar `nivel_esperado_for(avaliado.cargo.nivel)` — clarification #2 |

### Auto vs líder

```text
is_auto(row) =
  canonical_key(Nome Avaliador) == canonical_key(Nome Avaliado)
  and canonical_key(Nome Avaliado) != ""

Nota → nota_autoavaliacao se is_auto else nota_lider
```

Reutilizar `canonical_key` da 003. Nunca copiar um campo no outro.

---

## `backup_comentarios_avaliacoes_*.xlsx` → `reviews.Feedback`

Dump 2026-06-24: ~1.494 linhas.

### Colunas obrigatórias (parse)

| Coluna Sólides | Obrigatória | Uso | Regras |
|---|---|---|---|
| `Identificador Solicitação` | não | contexto/relatório | Não inventa ciclo |
| `Nome Solicitação` | não | ignorada no persist | |
| `Identificador` | sim | Resolve `Avaliacao` (mesmo R4 das notas) | É o ID de **avaliação**, não do comentário |
| `Identificador Avaliador` | sim | Resolve `autor` (`User.solides_id`) | Fallback nome único |
| `Nome Avaliador` | sim* | tipo auto vs líder + fallback autor | `canonical_key` |
| `Identificador Avaliado` | não | relatório / `is_auto` | |
| `Nome Avaliado` | sim* | `is_auto` para `Feedback.tipo` | |
| `Comentário` | sim | `Feedback.conteudo` | Persistido no DB; **mascarado** no relatório |
| `Criado em` | sim* | `ciente_em` (lider) + chave natural / `created_at` | serial Excel via `dates.py` |

\* Ausência de `Criado em` interpretável em feedback **líder** → conflito `ciencia_data_invalida` (não persistir nulo em massa). Colaborador: `ciente_em` permanece `null`.

### Tipo

```text
Feedback.tipo = COLABORADOR se is_auto else LIDER
```

---

## `--avaliacoes` (`backup_avaliacoes_*.xlsx`) — só mapa

Reusar `parse_avaliacoes_headers_xlsx` + colunas da [011 column-mapping](../../011-import-ciclos-avaliacoes-legado/contracts/column-mapping-contract.md) § avaliações. Esta fatia **não** persiste cabeçalhos.

---

## `--habilidades` opcional (`backup_habilidades_*.xlsx`)

Usado **somente** para completar `tipo`/`nome` de extras criadas como FK de nota.

| Coluna Sólides | Uso |
|---|---|
| `Identificador` | `Competencia.solides_id` |
| `Habilidade` | `nome` |
| `Grupo` | `map_grupo_tipo` → `tipo` |

**Proibido**: persistir a matriz `backup_habilidades_cargo_*` (~2.720).

---

## Datas — `Criado em` (serial Excel)

Reutilizar / estender `apps/accounts/services/legacy_import/dates.py`:

- serial Excel (epoch 1899-12-30), **incluindo fração de dia** → `datetime`
- `date`/`datetime` tipados openpyxl
- strings ISO / `fromisoformat`
- `0` / vazio → ausente

Se só `date` (sem hora) → `datetime` à meia-noite, tornada aware se `USE_TZ`.  
**Não** importar openpyxl em `dates.py`.

`ciente_em` (líder) = esse instante. Fallback documentado: se `Criado em` faltar mas `created_at` legado for gravável, usar o mesmo instante — no dump de referência a fonte é a coluna `Criado em`.

---

## Identificadores canônicos (string)

Reusar `canonicalize_id` de `parse_xlsx.py` (010/011):

```text
canonicalize_id(value) =
  str(int(value)) se float/int integral (ex. 123.0 → "123")
  senão strip(str(value))
```

---

## Fator / Nota (numéricos)

```text
parse_decimal(Fator no Momento):
  vazio / não-numérico / ≤ 0 → conflito fator_invalido

parse_decimal(Nota):
  vazio / não-numérico → conflito nota_invalida
  fora de [escala.valor_minimo, escala.valor_maximo] → conflito nota_fora_da_escala
```
