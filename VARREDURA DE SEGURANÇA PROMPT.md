# Varredura de Segurança — Greenn People

Você vai agir como um pentester sênior especializado em aplicações **Django monolíticas** com autorização hierárquica no backend. Sua missão é fazer uma varredura de segurança completa neste projeto e corrigir **TODA** vulnerabilidade encontrada, sem exceção.

## Contexto do projeto

Antes de começar, internalize o contexto abaixo. Ele substitui qualquer referência genérica a stacks de terceiros (Lovable, Supabase, Edge Functions, RLS, buckets, chaves anon/service_role, etc.).

| Aspecto | Greenn People |
|---|---|
| **Tipo** | App web interna de gestão de desempenho (~130 colaboradores) |
| **Backend** | Django 6 (monólito full stack, **sem DRF** na v1) |
| **Frontend** | Django Template Language (DTL) + HTMX + Tailwind CSS CLI |
| **Banco** | SQLite (dev) / PostgreSQL (prod via `DATABASE_URL`) |
| **Fila** | Redis + Celery + Celery Beat |
| **Auth** | Django nativo + `CustomUser` (`USERNAME_FIELD = email`) |
| **Autorização** | Escopo hierárquico por `line_manager` via `get_visible_users` / `ScopedObjectMixin` |
| **Auditoria** | `AuditLog` append-only + `log_scope_denied` em IDOR |
| **Deploy** | `config.settings.prod`, WhiteNoise, variáveis via `.env` / django-environ |
| **Constituição** | `.specify/memory/constitution.md` — Princípio II (segurança no backend) é inegociável |

**Erro crítico nº 1 neste projeto:** expor ou permitir acesso a dados de avaliação, metas, PDI ou talentos **fora do escopo hierárquico** do usuário autenticado (IDOR). Isso inclui views sem `ScopedObjectMixin`, queryset sem filtro de escopo, ou bypass de `user_in_scope`.

**Erro crítico nº 2:** segredos (`SECRET_KEY`, credenciais de banco, SMTP) versionados no repositório ou expostos em templates/JS estático.

**Erro crítico nº 3:** `DEBUG=True` ou settings de dev em produção.

Referências internas úteis durante a varredura:

- `.specify/memory/constitution.md` (Princípios II, III, IV)
- `specs/001-gestao-desempenho-talentos/contracts/scope-contract.md`
- `config/settings/prod.py`, `config/settings/base.py`
- `apps/core/mixins.py` (`ScopedObjectMixin`, mixins de papel)
- `apps/accounts/services/scope.py`
- `specs/002-pos-mvp-hardening/contracts/production-ux-test-contract.md`

---

Execute em **3 fases**. Não pule nenhuma.

═══════════════════════════════════════════════════════  
**FASE 1 — VARREDURA E RELATÓRIO**  
═══════════════════════════════════════════════════════

Faça um diagnóstico completo do app e retorne um relatório com status de cada item abaixo (**✅ OK**, **⚠️ RISCO**, **❌ FALHA CRÍTICA**). Para cada item em risco ou falha, explique em uma frase por que é um problema e qual o impacto.

---

### **A. AUTORIZAÇÃO E ESCOPO DE DADOS (substitui RLS/Supabase)**

1. Toda `DetailView`, `UpdateView` e `DeleteView` que expõe dados sensíveis usa `ScopedObjectMixin` (ou equivalente explícito com `user_in_scope`)?
2. Toda `ListView` de dados sensíveis filtra o queryset via `get_visible_users` (direta ou via mixin)?
3. Views de escrita (POST: aprovar/reprovar meta, avançar etapa, criar feedback, classificar talento) validam escopo **no servidor**, não só ocultam botões no template?
4. Tentativa de acesso a registro existente fora do escopo retorna `Http404` genérico e registra `log_scope_denied` (RF-36)?
5. Views admin-only (`Ciclo`, catálogos, usuários, audit log) usam mixin de papel (`RequiresAdminMixin`, `AdminOrganizationMixin`, etc.) e não dependem só de links ocultos na sidebar?
6. A exceção de aprovação por admin (gestor ausente) está limitada a `is_admin=True` e gera `AuditLog` com o ator real?
7. Nenhuma view sensível confia em parâmetros de URL/querystring (`user_id`, `area_id`) sem revalidar contra `get_visible_users`?
8. O Django Admin (`/admin/`) está restrito a staff/superuser e não expõe dados além do necessário?

---

### **B. AUTENTICAÇÃO**

9. Há proteção contra brute force no login (rate limit por IP/usuário)?
10. E-mail corporativo é exigido no cadastro (`@greenn.com.br`) e confirmação de e-mail é obrigatória antes do login (`email_confirmado_em`)?
11. Existe opção de MFA (autenticação de dois fatores) para usuários que quiserem ativar?
12. Senhas usam os validadores Django configurados em `AUTH_PASSWORD_VALIDATORS` (comprimento, senhas comuns, similaridade)?
13. Tokens de sessão e reset de senha expiram em tempo razoável (`SESSION_COOKIE_AGE`, validade do token de reset)?
14. Logout exige POST e invalida a sessão no servidor (não apenas redireciona)?
15. Cadastro self-service (`RegisterView`) é intencional para o ambiente alvo? Em produção interna, deveria estar desabilitado?

---

### **C. CHAVES E SEGREDOS**

16. `SECRET_KEY`, `DATABASE_URL`, `EMAIL_HOST_PASSWORD` e demais segredos vêm **somente** de variáveis de ambiente (`.env` local, secrets do deploy) — nunca hardcoded?
17. Nenhum segredo aparece em templates, arquivos estáticos, `docker-compose.yml` commitado ou logs?
18. `.env` está no `.gitignore` e `.env.example` contém apenas placeholders?
19. Comandos de import legado (`importar_colaboradores`, `importar_ciclos_avaliacoes`, etc.) só rodam via CLI com acesso ao servidor — não há endpoint HTTP equivalente?
20. Credenciais SMTP/Redis/PostgreSQL de produção não são as defaults do Docker (`greenn/greenn`) em ambiente real?

---

### **D. INPUTS, FORMULÁRIOS E VALIDAÇÃO**

21. Todos os formulários com impacto de negócio validam no servidor (Forms Django / `clean_*` / services), não só HTML5 no cliente?
22. Saída de texto do usuário em templates usa auto-escape Django (sem `|safe` indevido que abra XSS)?
23. Campos numéricos (notas, pesos, percentuais) validam tipo, mínimo e máximo no servidor?
24. Não há SQL bruto com interpolação de input do usuário fora de `SELECT 1` no health check? Queries dinâmicas usam ORM ou parâmetros bound?
25. Formsets e POSTs HTMX incluem e validam token CSRF (`{% csrf_token %}` / `hx-headers` com `X-CSRFToken`)?

---

### **E. RATE LIMITING E ABUSO**

26. Endpoints de login têm rate limit (recomendado: 5 tentativas por minuto por IP)?
27. Endpoints de reset de senha, reenvio de confirmação e cadastro têm rate limit ou throttling?
28. Formulários públicos (cadastro, recuperação de senha) têm CAPTCHA ou rate limit?
29. Tarefas Celery que disparam e-mails em massa têm proteção contra disparo abusivo (fila, idempotência)?

---

### **F. ARMAZENAMENTO DE ARQUIVOS**

30. O app **não** expõe upload de arquivo pelo usuário sem validação — ou, se existir, valida MIME, tamanho máximo e renomeia o arquivo?
31. `MEDIA_ROOT` / arquivos sensíveis não são servidos publicamente sem autenticação e checagem de escopo?
32. Arquivos estáticos em produção passam por `collectstatic` + WhiteNoise (ou reverse-proxy) — sem listagem de diretório?

---

### **G. HEADERS E CONFIGURAÇÃO DE PRODUÇÃO**

33. Produção usa `DJANGO_SETTINGS_MODULE=config.settings.prod` com `DEBUG=False`?
34. `ALLOWED_HOSTS` está explícito (sem `*` em produção)?
35. `SECURE_SSL_REDIRECT`, `SESSION_COOKIE_SECURE` e `CSRF_COOKIE_SECURE` estão ativos em prod?
36. `SECURE_HSTS_SECONDS` e `SECURE_HSTS_INCLUDE_SUBDOMAINS` estão configurados?
37. `X_FRAME_OPTIONS = 'DENY'` (clickjacking) está ativo?
38. `SECURE_CONTENT_TYPE_NOSNIFF` está ativo?
39. `Content-Security-Policy` restringe origens de scripts (atenção: HTMX carregado de CDN em `base.html`)?
40. `Referrer-Policy` está configurado como `strict-origin-when-cross-origin` ou mais restritivo?
41. `SECURE_PROXY_SSL_HEADER` está correto se houver reverse-proxy/load balancer?

---

### **H. SESSÃO E ARMAZENAMENTO NO CLIENTE**

42. Autenticação usa cookie de sessão Django (não token em `localStorage`)?
43. Cookies de sessão têm `Secure` em produção e `SameSite` adequado (`Lax` ou `Strict`)?
44. Nenhum dado sensível (PII, tokens) é persistido em `localStorage` / `sessionStorage` no JS do projeto?
45. HTMX e JS mínimo (`modal.js`, `row_actions_menu.js`) não expõem dados de escopo que deveriam ficar só no backend?

---

### **I. EXPOSIÇÃO DE INFORMAÇÃO**

46. Com `DEBUG=False`, páginas de erro não vazam stack trace, queries SQL ou paths internos?
47. Mensagens de erro ao usuário são genéricas (ex.: IDOR → 404, login → mensagem uniforme sem enumeração de e-mail)?
48. Endpoint `/health/` expõe apenas `{status, database}` — sem dados sensíveis — e está protegido por network policy se exposto publicamente?
49. Respostas HTMX/partials não retornam campos ou registros além do escopo do usuário (overfetching)?
50. Logs de aplicação e Celery não contêm senhas, tokens ou PII desnecessária?

---

### **J. AUDITORIA, LOGGING E MONITORAMENTO**

51. Alterações em entidades sensíveis geram `AuditLog` append-only (campo, valor anterior, valor novo)?
52. Acessos negados por escopo (`ACCESS_DENIED`) são registrados quando o registro existe mas está fora do escopo?
53. Aprovações/reprovações por admin substituto registram o ator real na auditoria?
54. Existe registro ou alerta para tentativas de login falhas, alteração de senha e ações administrativas críticas?
55. Há mecanismo de detecção/notificação de incidentes (picos de `ACCESS_DENIED`, brute force, erros 5xx)?

---

### **K. INTEGRIDADE DE DADOS E COMANDOS (específico Greenn People)**

56. FKs de dados históricos/ciclo usam `on_delete=PROTECT` (sem cascade destrutivo indevido)?
57. Snapshots write-once (`peso`, `nivel_esperado` em avaliações) não podem ser alterados após criação?
58. Comandos `importar_*` respeitam denylist de PII e rodam em transação com relatório — sem vazar dados do legado em stdout em produção?
59. Testes automatizados de escopo existem e falhariam se IDOR fosse reintroduzido (`tests/test_scope.py`, `tests/test_talent_matrix_authz.py`, contrato de produção)?

---

**Pare aqui.** Apresente o relatório completo antes de avançar.

═══════════════════════════════════════════════════════  
**FASE 2 — CORREÇÃO AUTOMÁTICA**  
═══════════════════════════════════════════════════════

Após aprovação do relatório, corrija **TODAS** as falhas encontradas, na ordem de criticidade:

1. **Primeiro:** tudo marcado como ❌ FALHA CRÍTICA (IDOR/escopo, segredos expostos, `DEBUG` em prod, CSRF ausente, admin desprotegido).
2. **Depois:** tudo marcado como ⚠️ RISCO.

Para cada correção, mostre:

- O que estava errado
- O código antes
- O código depois
- Como testar que a correção funcionou

**Padrões de correção deste projeto (não use Supabase/Edge Functions):**

| Problema | Correção canônica |
|---|---|
| IDOR / escopo | Aplicar `ScopedObjectMixin` + `scope_user_field` conforme `scope-contract.md`; em views POST, chamar `user_in_scope` ou serviço que já valida escopo |
| View admin | Usar `RequiresAdminMixin` ou mixin admin do app (`AdminOrganizationMixin`, etc.) |
| Segredo no código | Mover para variável de ambiente; atualizar `.env.example` |
| Rate limit login | `django-axes`, middleware de throttling no reverse-proxy, ou cache Redis — justificar na correção |
| CSP / headers | Adicionar em `config/settings/prod.py` ou middleware; documentar exceção do CDN HTMX se necessário |
| Validação | Form Django + service layer; nunca confiar só no template |
| Teste de regressão | Adicionar/ajustar teste pytest que falha se o bypass voltar |

═══════════════════════════════════════════════════════  
**FASE 3 — CHECKLIST FINAL DE PRÉ-LANÇAMENTO**  
═══════════════════════════════════════════════════════

Depois das correções, rode novamente a varredura da Fase 1 e confirme item por item que tudo está ✅. Em seguida, entregue:

1. **Resumo executivo** do que foi corrigido.
2. **Configurações FORA do código** — passo a passo manual para:
   - Variáveis de ambiente no servidor (`SECRET_KEY`, `DATABASE_URL`, `ALLOWED_HOSTS`, e-mail, Redis)
   - `python manage.py collectstatic` e serving estático (WhiteNoise ou nginx)
   - Backup PostgreSQL (`docs/ops/backup.md`)
   - Network policy para `/health/` e `/admin/`
   - TLS/HTTPS no load balancer
   - Desabilitar cadastro público se aplicável
3. **Quando rodar de novo** (sugerido):
   - Antes de cada release
   - Após adicionar view/model que exponha dados de colaborador
   - Após integrar terceiro (e-mail, SSO, etc.)
   - Após alterar `line_manager`, escopo ou mixins em `core`

---

**Comece pela FASE 1.** Aguarde o relatório completo antes de qualquer correção.
