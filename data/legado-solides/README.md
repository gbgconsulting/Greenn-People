# Legado Sólides — Backups e layout para importação

**Data do dump:** 2026-06-24 (prefixo `20260624` nos nomes dos arquivos)  
**Origem:** exportação/backup Sólides Performance  
**Status:** inventário e mapeamento documentados (Decisão #22 / PRD Sprint 6.5) — **comandos de import ainda não implementados** (exceto catálogo parcial, spec `003-import-catalogo-legado`)

Este diretório alimenta a especificação e os management commands da Sprint 6.5 (PRD §6.5). Não executar writes de produção a partir destes arquivos sem `--dry-run` e banco descartável/staging.

---

## Estrutura

```text
data/legado-solides/
├── README.md          ← este arquivo
└── raw/               ← backups completos (contêm PII — ver § Segurança)
    ├── backup_colaboradores_*.xlsx
    ├── backup_habilidades_*.xlsx
    ├── backup_habilidades_cargo_*.xlsx
    ├── backup_solicitacoes_avalicaoes_*.xlsx
    ├── backup_avaliacoes_*.xlsx
    ├── backup_notas_avaliacoes_*.xlsx
    ├── backup_comentarios_avaliacoes_*.xlsx
    ├── backup_pdi_*.xlsx
    └── backup_treinamentos_*.xlsx   ← fora do escopo PRD 6.5
```

---

## Formato dos arquivos

| Aspecto | Catálogo 003 (`lista-*.xlsx` na raiz) | Backups Sólides (`raw/*.xlsx`) |
|---|---|---|
| Formato real | CSV UTF-8 com extensão `.xlsx` | **Microsoft Excel 2007+ (OOXML)** |
| Parser atual | `csv` (stdlib) | Requer **`openpyxl`** ou equivalente |
| Planilhas | 1 | 1 (`sheet1`) por arquivo |

Inspeção rápida (2026-08-12):

```bash
file data/legado-solides/raw/*.xlsx
# → Microsoft Excel 2007+
```

---

## Inventário e volumes

| Arquivo | Linhas (c/ header) | Fatia PRD | Comando previsto |
|---|---:|---|---|
| `backup_colaboradores_*.xlsx` | 325 | 6.5.2 | `importar_colaboradores` |
| `backup_habilidades_*.xlsx` | 100 | 6.5.3 (extensão) | reutilizar / estender `importar_competencias_cargo` |
| `backup_habilidades_cargo_*.xlsx` | 2.720 | 6.5.3 | idem |
| `backup_solicitacoes_avalicaoes_*.xlsx` | 57 | pré-6.5.4 | mapeamento → `Ciclo` |
| `backup_avaliacoes_*.xlsx` | 1.925 | 6.5.4 | `importar_avaliacoes` |
| `backup_notas_avaliacoes_*.xlsx` | 7.360 | 6.5.5 | `importar_notas` |
| `backup_comentarios_avaliacoes_*.xlsx` | 1.494 | 6.5.5 | `importar_comentarios` |
| `backup_pdi_*.xlsx` | 86 | 6.5.6 | `importar_pdi` |
| `backup_treinamentos_*.xlsx` | 119 | — | **fora de escopo** v1 |

### Estatísticas úteis (dump 2026-06-24)

**Colaboradores**

- 325 registros totais; **127 ativos** (sem `Data demissão`); **198 demitidos**
- 325 com algum e-mail; **212** `@greenn.com.br` no campo principal `E-mail`
- 260 com `Superior direto id`; **15 ativos** sem superior (topo ou dado incompleto)
- 27 `Departamento` distintos; coluna `Unidade` **vazia** em todos
- **Sem coluna de ID Sólides do colaborador** no export (ver § Identificadores)

**Catálogo (vs. spec 003)**

- `lista-competencias` (003): 43 competências — **100% contidas** em `backup_habilidades` (match exato por nome)
- `backup_habilidades`: **57 habilidades extras** (grupos legados adicionais, ex. Comportamental Geral, Preparo e Qualificação Técnica)
- Cargos: 100 nomes em colaboradores; **92** intersectam `lista-cargos`; **8** só no backup de colaboradores

**Avaliações / histórico**

- 57 solicitações (= ciclos Sólides): 50 `finished`, 1 `active`, 3 `draft`, 3 `canceled`
- 1.925 cabeçalhos de avaliação; 7.360 linhas de nota (escala **1–5**)
- Notas: **2.213** auto (`Nome Avaliador` = `Nome Avaliado`); **5.147** líder
- 1.494 comentários qualitativos
- IDs de avaliação neste dump **sem** anomalia “ano 5810”; tratar defensivamente na implementação (PRD 6.5.4)

**PDI**

- 86 registros: 67 `finalizado`, 19 `em_andamento`

---

## Segurança e PII

Os arquivos em `raw/` contêm **dados pessoais sensíveis**, incluindo:

- CPF, RG, CTPS, PIS, dados bancários, endereço, telefone
- E-mails pessoais e corporativos
- Comentários qualitativos de avaliação

**Regras:**

- Repositório **privado** apenas; não publicar `raw/` em fork público
- Comandos de import **não** devem logar linhas completas em produção
- Testes automatizados devem usar **fixtures mínimas anonimizadas**, não estes arquivos
- Import sempre em **staging / banco descartável** antes de produção

---

## Ordem de importação (dependências)

Ordem segura para não quebrar FKs nem regras de domínio:

```text
1. [6.5.1] Migration solides_id (CustomUser, Cargo, Competencia, Avaliacao, PDI) — ainda não existe
2. [6.5.3] Catálogo cargos/competências — importar_competencias_cargo (003) OU extensão via backup_habilidades*
3. [6.5.2] Colaboradores + áreas + hierarquia — backup_colaboradores (+ crosswalk de IDs)
4. Solicitações → Ciclo (status encerrado; histórico não abre ciclo ativo)
5. [6.5.4] Cabeçalhos Avaliacao — backup_avaliacoes
6. [6.5.5] Notas — backup_notas_avaliacoes
7. [6.5.5] Comentários / feedback — backup_comentarios_avaliacoes
8. [6.5.6] PDI — backup_pdi
9. Homologação — contagens, FKs, pytest stage/scope
```

**Denylist (não alterar na importação):** `stage.py`, `approval.py`, fórmulas de nota/aderência, `scope.py`, regras de avanço de etapa. Import **persiste histórico**; não simula POSTs de ciclo.

---

## Identificadores Sólides (`solides_id`)

PRD 6.5.1 prevê `solides_id` em `CustomUser`, `Cargo`, `Competencia`, `Avaliacao`, `PDI`. **Campo ainda não existe nos models** (2026-08-12).

| Entidade | Coluna(s) no backup | Estratégia proposta |
|---|---|---|
| **Cargo** | `Cargo ID` (colaboradores); `Identificador Cargo` (habilidades_cargo) | Chave primária legado; match nome via `canonical_key` (003) como fallback |
| **Competência** | `Identificador` (habilidades) | Idem; 43 já importáveis via 003 por nome |
| **Usuário** | **Ausente** em colaboradores | Crosswalk: `Nome` → `Identificador Avaliado` em `backup_avaliacoes` (~187 matches, 0 conflitos de ID); demais usuários: **`solides_id` nullable**, chave natural = **e-mail** |
| **Gestor** | `Superior direto id` | ID Sólides; resolver para `CustomUser` após import de usuários (29/31 IDs batem com avaliações) |
| **Ciclo** | `Identificador Solicitação` (avaliações) / `Identificador` (solicitações) | Mapear para `Ciclo`; solicitações `finished` → `status=encerrado` |
| **Avaliação** | `Identificador` (avaliações) | FK composta lógica: solicitação + avaliado + avaliador |
| **Nota** | `Identificador Avaliação` + `Identificador Habilidade` | Join avaliação + competência |
| **PDI** | (sem ID explícito no export) | Chave composta: `Nome` + `Título do PDI` + `Criado em` ou gerar hash determinístico |

---

## Mapeamento coluna → domínio Django

### `backup_colaboradores_*.xlsx` → `accounts.CustomUser` + `organization`

| Coluna Sólides | Campo Django | Regras |
|---|---|---|
| `Nome` | `CustomUser.nome` | strip / colapsar whitespace |
| `E-mail empresarial` | `CustomUser.email` | **1ª preferência** |
| `E-mail` | `CustomUser.email` | 2ª preferência |
| `E-mail pessoal` | — | 3ª preferência se demais vazios; import **não** exige `@greenn.com.br` (Decisão #21) |
| *(import)* | `CustomUser.email_confirmado_em` | `now()` na importação — sem link de confirmação |
| `Data demissão` | `CustomUser.is_active` | Preenchida e ≠ 0 → `False`; senão `True` |
| `Cargo` / `Cargo ID` | `CustomUser.cargo` | Resolver `Cargo` por `solides_id` ou `canonical_key(nome)` |
| `Departamento` | `CustomUser.area` | Criar/obter `Area.nome`; `Unidade` ignorada (vazia) |
| `Superior direto id` | `CustomUser.line_manager` | 2ª fase: após todos os usuários; validar aciclicidade (RF-04.1) |
| `Data admissão` | — | Informativo / auditoria futura; serial Excel ou ISO |
| CPF, RG, banco, endereço, etc. | — | **Não importar** na v1 (fora do model) |

**Datas:** muitas colunas usam **serial Excel** (ex. `45446.0` = dias desde 1899-12-30). Parser deve aceitar serial numérico e strings ISO.

### `backup_habilidades_*.xlsx` → `competencies.Competencia`

| Coluna | Campo | Notas |
|---|---|---|
| `Identificador` | `solides_id` (futuro) | |
| `Habilidade` | `nome` | Reutilizar `canonical_key` da 003 |
| `Descrição` | `descricao` | |
| `Grupo` | `tipo` | De-para 003: Liderança→`lideranca`, Comportamento*→`comportamental`, Desempenho→`tecnica`; grupos novos → relatório / filtro KPI |
| `Arquivado?` | `is_active` | `t` → inativo |
| `Fator` | — | Ignorar ou snapshot informativo |

### `backup_habilidades_cargo_*.xlsx` → `competencies.CargoCompetencia`

| Coluna | Campo | Notas |
|---|---|---|
| `Identificador Cargo` | FK `Cargo` | via `solides_id` |
| `Identificador Habilidade` | FK `Competencia` | via `solides_id` |
| — | `peso` | `1` (igual 003) |
| — | `nivel_esperado` | derivado de `Cargo.nivel` (tabela 003) |

### `backup_solicitacoes_avalicaoes_*.xlsx` → `cycles.Ciclo`

| Coluna | Campo | Notas |
|---|---|---|
| `Identificador` | `solides_id` (futuro) | |
| `Nome` | `Ciclo.nome` | Cuidado: algumas linhas podem vir como serial Excel (ex. `46113.0`) — normalizar |
| `Iniciada em` / `Terminada em` | `data_inicio` / `data_fim` | Serial Excel → date |
| `Status` | `Ciclo.status` | `finished`/`canceled`/`draft` → `encerrado`; `active` → decisão explícita (provavelmente `encerrado` no histórico) |
| `Criada em` | — | Auditoria |

### `backup_avaliacoes_*.xlsx` → `reviews.Avaliacao`

| Coluna | Campo | Notas |
|---|---|---|
| `Identificador Solicitação` | FK `Ciclo` | |
| `Identificador Avaliado` | FK `usuario` | crosswalk e-mail/nome |
| `Identificador` | `solides_id` (futuro) | |
| `Avaiação criada em` | — | Referência temporal; etapa importada como **concluída** ou derivada do status Sólides (definir na spec) |
| — | `etapa` | Histórico: preferir estado terminal coerente (`feedback` + `concluida=True`) sem reexecutar máquina de estados |

### `backup_notas_avaliacoes_*.xlsx` → `reviews.AvaliacaoCompetencia`

| Coluna | Campo | Notas |
|---|---|---|
| `Identificador Avaliação` | FK `avaliacao` | |
| `Identificador Habilidade` | FK `competencia` | |
| `Nota` | `nota_autoavaliacao` **ou** `nota_lider` | Se `Nome Avaliador` = `Nome Avaliado` → auto; senão → líder (PRD 6.5.5) |
| `Fator no Momento` | `peso_utilizado` | Snapshot write-once (RF-19.2) |
| — | `nivel_esperado_utilizado` | Snapshot; valor vigente na Sólides ou derivado do cargo na data |

### `backup_comentarios_avaliacoes_*.xlsx` → `reviews.Feedback`

| Coluna | Campo | Notas |
|---|---|---|
| `Identificador` | FK `avaliacao` | join por ID avaliação Sólides |
| `Identificador Avaliador` | `autor` | |
| `Comentário` | `conteudo` | |
| `Criado em` | `created_at` | se suportado sem violar append-only |
| — | `tipo` | Inferir colaborador vs líder pelo papel do autor |

### `backup_pdi_*.xlsx` → `pdi.PDI` / `pdi.AcaoPDI`

| Coluna | Campo | Notas |
|---|---|---|
| `Nome` | FK `usuario` | |
| `Título do PDI` | `PDI.titulo` | |
| `Status` | `PDI.status` | De-para: `finalizado`→`concluido`, `em_andamento`→`ativo` |
| `Objetivo` / `Situação Atual` / `Situação Desejada` | `AcaoPDI.descricao` ou agregado | Modelo GP: PDI + ações — definir granularidade na spec |
| `Data de Entrega` | `AcaoPDI.prazo` | Serial Excel ou ISO |
| — | atrasada | Se prazo vencido e não finalizado → `AcaoPDI.status=atrasada` (PRD 6.5.6) |

### `backup_treinamentos_*.xlsx`

Fora do escopo PRD v1. Arquivo mantido apenas como referência; **não** importar.

---

## Relação com spec `003-import-catalogo-legado`

| Fonte | Uso recomendado |
|---|---|
| `lista-cargos.xlsx` + `lista-competencias.xlsx` (raiz) | Comando **já implementado** — núcleo de 43 competências + 134 cargos |
| `backup_habilidades*` | **Extensão opcional** — +57 competências e +2.720 vínculos; exige filtro KPI/ambíguos (reutilizar `mapping.py` da 003) |
| `backup_colaboradores` | **8 cargos** não presentes em `lista-cargos` — criar na importação de colaboradores ou pré-criar via catálogo estendido |

Comando existente:

```bash
python manage.py importar_competencias_cargo \
  --cargos lista-cargos.xlsx \
  --competencias lista-competencias.xlsx \
  --dry-run
```

Contrato: `specs/003-import-catalogo-legado/contracts/import-command-contract.md`

---

## Padrões de implementação (espelhar 003)

Todo comando novo SHOULD:

1. Aceitar `--dry-run` (parse + totais projetados, **zero commit**)
2. Usar `transaction.atomic()` na persistência
3. Emitir relatório (`criados` / `atualizados` / `inalterados` / `conflitos` / `excluídos`)
4. Ser **idempotente** (reexecução sem duplicar ativos)
5. Exit `0` sucesso / `1` erro fatal pré-persistência
6. Cobrir com `tests/test_import_*` usando fixtures **anonimizadas**, não `raw/`

---

## Referências

| Documento | Conteúdo |
|---|---|
| `PRD_Greenn_People.md` §6.5, Decisão #21, #22 | Requisitos e pré-requisitos |
| `SOLIDES.md` | Checklist Sprint 6.5 |
| `specs/003-import-catalogo-legado/` | Catálogo implementado (CSV disfarçado) |
| `specs/003-import-catalogo-legado/contracts/legado-domain-mapping-contract.md` | `canonical_key`, senioridade, KPI |
| `apps/competencies/management/commands/importar_competencias_cargo.py` | Único comando legado existente |

---

## Próximos passos (fora deste README)

1. Spec dedicada (ex. `010-import-legado-solides`) fatiada por comando
2. Migration `solides_id`
3. Implementação `importar_colaboradores` (primeira fatia de maior valor)
4. Fixtures anonimizadas em `data/legado-solides/samples/` para CI

*Última atualização do inventário: 2026-08-12 — inspeção read-only dos arquivos em `raw/`.*
