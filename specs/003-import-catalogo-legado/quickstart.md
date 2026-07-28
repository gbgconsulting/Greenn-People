# Quickstart: Validação — Importação One-Shot do Catálogo Legado

**Branch**: `003-import-catalogo-legado` | **Date**: 2026-07-28

Guia de validação end-to-end conforme [spec.md](./spec.md). Modelo: [data-model.md](./data-model.md). Contratos: [contracts/](./contracts/).

## Pré-requisitos

- Python 3.x, dependências: `pip install -r requirements.txt`
- App migrada (`python manage.py migrate`)
- Fontes na raiz do repo (ou paths equivalentes):
  - `lista-cargos.xlsx`
  - `lista-competencias.xlsx`

```bash
export DJANGO_SETTINGS_MODULE=config.settings.dev
python manage.py migrate
```

## Comando

```bash
# Preview sem gravar
python manage.py importar_competencias_cargo \
  --cargos lista-cargos.xlsx \
  --competencias lista-competencias.xlsx \
  --dry-run

# Carga real + relatório em arquivo
python manage.py importar_competencias_cargo \
  --cargos lista-cargos.xlsx \
  --competencias lista-competencias.xlsx \
  --report-file /tmp/relatorio-catalogo-legado.txt
```

Contrato CLI: [contracts/import-command-contract.md](./contracts/import-command-contract.md).

## Cenários de validação

### C1 — Carga inicial do catálogo (US1 / P1)

**Pré**: catálogo vazio (ou sem equivalentes dos nomes legados).

| Passo | Ação | Esperado |
|---|---|---|
| 1 | Rodar comando sem `--dry-run` | exit `0`; relatório com `*_criados` > 0 |
| 2 | Conferir escala | Existe `Escala padrão 1-5` ativa (1..5) |
| 3 | CRUD / shell: amostrar cargos | Nomes normalizados; `nivel` conforme de-para (ex.: `* JR` → 2; sem sufixo → 6) |
| 4 | Amostrar competências | Tipo mapeado (Liderança→`lideranca`, etc.); escala padrão associada |

Ver [legado-domain-mapping-contract.md](./contracts/legado-domain-mapping-contract.md).

### C2 — Perfil cargo↔competência (US2 / P1)

| Passo | Ação | Esperado |
|---|---|---|
| 1 | Escolher cargo conhecido nas duas fontes | Vínculos `CargoCompetencia` existem |
| 2 | Inspecionar vínculo | `peso=1`; `nivel_esperado` coerente com senioridade do cargo |
| 3 | Abrir CRUD de perfil por cargo (US-14) | RH consegue editar `nivel_esperado`/`peso` sem reimportar |

### C3 — Exclusão de KPI (US3 / P2)

| Passo | Ação | Esperado |
|---|---|---|
| 1 | Buscar no relatório seção `Excluídos KPI` | Contém SLA, Lead time discovery, Throughput, Índice de incidentes, Custo de nuvem, etc. |
| 2 | Shell: `Competencia` ativa com esses nomes | **Não** existem |
| 3 | Competências comportamentais/liderança reais | Importadas normalmente |

### C4 — Idempotência e soft-delete (US4 / P2)

| Passo | Ação | Esperado |
|---|---|---|
| 1 | Reexecutar o mesmo comando | exit `0`; delta de ativos duplicados = 0; predominantemente `inalterados` |
| 2 | Soft-delete de um cargo/competência importado; reimportar | Permanece inativo; aparece em `Conflitos` (`inativo_existente`) |
| 3 | Introduzir divergência artificial só em uma fonte (fixture de teste) | Par em `Divergências`; demais carga ok |

### C5 — Arquivo inválido

| Passo | Ação | Esperado |
|---|---|---|
| 1 | Path inexistente ou CSV sem colunas | exit `1`; mensagem clara; **nenhuma** alteração parcial |

## Checagens rápidas via shell

```bash
python manage.py shell
```

```python
from apps.organization.models import Cargo
from apps.competencies.models import Competencia, CargoCompetencia, Escala

print(Escala.objects.filter(is_active=True, nome='Escala padrão 1-5').count())  # 1
print(Cargo.objects.filter(is_active=True).count())
print(Competencia.objects.filter(is_active=True).count())
print(CargoCompetencia.objects.count())

# Amostra: cargo júnior
c = Cargo.objects.filter(is_active=True, nome__icontains=' JR').first()
assert c is None or c.nivel == 2
# KPI não deve existir como ativa
assert not Competencia.objects.filter(is_active=True, nome__iexact='SLA').exists()
```

## Testes automatizados

```bash
pytest tests/test_import_catalogo_legado.py -q
```

Cobertura mínima esperada: de-para de nivel/`nivel_esperado`, filtro KPI, matriz/divergência, segunda execução sem duplicata, soft-delete não reativado, arquivo inválido sem writes.

## Critérios de sucesso (smoke)

- SC-001..003: cargos, competências elegíveis e vínculos coerentes após 1ª carga
- SC-004: divergências só no relatório (não silenciosas)
- SC-005: KPIs da lista de exclusão ausentes do catálogo ativo
- SC-006: 2ª execução sem duplicatas ativas
- SC-007: relatório revisável em < 1 min
- SC-008: CRUD de perfil utilizável imediatamente após a carga
