# Evidence: before/after (telas-piloto)

Capturar **before** antes do polish de cada superfície; **after** na mesma viewport (~1280px) e conta.

## Convenção de nomes (congelada)

Padrão: `NN-<slug>-before.png` / `NN-<slug>-after.png` — IDs `01`–`07` (zero-padded).

| ID | Arquivo before | Arquivo after | Tela |
|---|---|---|---|
| 01 | `01-shell-admin-before.png` | `01-shell-admin-after.png` | Shell / nav Admin |
| 02 | `02-dashboard-team-before.png` | `02-dashboard-team-after.png` | Dashboard time |
| 03 | `03-dashboard-pessoal-before.png` | `03-dashboard-pessoal-after.png` | Dashboard pessoal |
| 04 | `04-login-before.png` | `04-login-after.png` | Login |
| 05 | `05-lista-ciclos-before.png` | `05-lista-ciclos-after.png` | Lista ciclos |
| 06 | `06-pdi-detail-before.png` | `06-pdi-detail-after.png` | PDI detail |
| 07 | `07-avaliacoes-list-before.png` | `07-avaliacoes-list-after.png` | Avaliações list |

Todos os PNGs ficam neste diretório (`evidence/before-after/`), ao lado deste README.

## Confirmação de baseline (T006)

Verificado em 2026-07-29 antes de qualquer polish de templates:

| Checagem | Resultado |
|---|---|
| Branch | `004-ux-visual-foundation` @ `80c30d8` = mesmo commit que `development` |
| Diff de templates/static vs `development` | Nenhum (apenas docs/specs da feature) |
| WIP Impeccable | Existe só como `stash@{0}: wip impeccable visual-regress` — **não** aplicado, mergeado nem cherry-picked |
| Befores 01–07 | Capturados da UI operacional atual (R1 / FR-017) |

**Gate**: polish de templates (T007+) pode começar a partir desta baseline limpa.

## Status de captura

Baseline **before** capturado (viewport ~1280px) em 2026-07-29 — UI operacional atual. **After** por superfície, conforme polish.

| ID | Tela | Before | After | Notas de hierarquia/clareza |
|---|---|---|---|---|
| 01 | Shell / nav Admin | ✓ `01-shell-admin-before.png` | ✓ `01-shell-admin-after.png` | Ver bullets US1 abaixo |
| 02 | Dashboard time | ✓ `02-dashboard-team-before.png` | ✓ `02-dashboard-team-after.png` | Ver bullets US2 abaixo |
| 03 | Dashboard pessoal | ✓ `03-dashboard-pessoal-before.png` | ✓ `03-dashboard-pessoal-after.png` | Ver bullets US2 abaixo |
| 04 | Login | ✓ `04-login-before.png` | ✓ `04-login-after.png` | Ver bullets US3 abaixo |
| 05 | Lista ciclos | ✓ `05-lista-ciclos-before.png` | ✓ `05-lista-ciclos-after.png` | Ver bullets US3 abaixo |
| 06 | PDI detail | ✓ `06-pdi-detail-before.png` | ✓ `06-pdi-detail-after.png` | Ver bullets US3 abaixo |
| 07 | Avaliações list | ✓ `07-avaliacoes-list-before.png` | ✓ `07-avaliacoes-list-after.png` | Ver bullets US3 abaixo |

### 01 — Shell / nav Admin (after · US1)

Conta: `admin@test.greenn.com.br` · URL: `/dashboard/admin/` · viewport ~1280×900 · 2026-07-29

- Lista flat **Administração** substituída por três grupos: **Governança** / **Cadastros** / **Sistema**
- **Ciclos** no topo de Governança com `font-semibold` + `border-l-2 border-emerald-500` (peso maior que itens de Cadastros)
- **Aderência** mantém o mesmo destaque P1 (seção Gerente quando o usuário também é manager; Governança no admin-only)

### 02 — Dashboard time (after · US2)

Conta: `lider@test.greenn.com.br` · URL: `/dashboard/team/` · viewport ~1280×900 · 2026-07-29

- Badge do ciclo aberto alinhado ao título (antes só no subtítulo); seção **Status no ciclo** com hierarquia título + descrição
- Colunas operacionais **Etapa** e **Nota líder** imediatamente após colaborador (antes intercaladas com Área/Cargo)
- Etapa em badge de status; nome do colaborador com peso tipográfico maior na lista

### 03 — Dashboard pessoal (after · US2)

Conta: `colab@test.greenn.com.br` · URL: `/` · viewport ~1280×900 · 2026-07-29

- Badge do ciclo no header + seção **Meu desempenho** explicitando KPIs no first viewport
- Cards de **Nota atual** / **Nível esperado** com badges de origem/estado (ex.: Sem nota, Vínculo pendente)
- Aviso amarelo de vínculo pendente substituído por `empty_state` acionável (orientação ao admin)

### 04 — Login (after · US3)

Conta: anônimo · URL: `/accounts/login/` · viewport ~1280×900 · 2026-07-30

- Cabeçalho com tipografia alinhada ao design system (`text-2xl` + subtítulo `text-sm`)
- Campos e CTA via componentes `input.html` / `button.html` (sem ilha de estilo)
- Espaçamento do cartão auth coerente com `card.html` (`p-5`); marca preservada

### 05 — Lista ciclos (after · US3)

Conta: `admin@test.greenn.com.br` · URL: `/cycles/` · viewport ~1280×900 · 2026-07-30

- Header com subtítulo operacional + CTA **Novo ciclo** no padrão botão primary
- Ciclo aberto com destaque de linha (`border-l` + fundo suave) e badge de status
- Tabela em container bordered/shadow; empty state acionável quando lista vazia

### 06 — PDI detail (after · US3)

Conta: `admin@test.greenn.com.br` · URL: `/pdi/3/` · viewport ~1280×900 · 2026-07-30

- Resumo em cards (Status badge / Progresso / Área / Cargo) no first viewport
- Seção **Ações de desenvolvimento** com hierarquia título + descrição + **Nova ação**
- Lista de ações com badges de status; triggers HTMX `#modal-container` / `#acao-list` intactos

### 07 — Avaliações list (after · US3)

Conta: `admin@test.greenn.com.br` · URL: `/reviews/` · viewport ~1280×900 · 2026-07-30

- Subtítulo com ciclo aberto em peso maior; lista em container bordered/shadow
- Etapa como badge de status; colaborador com nome + e-mail tipograficamente hierárquicos
- Empty states via componente unificado; contrato HTMX `#list-container` preservado

## Smoke HTMX (T022 · US3)

Conta: `admin@test.greenn.com.br` · 2026-07-30 · verificação via requests `HX-Request: true` (contrato [htmx-pilot-surfaces.md](../../contracts/htmx-pilot-surfaces.md))

| Checagem | Esperado | Resultado |
|---|---|---|
| Abrir modal “Nova ação” em `/pdi/3/` (`GET …/actions/create/modal/`) | 200 + form com `hx-target="#acao-list"` (swap em `#modal-container`) | **ok** |
| Detail PDI preserva triggers | `hx-target="#modal-container"` + `#acao-list` no markup | **ok** |
| Lista ciclos HTMX (`GET /cycles/?page=1`) | Fragmento com `#list-container` (sem `<html>` full page) | **ok** |
| Lista avaliações HTMX (`GET /reviews/?page=1`) | Fragmento com `#list-container` (sem `<html>` full page) | **ok** |

Notas: paginação UI só renderiza se `num_pages > 1` (dados atuais ≤1 página); atributo `hx-target="#list-container"` permanece em `templates/components/pagination.html`. Sem regressão nos alvos HTMX pós-polish US3.
