# Data Model: 9-box Interativa (Matriz de Talentos)

**Branch**: `006-ninebox-interativa` | **Date**: 2026-07-31

## Declaração

Esta feature **não introduz models Django novos**, **não cria migrations** e **não altera** campos, FKs, `on_delete`, defaults de `visivel_ao_colaborador` nem fórmulas de `derive_desempenho` / `calculate_quadrante`.

As Key Entities da [spec.md](./spec.md) mapeiam para `ClassificacaoTalento`, layout de grade na view e partials de UI. Persistência de potencial/visibilidade reutiliza serviços existentes (+ toggle extraído).

Contratos: [contracts/](./contracts/).

---

## Entidade persistida (existente)

### ClassificacaoTalento

| Campo | Tipo / regra | Papel nesta feature |
|---|---|---|
| `usuario` | FK `PROTECT` → User | Identidade na célula/drawer |
| `ciclo` | FK `PROTECT` → Ciclo | Filtro da matriz; chave do upsert |
| `desempenho` | 1–3, derivado | **Somente leitura** na UI interativa; recalculado em `upsert_classification` a partir de `nota_final_lider` |
| `potencial` | 1–3, manual admin | **Único eixo editável** (drawer + drag) |
| `quadrante` | TextChoices 9 valores | Recalculado após potencial válido |
| `visivel_ao_colaborador` | bool, **default=False** | Toggle admin; gate colaborador intacto |
| `created_at` / `updated_at` | TimeStampedModel | Sem mudança |

**Constraints**: `unique_together (usuario, ciclo)`; checks 1–3 em desempenho/potencial.

**Auditoria**: signals existentes rastreiam `desempenho`, `potencial`, `quadrante`, `visivel_ao_colaborador` (append-only) — consumidos, não redesenhados.

**Validação de escrita** (via `upsert_classification`):

- Ator admin obrigatório.
- `potencial ∈ {1,2,3}`.
- Existe `Avaliacao` do par usuario+ciclo com `nota_final_lider` não nulo.
- Desempenho = `derive_desempenho(nota)`; quadrante = `calculate_quadrante(desempenho, potencial)`.

**Toggle** (serviço a extrair / view atual): inverte `visivel_ao_colaborador`; admin only; não altera potencial/desempenho/quadrante.

---

## Entidades de apresentação (não persistidas)

### Célula da Grade 3×3

| Aspecto | Valor |
|---|---|
| Identidade | Par `(desempenho, potencial)` com `desempenho ∈ {3,2,1}` (linha) e `potencial ∈ {1,2,3}` (coluna) |
| Conteúdo | Lista de `ClassificacaoTalento` do queryset filtrado/escopo cujo `quadrante` mapeia ao par |
| UI | Partial `_cell.html` (ou equivalente) + cards `_person_card.html` |
| Empty | Célula sem itens: área vazia honesta; grade com zero classificados → empty state de página |

Constantes de layout atuais em `TalentMatrixView`: `_DESEMPENHO_ROWS`, `_POTENCIAL_COLS`, `_QUADRANTE_MEMBER` — reutilizar / extrair helper se shared entre full page e partials.

### Drawer in-matrix

| Aspecto | Valor |
|---|---|
| Persistência | Nenhuma (estado de UI) |
| Conteúdo | Identidade (`nome`/email), área/cargo se disponíveis, desempenho (rótulo), potencial (editável se admin), quadrante, badge Visível/Oculto |
| Modos | **write** (admin) / **read-only** (gerente/manager viewer) |
| Container | `#matrix-drawer` na `matrix.html` |

### Movimentação por Arraste

| Aspecto | Valor |
|---|---|
| Persistência | Indireta: POST move → `upsert_classification(..., potencial=P′)` |
| Payload lógico | `user_pk` / `classificacao_pk`, `ciclo_id`, `potencial` (1–3) — **sem** campo desempenho mutável |
| Política visual | Snap para `(desempenho_derivado, P′)` — ver [research R4](./research.md) |

### Escopo de Visibilidade

| Aspecto | Valor |
|---|---|
| Resolução | `get_visible_users(request.user)` no queryset da matriz |
| Gate página | `RequiresManagerOrAdminMixin` (manager \| admin) |
| Escrita | `RequiresAdminMixin` + checks no service |
| Colaborador | Fora da matriz; `/talent/mine/` + `get_visible_classification_for_collaborator` |

---

## Fluxos de estado (UI ↔ persistência)

### Drawer: open → save potencial → refresh

```text
[Matriz] selecionar card
    → GET drawer partial (pessoa no escopo)
    → Drawer aberto (write|readonly)

[Admin] alterar potencial 1–3 → salvar
    → POST HTMX → upsert_classification
    → sucesso: drawer atualizado + célula origem/destino (ou grade) refresh + toast
    → erro validação/permissão: toast/erro no drawer; estado anterior permanece

[Admin] toggle Visível/Oculto
    → POST HTMX → toggle service
    → badge drawer + card atualizados + toast
```

### Drag: start → drop → persist → revert on error

```text
[Admin] dragstart (card)
    → UI: ghost/opacity; sem persistência

drop em célula (potencial P′)
    → POST move (potencial-only)
    → sucesso: card na célula (desempenho_derivado, P′); toast se houve snap de linha
    → noop se P′ == atual
    → erro: restore posição anterior + toast erro (sem sucesso silencioso)

cancel (Esc / fora da grade)
    → restore visual; zero POST
```

### Filtros após save/move

Pessoa continua sujeita a filtros GET (`ciclo`, `área`, `cargo`). Se após mudança deixar de atender filtro (raro para potencial-only), some da vista filtrada de forma coerente — sem vazar em outra célula fora do queryset.

---

## Relacionamentos

```text
CustomUser 1──* ClassificacaoTalento *──1 Ciclo
Avaliacao (usuario, ciclo) ──derive──▶ desempenho (não editável na feature)
ClassificacaoTalento.potencial ──admin──▶ calculate_quadrante ──▶ quadrante
ClassificacaoTalento.visivel_ao_colaborador ──gate──▶ MyClassificationView
```

---

## Fora deste modelo

- Novas faixas/fórmulas; edição livre de desempenho; models de “move history”; tornar default `visivel_ao_colaborador=True`; Chart.js / entities de 005.
