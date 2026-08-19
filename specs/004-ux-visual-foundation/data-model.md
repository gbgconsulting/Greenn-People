# Data Model: Fundação Visual e UX Estável

**Branch**: `004-ux-visual-foundation` | **Date**: 2026-07-29

## Declaração

Esta feature **não introduz models Django novos**, **não cria migrations** e **não altera** campos, FKs, `on_delete`, snapshots nem máquina de estados.

As “Key Entities” da [spec.md](./spec.md) são **conceitos de UX/documentação** mapeados para templates, contexto de view existente e artefatos em `specs/`.

Contratos: [contracts/](./contracts/).

---

## Mapeamento spec → implementação existente

### Tela-piloto

| Conceito | Persistência | Mapeamento concreto |
|---|---|---|
| Tela-piloto | Nenhuma | Templates + rotas existentes; registro before/after em `evidence/before-after/` |
| Login | — | `templates/accounts/login.html` (+ `base_auth.html`) |
| Dashboard pessoal | — | `templates/dashboard/personal.html` |
| Dashboard time | — | `templates/dashboard/team.html` + `team_list_partial.html` |
| Shell / nav Admin | — | `templates/components/nav_menu.html` (bloco `user.is_admin`) + `sidebar.html` |
| Ciclos (lista) | `cycles.Ciclo` (leitura UI) | `templates/cycles/ciclo_list.html` + partial |
| PDI detail | `pdi.*` (leitura UI) | `templates/pdi/pdi_detail.html` + partials |
| Avaliações list | `reviews.Avaliacao` (leitura UI) | `templates/reviews/avaliacao_list.html` + partial |

**Validação**: elegível ao polish apenas se fluxo e permissões atuais permanecerem; empty state sem inventar dados.

---

### Token / padrão de UI

| Conceito | Persistência | Mapeamento |
|---|---|---|
| Token / padrão | Arquivos de doc + CSS | `docs/design-system.md` (fonte da verdade); `static/src/input.css` (`@theme`, `@layer`); classes Tailwind nos components |
| Freeze | Marcador documental | Seção explícita “Freeze” em `docs/design-system.md` ao fechar a feature |

**Campos lógicos (não ORM)**: tipografia, espaçamento, cor de status, badge, botão, empty state, tabela, indicador KPI/card, focus-visible.

**Estado**: draft durante polish → **frozen** (SC-006) ao aceitar before/after.

---

### Grupo do shell (Administração)

| Conceito | Persistência | Mapeamento |
|---|---|---|
| Grupo Governança / Cadastros / Sistema | Nenhuma | Estrutura HTML em `nav_menu.html`; contrato [admin-nav-grouping.md](./contracts/admin-nav-grouping.md) |
| Destino de link | URLs Django existentes | `{% url %}` já usados; sem novas routes |

**Transição**: lista plana Admin → três subgrupos com progressive disclosure visual (não muda autorização).

---

### Contexto de ciclo (topbar)

| Conceito | Persistência | Mapeamento |
|---|---|---|
| Ciclo aberto | Model existente `cycles.Ciclo` (`status=ABERTO`) | Função existente `get_open_ciclo()`; novo **context processor** em `apps.core` expõe ao template global |
| Fallback | — | String/UI quando `get_open_ciclo()` retorna `None` |
| Superfície | — | `templates/components/topbar.html` |

**Não é** novo domínio: não cria tabela “contexto de topbar”; não altera serviços de cálculo.

Reuso: várias views já passam `ciclo_aberto` no contexto local; o processor unifica consumo na topbar sem endpoints novos. Ver [topbar-cycle-context.md](./contracts/topbar-cycle-context.md).

---

### Critério before/after

| Conceito | Persistência | Mapeamento |
|---|---|---|
| Critério before/after | Arquivos em repo (evidência) | `evidence/before-after/` + checklist em [quickstart.md](./quickstart.md) |
| Aceite | Revisão humana | SC-001–SC-003 |

---

## Entidades de domínio tocadas só por leitura (inalteradas)

| Model | App | Uso nesta feature |
|---|---|---|
| `Ciclo` | `cycles` | Leitura `status=ABERTO` para topbar / dashboards já existentes |
| Demais (User, Avaliacao, PDI, …) | vários | Renderização template; **zero** mudança de schema ou regras |

---

## Relacionamentos

```text
[CustomUser papéis cumulativos] --vista--> [nav_menu seções]
[Ciclo.status=ABERTO] --get_open_ciclo--> [context processor] --template--> [topbar]
[Token/padrão] --documentado--> [docs/design-system.md] --aplicado--> [components + telas-piloto]
[Tela-piloto] --evidência--> [evidence/before-after]
```

Nenhuma FK nova. Nenhum `on_delete` alterado.
