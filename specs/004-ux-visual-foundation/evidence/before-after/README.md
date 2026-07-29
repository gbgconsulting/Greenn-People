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

Baseline **before** capturado (viewport ~1280px) em 2026-07-29 — UI operacional atual. **After** permanece pendente até o polish de cada superfície.

| ID | Tela | Before | After | Notas de hierarquia/clareza |
|---|---|---|---|---|
| 01 | Shell / nav Admin | ✓ `01-shell-admin-before.png` | _pendente_ | Governança + destaque Ciclos/Aderência |
| 02 | Dashboard time | ✓ `02-dashboard-team-before.png` | _pendente_ | Status no first viewport |
| 03 | Dashboard pessoal | ✓ `03-dashboard-pessoal-before.png` | _pendente_ | Espelho de clareza (KPIs existentes) |
| 04 | Login | ✓ `04-login-before.png` | _pendente_ | Consistência tipografia/form |
| 05 | Lista ciclos | ✓ `05-lista-ciclos-before.png` | _pendente_ | Hierarquia lista/empty |
| 06 | PDI detail | ✓ `06-pdi-detail-before.png` | _pendente_ | Badges/ações/empty + HTMX |
| 07 | Avaliações list | ✓ `07-avaliacoes-list-before.png` | _pendente_ | Scan + empty/HTMX |
