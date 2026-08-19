# Contract: Management Command `importar_colaboradores`

**App**: `accounts`  
**Feature**: `010-import-colaboradores-legado`  
**Data**: 2026-08-12

Contrato da superfície CLI. Mapeamento colunas: [column-mapping-contract.md](./column-mapping-contract.md). Crosswalk: [solides-id-crosswalk-contract.md](./solides-id-crosswalk-contract.md). Modelo: [../data-model.md](../data-model.md).

---

## Invocação

```bash
python manage.py importar_colaboradores \
  --colaboradores /caminho/backup_colaboradores_20260624.xlsx \
  [--avaliacoes /caminho/backup_avaliacoes_20260624.xlsx] \
  [--report-file /caminho/relatorio.txt] \
  [--dry-run]
```

### Argumentos

| Arg | Obrigatório | Descrição |
|---|---|---|
| `--colaboradores` | sim | Path do backup colaboradores (OOXML real) |
| `--avaliacoes` | não | Path do backup avaliações para crosswalk `solides_id` |
| `--report-file` | não | Grava relatório UTF-8 adicional |
| `--dry-run` | não | Parse + totais projetados, **zero commit** |

---

## Pré-condições

1. Migrations 6.5.1 aplicadas (`solides_id` existe nos cinco models).
2. Catálogo spec 003 executado (recomendado — cargos base existentes).
3. Path colaboradores existe e é legível OOXML.
4. Header contém colunas obrigatórias (ver column-mapping-contract § Obrigatórias).
5. Se `--avaliacoes`: header contém `Nome Avaliado`, `Identificador Avaliado`.

Falha pré-persistência → **nenhuma escrita**; exit `1`.

---

## Semântica de execução

1. **Parse** colaboradores (+ avaliações se informado) via openpyxl.
2. **Crosswalk** Nome → Identificador Avaliado (opcional).
3. **Simulação ou persist**:
   - `--dry-run`: totais projetados only.
   - Caso contrário: `transaction.atomic()` ordem Area → Cargo → User → line_manager (2ª passada).
4. Toda persistência via `full_clean()` + `save()` / `create_user()`.
5. Relatório com amostras **mascaradas** (nunca CPF/e-mail completo em stdout produção).

---

## Códigos de saída

| Code | Significado |
|-----:|---|
| `0` | Concluído (persist ok ou dry-run ok). Relatório pode conter conflitos/não resolvidos não-fatais. |
| `1` | Erro fatal: args inválidos, arquivo ausente/ilegível, colunas obrigatórias ausentes, falha de migration pré-requisito, exceção na persistência (rollback). |

Alinhado à spec 003. Sem exit `2` nesta versão.

---

## Formato do relatório (stdout / `--report-file`)

Texto UTF-8, seções estáveis:

```text
=== Importação colaboradores legado Sólides ===
modo: persist|dry-run
colaboradores_file: ...
avaliacoes_file: ...|ausente

--- Resumo ---
areas_criadas: N
areas_reutilizadas: N
cargos_criados: N
cargos_atualizados: N
cargos_inalterados: N
usuarios_criados: N
usuarios_atualizados: N
usuarios_inalterados: N
solides_id_preenchidos: N
demitidos_inativos: N
gestores_vinculados: N
sem_gestor: N
nao_importaveis: N
conflitos: N
ciclos_hierarquia: N

--- Amostra (mascarada, max 5 por seção) ---
criados:
  - nome=João Silva | email=j***@greenn.com.br | area=Tech | cargo=Dev PL
nao_importaveis:
  - linha=42 | motivo=sem_email
conflitos:
  - tipo=email_duplicado_backup | email=m***@example.com | linhas=10,88
  - tipo=crosswalk_ambiguo | nome=Maria | ids=123,456
  - tipo=gestor_nao_resolvido | superior_id=999 | usuario=m***@example.com
ciclos_hierarquia:
  - usuarios=a@..., b@..., c@... | motivo=ciclo_detectado

=== Fim ===
```

Requisitos:
- Contadores MUST bater com cardinalidade das listas (ou amostra documentada como truncada).
- **NEVER** emitir CPF, RG, telefone, endereço ou e-mail completo.
- Operador revisa totais em < 2 min para ~325 linhas (SC-010).

---

## Efeitos colaterais permitidos

| Permitido | Proibido |
|---|---|
| Create/update `Area`, `Cargo`, `CustomUser` | Alterar `scope.py`, AuthZ, stage, approval |
| Set `email_confirmado_em=now()` na importação | Importar avaliações/notas/PDI |
| Set `solides_id` em User/Cargo quando resolvível | Mutar `Avaliacao.etapa` / snapshots |
| `set_unusable_password()` em novos users | Log linha completa com PII |
| Relatório mascarado | UI/upload/DRF/Celery |

---

## Contratos de teste

- Args faltando / arquivo inexistente → exit 1, DB inalterado.
- Fixture mínima anonimizada → cria areas/users; dry-run zero writes.
- Segunda execução → zero duplicatas e-mail.
- Demitido com data → `is_active=False`.
- Ciclo hierárquico artificial → reportado, vínculo não aplicado.
- `--avaliacoes` fixture → `solides_id` preenchido quando match único.
- Nenhum teste lê `data/legado-solides/raw/`.
