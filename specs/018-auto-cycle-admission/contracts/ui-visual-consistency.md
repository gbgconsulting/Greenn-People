# Contract: Consistência visual UI — Governança da abertura automática

**Referências canônicas**:
- [speckit_princ_pios_e_diretrizes_greenn_people.md](../../../speckit_princ_pios_e_diretrizes_greenn_people.md)
- `docs/design-system.md` (Freeze v2 shipado; se conflitar em token pontual, preferir o que já está nas telas Stitch + ciclos + PDI 017)
- Padrões vivos: `templates/cycles/ciclo_list*.html`, `user_list_filters`, `avaliacao_list_*`, `badge_status`, `components/card.html`, `emails/base.html`, contrato visual 017

## Princípios de experiência (obrigatórios nesta feature)

1. **Anti-planilha fria / anti-burocracia**: governança respira (envelope card, hover suave, badges pastel). Não parecer log de servidor nem Excel.
2. **Situação + próxima ação em <3s**: no topo, RH deve responder: “o lote do mês rodou?”, “há alertas/pendências?”, “o que faço agora?”.
3. **Um CTA primário soberano** por viewport (ex.: na lista de ciclos, manter soberania do fluxo manual vigente **ou** um único CTA “Ver governança do automático” se essa for a landing — nunca dois primários emerald competindo). Secundários = `secondary`/`outlined`/links neutros.
4. **Sobriedade**: sem gamificação de marcos, confete, streak, emoji de sirene em massa.
5. **Semântica de cor rigorosa**:
   - **Rose/vermelho** = prazo de 20 dias **estourado** **ou** falha real da rotina.
   - **Amber** = atenção (alerta de ciclo ainda aberto; pendência de cadastro sem admissão) — não crítico de sistema.
   - **Slate** = neutro/espera/noop (“hoje não é 1º dia útil”).
   - **Emerald** = brand, sucesso do lote, chip/CTA ativo.

## Tipografia e superfície

| Elemento | Token / classe |
|---|---|
| Título da página (Ciclos / Governança automática) | `font-display` (Fraunces) |
| Tabela, filtros, badges, métricas, copy operacional | `font-ui` / Source Sans 3 |
| Fundo app | superfície base slate clara do shell |
| Cards / KPI / envelope lista | branco + `border-line` / `border-slate-200` |
| Radius | `rounded-lg` (8px); envelope lista pode `rounded-xl` como cadastros |
| Sombra | `shadow-none` / `shadow-sm` no máximo |

## Padrões por superfície

### Lista de ciclos (shell existente)

- **Reusar** `ciclo_list.html` / partials / `_ciclo_card.html`.
- Remover copy “Só um ciclo pode estar aberto por vez”; substituir por linguagem honesta de convivência (manual + automático).
- Badge/origem discreto no card: `Manual` (slate) vs `Automático` (emerald suave) — mesmo DNA de `badge_status`, não pill gamificada.
- Link/entrada para governança do automático = secundário ou item de nav contextual — **não** inventar hero paralelo.

### Governança do automático (US4)

- Composição: **KPI strip** (entrantes / sem admissão / alertas / falhas) + **filter bar** + **tabela/lista** — espelhar painel gerencial Freeze C e listagens admin.
- KPIs via `components/card.html`; zero = estado **neutro** (slate), não rose.
- Filter segment: busca + `<details>` Filtros (período, tipo de evento) — espelhar `user_list_filters` / PDI 017.
- Tabela: `leader-team-table` / `*-registry-table`; linhas `border-b border-slate-100`; hover `hover:bg-slate-50/80`.
- Empty states **guiados** (ilustração limpa + frase RH + um CTA): ex. “Nenhum lote automático neste período” / “Nenhuma pendência sem data de entrada”.
- Copy em linguagem de RH (“Entrou no lote”, “Sem data de entrada”, “Ciclo ainda aberto”, “Falha na rotina”) — sem stack traces na UI.

### Alertas (ciclo ainda aberto)

- Superfície e e-mail: tom **âmbar/atenção**, não rose — o lote **não** falhou.
- Rose só se o prazo de 20 dias da avaliação/ciclo automático estiver estourado na coluna de atraso.

### Multi-open (topbar / seletor)

- Indicador de ciclo **não pode mentir** “o único vigente” se houver N abertos.
- Preferir seletor/`badge` que liste ou indique quantidade (“2 ciclos abertos”) com default = mais recente — visual alinhado a `_ciclo_header_badge` / `_ciclo_selector`, sem chrome novo.
- Sem redesenhar sidebar/nav IA.

### E-mails RH

- Layout `templates/emails/base.html`.
- Tom corporativo; **um** CTA para a governança ou ficha do ciclo.
- Sem lista infinita: totais + top N nominativos se necessário.

## Checklist de aceite visual (gate de PR)

- [x] `h1` Fraunces / `font-display`
- [x] Corpo/tabela Source Sans 3
- [x] Emerald brand sem azul genérico / roxo / glow
- [x] `rounded-lg` em botões/inputs/badges
- [x] Um CTA primário dominante na viewport de governança
- [x] Rose só para prazo estourado ou falha real
- [x] Alerta de ciclo aberto = amber/neutro enfatizado — **não** rose
- [x] Filtros avançados em `<details>` / segment bar
- [x] Tabela alinhada a listagens ciclos/cadastros/PDI (não inventar grid)
- [x] Empty/zero neutros (slate)
- [x] Sem segunda tipografia/paleta “só automático”

## Denylist visual

- Nova fonte ou paleta “modo robô / automação”
- Cards no hero competindo com CTA soberano
- Chips rose para “alerta de ciclo aberto” (falso alarmismo)
- Shadow pesada / glassmorphism / `rounded-full` em massa fora do padrão
- Planilha full-bleed sem envelope
- Dashboard analítico paralelo só para o automático nesta feature
