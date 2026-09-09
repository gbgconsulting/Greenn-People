# Data Model: 017-pdi-gestao-rh

**Date**: 2026-09-09  
**Spec**: [spec.md](./spec.md)

## Entities (existentes — comportamento estendido)

### PDI

| Campo / conceito | Notas |
|---|---|
| `usuario` | Dono do plano (destinatário de alerta + âncora de escopo) |
| `status` | `ativo` \| `concluido` \| `arquivado` |
| progresso | % ações `concluida` (serviço existente) |

**Transições novas/clarificadas**:

```text
ativo --[complete_pdi: 100% ações concluida]--> concluido
ativo --[archive_pdi]--> arquivado          (já existe)
concluido ✗ archive                        (já rejeitado)
arquivado ✗ complete / mutações de ação    (já bloqueado)
```

### AcaoPDI

| Campo | Notas |
|---|---|
| `pdi` | FK |
| `responsavel` | Não é destinatário do alerta nesta feature |
| `prazo` | Nullable; sem prazo ⇒ sem atraso |
| `status` | `pendente` \| `em_andamento` \| `concluida` \| `atrasada` |

**Job diário** (`mark_overdue_pdi_actions`): `prazo < hoje` e não concluída/atrasada → `atrasada` (PDI não arquivado). Em seguida dispara notificações (novo).

### Escopo de visibilidade

Não é tabela: resolvido por hierarquia (`line_manager`) + `is_admin`. Listagem/tabela/widget/digest **somente** sobre donos no escopo do viewer (admin = org).

### NotificacaoLog (extensão aditiva)

| Tipo novo | `referencia` | `janela` | Destinatários |
|---|---|---|---|
| `atraso_pdi` | `acao_pdi:{id}` | data ISO do dia em que a ação foi marcada atrasada (evento) | dono; gestor direto do dono |
| `digest_pdi_atrasos` | `org:digest` (ou constante org) | semana ISO `YYYY-Www` | admins ativos |

Tipos existentes **inalterados**: `lembrete_pdi`, `lembrete_etapa`, `feedback_continuo`.

Immutabilidade: append-only (já vigente).

## Derived metrics (não persistidos)

Calculados no annotate/serviço de listagem:

| Métrica | Definição |
|---|---|
| `acoes_atrasadas_count` | Count ações `status=atrasada` |
| `dias_atraso_max` | `hoje - min(prazo)` entre ações atrasadas; null se zero atrasadas |
| `proximo_prazo` | `min(prazo)` entre ações não concluídas com prazo; null se nenhum |
| `faixa_atraso` | derivada de `dias_atraso_max`: `1-7` / `8-30` / `30+` |

Filtro `atrasadas=1` ⇔ `acoes_atrasadas_count >= 1`.

## Validation rules

- `complete_pdi`: falha se status ≠ `ativo` ou existe ação não `concluida`.
- Alertas: skip se PDI arquivado, ação concluída, destinatário inativo, ou `already_sent`.
- Digest: skip total se contagem org de atrasadas == 0.
- Faixas: ação sem prazo nunca entra.

## Relationships (visão)

```text
User (dono) 1──* PDI 1──* AcaoPDI
User (dono).line_manager → User (gestor)   # alerta
User (admin) ← digest
NotificacaoLog *──1 User (destinatario)
```
