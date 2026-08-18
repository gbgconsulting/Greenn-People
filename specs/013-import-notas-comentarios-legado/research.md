# Research: Importação One-Shot do Legado Sólides — Notas por Competência e Comentários Qualitativos

**Branch**: `013-import-notas-comentarios-legado` | **Date**: 2026-08-18

Pesquisa consolidada a partir de [spec.md](./spec.md) (clarifications 2026-08-18 **fechadas**), constituição I–VI, [data/legado-solides/README.md](../../data/legado-solides/README.md) § notas/comentários/PII, specs [003](../003-import-catalogo-legado/), [010](../010-import-colaboradores-legado/), [011](../011-import-ciclos-avaliacoes-legado/) (contrato normativo de agregação), models atuais (`AvaliacaoCompetencia` write-once, `Feedback`, `Competencia.solides_id`) e `apps/reviews/services/evaluation.py` (`calcular_nota_final_*` vs `create_competency_lines`).

**Zero `NEEDS CLARIFICATION` residual.** Clarifications 2026-08-18 são decisões **fechadas** — research **implementa**, não re-debate. Stack preenchida no [plan.md](./plan.md) sem marcadores de stack.

Espelha o rigor da [011 research](../011-import-ciclos-avaliacoes-legado/research.md), adaptado a esta fatia (persistência de nota/feedback; **zero** migration).

---

## Decisões clarificadas (obrigatórias — não reabrir)

| # | Decisão | Implementação |
|---|---|---|
| 1 | 57 habilidades extras: **só** FK estrita de nota + filtro KPI/ambíguos da 003; **sem** matriz ~2.720 `CargoCompetencia` | R11 |
| 2 | `nivel_esperado_utilizado`: dump de notas **sem** coluna de nível → tabela 003 `Cargo.nivel` → `nivel_esperado_for` no cargo do **avaliado**; **NUNCA** `CargoCompetencia` vigente | R7 |
| 3 | `Feedback.tipo=lider` histórico: `ciente_em` = `Criado em` (ou `created_at` legado); **NÃO** deixar pendência; **NÃO** mutar `Avaliacao.etapa`/`concluida` da 011 | R12 |

---

## R1 — Parser: estender `parse_xlsx.py` (openpyxl só aqui)

- **Decision**: Estender `apps/accounts/services/legacy_import/parse_xlsx.py` com parsers de sheets **notas** e **comentários** (colunas da spec Assumptions). Parser opcional de `backup_habilidades_*` **somente** se `--habilidades` for passado na run. `openpyxl` permanece **exclusivo** deste módulo. Nenhum módulo em `reviews/` importa openpyxl.
- **Rationale**: Princípio I + precedente 010/011; FR-002; backups são OOXML real. Complexity Tracking: lib **já** justificada na 010 — esta fatia **não** adiciona dependência.
- **Alternatives considered**:
  - Nova lib (pandas/xlrd) — rejeitada: constituição I; já existe openpyxl.
  - Segundo `parse_xlsx` em `reviews` — rejeitada: parsers divergentes (Princípio IV).
  - CSV — rejeitada: fonte é OOXML.

Detalhe: [contracts/column-mapping-contract.md](./contracts/column-mapping-contract.md).

---

## R2 — CLI: um comando, duas fases, mapa via `--avaliacoes`

- **Decision**: UM management command, default `importar_notas_comentarios`, duas fases na **mesma** `transaction.atomic()` (notas → comentários).

```bash
python manage.py importar_notas_comentarios \
  --notas PATH \
  --comentarios PATH \
  --avaliacoes PATH \
  [--habilidades PATH] \
  [--report-file PATH] \
  [--dry-run]
```

Paths **obrigatórios**: `--notas`, `--comentarios`, `--avaliacoes`.  
`--avaliacoes` = backup de **cabeçalhos** da 011 (`backup_avaliacoes_*`). Serve **somente** para reconstruir o mapa `ids_colapsados` em memória pelo **mesmo** algoritmo 011. **NÃO** reimporta cabeçalhos, **NÃO** cria/atualiza `Avaliacao`/`Ciclo`.

`--habilidades` **opcional**: só quando a run precisa criar `Competencia` extra (FK de nota). Sem o arquivo, extras irresolvíveis pelo catálogo 003 → órfão (salvo `solides_id` já persistido).

`--dry-run` / `--report-file` / exit `0` sucesso (conflitos/órfãos não-fatais) / `1` erro fatal — espelho 010/011.

- **Rationale**: IDs colapsados **não** estão no banco (só `Avaliacao.solides_id` canônico). FR-001/FR-003; DX igual à 011 (um comando, dois arquivos + insumo de resolução).
- **Alternatives considered**:
  - Dois commands (`importar_notas` + `importar_comentarios`) — rejeitado: FR-001 default é um; risco de persistência parcial entre fases; README lista nomes provisórios, o contrato desta fatia **fecha** o nome único.
  - Tabela persistida de mapa / PII extra — **proibido** (FR-003; R3).
  - Celery porque ~7k linhas — **proibido** (Princípio VI desta fatia = CLI one-shot, não request HTTP; precedente 011).

Detalhe: [contracts/import-command-contract.md](./contracts/import-command-contract.md).

---

## R3 — Mapa `ids_colapsados`: IMPORTAR `aggregate.py` da 011

- **Decision**: Reconstruir o mapa em memória:

```text
headers = parse_avaliacoes_headers_xlsx(--avaliacoes)   # parser 011 já existente
groups  = aggregate_avaliacao_headers(headers.rows)     # IMPORTAR de cycles/.../aggregate.py
mapa    = { collapsed_id → group.canonical_id }  ∪  { canonical_id → canonical_id }
```

Consumir `group_key`, `auto_rows`/`is_autoavaliacao`, `min_id`, `collapsed_ids` — **proibido** segundo algoritmo. Default = memória. **PROIBIDO** tabela persistida / PII extra.

- **Rationale**: FR-003; contrato normativo da 011 é a fonte; copiar o algoritmo divergiria em silêncio.
- **Alternatives considered**:
  - Copiar `aggregate.py` para `reviews` — **proibido** (pedido explícito; dois algoritmos).
  - Persistir mapa no DB — rejeitado: FR-003; PII/IDs extras sem necessidade.
  - Relatório da 011 como arquivo de mapa — rejeitado: amostra truncada (máx. 5); incompleto.

Detalhe: [contracts/collapsed-id-resolution.md](./contracts/collapsed-id-resolution.md).

---

## R4 — Resolução `Identificador Avaliação`

- **Decision**: Ordem normativa:

```text
id = canonicalize_id(Identificador Avaliação)
1. Avaliacao.objects.filter(solides_id=id).first()           # canônico
2. senão canonical = mapa.get(id); Avaliacao.objects.filter(solides_id=canonical).first()
3. senão órfão (orfaos_avaliacao); skip; NÃO inventar Avaliacao/Ciclo/User
```

**NUNCA** `get_or_create` por `(ciclo, usuario)`. **NUNCA** novo `unique_together`. Cabeçalhos da 011 são **read-only** nesta fatia.

- **Rationale**: FR-004; SC-006; `unique_together (ciclo, usuario)` já força 1:1 — inventar segunda avaliação violaria a 011.
- **Alternatives considered**:
  - Match por `(ciclo, usuario)` novo a partir de nomes — rejeitado: IDs colapsados já cobrem o caso; inventaria cabeçalho.
  - Reabrir agregação 011 — **proibido**.

---

## R5 — Auto vs líder (`canonical_key`)

- **Decision**: Reutilizar `canonical_key` da 003 (`apps/competencies/services/catalog_import/normalize.py`):

```text
is_auto(row) =
  canonical_key(Nome Avaliador) == canonical_key(Nome Avaliado)
  and ambos não-vazios
```

- Nota: `is_auto` → `nota_autoavaliacao`; senão → `nota_lider`.
- Feedback: `is_auto` → `Feedback.Tipo.COLABORADOR`; senão → `Feedback.Tipo.LIDER`.

Nunca inverter; nunca copiar um campo no outro.

- **Rationale**: FR-007/FR-012; mesma chave das specs 003/010/011; `is_autoavaliacao` da 011 já usa essa regra — reusar a função de normalize, não copiar.
- **Alternatives considered**:
  - Comparação crua de string — rejeitada: acentos/caixa divergiriam do recorte ~2.213 auto / ~5.147 líder.
  - Inferir pelo papel de `line_manager` — rejeitada: dump traz os dois nomes.

---

## R6 — Conflito dois líderes (sem média)

- **Decision**: Agrupar notas por `(avaliacao_canônica, competencia)` **antes** do persist. Se o conjunto de `nota_lider` (linhas não-auto) tiver **mais de um valor distinto** → `conflitos_lider_divergente`; **não** persistir `nota_lider`; **não** inventar média; **não** criar segunda `Avaliacao` nem segunda `AvaliacaoCompetencia`. Autoavaliação do mesmo par (se unívoca) **pode** ser persistida. Dois autos divergentes → conflito simétrico (`conflitos_auto_divergente`), mesma política.
- **Rationale**: FR-008; unicidade `(avaliacao, competencia)` intacta.
- **Alternatives considered**:
  - Média — **proibido**.
  - Último ganha — rejeitado: silencia divergência.
  - Segunda avaliação — **proibido** (011 / FR-004).

---

## R7 — Snapshots write-once (peso do dump; nível da tabela 003)

- **Decision**:

```text
peso_utilizado ← Decimal(Fator no Momento)
  ausente / não-numérico / ≤ 0 → conflito da linha; NÃO assumir peso 1

nivel_esperado_utilizado ← nivel_esperado_for(avaliado.cargo.nivel)
  # tabela 003: 1→2, 2→2, 3→3, 4→4, 5→4, 6→4
  cargo None / nivel irresolvível / ValueError → skip/conflito da linha

NUNCA ler CargoCompetencia.peso / CargoCompetencia.nivel_esperado
NUNCA chamar create_competency_lines
```

Primeira `save()`: preenche snapshots. Reexecução: **não** atribui novos valores aos campos snapshot; se a fonte divergir do persistido → `conflito` no relatório (`snapshot_divergente`); se coincidir → `inalterado` (notas ainda podem `atualizado`). `ValidationError` write-once do model = sinal de que o importer tentou mutar — tratar como conflito, **não** apagar a linha, **não** apagar `Avaliacao` 011 para “refazer”.

- **Rationale**: Clarification #2; FR-009/FR-010; constituição III; RF-19.2. Dump 2026-06-24 **não tem** coluna de nível.
- **Alternatives considered**:
  - Copiar perfil `CargoCompetencia` vigente — **proibido** (mentiria o passado).
  - Peso default 1 — **proibido** (spec Assumptions).
  - Coluna legado de nível “se existir” — dump de referência não tem; se uma run futura trouxer coluna, o contrato de colunas permanece o dump 2026-06-24 (sem coluna) até emenda da spec.

Detalhe: [contracts/snapshot-and-formula.md](./contracts/snapshot-and-formula.md).

---

## R8 — Nota fora da escala: conflito, sem clip

- **Decision**: Se `Nota` (numérica) ∉ `[competencia.escala.valor_minimo, competencia.escala.valor_maximo]` (inclusive) → conflito `nota_fora_da_escala`; **não** recortar; **não** persistir esse valor. Ausência/não-numérico → conflito `nota_invalida`.
- **Rationale**: FR-015; fórmula vigente assume nota dentro da escala (`normalize_score`).
- **Alternatives considered**:
  - Clip silencioso — **proibido**.
  - Persistir e deixar o cálculo falhar depois — rejeitado: mistura dado inválido no histórico.

---

## R9 — `nota_final_*`: CHAMAR `calcular_nota_final_*`; NÃO editar `evaluation.py`

- **Decision**: Após upsert de **todas** as linhas de competência de uma `Avaliacao` no lote:

```text
try:
    calcular_nota_final_lider(avaliacao)          # persiste nota_final_lider
except CalculationError:
    report conflito_calculo_lider; NÃO inventar média

# auto quando o contrato vigente aplicar (None se nenhuma linha tem auto):
try:
    calcular_nota_final_autoavaliacao(avaliacao)  # persiste ou retorna None
except CalculationError:
    report conflito_calculo_auto; NÃO inventar
```

`git diff` de `apps/reviews/services/evaluation.py` **MUST be empty**. **PROIBIDO** reimplementar `normalize_score` / média ponderada. **PROIBIDO** `create_competency_lines` (snapshotaria `CargoCompetencia` **atual** — viola FR-010 / RF-19.2).

`stage.py` / `cycle.py` open-close / `approval.py` / `adherence.py` **intocáveis**. `Avaliacao.etapa` / `concluida` da 011 **intactas** (não atribuir).

- **Rationale**: FR-011/FR-014/FR-021; constituição V. As funções vigentes já persistem o retorno — o importador **chama**, não duplica o `save`.
- **Alternatives considered**:
  - Copiar a fórmula no importer — **proibido**.
  - Editar `calcular_*` para “tolerar linhas só-auto” — **proibido** (diff MUST empty). `CalculationError` → conflito, honesto.
  - `create_competency_lines` + depois overwrite — **proibido** (retrato do presente).

---

## R10 — Ciclo aberto: skip/conflito (histórico ≠ operação)

- **Decision**: Após resolver a `Avaliacao`, se `avaliacao.ciclo.status == Ciclo.Status.ABERTO` → `conflitos_ciclo_aberto`; skip da linha (nota e comentário). Detecção **read-only** no status do ciclo alvo (equivalente ao predicado de `get_open_ciclo()` para aquele ciclo). **NÃO** importar `get_open_ciclo` de `apps/goals/forms.py` (evita acoplamento reviews→goals). **NÃO** chamar `open_cycle` / `close_cycle`.
- **Rationale**: FR-016; SC-012; denylist V. Import CLI não é request HTTP de ciclo operacional.
- **Alternatives considered**:
  - Persistir nota em ciclo aberto “porque é legado” — **proibido**.
  - Encerrar o ciclo aberto para “liberar” a carga — **proibido**.

---

## R11 — Habilidades extras (FK de nota apenas)

- **Decision**:

```text
resolve Competencia.solides_id == Identificador Habilidade
se hit → usar
se miss E a nota referencia E NÃO is_kpi(nome) E NÃO is_ambiguous(nome):
  criar Competencia mínima:
    nome = display_name(habilidade)
    tipo = map_grupo_tipo(grupo) se --habilidades trouxe Grupo mapeável
           senão Competencia.Tipo.TECNICA (default conservador)
    escala = resolve_default_escala() da 003 (Escala padrão 1-5)
    solides_id = Identificador Habilidade
  SEM criar CargoCompetencia
  report habilidades_extras_criadas
senão → orfaos_competencia
```

Filtro = KPI/ambíguos da 003 (`is_kpi` / `is_ambiguous` / `classify` só para exclusão). **Não** é sprint de catálogo; matriz ~2.720 **fora**. Habilidade sem evidência de nota **não** é criada mesmo que `--habilidades` liste 57.

`--habilidades` opcional: parse só para `Identificador` → (`Habilidade`, `Grupo`) quando a extra precisa de tipo. Sem arquivo, extras ainda podem ser criadas com tipo default se passarem o filtro (nome da coluna `habilidade` no dump de notas).

- **Rationale**: Clarification #1; FR-005; SC-014. `resolve_default_escala` já existe na 003 — reusar, não copiar.
- **Alternatives considered**:
  - Importar 57 + 2.720 — **descartado** na clarification.
  - Recusar toda extra — rejeitado: notas órfãs demais; FK estrita é o recorte.
  - Criar `CargoCompetencia` “para a fórmula funcionar” — **proibido** (FR-010).

---

## R12 — Feedback: N por avaliação; ciência no líder; append-only

- **Decision**:
  - N `Feedback` por `Avaliacao` (sem unique que descarte o segundo texto).
  - Autor: `CustomUser.solides_id == Identificador Avaliador`; fallback `canonical_key(Nome Avaliador)` **único**; senão `orfaos_autor`. User **inativo** (010) **permitido**. Nunca inventar User.
  - Tipo: regra R5 (`COLABORADOR` vs `LIDER`).
  - Idempotência chave natural: `(avaliacao canônica, autor, tipo, conteúdo normalizado, Criado em)`. Normalização de conteúdo = `display_name` (strip + colapso de whitespace) — **não** `canonical_key` (perderia distinção de textos).
  - `ciente_em`: **somente** `tipo=lider`; valor = datetime parseado de `Criado em` (serial Excel via `dates.py`, estender para datetime se a célula tiver fração de dia). Se `Criado em` ilegível → conflito `ciencia_data_invalida` (não persistir nulo em massa). `tipo=colaborador` → `ciente_em` permanece `null` (ciência de líder não se aplica).
  - `created_at`: após `save()`, `QuerySet.update(created_at=...)` se `Criado em` parseável ( `auto_now_add` do `TimeStampedModel` não exige migration). Idempotência compara esse instante.
  - Reexecução: match da chave natural → não duplicar; **não** reescrever `conteudo` alheio (append-only).
  - **NÃO** atribuir `Avaliacao.etapa` / `concluida`.

- **Rationale**: Clarification #3; FR-012/FR-013/FR-014; SC-007. Evita falso positivo de pendência de ciência em ciclo morto.
- **Alternatives considered**:
  - Deixar `ciente_em` nulo “para o líder cientificar de novo” — **descartado** na clarification.
  - Mutar `concluida`/`etapa` — **proibido**.
  - Unique `(avaliacao, autor)` — rejeitado: N textos distintos são válidos.

Datas: [contracts/column-mapping-contract.md](./contracts/column-mapping-contract.md).

---

## R13 — Relatório mascarado (seções desta fatia)

- **Decision**: Estender `apps/accounts/services/legacy_import/report.py` (não criar segundo formatter em `reviews`). Seções estáveis:

```text
notas_criadas / notas_atualizadas / notas_inalteradas
comentarios_criados / comentarios_inalterados
orfaos_avaliacao / orfaos_competencia / orfaos_autor
conflitos_lider_divergente / conflitos_ciclo_aberto
habilidades_extras_criadas / ids_colapsados_resolvidos
(+ conflitos genéricos: peso, escala, snapshot, cálculo, ciência)
```

Amostra mascarada: **máx. 5** por seção; `mask_solides_id` / `mask_pii` existentes; **sem** comentário completo, nome ou e-mail; logs **sem** linha XLSX crua. Totais sempre completos. `raw/` fora do CI.

- **Rationale**: FR-017/FR-018; SC-010; Princípio II.
- **Alternatives considered**:
  - Dump de PII “para debug” — **proibido**.
  - Formatter só em `reviews` — rejeitado: dois mascaramentos (010/011 já em `accounts`).

---

## R14 — Layout de código (accounts parse; reviews domínio)

- **Decision**:

```text
apps/accounts/services/legacy_import/
  parse_xlsx.py     ESTENDER (notas + comentários [+ habilidades opcional])
  dates.py          ESTENDER se necessário (datetime Criado em)
  report.py         ESTENDER (seções R13)

apps/reviews/services/legacy_import/     NOVO
  resolve.py        avaliação canônica, competência, autor, ciclo aberto, extras
  importer.py       orquestração atomic: notas → comentários → calcular_nota_final_*
  snapshots.py      opcional: peso/nível write-once (pode viver em importer)

apps/reviews/management/commands/
  importar_notas_comentarios.py   NOVO — CLI fino

IMPORTAR (não copiar):
  apps/cycles/services/legacy_import/aggregate.py
  apps/competencies/services/catalog_import/{normalize,mapping}.py
  apps/reviews/services/evaluation.py  (só calcular_nota_final_*; NÃO editar)
  resolve_default_escala (003 importer) — reuso read-only
```

**Sem** tocar `apps/dashboard`, templates, urls da 012, `apps/pdi`, `talent` mutators.

- **Rationale**: Princípio IV; FR-002. Reviews persiste nota/feedback; parse único em accounts.
- **Alternatives considered**:
  - Tudo em `accounts` — rejeitado: nota/feedback não são domínio accounts.
  - Tudo em `cycles` — rejeitado: 011 já fechou ciclos/cabeçalhos; esta fatia é reviews.
  - Copiar `aggregate.py` — **proibido**.

---

## R15 — Schema: NENHUMA migration

- **Decision**: `migration-safety` = **zero** migrations. Sem `AddField`, sem `AlterField`, sem `RunPython` de domínio. `sqlmigrate` **não se aplica**. Persistência via ORM existente: `AvaliacaoCompetencia`, `Feedback`, `Competencia` (create mínimo), campos `nota_final_*` via `calcular_*`. Allowlist **sem** `models.py` (exceto create ORM de `Competencia` no schema vigente).
- **Rationale**: FR-019; pedido explícito desta fatia (contraste com 011 que tinha `Ciclo.solides_id`).
- **Alternatives considered**:
  - Migration “por precaução” (ex. unique de Feedback) — **proibido**.
  - Campo de mapa persistido — **proibido** (FR-003).
  - `bulk_create` bypass `full_clean`/`save` — **proibido** (write-once vive em `save()`).

Detalhe: [contracts/migration-safety.md](./contracts/migration-safety.md).

---

## Resolução de Technical Context

| Item | Resolução |
|---|---|
| Parser XLSX | openpyxl existente (010) — R1 |
| CLI | um comando duas fases; `--avaliacoes` só mapa — R2 |
| Mapa colapsado | IMPORTAR `aggregate.py` 011; memória — R3 |
| Resolução avaliação | canônico → mapa → órfão — R4 |
| Auto vs líder | `canonical_key` 003 — R5 |
| Dois líderes | conflito, sem média — R6 |
| Snapshots | Fator + `nivel_esperado_for`; write-once — R7 |
| Fora da escala | conflito, sem clip — R8 |
| Nota final | CHAMAR `calcular_*`; diff `evaluation.py` vazio — R9 |
| Ciclo aberto | status `aberto` → skip — R10 |
| Extras | FK de nota + filtro 003; sem matriz — R11 |
| Feedback | chave natural; `ciente_em` líder — R12 |
| Relatório | estender `report.py`; mascarado — R13 |
| Layout | parse accounts; domínio reviews — R14 |
| Schema | zero migrations — R15 |

**Nenhum NEEDS CLARIFICATION residual.**

---

## Agent context script

**Decision**: Script `update-agent-context` **não existe** neste repositório (`.specify/scripts` só PowerShell de feature setup; `pwsh` também ausente no host — `setup-plan.ps1` replicado em bash). Skip documentado; artefatos em `specs/013-import-notas-comentarios-legado/` são a fonte de verdade (precedente 008/009/012).
