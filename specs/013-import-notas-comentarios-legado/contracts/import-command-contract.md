# Contract: Management Command `importar_notas_comentarios`

**App**: `reviews`  
**Feature**: `013-import-notas-comentarios-legado`  
**Data**: 2026-08-18

Contrato da superfície CLI. Mapeamento: [column-mapping-contract.md](./column-mapping-contract.md). Mapa de IDs: [collapsed-id-resolution.md](./collapsed-id-resolution.md). Snapshots/fórmula: [snapshot-and-formula.md](./snapshot-and-formula.md). Modelo: [../data-model.md](../data-model.md).

Espelha o padrão 011 (`importar_ciclos_avaliacoes`) / 010 (`importar_colaboradores`).

---

## Invocação

```bash
python manage.py importar_notas_comentarios \
  --notas /caminho/backup_notas_avaliacoes_20260624.xlsx \
  --comentarios /caminho/backup_comentarios_avaliacoes_20260624.xlsx \
  --avaliacoes /caminho/backup_avaliacoes_20260624.xlsx \
  [--habilidades /caminho/backup_habilidades_20260624.xlsx] \
  [--report-file /caminho/relatorio.txt] \
  [--dry-run]
```

### Argumentos

| Arg | Obrigatório | Descrição |
|---|---|---|
| `--notas` | sim | Path do backup de notas (OOXML real) |
| `--comentarios` | sim | Path do backup de comentários (OOXML real) |
| `--avaliacoes` | sim | Path do backup de **cabeçalhos** da 011. **Só** rebuild do mapa em memória. **NÃO** reimporta `Avaliacao`/`Ciclo` |
| `--habilidades` | não | Path do backup de habilidades. Só se a run precisar criar `Competencia` extra (FK de nota). **NÃO** importa matriz cargo↔competência |
| `--report-file` | não | Grava relatório UTF-8 adicional |
| `--dry-run` | não | Parse + mapa + totais projetados, **zero commit** |

---

## Pré-condições

1. Specs **003**, **010** e **011** aplicadas no ambiente alvo (catálogo, colaboradores com `solides_id`, ciclos encerrados + cabeçalhos canônicos).
2. **Nenhuma** migration desta fatia (schema já suficiente).
3. Paths obrigatórios existem e são legíveis OOXML (`sheet1`).
4. Headers contêm colunas obrigatórias (ver column-mapping-contract).

Falha pré-persistência → **nenhuma escrita**; exit `1`.

---

## Semântica de execução (duas fases)

Ordem fixa:

```text
1. Parse notas (openpyxl via parse_xlsx estendido)
2. Parse comentários
3. Parse cabeçalhos --avaliacoes + aggregate_avaliacao_headers (011) → mapa memória
4. Parse --habilidades se presente (não cria as 57 de antemão)
5. Se --dry-run: projetar totais e sair sem write
6. Senão, transaction.atomic():
   a. Fase Notas — resolve avaliação/competência; upsert AvaliacaoCompetencia;
      snapshots 1ª save; conflitos/órfãos não-fatais por linha
   b. Por avaliação tocada com linhas suficientes — CHAMAR calcular_nota_final_lider;
      calcular_nota_final_autoavaliacao quando o contrato vigente aplicar
   c. Fase Comentários — resolve avaliação/autor; create Feedback; ciente_em se lider
7. Emitir relatório (stdout e opcional --report-file)
```

Toda persistência de linha via `full_clean()` + `save()`.  
`--avaliacoes` **nunca** faz upsert de cabeçalho.

**Proibido** no command/serviço: `open_cycle`, `close_cycle`, `advance_stage`, `can_advance`, `approve_*`, `reject_*`, `create_competency_lines`, `calcular_aderencia`, mutar `evaluation.py`, atribuir `etapa`/`concluida`.

**Obrigatório**: chamar `calcular_nota_final_lider` / `calcular_nota_final_autoavaliacao` (funções existentes).

---

## Atomicidade

- Persist: uma `transaction.atomic()` cobre **as duas fases**. Exceção → rollback completo; exit `1`; nenhum estado parcial (notas sem comentários ou vice-versa da mesma run).
- Conflitos/órfãos **por linha** são não-fatais (continuam o lote; entram no relatório).
- `--dry-run`: **zero** `save`/`create`/`update` (contagem antes/depois inalterada para `AvaliacaoCompetencia`, `Feedback` e `nota_final_*`).

---

## Códigos de saída

| Code | Significado |
|-----:|---|
| `0` | Concluído (persist ok ou dry-run ok). Relatório pode conter conflitos/órfãos não-fatais. |
| `1` | Erro fatal: args inválidos, arquivo ausente/ilegível, colunas obrigatórias ausentes, exceção na persistência (rollback). |

Alinhado a 003/010/011. Sem exit `2` nesta versão.

---

## Formato do relatório (stdout / `--report-file`)

Texto UTF-8, seções estáveis:

```text
=== Importação notas/comentários legado Sólides ===
modo: persist|dry-run
notas_file: ...
comentarios_file: ...
avaliacoes_file: ...
habilidades_file: ... | (omitido)

--- Resumo ---
notas_criadas: N
notas_atualizadas: N
notas_inalteradas: N
comentarios_criados: N
comentarios_inalterados: N
orfaos_avaliacao: N
orfaos_competencia: N
orfaos_autor: N
conflitos_lider_divergente: N
conflitos_ciclo_aberto: N
habilidades_extras_criadas: N
ids_colapsados_resolvidos: N
conflitos: N

--- Amostra (mascarada, max 5 por seção) ---
notas_criadas:
  - avaliacao=***44 | competencia=***12 | lado=lider
orfaos_avaliacao:
  - id_legado=***99 | motivo=avaliacao_nao_resolvida
orfaos_competencia:
  - habilidade_id=***57 | motivo=kpi_ou_sem_nota
orfaos_autor:
  - avaliador_id=***8 | motivo=usuario_nao_resolvido
conflitos_lider_divergente:
  - avaliacao=***44 | competencia=***12
conflitos_ciclo_aberto:
  - avaliacao=***1 | ciclo=***aberto
habilidades_extras_criadas:
  - solides_id=***80 | tipo=tecnica
ids_colapsados_resolvidos:
  - colapsado=***45 → canônico=***44
conflitos:
  - tipo=nota_fora_da_escala | avaliacao=***44 | competencia=***12
  - tipo=fator_invalido | linha=120
  - tipo=snapshot_divergente | avaliacao=***44 | competencia=***12
  - tipo=calculo_lider | avaliacao=***44
  - tipo=ciencia_data_invalida | linha=30

=== Fim ===
```

Requisitos:
- Contadores MUST bater com cardinalidade (amostra truncada documentada).
- **NEVER** emitir comentário completo, nome ou e-mail; mascarar IDs (`mask_solides_id`).
- Logs MUST NOT imprimir linha bruta da planilha.
- Operador revisa totais em < 3 min (SC-010).

---

## Efeitos colaterais permitidos

| Permitido | Proibido |
|---|---|
| Create/update `AvaliacaoCompetencia` | Inventar `Avaliacao`/`Ciclo`/`User` |
| Create `Feedback` (append-only) | Reescrever conteúdo de feedback alheio |
| Create `Competencia` mínima (R11) | Create `CargoCompetencia`; catálogo 57 completo |
| `nota_final_*` via `calcular_*` | Editar `evaluation.py`; `create_competency_lines` |
| Relatório mascarado | Mutar `etapa`/`concluida`; UI/DRF/Celery; PDI; 9-box |
| Rebuild mapa em memória | Persistir tabela de mapa; reimportar cabeçalhos 011 |

---

## Contratos de teste

- Args faltando / arquivo inexistente → exit 1, DB inalterado.
- `--dry-run` samples → zero writes (SC-008).
- ID canônico / ID colapsado / órfão — ver [collapsed-id-resolution.md](./collapsed-id-resolution.md).
- Dois líderes divergentes → conflito; zero 2ª `Avaliacao`.
- 2ª run → snapshots estáveis; Feedback não duplicado pela chave natural.
- Ciclo aberto → skip + seção `conflitos_ciclo_aberto`.
- Nenhum teste lê `data/legado-solides/raw/`.
- Diff denylist vazio; stage/scope/reject_stage_invariant verdes **sem** alterar asserts.
