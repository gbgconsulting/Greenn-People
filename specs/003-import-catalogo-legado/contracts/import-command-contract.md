# Contract: Management Command `importar_competencias_cargo`

**App**: `competencies`  
**Feature**: `003-import-catalogo-legado`  
**Data**: 2026-07-28

Contrato da superfície CLI da importação one-shot. Mapeamentos legado→domínio: [legado-domain-mapping-contract.md](./legado-domain-mapping-contract.md). Modelo: [../data-model.md](../data-model.md).

---

## Invocação

```bash
python manage.py importar_competencias_cargo \
  --cargos /caminho/lista-cargos.xlsx \
  --competencias /caminho/lista-competencias.xlsx \
  [--report-file /caminho/relatorio.txt] \
  [--dry-run]
```

### Argumentos

| Arg | Obrigatório | Descrição |
|---|---|---|
| `--cargos` | sim | Path do arquivo lista-cargos (CSV UTF-8; extensão pode ser `.xlsx`) |
| `--competencias` | sim | Path do arquivo lista-competencias (idem) |
| `--report-file` | não | Se informado, grava o mesmo relatório UTF-8 neste path (além de stdout) |
| `--dry-run` | não | Executa parse + simulação de totais **sem** commit no banco |

Defaults de path **não** são obrigatórios no contrato; quickstart usa arquivos na raiz do repo como convenção operacional.

---

## Pré-condições de parse

1. Ambos os paths existem e são legíveis.
2. Encoding UTF-8.
3. Header contém colunas obrigatórias:
   - cargos: `Cargo`, `Competência`
   - competencias: `Competência`, `Grupo de competência`, `Descrição`, `Peso`, `Tipo de Avaliação`, `Cargo`
4. `csv.DictReader` parseia ao menos o header sem erro.

Falha em qualquer item → **nenhuma escrita**; exit `1`.

---

## Semântica de execução

1. Parse + normalização + classificação (KPI / ambíguo / avaliável) + reconciliação de pares.
2. Se não `--dry-run`: `transaction.atomic()` persistindo Escala → Cargos → Competências → CargoCompetencia.
3. Emitir relatório completo (mesmo em dry-run, com totais projetados).
4. Soft-delete: inativos com mesma chave canônica **não** são reativados; entram em `conflitos`.
5. Divergências / não mapeados / KPI: não abortam (exceto conflito fatal da escala padrão inativa — ver research R9).

---

## Códigos de saída

| Code | Significado |
|-----:|---|
| `0` | Concluído (persistência ok ou dry-run ok). Relatório pode conter conflitos/divergências/não mapeados não-fatais. |
| `1` | Erro fatal: args inválidos, arquivo ausente/ilegível, encoding/colunas inválidas, escala padrão inativa sem reativação, ou falha de persistência (rollback). |

Não há exit `2` nesta versão.

---

## Formato do relatório (stdout / `--report-file`)

Texto UTF-8, seções estáveis (ordem fixa). Exemplo canônico:

```text
=== Importação catálogo legado ===
modo: persist|dry-run
cargos_file: ...
competencias_file: ...

--- Resumo ---
cargos_criados: N
cargos_atualizados: N
cargos_inalterados: N
competencias_criadas: N
competencias_atualizadas: N
competencias_inalteradas: N
vinculos_criados: N
vinculos_atualizados: N
vinculos_inalterados: N
excluidos_kpi: N
nao_mapeados: N
conflitos: N
divergencias: N
merged: N

--- Excluídos KPI ---
- <nome> | motivo=kpi_operacional

--- Não mapeados ---
- <nome> | motivo=ambiguo|grupo_desconhecido|...

--- Conflitos ---
- <tipo> | <nome> | motivo=inativo_existente|escala_inativa|...

--- Divergências entre fontes ---
- cargo=<c> competencia=<k> | apenas_em=lista-cargos|lista-competencias

--- Merged (mesma chave canônica) ---
- <nome_a> ~ <nome_b> | chave=<canonical>

=== Fim ===
```

Requisitos:

- Contadores no resumo **MUST** bater com o tamanho das listas detalhadas correspondentes.
- Operador **MUST** distinguir criados/atualizados/inalterados/excluídos/não mapeados/conflitos/divergências (FR-009 / SC-007).

---

## Efeitos colaterais permitidos

| Permitido | Proibido |
|---|---|
| Create/update `Escala` padrão ativa | Reativar `is_active=False` silenciosamente |
| Create/update `Cargo` / `Competencia` ativos | Importar User / Avaliação / Meta / PDI |
| Create/update `CargoCompetencia` | Alterar fórmula de nota / etapas / snapshots |
| Escrever relatório | Exigir `solides_id` |

---

## Contratos de teste (CLI / serviço)

- Args faltando ou arquivo inexistente → exit 1, DB inalterado.
- CSV válido mínimo → cria escala + cargos + competências + vínculos; contagens no relatório.
- Segunda execução idêntica → zero novos ativos duplicados; predominantemente `inalterados`.
- Competência KPI na fixture → `excluidos_kpi`; ausente no catálogo ativo.
- Par só em uma fonte → aparece em `divergencias`; união grava se ambas pontas elegíveis.
- Cargo/Competencia inativos com mesmo nome canônico → `conflitos`; permanecem inativos.
- `--dry-run` → exit 0; nenhuma linha nova no DB.
