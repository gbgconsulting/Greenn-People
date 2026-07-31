# Contract: A11y mínima — drawer e matriz

**Feature**: `006-ninebox-interativa`  
**Escopo**: a11y **mínima** (FR-011 / SC-006) — não é auditoria WCAG formal (OUT).

## Drawer

| Requisito | Contrato |
|---|---|
| Abrir | Foco move para o painel (primeiro controle focável ou heading do drawer) |
| Fechar | Escape fecha; foco retorna ao trigger/card que abriu |
| Tab | Focus trap dentro do drawer enquanto aberto (padrão análogo a `modal.js`) |
| Controles | Labels associados a select/inputs de potencial; botões com texto visível (“Salvar”, “Liberar”/“Ocultar”, “Fechar”) |
| Read-only | Gerente: sem campos de edição; conteúdo ainda legível por leitores de tela (texto, não só ícone/cor) |

## Matriz / células

| Requisito | Contrato |
|---|---|
| Além da cor | Cada célula expõe rótulo textual de eixos e/ou nome do quadrante (já parcialmente via `label`); cards identificam pessoa por nome/email |
| Alternativa ao drag | Edição de potencial **sempre** disponível no drawer para admin (FR-011) |
| Handles de drag | Se presentes, têm nome acessível (ex. `aria-grabbed` / texto “Arrastar para alterar potencial”); ausentes no mobile |

## Estados honestos

| Estado | Contrato |
|---|---|
| Loading | Indicador HTMX / aria-busy; **não** apresentar como grade vazia definitiva |
| Empty | `empty_state` Freeze quando zero classificados no filtro/escopo |
| Erro | Mensagem em português; estado anterior preservado |

## Fora

- Auditoria WCAG completa; redesign tipográfico global; dependências a11y npm.
