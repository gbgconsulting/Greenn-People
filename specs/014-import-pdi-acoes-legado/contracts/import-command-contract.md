# Contract: Management Command `importar_pdi`

**App**: `pdi`  
**Feature**: `014-import-pdi-acoes-legado`  
**Data**: 2026-08-19

Contrato da superfície CLI. Mapeamento: [column-mapping-contract.md](./column-mapping-contract.md). Modelo: [../data-model.md](../data-model.md).

Espelha o padrão 013 (`importar_notas_comentarios`) / 011 / 010, com **um** path.

---

## Invocação

```bash
python manage.py importar_pdi \
  --pdi /caminho/backup_pdi_20260624.xlsx \
  [--report-file /caminho/relatorio.txt] \
  [--dry-run]
```

### Argumentos

| Arg | Obrigatório | Descrição |
|---|---|---|
| `--pdi` | sim | Path do backup de PDI (OOXML real, `backup_pdi_*.xlsx`) |
| `--report-file` | não | Grava relatório UTF-8 **idêntico** ao stdout |
| `--dry-run` | não | Parse + totais projetados, **zero commit** |

Sem segundo path. Sem `--ciclo`. Sem flags de produto.

---

## Pré-condições

1. Specs **003** e **010** aplicadas no ambiente alvo (chave canônica; colaboradores com ou sem `solides_id`; schema `PDI.solides_id`).
2. **011/013 não** são pré-requisito.
3. **Nenhuma** migration desta fatia.
4. `--pdi` existe e é OOXML legível (`sheet1`).
5. Headers contêm colunas obrigatórias (column-mapping-contract).

Falha pré-persistência → **nenhuma escrita**; exit `1`.

---

## Semântica de execução

```text
1. Parse --pdi (openpyxl via parse_pdi_xlsx em accounts)
2. data_carga = timezone.localdate()  # congelada para FR-011
3. Se --dry-run: projetar totais e sair sem write
4. Senão transaction.atomic():
   para cada linha: resolve + valida + upsert conservador (1 PDI + 1 ação ou skip)
5. Emitir relatório (stdout e, se presente, --report-file com o MESMO texto)
```

Toda persistência de linha via `full_clean()` + `save()`.  
`AcaoPDI.save()` dispara o hook vigente — **não** chamar `mark_overdue_pdi_actions`.

**Proibido** no command/serviço: `open_cycle`, `close_cycle`, `advance_stage`, `approve_*`, `get_visible_users`, `user_in_scope`, `ScopedObjectMixin`, `mark_overdue_pdi_actions`, `calculate_pdi_progress`, `calcular_aderencia`, `create_competency_lines`, simular POST de CreateView, inventar User, apagar PDI para refazer, raw SQL, `bulk_create` bypass `save`.

---

## Atomicidade

- Persist: uma `transaction.atomic()` cobre o lote. Exceção → rollback completo; exit `1`.
- Por linha resolvível: PDI **e** ação, ou nenhum.
- Conflitos/órfãos **por linha** são não-fatais (continuam o lote; entram no relatório).
- `--dry-run`: **zero** `save`/`create`/`update` (contagem antes/depois inalterada para `PDI` e `AcaoPDI`).

---

## Códigos de saída

| Code | Significado |
|-----:|---|
| `0` | Concluído (persist ok ou dry-run ok). Relatório pode conter conflitos/órfãos não-fatais. |
| `1` | Erro fatal: args inválidos, arquivo ausente/ilegível, colunas obrigatórias ausentes, exceção na persistência (rollback). |

Alinhado a 003/010/011/013. Sem exit `2` nesta versão.

---

## Formato do relatório (stdout / `--report-file`)

Texto UTF-8. **Se `--report-file` for passado, o arquivo MUST ser idêntico ao stdout.**

Seções estáveis:

```text
=== Importação PDI/ações legado Sólides ===
modo: persist|dry-run
pdi_file: ...

--- Resumo ---
pdis_criados: N
pdis_atualizados: N
pdis_inalterados: N
acoes_criadas: N
acoes_atualizadas: N
acoes_inalteradas: N
orfaos_usuario: N
orfaos_solicitacao: N
conflitos: N

--- Amostra (mascarada, max 5 por seção) ---
pdis_criados:
  - solides_id=pdi_***abcd
acoes_criadas:
  - pdi=pdi_***abcd | status_acao=atrasada
orfaos_usuario:
  - linha=12 | motivo=nome_ambiguo
orfaos_solicitacao:
  - id_legado=***99 | motivo=informativo_sem_fk
conflitos:
  - tipo=prazo_invalido | linha=4
  - tipo=status_desconhecido | linha=9
  - tipo=descricao_vazia | linha=11
  - tipo=titulo_ausente | linha=3
  - tipo=acao_chave_divergente | pdi=pdi_***abcd
  - tipo=id_vs_nome | linha=20

=== Fim ===
```

Requisitos:

- Contadores MUST bater com cardinalidade (amostra truncada documentada).
- **NEVER** emitir nome, e-mail, linha bruta, título/objetivo/situação **completos**.
- Mascarar digest/IDs (`mask_solides_id`); demais PII (`mask_pii`).
- Logs MUST NOT imprimir linha bruta da planilha.
- Operador revisa totais em < 3 min (SC-008).

Nesta fatia a política conservadora faz `pdis_atualizados` / `acoes_atualizadas` permanecerem **0** no caminho feliz (create vs inalterado vs conflito). Os campos existem para o resumo FR-015.

---

## Efeitos colaterais permitidos

| Permitido | Proibido |
|---|---|
| Create `PDI` + `AcaoPDI` (1+1) | Inventar `User` / `Ciclo` / `Avaliacao` |
| Preencher `PDI.solides_id` (digest) | `solides_id` em ação; FK ciclo |
| Relatório mascarado | Mutar etapa/ciclo/meta/nota/012/overdue.py |
| Inalterado na 2ª run | Apagar para refazer; UI/DRF/Celery |

---

## Contratos de teste

- Args faltando / arquivo inexistente → exit 1, DB inalterado.
- `--dry-run` samples → zero writes (SC-006).
- 1 PDI + 1 ação; responsável = dono; zero três ações.
- Órfão / ambíguo / inativo ok.
- De-para + atraso FR-011.
- Digest ≠ nome concatenado; comprimento ≤ 50.
- 2ª run delta 0 nas chaves naturais.
- PII mascarada; stdout == report-file.
- Nenhum teste lê `data/legado-solides/raw/`.
- Diff denylist vazio; stage/scope/reject_stage_invariant verdes **sem** alterar asserts.
