# Contract: Consistência visual UI — Gestão PDI atrasados

**Referências canônicas**:
- [speckit_princ_pios_e_diretrizes_greenn_people.md](../../../speckit_princ_pios_e_diretrizes_greenn_people.md)
- `docs/design-system.md` (se conflitar com o doc de princípios em tokens pontuais, preferir o que já está **shipado** nas telas Stitch + Status Triad)
- Padrões vivos: hub PDI, `user_list_filters`, `avaliacao_list_*`, `badge_status`, `ownership_visao_toggle`, `components/card.html`, `emails/base.html`

## Princípios de experiência (obrigatórios nesta feature)

1. **Anti-planilha fria**: a vista tabela é operacional, mas respira (envelope card, hover suave, badges pastel). Não parecer export Excel.
2. **Situação + próxima ação em <3s**: no hub, “quantos atrasados?” deve ser óbvio (chip + badge no card). No dashboard, KPI com link.
3. **Um CTA primário soberano** na viewport do hub: criar PDI. Toggle Cards/Tabela e filtros são secundários (neutros).
4. **Sobriedade**: sem confete, emoji de alerta em massa, ou gamificação de “streak de atraso”.
5. **Semântica de cor rigorosa**:
   - Rose/vermelho (`atrasada`) = prazo estourado **somente**.
   - Amber = atenção/em andamento (não crítico).
   - Slate = neutro/espera.
   - Emerald = brand, progresso saudável, chip/toggle ativo, CTA.

## Tipografia e superfície

| Elemento | Token / classe |
|---|---|
| Título da página PDI | `font-display` (Fraunces) |
| Tabela, filtros, badges, métricas | `font-ui` / Source Sans 3 (herdado do shell) |
| Fundo app | superfície base slate clara já usada |
| Cards / tabela envelope | branco + `border-line` / `border-slate-200` |
| Radius controles | `rounded-lg` (8px); envelope lista pode `rounded-xl` como cadastros |
| Sombra | `shadow-none` / `shadow-sm` no máximo |

## Padrões por superfície

### Hub (cards) — US1

- **Reusar** shell `pdi_list.html` + chips de status + ownership toggle.
- Novo chip “Com atrasadas” no **mesmo estilo** dos chips atuais (emerald quando ativo), não uma segunda toolbar.
- Indicador no card: pill/`badge_status` rose com texto do tipo “N atrasada(s)” só se N>0.
- Não substituir a variante do plano (`em_andamento` etc.) só porque há atraso.

### Vista tabela — US3

- Visível só com visão equipe/organização.
- Toggle Cards|Tabela: **mesmo DNA visual** de `ownership_visao_toggle` (segment slate + ativo brand-gradient).
- Estrutura: `filter-segment-bar` + busca + `<details>` Filtros (gestor, área, faixa) — espelhar `user_list_filters` / `avaliacao_list_filters`.
- Tabela: classes `leader-team-table` ou `*-registry-table` já em `input.css`; linhas `border-b border-slate-100`; hover `hover:bg-slate-50/80`.
- Colunas densas mas legíveis; badges discretos; ações = link/kebab padrão.
- Colaborador puro: **sem** toggle tabela nem filtros de gestor/área alheios.

### Board — US6

- Nova coluna “Atrasadas” no mesmo grid visual das colunas atuais.
- Cards de ação atrasada: manter `badge_status` + barra amber já usada em `acao_card_andamento` (atraso crítico no badge, progresso visual amber).
- CTA “Concluir plano”: botão **secundário/outline** quando elegível; não competir com primário de nova ação.

### Dashboard KPI — US5

- `components/card.html` apenas.
- Link footer “Ver PDIs atrasados” → listagem filtrada.
- Zero = estado neutro (não vermelho de erro).

### E-mails — US2 / US4

- Layout `templates/emails/base.html`.
- Tom corporativo sóbrio; CTA único para o PDI ou listagem.
- Digest: resumo + top focos; sem lista interminável de cada ação se passar de um limite razoável (exibir totais + top N).

## Checklist de aceite visual (gate de PR)

- [ ] `h1` Fraunces / `font-display`
- [ ] Corpo/tabela Source Sans 3
- [ ] Emerald brand sem azul genérico / roxo / glow
- [ ] `rounded-lg` em botões/inputs/badges
- [ ] Um CTA primário dominante no hub
- [ ] Atraso = rose; pendência ≠ rose
- [ ] Filtros avançados em menu discreto (`<details>`)
- [ ] Tabela alinhada a listagens admin/avaliações (não inventar grid)
- [ ] Empty/zero neutros (slate), não “erro”

## Denylist visual

- Nova fonte ou paleta “só para RH”
- Cards no hero do dashboard competindo com ação imediata do ciclo
- Chips amber **e** rose para o mesmo significado de atraso
- Shadow pesada / glassmorphism / pills `rounded-full` em massa fora do padrão já usado
- Planilha full-bleed sem envelope
