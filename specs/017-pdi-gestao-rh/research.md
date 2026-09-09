# Research: 017-pdi-gestao-rh

**Date**: 2026-09-09  
**Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md)

## 1. Visibilidade de atraso no hub

**Decision**: Annotate no queryset de `PDIListView` com `Count` de `acoes` em `status=atrasada` (e métricas derivadas para tabela: max dias de atraso, min próximo prazo). Chip de filtro `atrasadas=1` (ou equivalente) na barra de chips já existente do hub. Badge no card só quando contagem > 0.

**Rationale**: Status `atrasada` e job `mark_overdue_pdi_actions` já existem; o gap é superfície. Estender `_pdi_list_row` / `pdi_hub_card` evita segundo hub.

**Alternatives considered**:
- Variante de card “atrasado” no lugar de `em_andamento` — rejeitado: atraso é da **ação**, plano pode continuar “em andamento”.
- Queryset separado só para RH — rejeitado: quebra ownership único.

## 2. Destinatários e timing do alerta de atraso

**Decision**: Ao marcar ação como `atrasada` (job diário), notificar **dono do PDI** e **gestor direto (`line_manager`) do dono** se ativo e distinto. Tipo novo `atraso_pdi` (não reutilizar `lembrete_pdi`). Dedupe `(destinatario, tipo, referencia=acao_pdi:{id}, janela=data_do_evento_ISO)`.

**Rationale**: Spec e Assumptions; evita colisão com lembrete preventivo (janela = data alvo do prazo+N). Pipeline `_log_send` / `already_sent` já maduro.

**Alternatives considered**:
- Notificar `responsavel` da ação — fora de escopo nesta fatia.
- E-mail a todos os admins por ação — ruído; digest cobre RH.
- In-app/push — fora de escopo.

## 3. Vista tabela vs cards

**Decision**: Toggle **Cards | Tabela** apenas quando `can_view_team_ownership_list` e `visao=equipe` (ou label Organização para admin). Visual do toggle espelha `ownership_visao_toggle` (segment `bg-slate-100` + item ativo `bg-brand-gradient`). Tabela reusa CSS `leader-team-table` / envelope registry (avaliações / usuários). Filtros profundos (gestor, área, faixa) em `<details>` no padrão `user_list_filters` / `avaliacao_list_filters` — **não** empilhar todos como chips no hub.

**Rationale**: Diretrizes Greenn People §4.4 (filtros discretos) + consistência com listagens já shipped; evita planilha fria competindo com o hub de cards do colaborador.

**Alternatives considered**:
- Substituir cards por tabela para todos — rejeitado: colaborador perde a porta PDI (§4.3).
- Data-grid / lib JS — rejeitado (Constitution I).

## 4. Faixas de atraso

**Decision**: Base = dias do atraso **mais antigo** entre ações `atrasada` do plano (`today - min(prazo)` das atrasadas). Faixas: `1-7` (inclusivo), `8-30` (8 inclusivo, 30 inclusivo), `30+` (>30). Sem prazo → fora de atraso/faixa.

**Rationale**: Spec Edge Cases; uma métrica simples por linha de tabela.

**Alternatives considered**: média de dias — menos acionável para priorização RH.

## 5. Digest RH

**Decision**: Task Beat **semanal**; destinatários = users `is_admin` ativos; só envia se existir ≥1 ação atrasada em PDI não arquivado na org. Conteúdo: totais (PDIs com atraso, ações atrasadas) + top áreas/gestores; CTA para `/pdi/?visao=equipe&atrasadas=1` (e mode tabela se desejado). Tipo `digest_pdi_atrasos`; janela = semana ISO (`YYYY-Www`).

**Rationale**: Spec FR-009/010; silêncio quando zero.

**Alternatives considered**: digest diário — excessivo para RH; e-mail “zero atrasos” — rejeitado pela spec.

## 6. Widget dashboard

**Decision**: Card KPI via `templates/components/card.html` nos dashboards que já têm visão de time/org (`team` / `admin`), contagem scoped, link para listagem filtrada. `accent` alinhado a atenção crítica (warning/rose conforme DS do card — sem inventar KPI custom).

**Rationale**: Diretriz “acompanhamento passivo” + atalho; não compete com Hero de “sua vez”.

**Alternatives considered**: drawer lateral só de PDI — overkill vs link para módulo.

## 7. Board + conclusão

**Decision**: `_group_acoes` ganha bucket/coluna **Atrasadas** (actions `status=atrasada`). Conclusão: serviço `complete_pdi` exige PDI `ativo` + 100% ações `concluida`; transição → `concluido`; CTA explícito (botão secundário/outline no detalhe quando elegível — **não** roubar CTA primário de criar ação se existir). Arquivado continua bloqueado.

**Rationale**: Spec US6; `concluido` já existe no model/filtro mas sem transição de produto.

**Alternatives considered**: auto-concluir sem confirmação — rejeitado (Assumptions).

## 8. Visual / Design System (ponto de atenção do usuário)

**Decision**: Tratar [speckit_princ_pios_e_diretrizes_greenn_people.md](../../speckit_princ_pios_e_diretrizes_greenn_people.md) como gate de implementação UI, formalizado em [contracts/ui-visual-consistency.md](./contracts/ui-visual-consistency.md).

Pontos fechados na research:
| Tema | Escolha |
|---|---|
| Tipografia | `font-display` (Fraunces) no h1; `font-ui` (Source Sans 3) em tabela/badges |
| Atraso | `badge_status` `atrasada` = **rose** (Status Triad) — vermelho/rose só para prazo estourado |
| Pendência neutra | slate/amber — nunca rose |
| Chips hub | Manter padrão emerald do hub PDI para status de plano; chip “Com atrasadas” pode usar rose suave de selecionado **ou** emerald como os demais + indicador rose no card — preferir **chip no mesmo estilo emerald dos outros**, com badge rose no card (baixa carga cognitiva, um sistema de chip) |
| Tabela | Envelope `rounded-xl border border-line bg-surface-card` + `leader-team-table` / registry; hover `slate-50`; radius `rounded-lg` em controles |
| Filtros avançados | Ocultos em `<details>` “Filtros” |
| CTA | Um primário soberano no hub (`+` criar); toggle Cards/Tabela e filtros são secundários |
| Empty | Empty state guiado existente; filtro sem resultados = empty neutro, não erro vermelho |
| E-mail | `templates/emails/base.html` (marca emerald) |

**Alternatives considered**: Amber para badge de atraso — rejeitado (conflito com Status Triad e diretriz “vermelho só para prazo estourado”). Nova cor “laranja RH” — rejeitado.
