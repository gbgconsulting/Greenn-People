# Data Model: Gestão de Desempenho, PDI e Talentos

**Branch**: `001-gestao-desempenho-talentos` | **Date**: 2026-07-09

Referência complementar: [docs/data-model.md](../../docs/data-model.md) (diagrama ER completo).

## Convenções globais

- Todos os models concretos herdam `core.models.TimeStampedModel` (`created_at`, `updated_at`).
- Código-fonte em inglês; labels de UI em português via `verbose_name`.
- FKs históricas/sensíveis: `on_delete=models.PROTECT` (ver tabela de políticas abaixo).
- Campos snapshot: write-once, validados no `save()` — segunda escrita levanta `ValidationError`.

## Diagrama de dependência entre apps

```text
core
 ├── accounts ──┬── organization
 │              │
 ├── competencies
 ├── goals ──────┼── cycles ─── reviews
 │              │       │          │
 ├── pdi        │       └──── talent
 │              │
 ├── dashboard ─┘
 ├── notifications (signals → audit)
 └── audit
```

---

## App: `accounts`

### CustomUser

| Campo | Tipo | Constraints | Notas |
|---|---|---|---|
| `email` | EmailField | unique, USERNAME_FIELD | Login por e-mail |
| `nome` | CharField(150) | required | Display name |
| `is_admin` | BooleanField | default=False | Visão administrativa |
| `cargo` | FK → `organization.Cargo` | PROTECT, null=True | Opcional no cadastro |
| `area` | FK → `organization.Area` | PROTECT, null=True | Opcional no cadastro |
| `line_manager` | FK → self | SET_NULL, null=True | Gestor direto |
| `data_entrada` | DateField | null=True | |
| `is_active` | BooleanField | default=True | Offboarding |
| `email_confirmado_em` | DateTimeField | null=True | Separado de `is_active` |

**Propriedades calculadas** (não persistidas): `is_leader`, `is_manager` — derivadas de existência de liderados na hierarquia.

**Validações**:
- `clean()`: ausência de ciclo em `line_manager` (inclui self-reference).
- Desativação bloqueada se houver liderados diretos ativos (FR-028).

**Índices**: `line_manager_id`, `area_id`, `is_active`.

---

## App: `organization`

### Area

| Campo | Tipo | Constraints |
|---|---|---|
| `nome` | CharField(100) | |
| `parent` | FK → self | PROTECT, null=True |
| `is_active` | BooleanField | default=True |

**Validações**: `clean()` — sem ciclo em `parent`.

### Cargo

| Campo | Tipo | Constraints |
|---|---|---|
| `nome` | CharField(100) | |
| `nivel` | PositiveSmallIntegerField | senioridade |
| `is_active` | BooleanField | default=True |

---

## App: `competencies`

### Escala

| Campo | Tipo | Constraints |
|---|---|---|
| `nome` | CharField(100) | |
| `valor_minimo` | IntegerField | |
| `valor_maximo` | IntegerField | > min |
| `rotulos_por_nivel` | JSONField | mapa nível → rótulo |

### Competencia

| Campo | Tipo | Constraints |
|---|---|---|
| `nome` | CharField(150) | |
| `descricao` | TextField | blank=True |
| `tipo` | CharField | choices: tecnica, comportamental, lideranca |
| `escala` | FK → Escala | PROTECT |

### CargoCompetencia

| Campo | Tipo | Constraints |
|---|---|---|
| `cargo` | FK → Cargo | PROTECT |
| `competencia` | FK → Competencia | PROTECT |
| `nivel_esperado` | DecimalField | |
| `peso` | DecimalField | > 0 para cálculo |

**Unique together**: (`cargo`, `competencia`).

---

## App: `goals`

### ObjetivoEstrategico

| Campo | Tipo | Constraints |
|---|---|---|
| `descricao` | TextField | |
| `ciclo` | FK → `cycles.Ciclo` | PROTECT |

### Meta

| Campo | Tipo | Constraints |
|---|---|---|
| `usuario` | FK → CustomUser | PROTECT |
| `objetivo_estrategico` | FK → ObjetivoEstrategico | PROTECT |
| `descricao` | TextField | |
| `progresso` | DecimalField | 0–100; editável só na etapa `resultados` |
| `status` | CharField | pendente, aprovada, reprovada |
| `status_resultado` | CharField | pendente, aprovado, reprovado |

**Regras de transição**:
- `reprovada` → `pendente` (reabertura pontual, FR-026).
- `status_resultado=reprovado` → `pendente` (reabertura pontual).

---

## App: `cycles`

### Ciclo

| Campo | Tipo | Constraints |
|---|---|---|
| `nome` | CharField(100) | |
| `data_inicio` | DateField | |
| `data_fim` | DateField | informativo; encerramento manual |
| `status` | CharField | aberto, encerrado |

**Regras**:
- Apenas um ciclo `aberto` por vez (constraint de aplicação).
- Abertura cria `Avaliacao` para todos `is_active=True`.
- Encerramento manual bloqueia avanço de etapas.

### Avaliacao (model em `reviews`, etapas geridas por `cycles`)

| Campo | Tipo | Constraints |
|---|---|---|
| `ciclo` | FK → Ciclo | PROTECT |
| `usuario` | FK → CustomUser | PROTECT |
| `etapa` | CharField | ver máquina de estados |
| `nota_final_lider` | DecimalField | null=True, calculada |
| `nota_final_autoavaliacao` | DecimalField | null=True, referência |

**Etapas** (`etapa`): `input_metas` → `aprovacao_metas` → `resultados` → `aprovacao_resultados` → `avaliacao` → `feedback`.

**Unique together**: (`ciclo`, `usuario`).

---

## App: `reviews`

### AvaliacaoCompetencia

| Campo | Tipo | Constraints |
|---|---|---|
| `avaliacao` | FK → Avaliacao | PROTECT |
| `competencia` | FK → Competencia | PROTECT |
| `nota_autoavaliacao` | DecimalField | null=True |
| `nota_lider` | DecimalField | null=True |
| `peso_utilizado` | DecimalField | snapshot write-once |
| `nivel_esperado_utilizado` | DecimalField | snapshot write-once |

### Feedback

| Campo | Tipo | Constraints |
|---|---|---|
| `avaliacao` | FK → Avaliacao | PROTECT |
| `autor` | FK → CustomUser | PROTECT |
| `tipo` | CharField | colaborador, lider |
| `conteudo` | TextField | |
| `ciente_em` | DateTimeField | null=True |

---

## App: `pdi`

### PDI

| Campo | Tipo | Constraints |
|---|---|---|
| `usuario` | FK → CustomUser | PROTECT |
| `titulo` | CharField(200) | |
| `status` | CharField | ativo, concluido, arquivado |

### AcaoPDI

| Campo | Tipo | Constraints |
|---|---|---|
| `pdi` | FK → PDI | PROTECT |
| `descricao` | TextField | |
| `responsavel` | FK → CustomUser | PROTECT |
| `prazo` | DateField | |
| `status` | CharField | pendente, em_andamento, concluida, atrasada |

**Regra**: Celery Beat marca `atrasada` quando `prazo < today` e status não concluído.

---

## App: `talent`

### ClassificacaoTalento

| Campo | Tipo | Constraints |
|---|---|---|
| `usuario` | FK → CustomUser | PROTECT |
| `ciclo` | FK → Ciclo | PROTECT |
| `desempenho` | PositiveSmallIntegerField | 1–3, derivado de `nota_final_lider` |
| `potencial` | PositiveSmallIntegerField | 1–3, manual admin |
| `quadrante` | CharField | calculado (9 valores) |
| `visivel_ao_colaborador` | BooleanField | default=False |

**Unique together**: (`usuario`, `ciclo`).

**Cálculo desempenho**: `< 0.33 → 1`, `0.33–0.66 → 2`, `> 0.66 → 3` (nota normalizada 0–1).

---

## App: `dashboard`

### AderenciaSnapshot

| Campo | Tipo | Constraints |
|---|---|---|
| `lider` | FK → CustomUser | PROTECT |
| `ciclo` | FK → Ciclo | PROTECT |
| `percentual` | DecimalField | 0–100 |
| `componentes` | JSONField | breakdown do cálculo |
| `calculado_em` | DateTimeField | |

**Unique together**: (`lider`, `ciclo`).

---

## App: `notifications`

### NotificacaoLog

| Campo | Tipo | Constraints |
|---|---|---|
| `destinatario` | FK → CustomUser | PROTECT |
| `tipo` | CharField | lembrete_etapa, lembrete_pdi, etc. |
| `status` | CharField | enviado, falha |
| `erro` | TextField | blank=True |

*Sem `updated_at` — log imutável após criação.*

---

## App: `audit`

### AuditLog

| Campo | Tipo | Constraints |
|---|---|---|
| `usuario` | FK → CustomUser | SET_NULL, null=True |
| `acao` | CharField | create, update, access_denied, etc. |
| `entity_type` | CharField | model label |
| `entity_id` | PositiveIntegerField | |
| `campo` | CharField | blank para access_denied |
| `valor_anterior` | TextField | blank=True |
| `valor_novo` | TextField | blank=True |

*Append-only; sem `updated_at`; sem delete no admin.*

---

## Política de `on_delete`

| FK | on_delete | Motivo |
|---|---|---|
| `User.line_manager` | SET_NULL | Colaborador permanece se gestor desativado |
| `User.area`, `User.cargo` | PROTECT | Impede exclusão com vínculos |
| `Area.parent` | PROTECT | Impede exclusão com subáreas |
| Avaliação, Meta, PDI, Feedback, ClassificacaoTalento | PROTECT | Preserva histórico |
| `AuditLog.usuario` | SET_NULL | Log persiste se autor removido |

---

## Máquina de estados — `Avaliacao.etapa`

```text
input_metas
    │ (colaborador submete ≥1 meta)
    ▼
aprovacao_metas
    │ (100% metas status=aprovada, ≥1 meta)
    ▼
resultados
    │ (colaborador registra progresso)
    ▼
aprovacao_resultados
    │ (100% status_resultado=aprovado)
    ▼
avaliacao
    │ (notas preenchidas; cargo com competências e Σpeso > 0)
    ▼
feedback
    │ (feedback registrado + ciente_em)
    ▼
(concluída — ciclo pode ainda estar aberto)

Ciclo encerrado → nenhuma transição permitida
```

**Bloqueios adicionais**:
- Avanço para `avaliacao` bloqueado se cargo sem `CargoCompetencia` ou Σpeso = 0.
- Colaborador sem `line_manager`: aprovações por `is_admin=True`.

---

## Mapeamento spec → entidades

| Requisito | Entidade(s) |
|---|---|
| FR-001–005 | CargoCompetencia, Meta, ObjetivoEstrategico, Avaliacao |
| FR-006–011 | CustomUser (escopo), Avaliacao, Feedback, ClassificacaoTalento |
| FR-012–014 | PDI, AcaoPDI |
| FR-015–021 | Ciclo, Avaliacao, Meta |
| FR-022–028 | AvaliacaoCompetencia, AuditLog, CustomUser |
| SC-001–010 | Todos os acima + AderenciaSnapshot |
