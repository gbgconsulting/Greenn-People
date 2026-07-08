# TASKS — Greenn People

> Checklist de execução do desenvolvimento, derivado do `PRD_Greenn_People.md` (v1.4). Marque cada item com `[x]` conforme for concluído. A ordem das sprints reflete dependências reais entre os módulos — não pule uma sprint sem concluir a **Definição de Pronto** da anterior.

---

## Como usar este arquivo

- `[ ]` pendente · `[x]` concluído · `[~]` em andamento (marque manualmente ao começar) · `[!]` bloqueado (descreva o bloqueio ao lado).
- Cada sprint tem uma seção **🎯 Objetivo**, os **Pré-requisitos**, o **Checklist** de tarefas e uma **✅ Definição de Pronto (DoD)** — só avance para a próxima sprint quando a DoD estiver satisfeita.
- Referências como `RF-XX` e `Decisão #N` apontam para as seções 6 e 15 do `PRD_Greenn_People.md`, caso precise revisitar a regra de negócio completa.
- Sprints 0 a 6 podem começar imediatamente. A **Sprint 6.5** tem um pré-requisito bloqueante externo (layout dos arquivos Sólides) — ver aviso na própria seção.

---

## Status atual do repositório (ponto de partida)

Já existe: projeto Django (`django-admin startproject`) com `core/` (settings, urls, wsgi, asgi), `manage.py`, `requirements.txt` (Django 6.0.7) e `db.sqlite3` vazio. **Nada mais foi implementado ainda** — nenhum app de domínio, sem Tailwind, sem Celery, sem controle de versão. A Sprint 0 abaixo já reflete esse ponto de partida.

---

## Visão geral das sprints

| # | Sprint | Módulo/App | Depende de |
|---|---|---|---|
| 0 | Fundação do Projeto | `core` | — |
| 1 | Contas e Autenticação | `accounts` | Sprint 0 |
| 2 | Organização | `organization` | Sprint 1 |
| 3 | Competências | `competencies` | Sprint 2 |
| 4 | Metas e Objetivos | `goals` | Sprint 2, 3 |
| 5 | Ciclo de Avaliação | `cycles` + `reviews` | Sprint 3, 4 |
| 6 | PDI | `pdi` | Sprint 1 |
| 6.5 | Carga de Dados Legado (Sólides) | `accounts`, `competencies`, `reviews`, `pdi` | Sprints 0–6 + doc. do layout Sólides |
| 7 | Talentos (9-box) | `talent` | Sprint 5 |
| 8 | Dashboards e Aderência | `dashboard` | Sprint 5, 6, 7 |
| 9 | Notificações | `notifications` | Sprint 5, 6 |
| 10 | Auditoria | `audit` | Sprint 2, 5, 7 |
| 11 | Refino de UI e Responsividade | transversal | Sprints 1–10 |
| 12 | Preparação para PostgreSQL | transversal | Sprints 1–10 |
| 13 | Docker | transversal | Sprint 12 |
| 14 | Testes Automatizados | transversal | Sprints 1–10 |

---

## Sprint 0 — Fundação do Projeto

### 🎯 Objetivo
Deixar o projeto pronto para receber os apps de domínio: ambiente configurado, settings por ambiente, template base com Tailwind, Celery/Redis funcionando e padrões de código definidos.

### Pré-requisitos
- Python 3.12+ instalado.
- Redis disponível localmente (ou via Docker) para testar Celery.

### Checklist

**0.0 — Controle de versão e ambiente (complemento à fundação)**
- [X] 0.0.1 Criar `.gitignore` (venv, `__pycache__`, `.env`, `db.sqlite3`, `staticfiles/`, `*.pyc`, `node_modules` se aplicável)
- [ ] 0.0.2 Inicializar repositório Git (`git init`) e primeiro commit
- [ ] 0.0.3 Confirmar `venv` ativo e `requirements.txt` atualizado a cada nova dependência

**0.1 — Inicializar projeto Django**
- [x] 0.1.1 Criar projeto Django (`django-admin startproject config .`) — já existe como `core/`
- [ ] 0.1.2 Configurar settings separados por ambiente (`core/settings/base.py`, `dev.py`, `prod.py` + `__init__.py`) — migrar o `settings.py` atual para essa estrutura
- [ ] 0.1.3 Configurar `.env` e `django-environ` (ou `python-decouple`) para variáveis sensíveis (`SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`, credenciais de e-mail/Redis)
- [ ] 0.1.4 Configurar `LANGUAGE_CODE = 'pt-br'` e `TIME_ZONE = 'America/Sao_Paulo'`
- [ ] 0.1.5 Atualizar `SECRET_KEY` para vir de variável de ambiente (nunca hardcoded/commitada)

**0.2 — Criar app core**
- [ ] 0.2.1 Criar app `core` de domínio (recursos compartilhados — distinto do `core/` de config; avaliar renomear a pasta de configuração para `config/` se for gerar confusão de nomes)
- [ ] 0.2.2 Criar model base abstrato `TimeStampedModel` com `created_at`/`updated_at`
- [ ] 0.2.3 Criar template base (`templates/base.html`) com sidebar, topbar e bloco de conteúdo (`{% block content %}`)
- [ ] 0.2.4 Criar pasta de componentes reutilizáveis (`templates/components/`)
- [ ] 0.2.5 Configurar `DIRS` de templates no settings apontando para `templates/` na raiz do projeto

**0.3 — Configurar Tailwind CSS**
- [ ] 0.3.1 Baixar/configurar Tailwind CLI standalone (binário, sem Node.js)
- [ ] 0.3.2 Criar `tailwind.config.js` com paleta de cores e fontes do design system (ver `docs/design-system.md`)
- [ ] 0.3.3 Configurar script de build/watch do CSS (`npm run` opcional ou script `.sh`/`.ps1` chamando o binário)
- [ ] 0.3.4 Integrar arquivo CSS gerado ao `static/` e referenciar no `base.html`
- [ ] 0.3.5 Baixar fonte Inter localmente (Google Fonts) e servir via `static/`

**0.4 — Configurar Redis e Celery**
- [ ] 0.4.1 Instalar `celery` e configurar `core/celery.py`
- [ ] 0.4.2 Configurar broker e result backend apontando para Redis (via variável de ambiente)
- [ ] 0.4.3 Criar task de teste (`ping_task`) e validar execução local (`celery -A core worker`)
- [ ] 0.4.4 Configurar Celery Beat com uma tarefa agendada de teste (`django-celery-beat` ou schedule estático)

**0.5 — Padrões de código**
- [ ] 0.5.1 Configurar `ruff` (ou `flake8`) com regras PEP 8 e preferência por aspas simples
- [ ] 0.5.2 Documentar convenções do projeto em `README.md` (idioma do código, apps, signals, como rodar Celery/Tailwind localmente)
- [ ] 0.5.3 Configurar pre-commit hook opcional (lint automático antes do commit)

### ✅ Definição de Pronto
`python manage.py runserver` sobe sem erros com settings de dev; template base renderiza com Tailwind aplicado; `celery -A core worker` e `celery -A core beat` executam a task de teste com sucesso; lint roda sem erros no projeto vazio.

---

## Sprint 1 — Contas e Autenticação (`accounts`)

### 🎯 Objetivo
Login por e-mail, cadastro restrito a `@greenn.com.br` com confirmação de posse do e-mail, recuperação de senha e proteção básica de rotas — sem depender ainda de área/cargo/gestor (isso vem na Sprint 2).

### Pré-requisitos
Sprint 0 concluída (template base, settings, e-mail backend configurável).

### Checklist

**1.1 — Modelo de usuário customizado**
- [ ] 1.1.1 Criar app `accounts`
- [ ] 1.1.2 Criar `CustomUser(AbstractUser)` com e-mail único e `USERNAME_FIELD = 'email'`
- [ ] 1.1.3 Remover campo `username` do fluxo de cadastro/login
- [ ] 1.1.4 Adicionar campo `is_admin` (booleano) — sem campo "papel" fixo (RF-03)
- [ ] 1.1.5 Adicionar campo `email_confirmado_em` (datetime, nullable — RF-02.1)
- [ ] 1.1.6 Configurar `AUTH_USER_MODEL` no settings **antes** da primeira migration
- [ ] 1.1.7 Criar e aplicar migrations iniciais
- [ ] 1.1.8 Criar propriedades `is_leader` (possui liderados diretos) e `is_manager` (possui liderados que também lideram), calculadas a partir de `line_manager` (ficam "vazias"/`False` até a Sprint 2, quando o campo existir — ver nota abaixo)

> **Nota de sequenciamento:** o campo `line_manager` só é criado na Sprint 2 (`organization`). Nesta sprint, implemente `is_leader`/`is_manager` já preparados para consultar `line_manager`, mas o comportamento completo só pode ser validado após a Sprint 2.3.1.

**1.2 — Cadastro (registre-se)**
- [ ] 1.2.1 Criar `RegisterForm` com validação de e-mail único, domínio `@greenn.com.br` e senha (usando `AUTH_PASSWORD_VALIDATORS`)
- [ ] 1.2.2 Criar `RegisterView` (CBV): grava usuário com `email_confirmado_em` nulo, dispara e-mail de confirmação com link (token), redireciona para tela "verifique seu e-mail"
- [ ] 1.2.3 Criar `ConfirmEmailView` (uidb64 + token, especializando `PasswordResetTokenGenerator`): valida token, grava `email_confirmado_em=now()`, redireciona ao login
- [ ] 1.2.4 Criar view/rota de reenvio do link de confirmação
- [ ] 1.2.5 Criar templates `accounts/register.html` e `accounts/verify_email.html` seguindo o design system
- [ ] 1.2.6 Validar estritamente o domínio de e-mail (`@greenn.com.br`) — rejeitar no `clean_email()` do form
- [ ] 1.2.7 Envio do e-mail de confirmação **síncrono** (backend nativo do Django, console em dev) — sem Celery (RF-02.1)

**1.3 — Login**
- [ ] 1.3.1 Customizar `AuthenticationForm` para autenticar por e-mail e bloquear login se `email_confirmado_em` for nulo, com mensagem e link de reenvio
- [ ] 1.3.2 Criar `LoginView` (CBV baseada em `django.contrib.auth.views.LoginView`)
- [ ] 1.3.3 Criar template `accounts/login.html` com identidade visual do produto
- [ ] 1.3.4 Implementar redirecionamento pós-login sempre para o dashboard pessoal (`get_success_url`)

**1.4 — Recuperação de senha**
- [ ] 1.4.1 Configurar views nativas de reset de senha do Django (`PasswordResetView`, `PasswordResetConfirmView`, etc.)
- [ ] 1.4.2 Customizar templates de reset com o design system
- [ ] 1.4.3 Configurar backend de e-mail (console em dev; deixar pronto para SMTP em produção via variável de ambiente)

**1.5 — Logout e proteção de rotas**
- [ ] 1.5.1 Configurar `LogoutView`
- [ ] 1.5.2 Criar `LoginRequiredMixin` padrão para views internas (ou usar o nativo do Django consistentemente)
- [ ] 1.5.3 Criar mixins de checagem de visão (`RequiresLeaderMixin`, `RequiresManagerMixin`, `RequiresAdminMixin`), baseados em `is_leader`/`is_manager`/`is_admin`
- [ ] 1.5.4 Criar templates customizados `404.html`/`403.html` seguindo o design system (mesma sidebar/topbar, mensagem genérica)

### ✅ Definição de Pronto
Um usuário com e-mail `@greenn.com.br` consegue se cadastrar, recebe (no console) o e-mail de confirmação, confirma via link, faz login e cai no dashboard (placeholder). Cadastro com domínio diferente é rejeitado. Login antes da confirmação é bloqueado com mensagem clara. Reset de senha funciona ponta a ponta. `404.html`/`403.html` customizados aparecem corretamente.

---

## Sprint 2 — Organização (`organization`)

### 🎯 Objetivo
Estrutura organizacional (área, cargo, hierarquia de liderança) e o serviço central de resolução de escopo (`get_visible_users` + `ScopedObjectMixin`) que será reutilizado por praticamente todas as sprints seguintes.

### Pré-requisitos
Sprint 1 concluída (`CustomUser` existente).

### Checklist

**2.1 — Model de Área**
- [ ] 2.1.1 Criar model `Area` (`nome`, `parent` auto-FK com validação anti-ciclo — RF-07.1, `is_active`, `created_at`/`updated_at`)
- [ ] 2.1.2 Implementar validação anti-ciclo no `clean()`/`save()` de `Area.parent` (cobrir caso trivial de autorreferência)
- [ ] 2.1.3 Criar admin do Django para `Area`

**2.2 — Model de Cargo**
- [ ] 2.2.1 Criar model `Cargo` (`nome`, `nivel`, `is_active`)
- [ ] 2.2.2 Criar admin do Django para `Cargo`

**2.3 — Vínculo com usuário**
- [ ] 2.3.1 Adicionar FK `area` (`PROTECT`), `cargo` (`PROTECT`) e `line_manager` (`SET_NULL`, nullable) ao `CustomUser`, com validação anti-ciclo em `line_manager` (RF-04.1, incluindo autorreferência)
- [ ] 2.3.2 Criar migration e ajustar admin de usuário (exibir área/cargo/gestor)
- [ ] 2.3.3 Atualizar `RegisterForm` com campos **opcionais** de área/cargo/gestor (selects — RF-04.2)

**2.4 — Telas de gestão (admin do sistema)**
- [ ] 2.4.1 CRUD de áreas (CBVs: `ListView`, `CreateView`, `UpdateView`, `DeleteView`), restrito ao admin
- [ ] 2.4.2 CRUD de cargos (mesmas CBVs), restrito ao admin
- [ ] 2.4.3 Tela de gestão de usuários (listar, editar `is_admin`/área/cargo/`line_manager`)
- [ ] 2.4.4 Tela "Usuários pendentes de vínculo" (admin): listar usuários ativos com `area` e/ou `cargo` nulos (RF-04.2; `line_manager` nulo **não** entra nesse filtro)
- [ ] 2.4.5 Implementar bloqueio de desativação (`is_active=False`) quando o usuário possuir liderados diretos ativos, exigindo reatribuição manual em lote antes de confirmar (RF-04.3) — cobrir tanto a tela de gestão quanto o admin nativo do Django
- [ ] 2.4.6 Gerar linha em `AuditLog` para desativação e cada reatribuição (placeholder até a Sprint 10 existir — ver nota abaixo)

> **Nota de sequenciamento:** o app `audit` só é implementado na Sprint 10. Até lá, deixe um comentário/TODO no código nos pontos que deverão emitir `AuditLog` (2.4.5/2.4.6), ou implemente um stub simples de log que será substituído depois.

**2.5 — Serviço de escopo de visibilidade**
- [ ] 2.5.1 Criar função `get_visible_users(user)` em `organization/services.py`
- [ ] 2.5.2 Implementar regra: colaborador → próprio
- [ ] 2.5.3 Implementar regra: líder → próprio + liderados diretos
- [ ] 2.5.4 Implementar regra: gerente → próprio + toda a subárvore de liderados (query otimizada — CTE recursiva ou cache, evitar recursão pura em Python)
- [ ] 2.5.5 Implementar regra: admin → todos
- [ ] 2.5.6 Criar `ScopedObjectMixin` reutilizável que sobrescreve `get_object()` e retorna 404 quando o registro está fora do escopo do usuário
- [ ] 2.5.7 Escrever caso de uso manual de validação: usuário A tentando acessar URL de registro do usuário B fora do escopo (checagem manual nesta sprint; teste automatizado formal fica para a Sprint 14.2.2)

### ✅ Definição de Pronto
Área/cargo têm CRUD funcional com hierarquia de área visível na listagem; usuário pode ser vinculado a área/cargo/gestor; ciclo em `Area.parent`/`line_manager` é bloqueado na validação; desativar usuário com liderados ativos é bloqueado; `get_visible_users` retorna o conjunto correto para os 4 perfis testados manualmente; `ScopedObjectMixin` bloqueia acesso cruzado entre usuários fora de escopo.

---

## Sprint 3 — Competências (`competencies`)

### 🎯 Objetivo
Cadastro de escalas e competências, e o perfil de competências esperadas por cargo (com pesos), base para o cálculo de nota da Sprint 5.

### Pré-requisitos
Sprint 2 concluída (model `Cargo` existente).

### Checklist

**3.1 — Escalas**
- [ ] 3.1.1 Criar model `Escala` (`nome`, `valor_minimo`, `valor_maximo`, rótulos por nível em JSON)
- [ ] 3.1.2 CRUD de escalas (CBVs) restrito ao admin

**3.2 — Competências**
- [ ] 3.2.1 Criar model `Competencia` (`nome`, `descricao`, `tipo`: técnica/comportamental/liderança, FK `Escala`)
- [ ] 3.2.2 CRUD de competências (CBVs) restrito ao admin

**3.3 — Perfil de competências por cargo**
- [ ] 3.3.1 Criar model `CargoCompetencia` (FK `Cargo` `PROTECT`, FK `Competencia` `PROTECT`, `nivel_esperado`, `peso` com `MinValueValidator` > 0 — RF-19.3)
- [ ] 3.3.2 Tela de vínculo de competências a um cargo (definindo nível esperado e pesos de cada competência), restrita ao admin

### ✅ Definição de Pronto
Admin consegue criar uma escala (ex.: 1 a 5), uma competência vinculada a essa escala, e associá-la a um cargo com peso > 0 e nível esperado — tudo validado (peso zero/negativo é rejeitado no formulário).

---

## Sprint 4 — Metas e Objetivos (`goals`)

### 🎯 Objetivo
Cadastro de objetivos estratégicos e metas do colaborador, com os dois fluxos de aprovação (meta e resultado) e reabertura pontual em caso de reprovação.

### Pré-requisitos
Sprint 2 concluída (usuário vinculado). Sprint 5 (Ciclo) ainda não existe — o model `ObjetivoEstrategico` referencia `Ciclo`; se necessário, criar o model `Ciclo` mínimo (só schema) antecipadamente, ou reordenar para criar `Ciclo` primeiro (ver nota abaixo).

> **Nota de sequenciamento:** o PRD lista `goals` antes de `cycles`, mas `ObjetivoEstrategico` tem FK para `Ciclo`. Recomenda-se criar o model `Ciclo` (schema básico, sem a máquina de estados) já nesta sprint, ou adiantar a Sprint 5.1.1 antes de 4.1.1.

### Checklist

**4.1 — Objetivos estratégicos**
- [ ] 4.1.1 Criar model `ObjetivoEstrategico` (`descricao`, FK `Ciclo`)
- [ ] 4.1.2 CRUD restrito ao admin

**4.2 — Metas do colaborador**
- [ ] 4.2.1 Criar model `Meta` (`usuario` `PROTECT`, `objetivo_estrategico` `PROTECT`, `descricao`, `progresso`, `status`, `status_resultado`) — **sem** campo `peso` (Decisão #19)
- [ ] 4.2.2 Tela de cadastro de metas pelo colaborador (`CreateView`)
- [ ] 4.2.3 Tela de listagem de metas com filtro por status
- [ ] 4.2.4 Implementar retorno da meta reprovada para edição (RF-14.2): reverter apenas o `status` daquela meta específica para `pendente`, sem afetar as demais metas nem o campo `etapa` da `Avaliacao`
- [ ] 4.2.5 Implementar `status_resultado` e reabertura pontual (RF-14.3/RF-14.4), com bloqueio de edição de `progresso` fora da etapa `resultados` (RF-15.2)

**4.3 — Atualização de progresso**
- [ ] 4.3.1 Formulário HTMX para atualizar progresso sem reload de página
- [ ] 4.3.2 Validação de faixa de progresso (0–100%)

### ✅ Definição de Pronto
Colaborador cria meta vinculada a um objetivo estratégico; meta nasce `pendente`; reprovação reabre só aquela meta; progresso só é editável dentro da janela permitida; nenhum campo `peso` existe no model `Meta`.

---

## Sprint 5 — Ciclo de Avaliação (`cycles` + `reviews`)

### 🎯 Objetivo
O coração do sistema: ciclo de avaliação, máquina de estados por colaborador, autoavaliação vs. avaliação do líder, cálculo da nota final ponderada e feedback com ciência.

### Pré-requisitos
Sprints 3 e 4 concluídas (competências e metas existentes).

### Checklist

**5.1 — Ciclo**
- [ ] 5.1.1 Criar model `Ciclo` (`nome`, `data_inicio`, `data_fim`, `status`: aberto/encerrado — sem `etapa_atual`, a progressão é por usuário)
- [ ] 5.1.2 CRUD de ciclos restrito ao admin
- [ ] 5.1.3 Implementar encerramento de ciclo (RF-16.1): fechamento exclusivamente manual pelo administrador, bloqueando novos avanços de etapa
- [ ] 5.1.4 Implementar abertura de ciclo (RF-16.2): criar `Avaliacao` em lote para todos os usuários ativos; garantir que apenas um ciclo esteja aberto por vez

**5.2 — Máquina de estados das etapas**
- [ ] 5.2.1 Definir `choices` das etapas (`input de metas` → `aprovação de metas` → `resultados` → `aprovação de resultados` → `avaliação` → `feedback`) como campo `etapa` em `Avaliacao`
- [ ] 5.2.2 Criar serviço `avancar_etapa(avaliacao)` com validação de pré-condição
- [ ] 5.2.3 Bloquear avanço sem aprovação da etapa anterior
- [ ] 5.2.4 Implementar pré-condição agregada de `aprovação de metas` → `resultados`: ao menos 1 meta **e** 100% com `status=aprovada` (RF-17.1) — reprovação pontual nunca retrocede a `etapa`
- [ ] 5.2.5 Implementar pré-condição agregada de `aprovação de resultados` → `avaliação` sobre `status_resultado` (RF-17.2)

**5.3 — Avaliação**
- [ ] 5.3.1 Criar model `Avaliacao` (`ciclo`, `usuario`, `nota_final_lider`, `nota_final_autoavaliacao`, `etapa`)
- [ ] 5.3.2 Criar model `AvaliacaoCompetencia` (`avaliacao`, `competencia`, `nota_autoavaliacao`, `nota_lider`, `peso_utilizado`, `nivel_esperado_utilizado`)
- [ ] 5.3.2.1 Ao criar as linhas de `AvaliacaoCompetencia` (início da etapa "avaliação"), copiar `peso` e `nivel_esperado` vigentes de `CargoCompetencia` para os campos snapshot `peso_utilizado`/`nivel_esperado_utilizado` via serviço interno (write-once, nunca editável em formulário — RF-19.2)
- [ ] 5.3.3 Tela de autoavaliação (colaborador), preenchendo `nota_autoavaliacao`
- [ ] 5.3.4 Tela de avaliação do líder, preenchendo `nota_lider`, exibindo autoavaliação lado a lado e comparando com `nivel_esperado_utilizado` (não com `CargoCompetencia.nivel_esperado` atual)
- [ ] 5.3.5 Criar serviço `calcular_nota_final_lider(avaliacao)`: normalizar cada nota pela escala (`(nota - min) / (max - min)`) e calcular a média ponderada usando exclusivamente `peso_utilizado` — incluir guarda defensiva contra soma de pesos zero (RF-15.1/RF-19.3)
- [ ] 5.3.6 Bloquear avanço para a etapa "avaliação" se o cargo não tiver competências vinculadas ou se a soma de `peso` das `CargoCompetencia` for zero (RF-19.3)

**5.4 — Aprovações**
- [ ] 5.4.1 Tela de aprovação de metas (líder/gerente; admin quando o colaborador não tiver `line_manager` — RF-16.3)
- [ ] 5.4.2 Tela de aprovação de resultados (líder; mesma regra de fallback para admin)

**5.5 — Feedback**
- [ ] 5.5.1 Criar model `Feedback` (`avaliacao`, `autor`, `tipo`, `conteudo`, `ciente_em`)
- [ ] 5.5.2 Tela de registro de feedback (colaborador e líder)
- [ ] 5.5.3 Botão "dar ciência" que grava `ciente_em` no feedback recebido pelo colaborador

### ✅ Definição de Pronto
Um ciclo completo roda ponta a ponta para um colaborador de teste: metas → aprovação → resultados → aprovação de resultados → autoavaliação + avaliação do líder → nota final calculada corretamente (validar manualmente a fórmula com 2+ competências de escalas diferentes) → feedback registrado e "ciente" marcado. Encerramento manual do ciclo bloqueia novos avanços.

---

## Sprint 6 — PDI (`pdi`)

### 🎯 Objetivo
Plano de Desenvolvimento Individual, independente do ciclo estar aberto.

### Pré-requisitos
Sprint 1 concluída (usuário autenticado). Não depende do ciclo.

### Checklist

**6.1 — Modelo de PDI**
- [ ] 6.1.1 Criar model `PDI` (`usuario`, `titulo`, `status`)
- [ ] 6.1.2 Criar model `AcaoPDI` (`pdi`, `descricao`, `responsavel`, `prazo`, `status`: pendente/em andamento/concluída/atrasada)

**6.2 — Telas de PDI**
- [ ] 6.2.1 Tela de criação de PDI (`CreateView`)
- [ ] 6.2.2 Tela de listagem de ações com filtro por status (HTMX)
- [ ] 6.2.3 Atualização de status de ação inline via HTMX

**6.3 — Cálculo de progresso**
- [ ] 6.3.1 Método `progresso()` no model `PDI` (percentual de ações concluídas)
- [ ] 6.3.2 Exibir barra de progresso no dashboard do colaborador (placeholder até a Sprint 8)

### ✅ Definição de Pronto
Colaborador cria um PDI a qualquer momento (sem depender de ciclo aberto), adiciona ações com prazo, e o percentual de progresso reflete corretamente as ações concluídas.

---

## Sprint 6.5 — Carga de Dados e Legado Sólides

> ⚠️ **Pré-requisito bloqueante (Decisão #22):** antes de iniciar esta sprint, a documentação ou amostra real dos arquivos de exportação da Sólides (formato, colunas, encoding) deve ser anexada ao PRD. Isso **não impede** o andamento das Sprints 0–6, que podem seguir em paralelo/antes.

### 🎯 Objetivo
Importar a base histórica da Sólides (colaboradores, competências, avaliações, PDIs) preservando integridade referencial e regras de auditabilidade.

### Pré-requisitos
Sprints 0–6 concluídas + amostra/layout dos arquivos Sólides disponível.

### Checklist

**6.5.1 — Adaptação do Schema**
- [ ] Adicionar `solides_id = models.CharField(max_length=50, blank=True, null=True, unique=True, db_index=True)` nos models: `CustomUser`, `Cargo`, `Competencia`, `Avaliacao` e `PDI`
- [ ] Gerar e aplicar as migrações (`makemigrations` e `migrate`)

**6.5.2 — Comando: Importação de Colaboradores**
- [ ] Criar o script `importar_colaboradores.py` na app `accounts`
- [ ] Validar a criação de Cargos, Áreas e Usuários (tratando `is_active=False` para demitidos)
- [ ] Preencher `email_confirmado_em` automaticamente com o timestamp da importação — sem exigir confirmação por link (Decisão #21)
- [ ] Executar o mapeamento da hierarquia (`line_manager`) cruzando com o arquivo de avaliações

**6.5.3 — Comando: Importação de Competências por Cargo**
- [ ] Criar o script `importar_competencias_cargo.py` na app `competencies`
- [ ] Mapear as habilidades obrigatórias de cada cargo no banco para uso em futuros ciclos

**6.5.4 — Comando: Importação de Avaliações (Cabeçalho)**
- [ ] Criar o script `importar_avaliacoes.py` na app `reviews`
- [ ] Implementar o tratamento de dados para corrigir o bug de formatação de data (Ano 5810) nos IDs da Sólides

**6.5.5 — Comando: Importação de Notas e Comentários**
- [ ] Criar o script `importar_notas.py` na app `reviews`
- [ ] Implementar a separação: se `Avaliador == Avaliado` salva em `nota_autoavaliacao`, senão em `nota_lider`
- [ ] Popular `peso_utilizado`/`nivel_esperado_utilizado` com os valores vigentes na Sólides no momento da importação (snapshot write-once, nunca dependente do `CargoCompetencia` atual)
- [ ] Criar o script `importar_comentarios.py` na app `reviews` para salvar feedbacks qualitativos
- [ ] Rodar o recálculo automático da média ponderada final com base em `AvaliacaoCompetencia.peso_utilizado` (não em `CargoCompetencia.peso` atual)

**6.5.6 — Comando: Importação de PDIs**
- [ ] Criar o script `importar_pdi.py` na app `pdi`
- [ ] Tratar de-para de status e aplicar marcação de `"atrasada"` caso o prazo da Sólides já tenha vencido

**6.5.7 — Homologação e Auditoria Visual**
- [ ] Acessar o Django Admin e conferir a consistência dos dados carregados
- [ ] Validar integridade das chaves estrangeiras (nenhum órfão, nenhum `solides_id` duplicado)

### ✅ Definição de Pronto
Todos os scripts rodam de forma idempotente contra uma amostra dos dados Sólides sem erros; contagens de registros importados batem com a origem; nenhuma avaliação importada quebra o cálculo de `nota_final_lider`.

---

## Sprint 7 — Talentos (`talent`)

### 🎯 Objetivo
Classificação 9-box (desempenho × potencial) por ciclo, com visibilidade controlada pelo admin.

### Pré-requisitos
Sprint 5 concluída (precisa de `nota_final_lider` calculada).

### Checklist

**7.1 — Classificação 9-box**
- [ ] 7.1.1 Criar model `ClassificacaoTalento` (`usuario` `PROTECT`, `ciclo` `PROTECT`, `desempenho` 1–3, `potencial` 1–3, `quadrante` calculado, `visivel_ao_colaborador`)
- [ ] 7.1.2 Criar serviço que deriva `desempenho` a partir da `nota_final_lider` normalizada (`< 0,33 → 1`, `0,33–0,66 → 2`, `> 0,66 → 3`) e calcula `quadrante` conforme a tabela fixa do RF-24
- [ ] 7.1.3 Tela de classificação restrita ao admin (matriz visual 3x3), com `potencial` inserido manualmente

**7.2 — Controle de visibilidade**
- [ ] 7.2.1 Garantir, na view/queryset, que o colaborador só veja o próprio registro se `visivel_ao_colaborador=True`
- [ ] 7.2.2 Botão de liberar/ocultar visibilidade (admin)

### ✅ Definição de Pronto
Admin classifica um colaborador na matriz 9-box para um ciclo específico; `desempenho` é derivado automaticamente e `quadrante` nunca é editável manualmente; colaborador não vê a própria classificação até o admin liberar.

---

## Sprint 8 — Dashboards e Aderência (`dashboard`)

### 🎯 Objetivo
Painéis por perfil de usuário (colaborador/líder/gerente/admin) e o índice de aderência da liderança, calculado de forma assíncrona e persistido.

### Pré-requisitos
Sprints 5, 6 e 7 concluídas.

### Checklist

**8.1 — Cálculo de aderência**
- [ ] 8.1.1 Definir componentes do índice (aprovações no prazo, feedbacks dados, ações de PDI concluídas); atribuir cada ação ao **autor real** registrado, nunca ao `line_manager` atual (RF-26)
- [ ] 8.1.2 Criar model `AderenciaSnapshot` (`lider`, `ciclo`, `percentual`, `componentes` em JSON, `calculado_em`)
- [ ] 8.1.3 Criar task Celery `calcular_aderencia(lider_id, ciclo_id)` que persiste o resultado em `AderenciaSnapshot`
- [ ] 8.1.4 Dashboards leem sempre o último `AderenciaSnapshot`, nunca recalculam no request síncrono

**8.2 — Dashboard do colaborador**
- [ ] 8.2.1 Cartões: minhas metas (resumo), meu PDI (progresso), últimos feedbacks

**8.3 — Dashboard do líder**
- [ ] 8.3.1 Cartão de pendências (metas/resultados aguardando aprovação)
- [ ] 8.3.2 Cartão de aderência própria

**8.4 — Dashboard do gerente**
- [ ] 8.4.1 Listagem de líderes da estrutura com respectivo índice de aderência
- [ ] 8.4.2 Filtro por área/cargo

**8.5 — Dashboard do admin**
- [ ] 8.5.1 Panorama geral: nº de ciclos ativos, % de PDIs ativos, % de conclusão de ciclo

### ✅ Definição de Pronto
Cada perfil (colaborador/líder/gerente/admin) acessa seu dashboard e vê apenas dados do seu escopo; a task Celery de aderência roda e grava snapshot; dashboards não recalculam nada pesado em tempo de request.

---

## Sprint 9 — Notificações (`notifications`)

### 🎯 Objetivo
Lembretes assíncronos por e-mail e marcação automática de atraso, via Celery Beat.

### Pré-requisitos
Sprints 5 e 6 concluídas (etapas de ciclo e ações de PDI existentes).

### Checklist

**9.1 — Tasks Celery**
- [ ] 9.1.1 Task `enviar_lembrete_prazo_etapa`
- [ ] 9.1.2 Task `enviar_lembrete_acao_pdi_vencendo`
- [ ] 9.1.3 Task `marcar_atrasados` — percorre ações de PDI e etapas vencidas e atualiza `status='atrasada'` (RF-32.1)

**9.2 — Agendamento**
- [ ] 9.2.1 Configurar Celery Beat para rodar as tasks diariamente
- [ ] 9.2.2 Definir janela de antecedência do lembrete (ex.: 3 dias antes do prazo)

**9.3 — Templates de e-mail**
- [ ] 9.3.1 Template de e-mail de lembrete de etapa
- [ ] 9.3.2 Template de e-mail de lembrete de ação de PDI

**9.4 — Log de notificações**
- [ ] 9.4.1 Criar model `NotificacaoLog` (`destinatario`, `tipo`, `status`: enviado/falha, `erro`, `created_at`)
- [ ] 9.4.2 Registrar em `NotificacaoLog` toda tentativa de envio de e-mail (sucesso ou falha)
- [ ] 9.4.3 Tela de consulta de falhas de notificação, restrita ao admin

### ✅ Definição de Pronto
Celery Beat dispara diariamente; e-mails de lembrete chegam (console em dev) para ações/etapas dentro da janela configurada; ações/etapas vencidas viram `atrasada` automaticamente; toda tentativa de envio fica registrada em `NotificacaoLog`.

---

## Sprint 10 — Auditoria (`audit`)

### 🎯 Objetivo
Log de auditoria append-only para alterações sensíveis e tentativas de acesso negado por escopo.

### Pré-requisitos
Sprints 2, 5 e 7 concluídas (pontos de origem dos eventos auditáveis).

### Checklist

**10.1 — Modelo de log**
- [ ] 10.1.1 Criar model `AuditLog` (`usuario` nullable, `acao`, `entity_type`, `entity_id`, `campo`, `valor_anterior`, `valor_novo`, `created_at`)

**10.2 — Captura via signals**
- [ ] 10.2.1 Criar `signals.py` no app `audit` (ou nos apps de origem, disparando para `audit`)
- [ ] 10.2.2 Conectar sinal `pre_save`/`post_save` em `Avaliacao`, `ClassificacaoTalento` e mudanças de `is_admin`/`is_active`/área/`line_manager` do usuário
- [ ] 10.2.3 Registrar em `AuditLog` tentativas de acesso negado pelo `ScopedObjectMixin` **somente quando o registro existe mas está fora do escopo** (RF-36) — IDs inexistentes retornam 404 genérico sem log
- [ ] 10.2.4 Voltar às Sprints 2.4.5/2.4.6 (desativação/reatribuição de usuário) e conectar ao `AuditLog` real, removendo o stub/TODO deixado antes

**10.3 — Imutabilidade**
- [ ] 10.3.1 Bloquear change/delete de `AuditLog` no Django Admin (`has_change_permission`/`has_delete_permission` retornando `False`)
- [ ] 10.3.2 Garantir que a criação do log seja feita apenas via signal/serviço interno, nunca por formulário exposto ao usuário

**10.4 — Tela de consulta**
- [ ] 10.4.1 Tela de auditoria restrita ao admin, com filtro por usuário, ação e período

### ✅ Definição de Pronto
Alterar nota de avaliação, classificação 9-box, ou campos sensíveis de usuário gera uma linha por campo alterado no `AuditLog`; tentar editar/excluir um log pelo admin nativo falha; acessar URL de registro fora do escopo gera log (registro existente) ou não gera log (ID inexistente); tela de consulta filtra corretamente.

---

## Sprint 11 — Refino de UI e Responsividade

### 🎯 Objetivo
Consistência visual e usabilidade mobile em todo o sistema, após todos os módulos funcionais estarem prontos.

### Pré-requisitos
Sprints 1–10 concluídas (todas as telas já existem para serem revisadas).

### Checklist

**11.1 — Revisão do design system**
- [ ] 11.1.1 Auditar todas as telas quanto à consistência de cores, espaçamento e componentes
- [ ] 11.1.2 Ajustar breakpoints Tailwind para mobile em todas as listagens

**11.2 — Componentização**
- [ ] 11.2.1 Extrair badges de status (PDI, aderência) para `components/badge_status.html`
- [ ] 11.2.2 Extrair tabelas padrão para `components/table.html`

**11.3 — Acessibilidade básica**
- [ ] 11.3.1 Checar contraste de cores nos estados de erro/sucesso
- [ ] 11.3.2 Adicionar `label` e `aria-*` básicos nos formulários

### ✅ Definição de Pronto
Todas as telas principais funcionam bem em viewport mobile; componentes repetidos (badges, tabelas) estão extraídos e reutilizados; formulários têm labels e atributos de acessibilidade básicos.

---

## Sprint 12 — Preparação para PostgreSQL

### 🎯 Objetivo
Garantir migração tranquila de SQLite para PostgreSQL, sem alteração de modelo.

### Pré-requisitos
Sprints 1–10 concluídas (schema estabilizado).

### Checklist

**12.1 — Compatibilidade**
- [ ] 12.1.1 Revisar uso de campos/queries específicas de SQLite
- [ ] 12.1.2 Adicionar driver `psycopg` como dependência opcional

**12.2 — Configuração**
- [ ] 12.2.1 Criar `settings/prod.py` com configuração de banco via variável de ambiente
- [ ] 12.2.2 Testar migrations completas contra uma instância PostgreSQL local

### ✅ Definição de Pronto
`python manage.py migrate` roda sem erros contra uma instância PostgreSQL local limpa, usando o mesmo conjunto de migrations gerado para SQLite.

---

## Sprint 13 — Docker

### 🎯 Objetivo
Containerizar a aplicação e seus serviços de apoio (banco, Redis, worker, beat).

### Pré-requisitos
Sprint 12 concluída (PostgreSQL configurado).

### Checklist

**13.1 — Containerização**
- [ ] 13.1.1 Criar `Dockerfile` da aplicação Django
- [ ] 13.1.2 Criar `docker-compose.yml` com serviços: app, PostgreSQL, Redis, worker Celery, Celery Beat

**13.2 — Ajustes de ambiente**
- [ ] 13.2.1 Externalizar variáveis de ambiente via `.env`
- [ ] 13.2.2 Configurar `collectstatic` no build da imagem

### ✅ Definição de Pronto
`docker-compose up` sobe todos os serviços e a aplicação fica acessível, com Celery worker/beat funcionando dentro dos containers.

---

## Sprint 14 — Testes Automatizados

### 🎯 Objetivo
Cobertura de testes nos pontos críticos de regra de negócio e segurança antes de considerar a v1 encerrada.

### Pré-requisitos
Sprints 1–10 concluídas.

### Checklist

**14.1 — Configuração**
- [ ] 14.1.1 Configurar `pytest-django` (ou `TestCase` nativo) no projeto

**14.2 — Cobertura por app**
- [ ] 14.2.1 Testes de autenticação (login por e-mail, cadastro, bloqueio por e-mail não confirmado, domínio inválido)
- [ ] 14.2.2 Testes de resolução de escopo (`organization/services.py`), incluindo tentativa de um usuário acessar diretamente a URL de registro (PDI, avaliação, feedback, 9-box) de outro usuário/gestor fora do seu escopo, esperando 404/403
- [ ] 14.2.3 Testes da máquina de estados do ciclo de avaliação (incluindo os edge cases: zero metas, reprovação pontual, soma de pesos zero)
- [ ] 14.2.4 Testes de visibilidade da classificação 9-box
- [ ] 14.2.5 Testes das tasks Celery de notificação

### ✅ Definição de Pronto
Suíte de testes roda em CI/local (`pytest` ou `manage.py test`) cobrindo os 5 itens acima, todos verdes.

---

## Notas transversais (válidas para todas as sprints)

- **Escopo de dados:** toda `ListView` filtra pelo escopo do usuário (nunca só esconder botão no template); toda `DetailView`/`UpdateView`/`DeleteView` usa `ScopedObjectMixin`.
- **Paginação:** `paginate_by = 20` em toda `ListView` desde a primeira tela criada.
- **Idioma:** código-fonte (nomes de variáveis, funções, classes) em inglês; toda a interface visível ao usuário em português.
- **Signals:** concentrar em `signals.py` por app.
- **Models:** sempre herdar de `TimeStampedModel` (criado na Sprint 0.2.1).
- **on_delete:** seguir estritamente a tabela de políticas da seção 9.3 do PRD (`PROTECT` para FKs organizacionais/histórico, `SET_NULL` apenas em `User.line_manager`).
- **Antes de cada sprint:** reler as RFs e Decisões referenciadas na seção correspondente do `PRD_Greenn_People.md` para não perder um edge case já mapeado na seção 16.
