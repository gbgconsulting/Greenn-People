# Data Model: Importação Legado Sólides — Notas por Competência e Comentários Qualitativos

**Branch**: `013-import-notas-comentarios-legado` | **Date**: 2026-08-18

**Nota**: Esta fatia **não** introduz models novos nem migrations. Persiste `AvaliacaoCompetencia` e `Feedback` no schema vigente; pode **criar** `Competencia` mínima (ORM existente) só como FK de nota; preenche `Avaliacao.nota_final_*` **chamando** a fórmula vigente. Cabeçalhos `Avaliacao` da 011 são **read-only**. Sem máquina de estados nova.

Models canônicos: [apps/reviews/models.py](../../apps/reviews/models.py), [apps/competencies/models.py](../../apps/competencies/models.py), [apps/accounts/models.py](../../apps/accounts/models.py), [apps/cycles/models.py](../../apps/cycles/models.py).

Contratos: [contracts/model-allowlist.md](./contracts/model-allowlist.md), [contracts/migration-safety.md](./contracts/migration-safety.md), [contracts/snapshot-and-formula.md](./contracts/snapshot-and-formula.md), [contracts/collapsed-id-resolution.md](./contracts/collapsed-id-resolution.md), [contracts/column-mapping-contract.md](./contracts/column-mapping-contract.md).

---

## Regras estritas de models / migrations

### PERMITIDO (esta fatia)

| Alteração | Escopo |
|---|---|
| ORM create/update `AvaliacaoCompetencia` | unique `(avaliacao, competencia)`; snapshots write-once na 1ª save |
| ORM create `Feedback` | N por avaliação; append-only de conteúdo |
| ORM create `Competencia` mínima | só FK de nota + filtro KPI/ambíguos 003; **sem** `CargoCompetencia` |
| `Avaliacao.nota_final_lider` / `nota_final_autoavaliacao` | **somente** via `calcular_nota_final_*` (não atribuição solta que recopie fórmula) |
| `Feedback.ciente_em` | preenchido em `tipo=lider` com `Criado em` |
| Extensão parse/dates/report 010/011 | módulos irmãos |
| Samples + testes | `data/legado-solides/samples/`, `tests/test_import_notas_comentarios_legado.py` |

### PROIBIDO

| Proibição | Motivo |
|---|---|
| Qualquer migration / `AddField` / `AlterField` / `RunPython` | FR-019 |
| Alterar tipo, opcionalidade, unicidade ou `on_delete` | Constituição III |
| Inventar `Avaliacao`, `Ciclo` ou `CustomUser` | FR-004/FR-012 |
| Mutar `Avaliacao.etapa` / `concluida` | Clarification #3; 011 intacta |
| Chamar `create_competency_lines` | FR-010 — retrato do presente |
| Editar `evaluation.py` / reimplementar normalização | FR-011/FR-021 |
| Criar `CargoCompetencia` (~2.720) | Clarification #1 |
| `bulk_create` bypass `full_clean`/`save` | write-once vive em `save()` |
| Tabela persistida de mapa de IDs | FR-003 |
| Usar `raw/` no CI | FR-022 |

### Persistência obrigatória

- Toda escrita MUST chamar `full_clean()` + `save()` (exceto `QuerySet.update(created_at=...)` pontual pós-save para honrar `Criado em` legado — não é bypass de domínio).
- Snapshots: 1ª save preenche; 2ª run **não** reatribui `peso_utilizado` / `nivel_esperado_utilizado`.

---

## Entidade: Avaliação (cabeçalho, 011) — read-only

**Model**: `reviews.Avaliacao`  
**Fonte desta fatia**: lookup apenas. **Não** cria, **não** duplica, **não** altera `etapa`/`concluida`.

| Campo | Uso nesta fatia |
|---|---|
| `solides_id` | Lookup (a) canônico; (b) via mapa colapsado→canônico |
| `ciclo` | Guard de ciclo aberto (`status=aberto` → skip) |
| `usuario` | Avaliado — cargo → `nivel_esperado_for` |
| `etapa` / `concluida` | **Intocados** (011: `feedback` / `True`) |
| `nota_final_lider` / `nota_final_autoavaliacao` | Preenchidos **só** por `calcular_nota_final_*` |

### Relacionamentos

- `AvaliacaoCompetencia.avaliacao` → `Avaliacao` (`on_delete=PROTECT`)
- `Feedback.avaliacao` → `Avaliacao` (`on_delete=PROTECT`)

Não há state machine nesta fatia.

---

## Entidade: Linha de nota por competência (`AvaliacaoCompetencia`)

**Model**: `reviews.AvaliacaoCompetencia`  
**Fonte**: `backup_notas_avaliacoes_*` (~7.360)

### Campos persistidos

| Campo | Origem | Regras |
|---|---|---|
| `avaliacao` | Resolução R4 (canônico / mapa / órfão) | Nunca inventar avaliação |
| `competencia` | `Identificador Habilidade` → `Competencia.solides_id`; extra sob R11 | Órfão se não resolve |
| `nota_autoavaliacao` | `Nota` se `is_auto` | Nunca copiar para `nota_lider` |
| `nota_lider` | `Nota` se não-auto | Dois valores distintos no grupo → conflito; não persiste líder |
| `peso_utilizado` | `Fator no Momento` | 1ª save; ausente/inválido/≤0 → conflito; **não** assumir 1 |
| `nivel_esperado_utilizado` | `nivel_esperado_for(avaliado.cargo.nivel)` | Dump **sem** coluna; cargo irresolvível → skip |

### Constraints existentes (intocados)

- `UniqueConstraint (avaliacao, competencia)` — idempotência = upsert dessa chave
- FKs `PROTECT`
- `save()`: se `pk` e snapshot diferir do persistido → `ValidationError` write-once

### Validação / upsert

| Situação | Ação |
|---|---|
| Linha nova | Create com snapshots + nota do lado correto |
| Mesma chave, snapshots iguais, nota muda | Update só `nota_*` → `atualizado` |
| Mesma chave, snapshots iguais, nota igual | `inalterado` |
| Mesma chave, fonte de snapshot diverge | `conflito` (`snapshot_divergente`); **não** reescrever snapshot; **não** apagar |
| `ValidationError` write-once | Tratar como conflito; linha permanece |
| Nota fora da escala da competência | Conflito; sem clip |
| Ciclo `aberto` | `conflitos_ciclo_aberto`; skip |
| Dois líderes divergentes | `conflitos_lider_divergente`; sem média |

### Transições de estado

Nenhuma. Não há máquina de estados em `AvaliacaoCompetencia`.

---

## Entidade: Competência extra mínima

**Model**: `competencies.Competencia` (schema vigente)  
**Pré-condição**: catálogo 003 (43) já carregado.

| Campo | Valor na create extra |
|---|---|
| `nome` | `display_name(habilidade)` |
| `tipo` | `map_grupo_tipo(Grupo)` se `--habilidades`; senão `tecnica` |
| `escala` | `resolve_default_escala()` (Escala padrão 1–5 da 003) |
| `solides_id` | `Identificador Habilidade` |
| `is_active` | `True` |
| `descricao` | `''` (mínimo) |

**Não** criar `CargoCompetencia`.  
Criar **somente** se a nota referencia **e** passa filtro `not is_kpi` **e** `not is_ambiguous`. Senão → `orfaos_competencia`.

---

## Entidade: Feedback qualitativo

**Model**: `reviews.Feedback`  
**Fonte**: `backup_comentarios_avaliacoes_*` (~1.494)

| Campo | Origem | Regras |
|---|---|---|
| `avaliacao` | Mesmo R4 da US1 (inclui IDs colapsados) | Órfão se avaliação irresolvível |
| `autor` | `User.solides_id` = `Identificador Avaliador`; fallback nome único | Órfão se não resolve; inativo ok |
| `tipo` | R5 auto → `colaborador`; senão `lider` | |
| `conteudo` | `Comentário` | Persistido no registro de negócio; **não** no relatório |
| `ciente_em` | `Criado em` se `tipo=lider` | **Não** nulo em massa; colaborador → `null` |
| `created_at` | `Criado em` via `update` pós-save | Parte da chave natural |

### Idempotência (chave natural)

```text
(avaliacao_id, autor_id, tipo, display_name(conteudo), instante Criado em)
```

Match → não duplicar; **não** reescrever `conteudo`. N por avaliação é válido.

### Transições

Nenhuma. Append-only. Sem unique de schema novo.

---

## Entidade: Mapa de IDs colapsados (em memória — não é model)

Derivado de `aggregate_avaliacao_headers` sobre `--avaliacoes` (backup de cabeçalhos 011).

```text
collapsed_id → canonical_id
canonical_id → canonical_id   # identidade
```

Não persistir. Relatório: `ids_colapsados_resolvidos` (totais + amostra mascarada).

Normativo: [specs/011-import-ciclos-avaliacoes-legado/contracts/aggregation-contract.md](../011-import-ciclos-avaliacoes-legado/contracts/aggregation-contract.md). Esta fatia só **consome**: [contracts/collapsed-id-resolution.md](./contracts/collapsed-id-resolution.md).

---

## Entidade: Nota final (derivada)

Não é model novo. Resultado de `calcular_nota_final_lider` / `calcular_nota_final_autoavaliacao` sobre as linhas históricas (peso congelado + escala da competência). `CalculationError` → conflito no relatório, sem média inventada.

---

## Entidades de suporte (read-only)

| Entidade | Uso |
|---|---|
| `CustomUser` | Avaliado (cargo/nível) e autor; `solides_id`; inativo permitido; **sem** create |
| `Cargo` | `nivel` (1–6) → `nivel_esperado_for` |
| `Ciclo` | `status`; aberto → skip |
| `Escala` | Bounds da nota; padrão 1–5 para extras |
| `CargoCompetencia` | **NUNCA lido** para peso/nível desta fatia |

---

## Relatório de carga (artefato operacional)

Não é model Django. Contadores estáveis (ver [contracts/import-command-contract.md](./contracts/import-command-contract.md)):

| Contador | Significado |
|---|---|
| `notas_criadas` / `atualizadas` / `inalteradas` | Fase 1 |
| `comentarios_criados` / `inalterados` | Fase 2 |
| `orfaos_avaliacao` / `orfaos_competencia` / `orfaos_autor` | Skip sem inventar |
| `conflitos_lider_divergente` | Dois líderes, sem média |
| `conflitos_ciclo_aberto` | Histórico ≠ operação |
| `habilidades_extras_criadas` | FK estrita |
| `ids_colapsados_resolvidos` | Handoff 011 consumido |
| `conflitos` (peso, escala, snapshot, cálculo, ciência) | Demais |

Amostra mascarada ≤ 5 / seção.

---

## Diagrama de relacionamentos (pós-import)

```text
Ciclo (011, encerrado; status=aberto → esta fatia SKIP)
  └── Avaliacao* (011 read-only; solides_id canônico; etapa/concluida intactos)
        ├── usuario → CustomUser (cargo.nivel → nivel_esperado_for)
        ├── nota_final_* ← calcular_nota_final_* (evaluation.py, intocado)
        ├── AvaliacaoCompetencia* (unique avaliacao+competencia)
        │     ├── competencia → Competencia (43 da 003 ∪ extras mínimas)
        │     ├── nota_autoavaliacao / nota_lider
        │     └── peso_utilizado, nivel_esperado_utilizado (write-once)
        └── Feedback* (N; tipo; ciente_em se lider)
              └── autor → CustomUser
```

Mapa colapsado: **não** aparece no DB.

---

## Ordem de persistência (dentro de `transaction.atomic`)

```text
0. Pré: 003 + 010 + 011 aplicadas; ZERO migrate desta fatia
1. Parse notas, comentários, cabeçalhos (--avaliacoes)
2. Rebuild mapa em memória (aggregate.py 011)
3. Se --dry-run: projetar totais; zero write; emitir relatório
4. Senão atomic:
   a. Fase Notas — resolve + upsert AvaliacaoCompetencia (snapshots 1ª save)
   b. Por avaliação tocada — calcular_nota_final_lider; auto se contrato aplicar
   c. Fase Comentários — resolve + create Feedback (ciência líder)
5. Emitir relatório mascarado
```

Falha na transação → rollback **das duas fases**. Dry-run nunca entra no atomic de write.
