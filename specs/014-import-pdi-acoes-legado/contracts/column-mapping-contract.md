# Contract: Mapeamento Coluna → Campo Django

**Feature**: `014-import-pdi-acoes-legado`  
**Fonte**: [spec.md](../spec.md) Assumptions; [data/legado-solides/README.md](../../../data/legado-solides/README.md) Decisão #22 § `backup_pdi_*`  
**Data**: 2026-08-19

Contrato normativo coluna Sólides → domínio Greenn People para `pdi.PDI` e `pdi.AcaoPDI`.

Dump 2026-06-24: ~86 linhas; 67 `finalizado` / 19 `em_andamento`. **Sem** ID Sólides de PDI no export.

---

## `backup_pdi_*.xlsx` → `PDI` + `AcaoPDI`

### Colunas obrigatórias (parse fatal se ausentes no header)

| Coluna Sólides | Obrigatória no header | Uso | Regras |
|---|---|---|---|
| `Nome` | sim | Resolve `PDI.usuario` / `AcaoPDI.responsavel` | `canonical_key`; vazio/ambiguo/miss → órfão (não-fatal) |
| `Título do PDI` | sim | `PDI.titulo` | `display_name`; vazio → conflito; `len>200` → conflito (não truncar) |
| `Status` | sim | `PDI.status` | `finalizado`→`concluido`; `em_andamento`→`ativo`; senão conflito. **Não** arquivado |
| `Objetivo` | sim | Parte 1 da `AcaoPDI.descricao` | Omitir se vazio após `display_name` |
| `Situação Atual` | sim | Parte 2 | Idem |
| `Situação Desejada` | sim | Parte 3 | Idem |
| `Data de Entrega` | sim | `AcaoPDI.prazo` | `parse_legacy_date`; ausente/ilegível → conflito; **não** inventar |

Células vazias em colunas presentes **não** são erro de parse; a persistência decide conflito/órfão.

### Colunas opcionais (parse se o header existir; ausência **não** é fatal)

| Coluna Sólides | Uso | Regras |
|---|---|---|
| `Criado em` | Instante do digest se parseável | `parse_legacy_datetime`; ilegível/ausente → omitir do material (não falha a linha só por isso) |
| `Identificador Solicitação` | Relatório informativo | **Não** FK; **não** bloqueia linha resolvível; seção `orfaos_solicitacao` |
| ID Sólides da pessoa (se o dump trouxer, ex. `Identificador` / `Identificador Avaliado`) | Reforço de match | Conflito se ID e nome único divergirem; **não** exigir a coluna |

### Colunas **não** importadas (presença ≠ persistir)

CPF, RG, CTPS, PIS, banco, endereço, telefone, e-mail — FR-018. `backup_treinamentos` **fora**.

---

## Concatenação da descrição (FR-005)

```text
trechos = [display_name(Objetivo), display_name(Situação Atual), display_name(Situação Desejada)]
trechos = [t for t in trechos if t]          # omite vazios
descricao = "\n\n".join(trechos)             # separador documentado
se descricao == "": conflito descricao_vazia  # não persiste PDI
```

Ordem fixa. Sem rótulos extras. **Não** três ações.

---

## Digest (`PDI.solides_id`)

Normativo: [research.md R-digest](../research.md).

```text
material = canonical_key(Nome) + "\n" + display_name(Título do PDI)
se Criado em → datetime UTC parseável:
    material += "\n" + dt_utc.isoformat()
solides_id = "pdi_" + sha256(utf-8(material)).hexdigest()[:40]
# 44 caracteres; unique do schema vigente
```

**MUST NOT** persistir nome/título concatenados nesse campo.  
**MUST NOT** hex 64. Upsert do PDI **por** `solides_id`.

---

## Chave natural da ação (sem coluna / sem DDL)

```text
(pdi_id, display_name(descricao), prazo: date)
```

Match → inalterado. Divergência no mesmo digest de PDI → conflito `acao_chave_divergente` (sem 2ª ação).

---

## Datas — `Data de Entrega` e `Criado em`

Reutilizar `apps/accounts/services/legacy_import/dates.py` (**sem** openpyxl):

| Coluna | Função | Destino |
|---|---|---|
| `Data de Entrega` | `parse_legacy_date` | `AcaoPDI.prazo` (`date`) |
| `Criado em` | `parse_legacy_datetime` | só material do digest (não grava `created_at` legado nesta fatia) |

Aceita: serial Excel (epoch 1899-12-30; fração de dia só no datetime), `date`/`datetime` tipados openpyxl, strings ISO / `fromisoformat`, `0` / vazio → ausente.

Data da carga (atraso FR-011) = `timezone.localdate()` no início da execução — **não** a data `Criado em`.

Estender `dates.py` **somente** se surgir formato não coberto pelo dump 6.5.6.

---

## Status (de-para)

### PDI

```text
normalize = display_name(Status).casefold()
finalizado   → concluido
em_andamento → ativo
*            → conflito status_desconhecido
```

### Ação (FR-011, **antes** do save)

```text
PDI concluido                         → concluida
PDI ativo e prazo < data_carga        → atrasada
PDI ativo e prazo >= data_carga       → pendente
```

Hook `recalculate_overdue_status` (via `save`): pode só rebaixar `atrasada→pendente` se `prazo>=hoje`.

---

## Identificadores canônicos (pessoa)

Se coluna de ID da pessoa existir, reusar `canonicalize_id` de `parse_xlsx.py` (010):

```text
canonicalize_id(value) =
  str(int(value)) se float/int integral (ex. 123.0 → "123")
  senão strip(str(value))
```

Nome: `canonical_key` / `display_name` da 003 — **IMPORTAR**, não copiar.

---

## Parser (`parse_pdi_xlsx`)

- Único módulo com openpyxl: `apps/accounts/services/legacy_import/parse_xlsx.py`.
- Arquivo ausente / OOXML inválido / colunas obrigatórias ausentes → `LegacyParseError` (exit 1, zero writes).
- Dataclass de linha: valores crus; domínio interpreta datas/status/digest.
