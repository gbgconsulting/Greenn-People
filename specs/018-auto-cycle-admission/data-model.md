# Data Model: Abertura Automática de Ciclos por Admissão

**Branch**: `018-auto-cycle-admission` | **Date**: 2026-09-09 | **Spec**: [spec.md](./spec.md)

Modelo aditivo sobre o domínio existente. Sem segundo campo de admissão. Sem app nova.

---

## Entities

### 1. `CustomUser` (accounts) — **intacto**

| Campo | Uso nesta feature |
|---|---|
| `data_entrada` | Fonte do ritmo (mês de admissão). NULL ⇒ fora do automático |
| `is_active` | Inativo ⇒ nunca elegível |

**Invariante**: edição posterior de `data_entrada` **não** apaga/altera `Avaliacao` existente (snapshot).

---

### 2. `Ciclo` (cycles) — **estendido**

Campos existentes relevantes: `nome`, `data_inicio`, `data_fim`, `status` (`aberto`/`encerrado`), `admitidos_ate` (015 manual).

#### Campos novos (aditivos)

| Campo | Tipo | Regra |
|---|---|---|
| `origem` | CharField choices `manual` \| `automatico` | Default `manual` (ciclos legados = manual). Write-once após create. |
| `marco_competencia` | DateField null | Para `automatico`: sempre dia 1 do mês de marco (`YYYY-MM-01`). NULL em manuais. |

#### Constraints

- `UniqueConstraint` onde `origem='automatico'` ∧ `marco_competencia` NOT NULL → **no máximo um** ciclo automático por mês de marco (idempotência estrutural).
- **Removido**: invariante applicacional “só um `status=aberto`” (`_validate_single_open`).
- `data_fim >= data_inicio` permanece.
- Manual: `admitidos_ate` continua obrigatório **na abertura** (`open_cycle`), não no DB.
- Automático: `admitidos_ate` permanece NULL (não governa elegibilidade auto).

#### Valores na abertura automática

| Campo | Valor |
|---|---|
| `origem` | `automatico` |
| `marco_competencia` | 1º dia civil do mês M |
| `data_inicio` | data do 1º dia útil (ativação) |
| `data_fim` | `data_inicio + 20 dias corridos` |
| `status` | `aberto` |
| `nome` | string RH-friendly com mês/ano do marco |

#### State transitions

```text
(inexistente) --[Beat no 1º dia útil + elegíveis]--> aberto (automatico)
aberto --[RH close_cycle / processo vigente]--> encerrado
encerrado --×--> automação NÃO reprocessa
```

Manual 015: fluxo atual `encerrado` → `aberto` via `open_cycle`, agora **sem** bloquear por outro aberto.

---

### 3. `Avaliacao` (reviews) — **intacto schema**

| Regra | Detalhe |
|---|---|
| Unique `(ciclo, usuario)` | Já existe — base da idempotência de matrícula |
| Snapshot | Create-only pelo ensure; sem delete por mudança de data |
| Auto | Criada só se elegível automático **e** não bloqueada por FR-008 |
| Manual | Predicado 015 intacto |

---

### 4. Marco de admissão (conceito / serviço — sem tabela)

Função pura:

```text
marcos(data_entrada) = { (y,m) | mês derivado de data_entrada + 6k meses, k ≥ 0 }
next_future_marco(data_entrada, ref) = min { marco ∈ marcos | marco ≥ month(ref) }
```

- Comparação por **(ano, mês)**, não pelo dia civil da admissão.
- Bootstrap: apenas `next_future_marco`; k passados nunca materializados.

---

### 5. `AutoCycleRun` (cycles) — **novo** (governança operacional)

Registro append-oriented de cada execução da rotina (diária).

| Campo | Tipo | Notas |
|---|---|---|
| `executado_em` | DateTimeField | |
| `data_referencia` | DateField | “hoje” da rotina |
| `era_primeiro_dia_util` | Boolean | |
| `marco_competencia` | DateField null | Preenchido se tentou/abriu coorte |
| `ciclo` | FK Ciclo null PROTECT | Ciclo da coorte se criado/reutilizado |
| `status` | `sucesso` \| `noop` \| `parcial` \| `falha` | |
| `matriculados` | PositiveInt | |
| `alertas_ciclo_aberto` | PositiveInt | |
| `excluidos_sem_admissao` | PositiveInt | snapshot da passada (ativos sem data) |
| `mensagem` | TextField blank | Resumo RH-readable |
| timestamps | TimeStampedModel | |

**Update policy**: status/contagens podem ser fechados ao fim do run; eventos filhos são append-only. Preferir não reescrever histórico de eventos.

---

### 6. `AutoCycleEvent` (cycles) — **novo** (linha de auditoria de negócio)

Append-only (bloquear update/delete no `save`/`delete`, padrão `NotificacaoLog`/`AuditLog`).

| Campo | Tipo | Notas |
|---|---|---|
| `run` | FK AutoCycleRun PROTECT | |
| `tipo` | `matricula` \| `alerta_ciclo_aberto` \| `pendencia_sem_admissao` \| `falha` \| `noop_dia` \| `coorte_criada` \| `coorte_reusada` | |
| `usuario` | FK User null PROTECT | Quando aplicável |
| `ciclo` | FK Ciclo null PROTECT | |
| `payload` | JSONField default dict | Detalhe mínimo (ids, motivo) |
| `criado_em` | DateTimeField auto | |

RH lê esses eventos na governança (FR-015/016) em linguagem de produto; `AuditLog` técnico complementar na criação do ciclo.

---

### 7. Notificações

| Peça | Uso |
|---|---|
| `NotificacaoLog.Tipo` | Novo tipo p.ex. `alerta_ciclo_ainda_aberto` (e opcional resumo de coorte) |
| Destinatários | `CustomUser.objects.filter(is_admin=True, is_active=True)` |
| Dedupe | `already_sent(dest, tipo, referencia, janela)` — referencia = ciclo coorte + user alertado ou run id |

---

## Relationships (overview)

```text
CustomUser.data_entrada ──► (serviço marco) ──► elegibilidade do mês
AutoCycleRun 1──* AutoCycleEvent
Ciclo(origem=automatico, marco_competencia) 1──* Avaliacao
Ciclo(manual) ── open_cycle 015 ──* Avaliacao
```

---

## Validation rules (resumo)

| Regra | Onde |
|---|---|
| Sem `data_entrada` ⇒ fora do auto | serviço marco / events `pendencia_sem_admissao` |
| Inativo ⇒ fora | serviço |
| Só próximo marco futuro | `next_future_marco` |
| Abertura só no 1º dia útil | calendário BR + task |
| 1 ciclo auto / `marco_competencia` | UniqueConstraint |
| FR-008: ciclo aberto ⇒ alerta, sem matrícula dela | `auto_cohort` |
| Alerta não atrasa lote | ordem do serviço |
| Avaliacao única por (ciclo, user) | Meta unique_together existente |
| N ciclos `aberto` permitidos | remoção `_validate_single_open` |

---

## State: alerta vs matrícula (pessoa com ciclo aberto)

```text
candidato elegível por marco
    ├─ tem Avaliacao em algum Ciclo.status=aberto?
    │     ├─ sim → AutoCycleEvent(alerta_ciclo_aberto) + e-mail RH
    │     │         → NÃO cria Avaliacao na nova coorte
    │     └─ não → ensure_avaliacao_for_user(user, ciclo=coorte)
    └─ demais candidatos seguem independentemente
```

---

## Migration safety

- Só `AddField` / `AddConstraint` / CreateModel.
- Default `origem='manual'` para linhas existentes.
- `marco_competencia=NULL` nos manuais.
- Sem `RunPython` que abra ciclos ou recupere marcos.
- Sem `AlterField` em `data_entrada`.
- Sem cascata nova que apague histórico (`on_delete=PROTECT` nas FKs novas).
