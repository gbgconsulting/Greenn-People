# Contract: Agrupamento da nav Administração

**Feature**: `004-ux-visual-foundation`  
**Superfície**: `templates/components/nav_menu.html` (bloco `user.is_admin`) + include em `sidebar.html` (desktop e mobile)

## Objetivo

Progressive disclosure visual em três grupos, sem novas URLs e sem mudança de autorização.

## Grupos

### Governança (ênfase)

Ordem sugerida (ajustável se before/after exigir, mas Ciclos e Aderência MUST permanecer com destaque maior que Cadastros):

1. **Ciclos** → `cycles:ciclo_list` — **destaque P1**
2. **Aderência** → `dashboard:adherence` — **destaque P1**
3. **Painel admin** → `dashboard:admin`
4. **Estrutura** / **Matriz de talentos** — apenas quando o template atual já os renderiza no bloco admin (`{% if not user.is_manager %}`), preservando a lógica vigente

### Cadastros (peso padrão)

- Áreas → `organization:area_list`
- Cargos → `organization:cargo_list`
- Usuários → `organization:user_list`
- Competências → `competencies:competencia_list`

### Sistema (secundário)

- Auditoria → `audit:list`
- Notificações → `notifications:log_list`

## Regras

- Cabeçalhos de grupo: texto uppercase / `text-xs` coerente com seções Colaborador/Líder/Gerente (ou hierarquia documentada no design system).
- Destaque Ciclos/Aderência: classe(s) documentadas no before/after (ex.: `font-semibold`, ordem no topo, ícone ou marker visual leve) — MUST ser perceptível vs. Cadastros.
- Item ativo: classes visuais atuais **e** `aria-current="page"` (ver [a11y-shell.md](./a11y-shell.md)).
- Seções fora de Admin (Colaborador / Líder / Gerente) fora deste contrato, exceto não regredir links.

## Fora de contrato

- Novos endpoints; ocultar itens só no front para “simular” permissão; drawers aninhados extras.
