# Research: Importação One-Shot do Catálogo Legado

**Branch**: `003-import-catalogo-legado` | **Date**: 2026-07-28

Pesquisa consolidada a partir de [spec.md](./spec.md), constituição, models atuais (`Cargo`, `Competencia`, `CargoCompetencia`, `Escala`) e inspeção das fontes na raiz (`lista-cargos.xlsx`, `lista-competencias.xlsx`). Todos os itens que seriam `NEEDS CLARIFICATION` no Technical Context foram resolvidos.

---

## R1 — Superfície de execução (management command)

- **Decision**: `python manage.py importar_competencias_cargo --cargos PATH --competencias PATH [--report-file PATH] [--dry-run]`. Lógica em `apps/competencies/services/catalog_import/`; o comando só valida args, chama o serviço e imprime o relatório. Sem DRF, sem UI, sem Celery.
- **Rationale**: FR-001/FR-012; Princípio I; alinhado ao nome PRD Sprint 6.5.3 (`importar_competencias_cargo`).
- **Alternatives considered**:
  - Nome inglês `import_catalogo_legado` — aceitável como alias interno de módulo; comando público em PT alinhado ao restante operacional.
  - Admin upload — rejeitado (FR-012 / sem UI).
  - Script solto fora do Django — rejeitado: perde ORM, constraints e testes pytest-django.

---

## R2 — Parse das fontes (CSV disfarçado de .xlsx)

- **Decision**: Abrir como texto UTF-8 com `csv.DictReader` (stdlib). Sem `openpyxl`. Validar colunas obrigatórias antes de qualquer escrita:
  - `lista-cargos`: `Cargo`, `Competência`
  - `lista-competencias`: `Competência`, `Grupo de competência`, `Descrição`, `Peso`, `Tipo de Avaliação`, `Cargo`
  - Campos pipe-separated (`Competência` em cargos; `Cargo` em competências): split em `|`, strip por item, descartar vazios.
- **Rationale**: `file(1)` confirma “CSV text”; openpyxl seria dependência injustificada. FR-001.
- **Alternatives considered**:
  - openpyxl / pandas — rejeitados (Princípio I; conteúdo não é XLSX real).
  - Detectar encoding via chardet — rejeitado; Assumption UTF-8; falha clara se encoding inválido.

**Evidência das fontes (2026-07-28)**: ~134 linhas de cargos; ~43 competências; grupos `Liderança` (6), `Comportamento` (4), `Desempenho` (33).

---

## R3 — Normalização determinística de nomes

- **Decision**: Função `canonical_key(nome) -> str`:
  1. `strip()` + colapsar whitespace interno (`\s+` → espaço único)
  2. Unicode NFKD + remover combining marks (acentos)
  3. `casefold()`
  - Chave de matching/idempotência = `canonical_key`.
  - Nome persistido = forma “display”: strip + colapso de espaços, **sem** alterar capitalização além do primeiro encontrado nas fontes (preferência: nome em `lista-competencias` para competências; nome em `lista-cargos` para cargos). Merges semânticos óbvios (mesma chave) são reportados como `merged`.
- **Rationale**: FR-007; evita duplicata por “Pleno” vs “pleno” / acentos.
- **Alternatives considered**:
  - Title-case forçado — rejeitado: altera grafias de marca/siglas (CEO, QA, UX).
  - Matching fuzzy (Levenshtein) — rejeitado: não determinístico o bastante para one-shot; ambíguos vão a `nao_mapeados` / relatório humano.

---

## R4 — De-para de senioridade (`Cargo.nivel` 1–6)

- **Decision**: Inferir `nivel` por tokens no nome canônico, avaliando regras em ordem de especificidade (primeira match vence). Sem match → **6 (Principal)**.

| Ordem | Tokens (casefold, após normalização) | nivel | Rótulo |
|------:|--------------------------------------|------:|--------|
| 1 | `estagiario`, `estag`, `trainee` | 1 | Estagiário |
| 2 | ` jr`, sufixo/token `jr`, `junior` | 2 | Júnior |
| 3 | ` pl`, token `pl`, `pleno` | 3 | Pleno |
| 4 | ` sr`, token `sr`, `senior`, `sênior`→`senior` | 4 | Sênior |
| 5 | `tech lead`, `ux lead`, `qa lead`, `lead` | 5 | Especialista |
| 6 | `gerente`, `diretor`, `coordenador`, `coordenadora`, `ceo`, `presidente`, `head` | 6 | Principal |
| 7 | (default) | 6 | Principal |

Tokens devem ser matched como palavras/sufixos delimitados (evitar falso positivo de substring). Preferir regex com boundaries / split por não-alfanuméricos.

- **Rationale**: FR-002; Assumptions da spec.
- **Alternatives considered**:
  - Coluna explícita de senioridade no CSV — não existe nas fontes.
  - Sempre 6 — rejeitado; perde perfil esperado coerente.

---

## R5 — De-para `nivel_esperado` e `peso`

- **Decision**:
  - `peso` sempre `Decimal('1')` na importação.
  - `nivel_esperado` derivado de `Cargo.nivel`:

| Cargo.nivel | Senioridade | nivel_esperado |
|------------:|-------------|----------------|
| 1 | Estagiário | 2 |
| 2 | Júnior | 2 |
| 3 | Pleno | 3 |
| 4 | Sênior | 4 |
| 5 | Especialista | 4 |
| 6 | Principal | 4 |

- **Rationale**: FR-004; SC-003. Ajuste fino pós-carga via CRUD (US-14).
- **Alternatives considered**:
  - Usar coluna `Peso` do legado (sempre 1) — irrelevante; fixar 1 evita surpresas.
  - `nivel_esperado = Cargo.nivel` — rejeitado: escala de cargo é 1–6; escala de avaliação é 1–5.

---

## R6 — Mapa de tipo de competência

- **Decision**: Mapear `Grupo de competência` → `Competencia.tipo`:

| Grupo legado | tipo |
|---|---|
| Liderança | `lideranca` |
| Comportamento | `comportamental` |
| Desempenho | `tecnica` (somente se passar filtro de elegibilidade) |

Grupo desconhecido → item em `nao_mapeados` (não cria competência).

- **Rationale**: FR-003.
- **Alternatives considered**: Usar coluna `Tipo de Avaliação` (valores “Desempenho”) — rejeitado: não discrimina liderança/comportamental; grupo é a fonte correta.

---

## R7 — Exclusão de KPI / operacionais vs ambíguos

- **Decision**: Classificação em três buckets após normalização do nome da competência:

1. **KPI_EXCLUSAO** (não cria `Competencia`; relatório `excluidos_kpi`) — match por chave canônica exata **ou** prefixo canônico da família:
   - `sla`
   - `lead time discovery`
   - `custo de nuvem por transacao`
   - `throughput por colaborador` (+ variantes “- Arquiteto”)
   - `indice de incidentes` (+ variantes “- QA Lead”)
   - `tempo medio de espera na esteira`
2. **Avaliáveis** — restante com grupo mapeado → importa como competência.
3. **Ambíguos / não mapeados** — grupo inválido, ou nomes explicitamente listados como ambíguos sem decisão de produto (vão a `nao_mapeados`, **não** bloqueiam a carga). Lista inicial de ambíguos (revisão humana pós-carga; **não** entram no catálogo nesta versão):
   - `erros de usabilidade`
   - `oportunidade de usabilidades entregues e cm problemas resolvidos`
   - `oportunidades entregues de modernizacao`
   - `oportunidades tracionadas`
   - `monitoramento continuo`

Itens em KPI_EXCLUSAO têm precedência sobre ambíguos.

- **Rationale**: FR-006; Assumption da lista documentada; SC-005. Exemplos do PRD cobertos; métricas equivalentes no arquivo incluídas.
- **Alternatives considered**:
  - Heurística (“contém % / tempo / índice”) — rejeitada: falsos positivos em competências reais.
  - Importar tudo e marcar depois — rejeitado (Decisão #1 PRD / domínio Meta vs Competência).

---

## R8 — Reconciliação das duas vistas (matriz cargo↔competência)

- **Decision**:
  1. Vista A (`lista-cargos`): pares `(cargo, competencia)` expandindo pipes.
  2. Vista B (`lista-competencias`): pares expandindo pipes de cargos.
  3. Normalizar chaves; filtrar pares cuja competência é KPI/ambígua/não mapeada.
  4. Divergências = pares só em A ou só em B → relatório `divergencias`.
  5. Matriz gravada = **união** dos pares em que **ambas** as pontas estão resolvidas como elegíveis (cargo criado/atualizado; competência avaliável criada/atualizada). Pares com ponta excluída não entram.
- **Rationale**: FR-005; Assumption da união; SC-004 (zero divergências silenciosas).
- **Alternatives considered**:
  - Interseção estrita — rejeitada: perde vínculos válidos presentes em uma fonte.
  - Preferir só lista-competencias — rejeitada: FR-005 exige mesma matriz após parse + reporte de divergência.

---

## R9 — Escala padrão 1–5

- **Decision**: Nome canônico persistido: `Escala padrão 1-5` (`valor_minimo=1`, `valor_maximo=5`). `get_or_create` por nome ativo (respeitando `unique_escala_nome_ativa`). Se existir ativa com esse nome, reutilizar; se inativa com mesmo nome, **não** reativar — criar conflito no relatório e falhar a fase de competências que dependem dela **ou** criar nova escala com sufixo operacional? → **não criar duplicata semântica**: reportar conflito `escala_inativa` e abortar persistência (exit 1) — escala é pré-requisito único. Em ambiente limpo: cria uma vez.
- **Rationale**: FR-010; alinhado à política de soft-delete (R10).
- **Alternatives considered**: Criar escala com nome timestamp — rejeitado: polui catálogo. Reativar escala inativa — rejeitado (Assumption soft-delete).

---

## R10 — Idempotência e soft-delete

- **Decision**:
  - Lookup de `Cargo`/`Competencia` ativos por `nome` via chave canônica (iterar ativos e comparar `canonical_key`, ou filtrar candidatos por normalização em Python — volume pequeno).
  - Ativo encontrado: atualizar campos divergentes (`nivel`, `descricao`, `tipo`, `escala_id`); marcar `atualizados` ou `inalterados`.
  - Inativo com mesma chave: **não reativar**; registrar `conflitos` com motivo `inativo_existente`; pular create.
  - `CargoCompetencia`: `update_or_create(cargo=..., competencia=...)` com `peso`/`nivel_esperado` defaults da regra; unique `unique_cargo_competencia` já cobre.
- **Rationale**: FR-008; Assumption soft-delete; constraints 002.
- **Alternatives considered**:
  - `get_or_create` cego por nome exact — rejeitado: falha com variação ortográfica.
  - Reativar inativos — rejeitado explicitamente pela spec.

---

## R11 — Transação e falhas

- **Decision**: Pipeline em duas fases:
  1. **Parse+validate** (sem DB): arquivos legíveis, colunas, encoding; monta estruturas em memória + relatório parcial. Qualquer erro fatal → exit 1, zero writes.
  2. **Persist** dentro de um único `transaction.atomic()`: Escala → Cargos → Competências → Vínculos. Exceção inesperada → rollback completo.
  - `--dry-run`: executa fase 1 + simula totais sem commit (ou atomic+rollback explícito); útil para preview.
  - Conflitos de soft-delete / não mapeados / divergências: **não** abortam a transação; entram no relatório; exit 0 se persistência ok.
  - Conflito de escala padrão inativa: aborta com exit 1 (pré-requisito).
- **Rationale**: Edge case “falha antes de gravar estado inconsistente”; all-or-nothing documentado.
- **Alternatives considered**:
  - Atomicidade por entidade — rejeitada para one-shot: catálogo parcial é pior que falha total.
  - Continuar após IntegrityError pontual — rejeitado: mascara bugs.

---

## R12 — Relatório de carga

- **Decision**: Estrutura textual (stdout) + opcional `--report-file` (mesmo conteúdo UTF-8). Seções: resumo de contagens (`criados`, `atualizados`, `inalterados`, `excluidos_kpi`, `nao_mapeados`, `conflitos`, `divergencias`, `merged`) + listas detalhadas. Formato formal em [contracts/import-command-contract.md](./contracts/import-command-contract.md).
- **Rationale**: FR-009; SC-007.
- **Alternatives considered**: Só JSON — rejeitado como único formato (operador prefere texto); JSON opcional futuro fora de escopo.

---

## R13 — Testes

- **Decision**: `tests/test_import_catalogo_legado.py` com fixtures CSV temporárias cobrindo:
  - de-para nivel / nivel_esperado
  - filtro KPI + ambíguos
  - matriz idêntica vs divergência reportada
  - segunda execução sem duplicata de ativos
  - soft-delete não reativado
  - arquivo inválido → exit/erro sem writes
- **Rationale**: requisitos do usuário + SC-001..006.
- **Alternatives considered**: Só smoke manual — rejeitado.

---

## R14 — Fora de escopo (confirmado)

- `solides_id` obrigatório; import de users/hierarquia/avaliações/notas/PDI; UI admin; alteração de fórmula/etapas; criação de Meta a partir de KPI excluído.

---

## Outcomes

Todos os `NEEDS CLARIFICATION` do Technical Context foram resolvidos. Nenhum gate de constituição violado sem justificativa. Próximo: [data-model.md](./data-model.md), [contracts/](./contracts/), [quickstart.md](./quickstart.md).
