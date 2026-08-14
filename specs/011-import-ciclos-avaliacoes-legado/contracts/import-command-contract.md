# Contract: Management Command `importar_ciclos_avaliacoes`

**App**: `cycles`  
**Feature**: `011-import-ciclos-avaliacoes-legado`  
**Data**: 2026-08-13

Contrato da superfície CLI. Mapeamento: [column-mapping-contract.md](./column-mapping-contract.md). Agregação: [aggregation-contract.md](./aggregation-contract.md). Modelo: [../data-model.md](../data-model.md).

Espelha o padrão 010 (`importar_colaboradores`).

---

## Invocação

```bash
python manage.py importar_ciclos_avaliacoes \
  --solicitacoes /caminho/backup_solicitacoes_avalicaoes_20260624.xlsx \
  --avaliacoes /caminho/backup_avaliacoes_20260624.xlsx \
  [--report-file /caminho/relatorio.txt] \
  [--dry-run]
```

### Argumentos

| Arg | Obrigatório | Descrição |
|---|---|---|
| `--solicitacoes` | sim | Path do backup de solicitações (OOXML real) |
| `--avaliacoes` | sim | Path do backup de avaliações (OOXML real) — cabeçalhos |
| `--report-file` | não | Grava relatório UTF-8 adicional |
| `--dry-run` | não | Parse + agregação + totais projetados, **zero commit** |

---

## Pré-condições

1. Spec **010** aplicada (`CustomUser.solides_id` quando crosswalk; `Avaliacao.solides_id` no schema).
2. Migration desta feature aplicada (`Ciclo.solides_id` existe).
3. Spec **003** recomendada (não bloqueia cabeçalho).
4. Paths existem e são legíveis OOXML (`sheet1`).
5. Headers contêm colunas obrigatórias (ver column-mapping-contract).

Falha pré-persistência → **nenhuma escrita**; exit `1`.

---

## Semântica de execução (duas fases)

Ordem fixa:

```text
1. Parse solicitações (openpyxl via parse_xlsx estendido)
2. Parse avaliações
3. Se --dry-run: projetar totais (ciclos + grupos agregados) e sair sem write
4. Senão, transaction.atomic():
   a. Fase Ciclos — upsert por Ciclo.solides_id; status sempre encerrado
   b. Fase Avaliações — aggregar → resolve FK → upsert Avaliacao
5. Emitir relatório (stdout e opcional --report-file)
```

Toda persistência via `full_clean()` + `save()`.

**Proibido** no command/serviço: `open_cycle`, `close_cycle`, `advance_stage`, `can_advance`, `approve_*`, `reject_*`, qualquer `calcular_*`.

---

## Códigos de saída

| Code | Significado |
|-----:|---|
| `0` | Concluído (persist ok ou dry-run ok). Relatório pode conter conflitos/órfãos não-fatais. |
| `1` | Erro fatal: args inválidos, arquivo ausente/ilegível, colunas obrigatórias ausentes, migration pré-requisito ausente, exceção na persistência (rollback). |

Alinhado a 003/010. Sem exit `2` nesta versão.

---

## Formato do relatório (stdout / `--report-file`)

Texto UTF-8, seções estáveis:

```text
=== Importação ciclos/avaliações legado Sólides ===
modo: persist|dry-run
solicitacoes_file: ...
avaliacoes_file: ...

--- Resumo ---
ciclos_criados: N
ciclos_atualizados: N
ciclos_inalterados: N
ciclos_conflitos: N
avaliacoes_criadas: N
avaliacoes_atualizadas: N
avaliacoes_inalteradas: N
grupos_agregados: N
orfaos_ciclo: N
orfaos_usuario: N
conflitos: N

--- Amostra (mascarada, max 5 por seção) ---
ciclos_criados:
  - solides_id=***123 | nome=Ciclo Q1 | status=encerrado
orfaos_usuario:
  - solicitacao=***10 | avaliado_id=***99 | motivo=usuario_nao_resolvido
conflitos:
  - tipo=datas_ausentes_ou_invalidas | solicitacao=***5 | linha=12
  - tipo=solides_id_avaliacao_em_uso | canonical=***44 | ciclo=***1 | usuario=***7
grupos_agregados / ids_colapsados:
  - grupo=(sol=***1, av=***7) | canonical=***44 | colapsados=***45,***46 | n_linhas=3

=== Fim ===
```

Requisitos:
- Contadores MUST bater com cardinalidade (amostra truncada documentada).
- **NEVER** emitir nomes/e-mails completos em massa; mascarar IDs sensíveis na amostra.
- Operador revisa totais em < 3 min (SC-009/SC-010).

---

## Efeitos colaterais permitidos

| Permitido | Proibido |
|---|---|
| Create/update `Ciclo` encerrado + `solides_id` | Abrir ciclo; chamar `cycle.py` open/close |
| Create/update `Avaliacao` cabeçalho terminal | Mutar `stage.py`, approval, evaluation, adherence, scope |
| Relatório mascarado | Preencher notas / AvaliacaoCompetencia / Feedback / PDI |
| Extensão parse/dates/report 010 | Inventar User ou Ciclo; UI/DRF/Celery |
| | Log linha completa com PII |

---

## Contratos de teste

- Args faltando / arquivo inexistente → exit 1, DB inalterado.
- Fixture samples → ciclos 100% encerrados; dry-run zero writes.
- Multi-avaliador → 1 Avaliacao por (ciclo, usuario); ids_colapsados no relatório.
- Órfão sem usuário → reportado; zero user inventado.
- Segunda execução → delta duplicatas = 0.
- Nenhum teste lê `data/legado-solides/raw/`.
- Diff denylist vazio; stage/scope/reject_stage_invariant verdes.
