# Contract: Table-frame · listas Category B (decisão B1)

**Feature**: `016-freeze-screen-conformity`  
**Status**: Extensão pontual aprovada (spec Clarifications · Session B1)  
**Documentar em**: `docs/design-system.md` (seção **Table-frame · listas de cadastro**) na **mesma entrega** da implementação (FR-017)  
**Não reabre**: Freeze A/B/C/D (charts, painel gerencial, densidade, paleta, shell)

---

## Escopo

Aplica-se **somente** a listagens Category B desta rodada:

- Áreas, Cargos, Usuários (+ pendentes correlatos), Competências

**Não** aplica a superfícies Category A (permanecem full-bleed no conteúdo do painel).  
**Não** unifica cap de lista com cap de formulário B.

---

## Layout de largura

| Superfície | Regra | Token default |
|------------|-------|---------------|
| Lista B com **≤ 4** colunas | Container centralizado, cap médio-largo | `mx-auto w-full max-w-5xl` |
| Lista B com **> 4** colunas | Mesmo padrão, um degrau maior | `mx-auto w-full max-w-6xl` |
| Formulário B da mesma entidade | Cap de form já definido (mais estreito) | `mx-auto max-w-lg` |
| Category A | Sem este cap | full-bleed do painel |

Referência de contagem atual:

| Lista | Colunas | Cap |
|-------|---------|-----|
| Áreas / Cargos / Competências | 4 | `max-w-5xl` |
| Usuários | 7 | `max-w-6xl` |
| Usuários pendentes (correlata) | conforme nº de cols da tela | mesma regra ≤4 → `max-w-5xl` / >4 → `max-w-6xl` |

---

## Anatomia da tabela B

1. Wrapper: `.table-frame` (chrome Freeze — borda/surface, **sem** sombra; overflow-x no frame).
2. `table` com `table-fixed w-full` + `<colgroup>` (larguras fixas/proporcionais).
3. Coluna **nome** não pode esticar a ponto de afastar as ações.
4. Coluna **Ações**:
   - Alinhamento à direita (`text-right` em `th`/`td`)
   - Links com separador leve: espaço ou ponto médio muted (`·`)
   - **Proibido** separador `\|` denso
5. Viewport ~375px: scroll horizontal **dentro** do `.table-frame`; página sem bleed.

### Proporções default (ponto de partida)

Ajustáveis por tela **sem** nova decisão de produto, desde que preservem ações à direita e legibilidade:

| Perfil | Sugestão |
|--------|----------|
| 4 colunas (nome · meta · status · ações) | ~40% / ~25% / ~15% / ~20% |
| 7 colunas (usuários) | nome+email maiores; ações ~12–15% fixos à direita |

---

## Componentes

- Frame: `.table-frame` apenas (não cardificar linhas).
- Status: `badge_status` (sem chip ad hoc).
- Empty: `empty_state` dentro da célula vazia / estado vazio.
- Paginação: `components/pagination.html` (fonte única).
- CTAs de header: `button`.

---

## O que vai para o DS (checklist de documentação)

Na seção nova do `docs/design-system.md`, registrar:

- [x] Título: Table-frame · listas de cadastro (Category B / decisão B1)
- [x] Caps `max-w-5xl` / `max-w-6xl` e form `max-w-lg`
- [x] `table-fixed` + `colgroup`
- [x] Ações à direita + separador leve (sem `\|`)
- [x] A full-bleed; B1 não reabre A/B/C/D
- [x] Exemplo mínimo de markup

**Execução T004 (2026-08-21):** seção publicada em `docs/design-system.md` — Freeze A/B/C/D intactos.

---

## Non-goals deste contrato

- Inventar outro frame de tabela
- Aplicar cap B1 em painéis A
- Unificar largura lista↔form
- Mudar AuthZ, paginação backend, ou schema
- Reabrir charts / painel gerencial / densidade

---

## Confirmação T002 (2026-08-21)

Contrato **alinhado** a [spec.md](../spec.md) Clarifications · Session B1 e **FR-015 / FR-016 / FR-017** (tokens concretos em Assumptions).

| Fonte | Exigência | Onde neste contrato |
|-------|-----------|---------------------|
| Clarifications B1 / FR-015 | Cap lista ≤4 cols médio-largo; >4 um degrau maior; form mais estreito; A sem cap | Layout de largura → `max-w-5xl` / `max-w-6xl` / form `max-w-lg` / A full-bleed |
| Clarifications B1 / FR-016 | Colunas fixas/proporcionais; ações à direita; separador leve; sem `\|` | Anatomia → `table-fixed` + `colgroup`; `text-right`; `·`/espaço; proibido `\|` |
| Clarifications B1 / FR-017 | Documentar no DS na mesma entrega; sem reabrir A/B/C/D | Header + checklist “O que vai para o DS” |
| Clarifications B1 | Scroll ~375px só no frame | Anatomia item 5 |
| Assumptions | Tokens `max-w-5xl` / `max-w-6xl` / `table-fixed` / `colgroup` | Tabelas de layout + anatomia |

- [x] Caps `max-w-5xl` / `max-w-6xl` e form `max-w-lg` fechados
- [x] `table-fixed` + `colgroup` como “definição de colunas”
- [x] Ações à direita com separador leve — sem `\|`
- [x] Escopo só Category B (incl. pendentes correlatos); A full-bleed; sem unificar lista↔form
- [x] FR-017 / SC-006: documentação DS é checklist desta entrega (execução em T004)

**Regra operacional**: remediação US3 consome este contrato; divergência de token/anatomia = violação B1.

---

## Confirmação T005 (2026-08-21) — CSS twin

**Pergunta**: B1 exige utilitário documentado novo em `static/src/input.css` (+ rebuild `static/css/tailwind.css`)?

**Resposta**: **Não.** A seção DS (T004) e este contrato usam apenas:

| Peça | Origem | Ação T005 |
|------|--------|-----------|
| Cap lista `max-w-5xl` / `max-w-6xl` | Utilitário Tailwind padrão | Nenhuma — basta no markup US3 |
| Cap form `max-w-lg` | Utilitário Tailwind padrão (já emitido no CSS versionado) | Nenhuma |
| `table-fixed` + `w-full` + `mx-auto` + `text-right` | Utilitários Tailwind padrão | Nenhuma |
| Larguras de `colgroup` (`w-[40%]` etc.) | Arbitrary values Tailwind | Nenhuma |
| Chrome `.table-frame` | Já em `input.css` `@layer components` | Intocado |

- [x] Nenhum token/classe B1 ausente do Freeze/Tailwind → **sem ESCALATE**
- [x] `static/src/input.css` **não** alterado nesta task
- [x] `static/css/tailwind.css` **sem** rebuild (só necessário se `input.css` mudar, ou quando US3 passar a referenciar as classes nos templates e o CSS gerado for atualizado)

**Nota operacional**: `max-w-5xl` / `max-w-6xl` / `table-fixed` ainda podem não aparecer no CSS versionado até as listas B consumirem as classes (content scan do `tailwind.config.js`); isso é esperado e **não** justifica inventar `@layer` custom.
