# Backup do banco (produção)

Estratégia mínima de backup do PostgreSQL do Greenn People (FR-021 / SC-007). Produção exige `DATABASE_URL` (`config/settings/prod.py`); desenvolvimento local pode usar SQLite — este documento cobre **somente PostgreSQL de produção**.

## Mínimos obrigatórios

| Parâmetro | Mínimo | Notas |
|---|---|---|
| **Frequência** | 1× por dia (diário) | Preferir horário de baixa carga; idealmente após o fechamento operacional do dia |
| **Retenção** | 7 dias de dumps diários | Manter pelo menos o dump mais recente + os 6 anteriores |
| **Escopo** | Banco completo (`greenn_people` ou equivalente em `DATABASE_URL`) | Inclui ciclos, avaliações, PDI, auditoria e catálogos |
| **Destino** | Storage fora do volume do Postgres | Objeto (S3/GCS/compatível) ou disco/volume distinto do `PGDATA` |

Além do diário, recomenda-se (não obrigatório neste mínimo):

- snapshot/volume do provedor (RDS, Cloud SQL, disco do host) com retenção ≥ 7 dias, se disponível;
- 1 dump semanal adicional retido por ≥ 30 dias, quando a política da organização exigir.

SQLite (`db.sqlite3`) **não** é banco de produção — não use cópia de arquivo SQLite como estratégia de go-live.

## Procedimento padrão: `pg_dump`

Obter host, porta, usuário, senha e nome do banco a partir de `DATABASE_URL` (ex.: `postgresql://user:pass@host:5432/greenn_people`).

### Dump lógico (aplicável em qualquer Postgres acessível)

```bash
# Variáveis — ajuste conforme o ambiente (não versionar senhas)
export PGHOST=...          # host do DATABASE_URL
export PGPORT=5432
export PGUSER=...
export PGPASSWORD=...      # ou use ~/.pgpass
export PGDATABASE=greenn_people

STAMP=$(date -u +%Y%m%dT%H%M%SZ)
OUT_DIR=/var/backups/greenn-people   # ou caminho do storage montado
mkdir -p "$OUT_DIR"

pg_dump --format=custom --file="${OUT_DIR}/greenn_people_${STAMP}.dump" \
  --no-owner --no-acl

# Verificar que o arquivo não está vazio
test -s "${OUT_DIR}/greenn_people_${STAMP}.dump"
```

Formato `custom` (`-Fc`) permite restore seletivo com `pg_restore` e compressão nativa.

### Via Docker Compose (ambiente alinhado ao repo)

Com o serviço `db` do `docker-compose.yml` (`postgres:16-alpine`, DB `greenn_people`):

```bash
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
OUT_DIR=./backups
mkdir -p "$OUT_DIR"

docker compose exec -T db pg_dump -U greenn -d greenn_people -Fc \
  > "${OUT_DIR}/greenn_people_${STAMP}.dump"

test -s "${OUT_DIR}/greenn_people_${STAMP}.dump"
```

Agende o mesmo comando no cron/systemd timer do host (ou job do orquestrador) **1× ao dia**.

### Retenção (exemplo de limpeza)

Após cada dump bem-sucedido, remover arquivos com mais de 7 dias:

```bash
find "$OUT_DIR" -name 'greenn_people_*.dump' -type f -mtime +7 -delete
```

Ajuste o caminho e o padrão de nome se o storage for remoto (lifecycle rule de 7 dias no bucket).

## Restore (smoke / desastre)

Restaurar **somente** em ambiente de teste ou após decisão explícita de recuperação — nunca sobrescrever produção sem confirmação.

```bash
# Banco destino vazio ou recriado
pg_restore --clean --if-exists --no-owner --no-acl \
  -d greenn_people /caminho/para/greenn_people_YYYYMMDD.dump
```

Via Compose (exemplo em volume local):

```bash
docker compose exec -T db pg_restore --clean --if-exists --no-owner --no-acl \
  -U greenn -d greenn_people < ./backups/greenn_people_YYYYMMDD.dump
```

Após restore: subir a app com `DJANGO_SETTINGS_MODULE=config.settings.prod`, rodar `python manage.py migrate --check` (ou migrar se o dump for de versão anterior) e validar `GET /health/` → 200.

## Alternativa: snapshots do provedor

Se o Postgres for gerenciado (RDS, Cloud SQL, Azure Database, etc.):

1. Habilitar backup automático diário com retenção ≥ **7 dias**.
2. Documentar no runbook interno da plataforma o console/CLI para restore point-in-time (se disponível).
3. Manter **pelo menos um** `pg_dump` lógico semanal exportável fora da conta do provedor (portabilidade / Ransomware), alinhado à retenção mínima acima.

Snapshots de volume Docker (`postgres_data`) **não** substituem o mínimo diário documentado aqui — servem como camada extra, não como única estratégia.

## Checklist operacional

- [ ] Job diário de `pg_dump` (ou backup gerenciado equivalente) ativo e monitorado
- [ ] Destino fora do volume `PGDATA`
- [ ] Retenção ≥ 7 dias verificada (arquivo ou lifecycle)
- [ ] Restore testado pelo menos 1× por trimestre em ambiente não produtivo
- [ ] Credenciais só em secret manager / env do job — nunca em git

## Referências

- Settings de produção: `config/settings/prod.py` (`DATABASE_URL`)
- Compose local: `docker-compose.yml` (serviço `db`)
- Contrato: `specs/002-pos-mvp-hardening/contracts/production-ux-test-contract.md`
- Estáticos / deploy: [static.md](./static.md)
