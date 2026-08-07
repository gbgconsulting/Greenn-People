# Contract: Ninebox visual-only (006)

**Feature**: `007-design-system-v2` · US4  
**Refs**: FR-007, FR-013; `specs/006-ninebox-interativa/contracts/*`

## Allowlist (visual only)

| Alvo | Paths | Permitido |
|---|---|---|
| Grade / células | `templates/talent/matrix.html`, `partials/_cell.html` | tipografia, densidade, bordas, empty |
| Person cards | `partials/_person_card.html` | classes, estados visuais |
| Drawer domínio | `partials/_drawer.html` | shell visual; **não** mudar `hx-*` de negócio |
| Feedback drag | `static/js/ninebox_matrix.js` + classes CSS | opacity/ring/cursor refinados sem alterar POST/handlers de regra |
| ARIA suporte | templates + JS | reforço visual/rótulos; sem remover trap/Escape |

Drawer permanece **domínio talent** — sem `templates/components/drawer.html` canônico nesta feature.

## Denylist (contratos 006)

| Contrato | Não alterar |
|---|---|
| `drag-persist.md` | Só `potencial` no POST; desempenho ignorado na gravação; snap; cancel = zero POST; sem SortableJS |
| `authz-scope.md` | Admin write; gerente RO; líder 403; escopo `get_visible_users`; IDOR 403 |
| `htmx-drawer-partials.md` | Targets `#matrix-drawer`, URLs drawer/move/toggle, partials HTML, filtros ciclo/área/cargo |
| `a11y-matrix-drawer.md` | Focus trap, Escape, restore; loading ≠ empty; alternativa drawer ao drag |

## Anti-padrões

- “Melhorar” UX mudando quem pode drag  
- Trocar fórmula visual por novos campos  
- Endpoints JSON  
- Redesign IA do shell global sob o pretexto da matriz  

## Aceite

Happy path 006 (abrir matriz, drawer, move potencial autorizado, empty) passa; aparência alinhada ao DS v2.
