# Data Model: Visualizações Gráficas nos Dashboards

**Branch**: `005-dashboard-charts` | **Date**: 2026-07-30

## Declaração

Esta feature **não introduz models Django novos**, **não cria migrations** e **não altera** campos, FKs, `on_delete`, snapshots de negócio nem máquina de estados.

As Key Entities da [spec.md](./spec.md) são **conceitos de visualização** mapeados para serviços, contexto de views e templates já existentes. Persistência de aderência continua sendo `AderenciaSnapshot` (Celery); charts apenas leem/formatam.

Contratos: [contracts/](./contracts/).

---

## Mapeamento spec → implementação existente

### Distribuição de Aderência

| Aspecto | Valor |
|---|---|
| Persistência | `dashboard.AderenciaSnapshot` (`percentual`, `lider`, `ciclo`) — **sem alteração** |
| Faixas | Função existente `aderencia_status(percentual)` → `alta` \| `media` \| `baixa` (constantes `_ADERENCIA_ALTA=80`, `_ADERENCIA_MEDIA=50` em `apps/dashboard/views.py`) |
| View / context hoje | `AdminDashboardView`: `aderencia_resumo`, `snapshots_destaque` |
| Payload chart | Contagens por faixa derivadas dos mesmos snapshots (helper de formatação na view/serviço de apresentação) |
| Template | `templates/dashboard/admin.html` (+ include de chart) |
| Empty | Sem ciclo ou `total_lideres == 0` / lista de snapshots vazia |

**Validação**: mesmas faixas e mesmos percentuais da tabela/badges; zero thresholds novos.

---

### Progresso do Ciclo

| Aspecto | Valor |
|---|---|
| Persistência | `reviews.Avaliacao` (`etapa`, `concluida`, FK `ciclo`) — **sem alteração** |
| Enum etapas | `Avaliacao.Etapa` (TextChoices já existentes) |
| View / context hoje | `AdminDashboardView._avaliacoes_resumo` → `total`, `concluidas`, `percentual_concluidas`; `ciclo_indicador` |
| Payload chart | Preferência: série por `etapa` (`Count` no ciclo); alternativa: concluídas vs restantes a partir do resumo já exposto |
| Template | `templates/dashboard/admin.html` |
| Empty | Sem ciclo indicador ou `total == 0` |

**Validação**: totais coerentes com cards existentes; não recalcular `concluida` nem mudar etapa.

---

### Status do Escopo

| Aspecto | Valor |
|---|---|
| Persistência | `Avaliacao.etapa` + membros do escopo; **sem** model novo |
| Escopo | `get_visible_users(request.user)` em `TeamDashboardView.get_queryset()` (+ exclude self, `is_active`) |
| View / context hoje | `membros_resumo` (por página); chart MUST agregar escopo completo |
| Payload chart | Contagens por etapa + “sem avaliação” |
| Template | `templates/dashboard/team.html` (fora do partial HTMX) |
| Correlato `structure` | **Não mapear** nesta feature (métricas ≠ etapa; ver research R3) |
| Empty | Escopo sem membros ou sem ciclo aberto / sem avaliações |

**Validação**: conjunto de user IDs no chart ⊆ `get_visible_users`; testes de escopo existentes continuam passando (SC-004).

---

### Gap de Competência

| Aspecto | Valor |
|---|---|
| Persistência | `CargoCompetencia.nivel_esperado` + notas em `AvaliacaoCompetencia` via `build_fr005_context` |
| View / context hoje | `PersonalDashboardView` → `competencias_resumo[]` (`competencia`, `nivel_esperado`, `nota_atual`) |
| Payload chart | Pares esperado × nota por competência (labels = nome da competência) |
| Template | `templates/dashboard/personal.html` |
| 9-box | `classificacao` via `get_visible_classification_for_collaborator` — **regra intacta** (FR-009) |
| Empty | `vinculo_pendente`, lista vazia ou ausência de notas |

**Validação**: valores iguais aos já mostrados na UI textual; sem campo `lacuna` novo obrigatório no ORM.

---

### Empty / Loading de Visualização

| Aspecto | Valor |
|---|---|
| Persistência | Nenhuma |
| UI | `empty_state.html` + flag `has_data` no JSON do chart |
| Loading | Não inicializar Chart com zeros fictícios; indicador HTMX permanece só nas listas |

---

## Relacionamentos (somente leitura)

```text
Ciclo 1──* AderenciaSnapshot *──1 User(lider)
Ciclo 1──* Avaliacao *──1 User
Avaliacao 1──* AvaliacaoCompetencia (notas)
User *── cargo ──* CargoCompetencia (nivel_esperado)
```

Nenhuma FK nova. Nenhuma migration.

---

## Fora deste data-model

- Novos snapshots, faixas ou fórmulas de aderência
- Alterar `visivel_ao_colaborador` / matriz 9-box
- Endpoints REST / serializers DRF
- Models de “ChartConfig” ou preferências de dashboard
