# Greenn People

Aplicação web interna Django que centraliza o ciclo de desempenho de colaboradores: metas, avaliações, feedbacks, PDI, classificação 9-box e dashboards de aderência.

Stack: Django 6 + DTL + HTMX + Tailwind CSS CLI + Celery/Redis. Documentação técnica em [`docs/`](docs/README.md); especificação da feature em [`specs/001-gestao-desempenho-talentos/`](specs/001-gestao-desempenho-talentos/).

## Pré-requisitos

- Python 3.11+ (recomendado)
- Redis em execução (necessário para Celery; opcional se você só validar fluxos sem notificações/tarefas em background)
- [Tailwind CSS CLI standalone](https://tailwindcss.com/docs/installation/tailwind-cli) (binário; sem Node.js)

## Setup local

```bash
# Na raiz do repositório
python -m venv .venv

# Windows
.venv\Scripts\activate

# Linux / macOS
# source .venv/bin/activate

pip install -r requirements.txt

# Variáveis de ambiente (opcional — defaults cobrem o básico em dev)
copy .env.example .env          # Windows
# cp .env.example .env          # Linux / macOS

# Settings de desenvolvimento (já é o default em manage.py)
set DJANGO_SETTINGS_MODULE=config.settings.dev   # Windows
# export DJANGO_SETTINGS_MODULE=config.settings.dev

python manage.py migrate
python manage.py createsuperuser
```

## Rodar a aplicação

Em terminais separados (com o venv ativado):

### 1. Servidor Django

```bash
python manage.py runserver
```

Acesse `http://127.0.0.1:8000/`.

### 2. Tailwind (watch)

Baixe o binário standalone do Tailwind CLI e coloque-o no `PATH`, ou use o caminho local (o `.gitignore` ignora `tailwindcss` / `tailwindcss.exe` na raiz e em `bin/`).

```bash
tailwindcss -i static/src/input.css -o static/css/tailwind.css --watch
```

O CSS gerado em `static/css/tailwind.css` já está versionado; o watch só é necessário ao alterar classes nos templates ou tokens em `static/src/input.css`.

### 3. Celery (worker + beat)

Requer Redis em `redis://127.0.0.1:6379/0` (ou o valor de `REDIS_URL` / `CELERY_BROKER_URL` no `.env`).

```bash
celery -A config worker -l info
celery -A config beat -l info
```

Tarefas agendadas (Beat): lembretes de prazo de etapa/PDI, ações PDI vencidas e snapshots diários de aderência. Detalhes em `config/celery.py`.

## Validação end-to-end

Os cenários manuais (expectativas, avaliação pelo líder, PDI, aderência RH, matriz 9-box) e checks constitucionais estão em:

[`specs/001-gestao-desempenho-talentos/quickstart.md`](specs/001-gestao-desempenho-talentos/quickstart.md)

## Comandos úteis

```bash
python manage.py check
python manage.py migrate --check
ruff check apps/
```

## Documentação

| Recurso | Descrição |
|---|---|
| [`docs/`](docs/README.md) | Stack, arquitetura, modelo de dados, coding standards, design system |
| [`specs/001-gestao-desempenho-talentos/quickstart.md`](specs/001-gestao-desempenho-talentos/quickstart.md) | Setup resumido + cenários de validação |
| [`specs/001-gestao-desempenho-talentos/plan.md`](specs/001-gestao-desempenho-talentos/plan.md) | Plano técnico e estrutura do projeto |
| [`.env.example`](.env.example) | Variáveis de ambiente (Django, Redis/Celery, e-mail) |
