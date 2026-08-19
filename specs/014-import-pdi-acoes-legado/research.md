# Research: Importação One-Shot do Legado Sólides — PDIs e Ações

**Branch**: `014-import-pdi-legado` | **Date**: 2026-08-19

Pesquisa consolidada a partir de [spec.md](./spec.md) (clarifications 2026-08-19 **fechadas**), constituição I–VI, [data/legado-solides/README.md](../../data/legado-solides/README.md) Decisão #22 § PDI, specs [003](../003-import-catalogo-legado/) e [010](../010-import-colaboradores-legado/), models atuais (`PDI.solides_id`, `AcaoPDI` sem ID Sólides, `on_delete=PROTECT`) e hook `AcaoPDI.save()` → `recalculate_overdue_status`.

**Zero `NEEDS CLARIFICATION` residual.** Clarifications 2026-08-19 são decisões **fechadas** — research **implementa**, não re-debate. Stack preenchida no [plan.md](./plan.md) sem marcadores de stack.

Espelha o rigor da [013 research](../013-import-notas-comentarios-legado/research.md), adaptado a esta fatia (persistência de PDI/ação; **zero** migration; **um** path).

---

## Decisões clarificadas (obrigatórias — não reabrir)

| # | Decisão | Implementação |
|---|---|---|
| Granularidade | 1 linha = 1 PDI + 1 ação; concatenação `\n\n`; sem PDI sem ação | R4 |
| Responsável | sempre o dono resolvido; nunca gestor; nunca inventar User | R5 |
| Ciclo / avaliação | zero FK; ID de solicitação só órfão informativo | R6 |
| Chave externa | digest curto em `PDI.solides_id`; ação sem `solides_id` | R-digest, R-idempotência |
| Status PDI/ação | de-para FR-010/FR-011; sem `arquivado` | R7, R-atraso |
| Pessoa | match único `canonical_key(Nome)`; inativo ok | R5 |
| Parser / datas | openpyxl só em `parse_xlsx`; serial Excel + ISO | R1, R8 |
| Operação | `--dry-run`; atomic; exit 0/1 | R2 |
| Schema | zero evolução; PROTECT intacto | R9 |
| Pré-condição | 003+010; 011/013 não bloqueiam | R-ordem |

---

## R1 — Parser: estender `parse_xlsx.py` (`parse_pdi_xlsx`; openpyxl só aqui)

- **Decision**: Estender `apps/accounts/services/legacy_import/parse_xlsx.py` com `parse_pdi_xlsx`. `openpyxl` permanece **exclusivo** deste módulo. Nenhum módulo em `pdi/` importa openpyxl. Colunas obrigatórias e opcionais: [contracts/column-mapping-contract.md](./contracts/column-mapping-contract.md). Células de data/texto permanecem **crus** no dataclass; interpretação em `dates.py` / domínio.
- **Rationale**: Princípio I + precedente 010/011/013; FR-002; backups são OOXML real. Complexity Tracking: lib **já** justificada na 010 — esta fatia **não** adiciona dependência.
- **Alternatives considered**:
  - Nova lib (pandas/xlrd) — rejeitada: constituição I; já existe openpyxl.
  - Segundo `parse_xlsx` em `pdi` — rejeitada: parsers divergentes (Princípio IV).
  - CSV — rejeitada: fonte é OOXML (`backup_pdi_*.xlsx`).

---

## R2 — CLI: um comando, um path `--pdi`

- **Decision**: UM management command `importar_pdi` (app `pdi`). Sem segundo comando.

```bash
python manage.py importar_pdi \
  --pdi PATH \
  [--report-file PATH] \
  [--dry-run]
```

`--pdi` **obrigatório**. `--dry-run` / `--report-file` / exit `0` sucesso (conflitos/órfãos não-fatais) / `1` erro fatal — espelho 010/011/013.

Stdout **MUST** ser byte-a-byte o mesmo conteúdo UTF-8 gravado em `--report-file` quando o arg estiver presente.

CLI **fino**: argparse + chamar `importer`; zero regra de domínio no command.

Scaffold: criar `apps/pdi/management/__init__.py` e `commands/__init__.py` se faltarem (hoje **não** existe pacote management em `pdi`).

- **Rationale**: FR-001; DX igual às fatias anteriores; volume ~86 cabe em one-shot síncrono.
- **Alternatives considered**:
  - Dois commands (PDI vs ação) — rejeitado: FR-001; quebraria a unidade 1+1.
  - UI/upload/DRF — **proibido** (Princípio II; FR-001).
  - Celery porque “padrão VI” — **proibido** nesta fatia (~86; precedente 010–013).

Detalhe: [contracts/import-command-contract.md](./contracts/import-command-contract.md).

---

## R-digest — `PDI.solides_id` = SHA-256 hex truncado (não PII em claro)

- **Decision**: Como o export **não** traz ID Sólides de PDI, preencher o campo **já existente** `PDI.solides_id` (`max_length=50`, unique, nullable) com digest determinístico:

```text
material = canonical_key(Nome) + "\n" + display_name(Título do PDI)
se Criado em parseável (parse_legacy_datetime):
    dt_utc = instante convertido para UTC
    material += "\n" + dt_utc.isoformat()
senão: omitir o instante (ausente ou ilegível = mesmo comportamento)

digest40 = hashlib.sha256(material.encode("utf-8")).hexdigest()[:40]
solides_id = "pdi_" + digest40
# comprimento = 4 + 40 = 44 ≤ 50
```

Regras fechadas:

- **NÃO** hex SHA-256 completo (64 chars estouraria 50, ou forçaria campo novo).
- **NÃO** concatenar nome/título em claro em `solides_id`.
- Prefixo `pdi_` **cabe** (44 ≤ 50) e distingue de IDs numéricos 010/011.
- Determinístico entre runs no mesmo conteúdo canônico + mesmo instante UTC.
- `Criado em` ausente: duas linhas mesmo nome+título colidem no **mesmo** digest — nunca inventar segundo identificador (clarification).
- Digest **não** é schema novo nem PII em claro; upsert do PDI é **por** esse valor.

Função vive em `pdi/services/legacy_import/resolve.py` (stdlib `hashlib`). Teste C6: digest ≠ concatenação de nome/título.

- **Rationale**: FR-008; SC-007; caber em 50; OPSEC no identificador.
- **Alternatives considered**:
  - Hex 64 — rejeitado: não cabe em 50.
  - Nome+título concatenados — **proibido** (PII no identificador).
  - UUID aleatório — rejeitado: não idempotente.
  - Sem prefixo (só 40 hex) — aceitável, mas prefixo curto melhora operação e ainda cabe.

---

## R-atraso — FR-011 **antes** do `save`; hook vigente só via `save()`

- **Decision**: Definir `AcaoPDI.status` pelas regras FR-011 **antes** de `full_clean()`+`save()`:

```text
data_carga = timezone.localdate() no início da execução  # não “Criado em”

se PDI.status == concluido:
    acao.status = concluida          # NUNCA atrasada
senão se PDI.status == ativo e prazo interpretável:
    se prazo < data_carga:  atrasada
    se prazo >= data_carga: pendente
senão prazo ausente/ilegível:
    conflito da linha; NÃO inventar data; NÃO persistir PDI nem ação
```

Depois: `full_clean()` + `save()` **sem** `update_fields` restritivo que pule `prazo` (o `save` vigente chama `recalculate_overdue_status` quando `update_fields is None` ou contém `prazo`).

Comportamento do hook **atual** (`overdue.py`, **MUST NOT edit**):

- `atrasada` + `prazo >= hoje` → rebaixa para `pendente` (coerente com FR-011: esse caso **não** deve ser gravado como atrasada).
- `atrasada` + prazo ainda passado → permanece.
- **Não** promove `pendente`/`em_andamento` → `atrasada` (isso é o job Celery). Por isso o importador **deve** setar `atrasada` **antes** do save quando FR-011 exigir.

**MUST NOT** chamar `mark_overdue_pdi_actions` / `.delay`.  
**MUST NOT** editar `overdue.py`.  
**MUST NOT** chamar `calculate_pdi_progress` nem dashboard/aderência.  
**MUST NOT** usar `AcaoPDI.Status.EM_ANDAMENTO` nesta fatia (só concluída / atrasada / pendente).

- **Rationale**: FR-011/FR-013; constituição V; hook só rebaixa — não substitui FR-011.
- **Alternatives considered**:
  - Confiar só no job diário — rejeitado: carga one-shot ficaria pendente até o Beat; FR-011 exige atraso na linha.
  - Editar `overdue.py` para promover no save — **proibido** (diff MUST empty).
  - Chamar a task Celery no command — **proibido** (massa + e-mail/Beat fora desta fatia).

---

## R-idempotência — upsert conservador (alinhado a 013)

- **Decision**:

**PDI** — chave = `solides_id` digest (R-digest).

| Situação | Ação | Relatório |
|---|---|---|
| Digest inexistente + linha resolvível | Create PDI (título/status da 1ª run) + 1 ação na **mesma** unidade | `pdis_criados` / `acoes_criadas` |
| Digest existe, mesma chave de ação | **Inalterado** — **não** reescrever `titulo`/`status`/`descricao` em silêncio | `pdis_inalterados` / `acoes_inalteradas` |
| Digest existe, título/status da fonte divergem | Conservador 013: **inalterado** (2ª run = skip de mutação; a 1ª run já criou) | `pdis_inalterados` + conflito **somente** se a ação também divergir (abaixo) |
| Digest existe, chave de ação **não** bate com a ação já ligada a esse PDI (descrição normalizada e/ou prazo diferentes) | **Conflito**; **não** criar 2ª ação; **não** apagar/reescrever a existente | `conflitos` (`acao_chave_divergente`) |

**Ação** — **sem** `solides_id`. Chave natural:

```text
(pdi_id, display_name(descricao), prazo)
```

`display_name` = strip + colapso de whitespace (003) — **não** `canonical_key` (perderia distinção de texto de desenvolvimento).

Match da chave → inalterado (não reescrever `descricao` se igual após normalização).  
Divergência de descrição/prazo **no mesmo PDI (mesmo digest)** → conflito, **sem** 2ª ação.

**NÃO** apagar PDI/ação para “refazer”. **NÃO** `bulk_create` que pule `save()`.

Unidade atômica por linha resolvível: persistir PDI **e** ação ou **nenhum** dos dois. Lote inteiro em **uma** `transaction.atomic()`; falha fatal → rollback; conflitos/órfãos por linha são não-fatais (skip da linha).

- **Rationale**: FR-008/FR-009/FR-015/FR-017; SC-005; precedente 013 (2ª run não reescreve snapshot/conteúdo alheio).
- **Alternatives considered**:
  - Update silencioso de título/status na 2ª run — rejeitado: menos conservador; mascara drift da fonte.
  - Segunda ação no mesmo PDI — **proibido** (1 linha = 1 ação; SC-002).
  - Apagar e recriar — **proibido** (PROTECT / constituição III).

---

## R-ordem — 003+010 no ambiente; 011/013 não bloqueiam

- **Decision**: Pré-condição **dura**: catálogo (003) + colaboradores inclusive inativos (010, `PDI.solides_id` já no schema 6.5.1). Specs **011** e **013** **não** são pré-requisito de FK (PDI independente de ciclo/avaliação). Ordem operacional README **passo 7** (6.5.6), depois da 6.5.5 se o ambiente já a tiver — mas a carga de PDI **não espera** notas/ciclos.

- **Rationale**: FR-007; Dependencies da spec; README Decisão #22.
- **Alternatives considered**:
  - Exigir 011/013 — rejeitado: criaria FK fantasma e atrasaria desligar a Sólides como arquivo de PDI.
  - Rodar PDI antes de 010 — rejeitado: não há dono para resolver.

---

## R-PII — persistir no registro; nunca dump completo em superfície tratada

- **Decision**: Título e descrição (Objetivo / Situações concatenados) **persistem** no registro de negócio. Relatório, stdout, stderr, logging, traceback **tratado** e `--report-file` **NUNCA** dumpam texto completo. Reusar `mask_solides_id` / `mask_pii`. Amostra máx. 5/seção: digest mascarado, códigos de motivo, **sem** nome, e-mail, linha bruta, título/objetivo/situação completos. CPF/RG/CTPS/PIS/banco/endereço/telefone **não** importar mesmo que a planilha traga. `raw/` fora do CI.

- **Rationale**: FR-018; SC-008; Princípio II.
- **Alternatives considered**:
  - Dump “só no arquivo de relatório” — **proibido** (stdout == report-file; ambos tratados).
  - Truncar no banco — rejeitado: o arquivo de desenvolvimento precisa do texto; o risco é a superfície operacional.

---

## R3 — Layout: parse accounts; domínio `pdi/services/legacy_import`

- **Decision**:

```text
apps/accounts/services/legacy_import/
  parse_xlsx.py     ESTENDER parse_pdi_xlsx
  dates.py          ESTENDER se necessário (reusar parse_legacy_date / parse_legacy_datetime)
  report.py         ESTENDER seções R10

apps/pdi/services/legacy_import/     NOVO
  resolve.py        pessoa, digest, concatenação, de-para, chave de ação
  importer.py       atomic: resolve → 1 PDI + 1 ação; dry-run

apps/pdi/management/commands/
  importar_pdi.py   NOVO — CLI fino

IMPORTAR (não copiar, NÃO editar):
  apps/competencies/services/catalog_import/normalize.py
  apps/pdi.models PDI / AcaoPDI / CustomUser
  AcaoPDI.save → overdue (chamar via save)
```

- **Rationale**: Princípio IV; FR-002.
- **Alternatives considered**:
  - Tudo em `accounts` — rejeitado: PDI não é domínio accounts.
  - Tudo em `pdi` incluindo openpyxl — rejeitado: segundo parser.

---

## R4 — Granularidade e concatenação da descrição

- **Decision**: 1 linha da planilha = 1 PDI + **exatamente** 1 ação. Descrição = trechos **não vazios** após `display_name`, nesta ordem, separados por `\n\n`:

```text
Objetivo  →  Situação Atual  →  Situação Desejada
```

Sem rótulo extra. Os três vazios (ou só whitespace) → conflito/skip; **não** persiste PDI sem ação. **Não** criar três ações.

- **Rationale**: Clarification granularidade; FR-004/FR-005.
- **Alternatives considered**:
  - Três ações — **descartado**.
  - Um campo “observações” extra — rejeitado: schema sem campo novo.

---

## R5 — Resolução de pessoa (nunca inventar)

- **Decision**: Match **único** via `canonical_key(Nome)` contra `CustomUser` já importado (010), **incluindo inativos**. Se o dump trouxer identificador Sólides da pessoa (coluna opcional, se o header existir — ex. `Identificador` de colaborador / `Identificador Avaliado`):

```text
1. Se ID presente e unique hit em CustomUser.solides_id:
     se Nome também unique e aponta para OUTRA pessoa → conflito (id_vs_nome)
     senão usar o User do ID
2. Senão match único por canonical_key(Nome)
3. Zero ou 2+ nomes → orfaos_usuario; NUNCA o “primeiro”
4. NUNCA get_or_create User; NUNCA inventar colaborador
```

Responsável da ação = **o mesmo** User do PDI. **Nunca** `line_manager`. Inatividade **não** bloqueia a carga e **não** cria atalho de visibilidade.

O comando **MUST NOT** chamar `get_visible_users` / `user_in_scope` / `ScopedObjectMixin` “para autorizar”.

- **Rationale**: FR-006/FR-012/FR-020; Princípio II.
- **Alternatives considered**:
  - Atribuir ao gestor — **proibido**.
  - Criar User órfão — **proibido**.

---

## R6 — Zero FK ciclo/avaliação

- **Decision**: Não persistir vínculo a `Ciclo` nem `Avaliacao`. Coluna opcional `Identificador Solicitação` (se existir): **não** bloqueia linha resolvível; no máximo seção informativa `orfaos_solicitacao` (contador + amostra mascarada de ID). **Não** lookup de ciclo.

- **Rationale**: FR-007; SC-004.
- **Alternatives considered**:
  - FK “se o ciclo 011 existir” — rejeitado: tornaria 011 pré-requisito.

---

## R7 — De-para de status do PDI

- **Decision**: Após `display_name` + casefold:

```text
finalizado   → PDI.Status.CONCLUIDO
em_andamento → PDI.Status.ATIVO
qualquer outro (incl. vazio, arquivado legado) → conflito/skip
```

**MUST NOT** gravar `PDI.Status.ARQUIVADO` nesta fatia. Recorte 67/19 do dump de referência **não** se inverte.

- **Rationale**: FR-010; SC-011.
- **Alternatives considered**:
  - Mapear desconhecido → arquivado — **proibido**.

---

## R8 — Datas: reusar `dates.py` (estender só se faltar formato)

- **Decision**: `Data de Entrega` → `parse_legacy_date` (serial Excel + ISO → `date`). `Criado em` → `parse_legacy_datetime` (serial com fração + ISO → instante do digest). Ambos **já** implementados na 013. Estender `dates.py` **somente** se o dump 6.5.6 trouxer formato não coberto; **sem** openpyxl neste módulo. `0` / vazio → ausente. `ValueError` em prazo → conflito da linha.

Data da carga para atraso = `timezone.localdate()` no **início** da execução.

- **Rationale**: FR-014; precedente 010/013.
- **Alternatives considered**:
  - Parser de data em `pdi/` — rejeitado: duplicação.
  - Usar “Criado em” como data de atraso — rejeitado (Assumptions da spec).

---

## R9 — Schema: NENHUMA migration

- **Decision**: `migration-safety` = **zero** migrations. Sem `AddField`, sem `AlterField` em `solides_id`, sem `solides_id` em `AcaoPDI`, sem FK ciclo/avaliação, sem RunPython. `sqlmigrate` **não se aplica**. Allowlist **sem** `models.py`.

- **Rationale**: FR-019.
- **Alternatives considered**:
  - Campo de mapa / ID na ação — **proibido**.
  - `bulk_create` bypass `save()` — **proibido** (atraso vive em `save()`).

Detalhe: [contracts/migration-safety.md](./contracts/migration-safety.md).

---

## R10 — Relatório mascarado (seções desta fatia)

- **Decision**: Estender `apps/accounts/services/legacy_import/report.py` (não criar segundo formatter em `pdi`). Seções estáveis:

```text
pdis_criados / pdis_atualizados / pdis_inalterados
acoes_criadas / acoes_atualizadas / acoes_inalteradas
orfaos_usuario
orfaos_solicitacao          # informativo; 0 se coluna ausente
conflitos_*                 # status, prazo, descricao_vazia, titulo, id_vs_nome, acao_chave_divergente, …
```

`pdis_atualizados` / `acoes_atualizadas` existem no contrato de totais (FR-015) mas a política conservadora R-idempotência **não** reescreve título/status/descrição na 2ª run — na prática o caminho feliz da reexecução é **inalterado** (contadores de atualizado podem permanecer 0). Reservados para a 1ª run **somente** se uma emenda futura documentar update; esta fatia **não** usa update silencioso.

Amostra mascarada: **máx. 5** por seção; `mask_solides_id` / `mask_pii`; **sem** nome, e-mail, linha bruta, título/objetivo completos.

- **Rationale**: FR-015/FR-018; SC-008.
- **Alternatives considered**:
  - Formatter só em `pdi` — rejeitado: dois mascaramentos (010/011/013 já em `accounts`).

---

## Resolução de Technical Context

| Item | Resolução |
|---|---|
| Parser XLSX | openpyxl existente (010) — R1 |
| CLI | um comando, `--pdi` — R2 |
| Digest | SHA-256 hex[:40] + prefixo `pdi_` (44) — R-digest |
| Atraso | FR-011 antes do save; hook só via save — R-atraso |
| Idempotência | upsert digest; ação (pdi, display_name, prazo); 2ª run inalterado; divergência → conflito — R-idempotência |
| Ordem | 003+010; 011/013 opcionais; README passo 7 — R-ordem |
| PII | persiste no DB; superfície mascarada — R-PII |
| Pessoa | canonical_key único; inativo ok — R5 |
| Concatenação | `\n\n`; 1+1 — R4 |
| Datas | `parse_legacy_date` / `parse_legacy_datetime` — R8 |
| Schema | zero migrations — R9 |
| Relatório | estender `report.py` — R10 |
| Layout | parse accounts; domínio pdi — R3 |

**Nenhum NEEDS CLARIFICATION residual.**

---

## Agent context script

**Decision**: Script `update-agent-context` **não existe** neste repositório (`.specify/scripts` só PowerShell de feature setup; `pwsh` também ausente no host — `setup-plan.ps1` replicado em bash). Skip documentado; artefatos em `specs/014-import-pdi-acoes-legado/` são a fonte de verdade (precedente 008–013).
