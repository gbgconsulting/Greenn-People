# Contract: Mapeamento Coluna → Campo Django

**Feature**: `010-import-colaboradores-legado`  
**Fonte**: [data/legado-solides/README.md](../../../data/legado-solides/README.md) § Mapeamento  
**Data**: 2026-08-12

Contrato normativo coluna Sólides → domínio Greenn People para `backup_colaboradores` e colunas mínimas de crosswalk em `backup_avaliacoes`.

---

## `backup_colaboradores_*.xlsx`

### Colunas obrigatórias (parse)

| Coluna Sólides | Obrigatória | Campo Django | Regras |
|---|---|---|---|
| `Nome` | sim | `CustomUser.nome` | `display_name()` de normalize 003 |
| `E-mail empresarial` | não* | `CustomUser.email` | 1ª preferência na resolução de e-mail |
| `E-mail` | não* | `CustomUser.email` | 2ª preferência |
| `E-mail pessoal` | não* | `CustomUser.email` | 3ª preferência |
| `Data demissão` | não | `CustomUser.is_active` | serial Excel ou ISO; preenchida → `False` |
| `Cargo` | não | resolução `CustomUser.cargo` | nome display + fallback |
| `Cargo ID` | não | `Cargo.solides_id` | lookup primário de cargo |
| `Departamento` | não | `CustomUser.area` → `Area.nome` | get_or_create |
| `Superior direto id` | não | `CustomUser.line_manager` | **2ª fase**; match `CustomUser.solides_id` |

\* Pelo menos uma coluna de e-mail MUST ter valor por linha importável; ausência nas três → `nao_importavel`.

### Colunas ignoradas (v1)

| Coluna | Motivo |
|---|---|
| `Unidade` | Vazia no dump 2026-06-24 |
| `Data admissão` | Informativo; não bloqueia import |
| CPF, RG, CTPS, PIS | PII — FR-015 |
| Dados bancários, endereço, telefone | PII — FR-015 |

### Regras de transformação

**E-mail**:
```text
resolve_email(row) =
  first_non_empty(
    normalize(strip(row['E-mail empresarial'])),
    normalize(strip(row['E-mail'])),
    normalize(strip(row['E-mail pessoal']))
  )
normalize = collapse_whitespace + CustomUserManager.normalize_email
```

**is_active**:
```text
is_active(row) = NOT is_dismissal_filled(row['Data demissão'])
is_dismissal_filled = parsed_date is not None AND parsed != sentinel_zero
```

**Cargo**:
```text
resolve_cargo(row):
  if row['Cargo ID']: lookup Cargo by solides_id
  else: lookup Cargo by canonical_key(row['Cargo']) among is_active=True
  if miss: create Cargo(nome=display_name(row['Cargo']), nivel=infer_seniority_003, solides_id=row['Cargo ID'] or null)
```

**Area**:
```text
resolve_area(row):
  if not row['Departamento']: return null
  get_or_create Area(nome=display_name(row['Departamento']), defaults={parent: null, is_active: true})
```

**line_manager** (fase B):
```text
if row['Superior direto id']:
  manager = CustomUser.objects.filter(solides_id=str(id)).first()
  if manager: user.line_manager = manager; full_clean(); save()
  else: report gestor_nao_resolvido
```

---

## `backup_avaliacoes_*.xlsx` (crosswalk only)

| Coluna | Uso |
|---|---|
| `Nome Avaliado` | Chave `canonical_key` → índice crosswalk |
| `Identificador Avaliado` | Valor `CustomUser.solides_id` |

Demais colunas ignoradas nesta fatia.

---

## Normalização reutilizada (spec 003)

```text
display_name(s) = collapse_whitespace(strip(s))
canonical_key(s) = casefold(strip_accents(NFKD(display_name(s))))
```

Implementação: `apps/competencies/services/catalog_import/normalize.py` (read-only import).

---

## Colisões e políticas

| Situação | Política |
|---|---|
| E-mail duplicado no backup (linhas distintas) | Conflito; linha posterior **não** sobrescreve |
| Crosswalk ambíguo (mesmo nome, IDs distintos) | Conflito; **não** atribuir `solides_id` |
| Cargo ID presente, nome diverge do catálogo 003 | Preferir match por ID; reportar conflito de nome |
| Superior aponta para demitido | Permitido (gestor histórico inativo) |
| Ativo sem superior | Importar; reportar `sem_gestor` |

---

## Testes MUST validar

- Ordem de preferência de e-mail (3 colunas).
- Serial Excel `45446.0` e ISO `2024-06-01` para demissão.
- Departamento novo → Area criada.
- Cargo só no backup → create com senioridade inferida.
- Colunas PII presentes no arquivo mas **ausentes** no model persistido.
