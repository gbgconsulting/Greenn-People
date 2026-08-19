# Arquivos estáticos (produção)

Como coletar e servir CSS/JS/imagens do Greenn People em produção.

## Decisão de serving

| Opção | Quando usar | Status neste repositório |
|---|---|---|
| **WhiteNoise** (padrão) | Container único / processo WSGI sem nginx no path do app | **Adotado** em `config/settings/prod.py` |
| Reverse-proxy (nginx, Caddy, etc.) | Proxy já serve `STATIC_ROOT` e o app só recebe tráfego dinâmico | Alternativa documentada abaixo |

WhiteNoise é justificado pelo deploy em container único (`Dockerfile` / `docker-compose.yml`) sem configuração de proxy só para static. Se o ambiente passar a usar nginx (ou CDN) na frente, pode-se desligar o middleware WhiteNoise e apontar o proxy para `STATIC_ROOT`.

## Settings

- `STATIC_URL` / `STATICFILES_DIRS` — `config/settings/base.py`
- `STATIC_ROOT` — `config/settings/prod.py` → `BASE_DIR / 'staticfiles'`
- Middleware `whitenoise.middleware.WhiteNoiseMiddleware` (logo após `SecurityMiddleware`)
- Storage: `whitenoise.storage.CompressedStaticFilesStorage`

`staticfiles/` está no `.gitignore` — não versionar o resultado do `collectstatic`.

## Checklist de deploy — collectstatic

Antes de expor a aplicação com `DJANGO_SETTINGS_MODULE=config.settings.prod`:

1. Instalar dependências (`pip install -r requirements.txt`), incluindo `whitenoise`.
2. Garantir variáveis de ambiente de produção (`SECRET_KEY`, `ALLOWED_HOSTS`, `DATABASE_URL`, etc.).
3. Coletar estáticos:

```bash
export DJANGO_SETTINGS_MODULE=config.settings.prod
python manage.py collectstatic --noinput
```

4. Confirmar que `staticfiles/` foi populado (ou o volume/caminho equivalente no container).
5. Subir o processo WSGI (gunicorn/uwsgi/etc.) — WhiteNoise serve `/static/` sem passo extra.

Em build de imagem Docker, o mesmo comando deve rodar no stage de build ou no entrypoint (antes do start), com settings de produção.

## Alternativa: reverse-proxy

Se nginx (ou similar) servir os estáticos:

1. Continuar rodando `collectstatic` no deploy (mesmo `STATIC_ROOT`).
2. Configurar o proxy, por exemplo:

```nginx
location /static/ {
    alias /caminho/absoluto/para/staticfiles/;
    access_log off;
    expires 30d;
}
```

3. Remover `WhiteNoiseMiddleware` e o storage WhiteNoise de `prod.py` (ou condicionar via env), para não duplicar serving.
4. Manter `SECURE_PROXY_SSL_HEADER` / HTTPS conforme o proxy.

## Smoke rápido

```bash
export DJANGO_SETTINGS_MODULE=config.settings.prod
python manage.py collectstatic --noinput
# Depois do start: GET /static/... deve retornar 200 (WhiteNoise ou proxy)
curl -sf -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8000/health/
```
