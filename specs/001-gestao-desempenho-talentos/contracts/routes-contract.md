# Contract: Rotas e Views

**Base URL**: `/` (aplicação interna, sem prefixo API)

Convenções:
- CBVs com `LoginRequiredMixin` (exceto auth pública)
- `paginate_by = 20` em toda `ListView`
- Templates em `templates/<app>/`; partials HTMX: `*_partial.html`
- Nomes de URL: `<app>:<action>` (ex.: `reviews:evaluation_detail`)

## Rotas públicas (`accounts`)

| Método | Path | View | Nome |
|---|---|---|---|
| GET/POST | `/accounts/register/` | `RegisterView` | `accounts:register` |
| GET/POST | `/accounts/login/` | `LoginView` | `accounts:login` |
| POST | `/accounts/logout/` | `LogoutView` | `accounts:logout` |
| GET/POST | `/accounts/password-reset/` | `PasswordResetView` | `accounts:password_reset` |
| GET | `/accounts/confirm-email/<uidb64>/<token>/` | `ConfirmEmailView` | `accounts:confirm_email` |

## Dashboard (`dashboard`)

| Método | Path | View | Escopo |
|---|---|---|---|
| GET | `/` | `PersonalDashboardView` | Autenticado |
| GET | `/dashboard/team/` | `TeamDashboardView` | `is_leader` |
| GET | `/dashboard/structure/` | `StructureDashboardView` | `is_manager` |
| GET | `/dashboard/admin/` | `AdminDashboardView` | `is_admin` |
| GET | `/dashboard/adherence/` | `AdherenceListView` | `is_manager` ou `is_admin` |

## Organização (`organization`) — admin

| Método | Path | View |
|---|---|---|
| CRUD | `/organization/areas/` | `AreaListView`, `AreaCreateView`, ... |
| CRUD | `/organization/positions/` | `CargoListView`, ... |
| GET/POST | `/organization/users/` | `UserListView`, `UserUpdateView` |
| GET | `/organization/users/pending/` | `PendingUsersListView` |

## Competências (`competencies`) — admin

| Método | Path | View |
|---|---|---|
| CRUD | `/competencies/scales/` | `EscalaListView`, ... |
| CRUD | `/competencies/` | `CompetenciaListView`, ... |
| GET/POST | `/competencies/positions/<pk>/profile/` | `CargoCompetenciaUpdateView` |

## Metas (`goals`)

| Método | Path | View | Escopo |
|---|---|---|---|
| GET | `/goals/expectations/` | `ExpectationsView` | Self |
| CRUD | `/goals/` | `MetaListView`, `MetaCreateView` | Scoped |
| POST | `/goals/<pk>/approve/` | `MetaApproveView` | Leader/admin |
| POST | `/goals/<pk>/reject/` | `MetaRejectView` | Leader/admin |
| POST | `/goals/<pk>/progress/` | `MetaProgressUpdateView` | Self, etapa=resultados |

## Ciclos (`cycles`) — admin

| Método | Path | View |
|---|---|---|
| CRUD | `/cycles/` | `CicloListView`, ... |
| POST | `/cycles/<pk>/open/` | `CicloOpenView` |
| POST | `/cycles/<pk>/close/` | `CicloCloseView` |
| CRUD | `/cycles/<pk>/objectives/` | `ObjetivoEstrategicoListView`, ... |

## Avaliações (`reviews`)

| Método | Path | View | Escopo |
|---|---|---|---|
| GET | `/reviews/` | `AvaliacaoListView` | Scoped |
| GET/POST | `/reviews/<pk>/` | `AvaliacaoDetailView` | Scoped |
| POST | `/reviews/<pk>/advance/` | `AdvanceStageView` | Leader/self conforme etapa |
| GET/POST | `/reviews/<pk>/self-assessment/` | `SelfAssessmentView` | Self |
| GET/POST | `/reviews/<pk>/leader-assessment/` | `LeaderAssessmentView` | Leader |
| CRUD | `/reviews/<pk>/feedbacks/` | `FeedbackListView`, `FeedbackCreateView` | Scoped |
| POST | `/reviews/feedbacks/<pk>/acknowledge/` | `FeedbackAcknowledgeView` | Self |

## PDI (`pdi`)

| Método | Path | View | Escopo |
|---|---|---|---|
| CRUD | `/pdi/` | `PDIListView`, `PDICreateView` | Scoped |
| GET | `/pdi/<pk>/` | `PDIDetailView` | Scoped |
| CRUD | `/pdi/<pk>/actions/` | `AcaoPDIListView`, ... | Scoped (HTMX partial) |

## Talentos (`talent`)

| Método | Path | View | Escopo |
|---|---|---|---|
| GET | `/talent/matrix/` | `TalentMatrixView` | Manager/admin |
| GET/POST | `/talent/<user_pk>/classify/` | `ClassifyTalentView` | Admin |
| POST | `/talent/<pk>/toggle-visibility/` | `ToggleVisibilityView` | Admin |

## Auditoria (`audit`) — admin

| Método | Path | View |
|---|---|---|
| GET | `/audit/` | `AuditLogListView` (filtros: usuário, ação, período) |

## Notificações (`notifications`) — admin

| Método | Path | View |
|---|---|---|
| GET | `/notifications/logs/` | `NotificacaoLogListView` |

## HTMX partials

| Trigger | Path partial | Target DOM |
|---|---|---|
| Lista ações PDI | `GET /pdi/<pk>/actions/partial/` | `#acao-list` |
| Aprovar meta inline | `POST /goals/<pk>/approve/` | `#meta-row-<pk>` |
| Modal criar ação | `GET /pdi/<pk>/actions/create/modal/` | `#modal-container` |

**Header**: requests HTMX incluem `HX-Request: true`. Views retornam partial sem `base.html` quando detectado.

## Respostas de erro

| Código | Template | Quando |
|---|---|---|
| 404 | `404.html` | Recurso inexistente ou fora do escopo |
| 403 | `403.html` | Permissão de visão (não escopo de objeto) |

Mensagem unificada para IDOR: sem revelar existência do registro.
