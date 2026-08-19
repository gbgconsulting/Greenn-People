# Data Model: Importação Legado Sólides — PDIs e Ações

**Branch**: `014-import-pdi-legado` | **Date**: 2026-08-19

**Nota**: Esta fatia **não** introduz models novos nem migrations. Persiste `PDI` e `AcaoPDI` no schema vigente; preenche `PDI.solides_id` já existente com digest curto. **Sem** `solides_id` em `AcaoPDI`. **Sem** FK Ciclo/Avaliação. Sem máquina de estados nova.

Models canônicos: [apps/pdi/models.py](../../apps/pdi/models.py), [apps/accounts/models.py](../../apps/accounts/models.py).

Contratos: [contracts/model-allowlist.md](./contracts/model-allowlist.md), [contracts/migration-safety.md](./contracts/migration-safety.md), [contracts/column-mapping-contract.md](./contracts/column-mapping-contract.md).

---

## Regras estritas de models / migrations

### PERMITIDO (esta fatia)

| Alteração | Escopo |
|---|---|
| ORM create `PDI` | 1ª run; `solides_id` = digest; `titulo`/`status`/`usuario` |
| ORM create `AcaoPDI` | exatamente 1 por linha resolvível; `save()` dispara hook de atraso |
| Lookup `PDI` por `solides_id` | 2ª run → inalterado se chave de ação bate |
| Extensão parse/dates/report 010/011/013 | módulos irmãos em `accounts` |
| Samples + testes | `data/legado-solides/samples/pdi_min.xlsx`, `tests/test_import_pdi_legado.py` |

### PROIBIDO

| Proibição | Motivo |
|---|---|
| Qualquer migration / `AddField` / `AlterField` / `RunPython` | FR-019 |
| Alterar tipo, `max_length=50`, unicidade, nullability ou `on_delete` de `PDI.solides_id` | FR-019; constituição III |
| `solides_id` em `AcaoPDI` | FR-009 |
| FK `Ciclo` / `Avaliacao` | FR-007 |
| Inventar `CustomUser` | FR-012 |
| Editar `models.py` / `overdue.py` / `progress.py` / `tasks.py` / views/urls/forms | denylist |
| `bulk_create` bypass `full_clean`/`save` | atraso vive em `save()` |
| Apagar PDI/ação para refazer | FR-017 |
| Usar `raw/` no CI | FR-022 |
| Gravar `PDI.status=arquivado` | FR-010 |

### Persistência obrigatória

- Toda escrita MUST chamar `full_clean()` + `save()`.
- Unidade por linha: PDI **e** ação, ou nenhum.
- `AcaoPDI.save()` MUST ser o caminho do hook (`recalculate_overdue_status`) — **não** chamar o hook solto de forma que pule o model, e **não** editar o módulo.

### O que NÃO muda no model

| Campo / constraint | Estado |
|---|---|
| `PDI.usuario` FK `PROTECT` | intacto |
| `PDI.titulo` `max_length=200` | intacto; overflow → conflito (não truncar em silêncio) |
| `PDI.status` choices (ativo/concluido/arquivado) | intacto; import só usa ativo/concluido |
| `PDI.solides_id` CharField 50 unique nullable indexed | intacto; só **preencher** |
| `AcaoPDI.pdi` FK `PROTECT` | intacto |
| `AcaoPDI.descricao` TextField | intacto |
| `AcaoPDI.responsavel` FK `PROTECT` | intacto |
| `AcaoPDI.prazo` DateField | intacto; obrigatório nesta fatia |
| `AcaoPDI.status` choices | intacto; import usa concluida/atrasada/pendente |
| Sem unique de ação no schema | idempotência **só** no serviço |

---

## Entidade: Colaborador (pessoa) — read-only create

**Model**: `accounts.CustomUser`  
**Fonte desta fatia**: lookup apenas. **Não** cria.

| Campo | Uso |
|---|---|
| `nome` | `canonical_key` para match único |
| `solides_id` | reforço opcional se o dump trouxer ID |
| `is_active` | inativo **permitido**; sem bypass de escopo depois |
| `line_manager` | **nunca** vira `responsavel` |

Zero ou 2+ matches → `orfaos_usuario`. ID vs nome único divergente → conflito.

---

## Entidade: PDI (plano)

**Model**: `pdi.PDI`  
**Fonte**: `backup_pdi_*` (~86)

### Campos persistidos

| Campo | Origem | Regras |
|---|---|---|
| `usuario` | R5 | Nunca inventar |
| `titulo` | `display_name(Título do PDI)` | vazio → conflito; >200 → conflito |
| `status` | FR-010 | `finalizado`→`concluido`; `em_andamento`→`ativo`; senão conflito |
| `solides_id` | R-digest | `pdi_` + sha256 hex[:40]; upsert por este valor |

### Chave natural (material do digest — **não** persistida em claro)

```text
canonical_key(Nome) + "\n" + display_name(título) [+ "\n" + ISO UTC de Criado em]
```

### Validação / upsert

| Situação | Ação |
|---|---|
| Digest novo + linha ok | Create + 1 ação |
| Digest existe + mesma chave de ação | Inalterado |
| Digest existe + ação divergente | Conflito; sem 2ª ação; sem delete |
| Título/status divergem na 2ª run | Inalterado no PDI (conservador) |

### Transições de estado

Nenhuma máquina nova. Não usar `arquivado`. Não mutar PDI de produto criado pela UI (só linhas com nosso digest).

---

## Entidade: Ação de PDI

**Model**: `pdi.AcaoPDI`  
**Fonte**: a mesma linha.

| Campo | Origem | Regras |
|---|---|---|
| `pdi` | PDI da linha (mesmo digest) | Nunca PDI sem ação |
| `descricao` | concatenação `\n\n` dos trechos não vazios | três vazios → conflito da **linha** |
| `responsavel` | = `pdi.usuario` | nunca gestor |
| `prazo` | `parse_legacy_date(Data de Entrega)` | ausente/ilegível → conflito |
| `status` | FR-011 **antes** do save | concluida / atrasada / pendente |

### Chave natural (idempotência — sem coluna nova)

```text
(pdi_id, display_name(descricao), prazo)
```

Match → inalterado. Divergência no mesmo PDI → conflito.

### Status (FR-011) vs hook vigente

```text
concluido → concluida (hook não promove/rebaixa concluida)
ativo + prazo < hoje  → setar atrasada; hook mantém se prazo ainda < hoje
ativo + prazo >= hoje → setar pendente; se alguém setar atrasada por engano, hook rebaixa
```

`em_andamento` de `AcaoPDI` **não** é usado nesta fatia.

---

## Entidade: Digest (não é model)

Valor em `PDI.solides_id`. Algoritmo normativo: [research.md R-digest](./research.md). Comprimento 44. Unique do schema vigente impede dois PDIs com o mesmo digest.

---

## Entidade: Relatório de carga (artefato operacional)

Não é model Django. Contadores: ver [contracts/import-command-contract.md](./contracts/import-command-contract.md).

Amostra mascarada ≤ 5 / seção. Totais sempre completos.

---

## Diagrama de relacionamentos (pós-import)

```text
CustomUser (010, ativo ou inativo)
  └── PDI* (usuario PROTECT; solides_id = digest; status ativo|concluido)
        └── AcaoPDI* (pdi PROTECT; responsavel = mesmo usuario; 1 por linha desta fatia)
              prazo, descricao concatenada, status FR-011

Ciclo / Avaliacao / Feedback / notas  ——  SEM vínculo
```

---

## Ordem de persistência (dentro de `transaction.atomic`)

```text
0. Pré: 003 + 010; ZERO migrate desta fatia; 011/013 opcionais
1. Parse --pdi (openpyxl via parse_pdi_xlsx)
2. Se --dry-run: projetar totais; zero write; emitir relatório
3. Senão atomic:
   para cada linha:
     resolve pessoa → skip órfão
     valida título/status/prazo/descrição → skip conflito
     digest = R-digest
     upsert conservador PDI+ação (create 1ª run / inalterado / conflito)
4. Emitir relatório mascarado (stdout == --report-file)
```

Falha na transação → rollback completo. Dry-run nunca entra no atomic de write.
