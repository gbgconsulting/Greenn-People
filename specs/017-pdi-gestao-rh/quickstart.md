# Quickstart: 017-pdi-gestao-rh

Validação end-to-end manual + pontos de teste automatizado. Detalhes de contrato: [contracts/](./contracts/).

## Prerequisites

- Branch `017-pdi-gestao-rh` com migrations aplicadas
- Redis/Celery disponíveis para tasks (ou `call_command` / `.delay` em shell de teste)
- Usuários seed: colaborador (dono), gestor (`line_manager` do dono), admin
- Pelo menos 2 PDIs ativos no escopo do gestor: um com ação `atrasada`, um sem

## Setup rápido (dev)

```bash
# na raiz do repo, venv ativo
python manage.py migrate
python manage.py runserver
# noutro terminal, se for validar Beat/tasks reais:
celery -A config worker -l info
celery -A config beat -l info
```

## Cenários de validação

### A. Hub — filtro e badge (US1)

1. Login como gestor → Meu PDI → visão Equipe.
2. Confirmar badge “N atrasada(s)” nos cards com atraso (rose/`badge_status`).
3. Chip **Com atrasadas** → só planos com atraso; busca/status ainda combinam.
4. Login colaborador → só próprios; sem vazamento.

**Esperado visual**: chips no estilo do hub; um CTA primário de criar; Fraunces no título.

### B. Alerta de atraso (US2)

1. Ação com `prazo` ontem, status pendente, PDI ativo.
2. Rodar `mark_overdue_pdi_actions` (ou task equivalente).
3. Verificar `NotificacaoLog` tipo `atraso_pdi` para dono e gestor; e-mails enviados.
4. Rodar de novo no mesmo dia → sem duplicata.

### C. Tabela operacional (US3)

1. Gestor/admin, visão equipe → toggle **Tabela**.
2. Colunas: colaborador, gestor, área, progresso, nº atrasadas, dias max, próximo prazo.
3. Filtros em “Filtros”: gestor, área, faixa 1–7 / 8–30 / 30+.
4. Colaborador não vê toggle/tabela gerencial.

**Esperado visual**: envelope registry / `leader-team-table`; filtros em `<details>`; toggle no DNA do ownership.

### D. Digest admin (US4)

1. Com atrasos na org → disparar task digest → admin recebe 1 e-mail com totais + CTA.
2. Sem atrasos → zero e-mail.
3. Gestor não-admin → não recebe digest.

### E. Widget dashboard (US5)

1. Dashboard time/admin → card com contagem e link para listagem `atrasadas=1`.
2. Zero atrasos → zero neutro (não erro vermelho).

### F. Board + concluir (US6)

1. Detalhe PDI → coluna **Atrasadas** isolada.
2. Todas ações concluídas → CTA Concluir plano → status `concluido` → filtro Concluídos.
3. Com ação aberta → CTA ausente ou rejeição clara.

## Automated smoke (após implement)

```bash
# Validação guiada A–F + gate visual (rollback; send mockado)
PYTHONPATH=. .venv/bin/python scripts/validate_quickstart_017_pdi.py

# Suite de contrato
.venv/bin/pytest tests/test_pdi_overdue_list_filters.py \
       tests/test_pdi_overdue_notifications.py \
       tests/test_pdi_digest.py \
       tests/test_pdi_complete.py -q
```

## Gate visual rápido

Usar checklist em [contracts/ui-visual-consistency.md](./contracts/ui-visual-consistency.md) antes do PR.
