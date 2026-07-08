# Padrões de Código

Convenções e requisitos não-funcionais do projeto.

## Idioma

| Contexto | Idioma |
|---|---|
| Código-fonte | Inglês |
| Interface do usuário | Português brasileiro |

## Estilo de código

| Regra | Detalhe |
|---|---|
| Padrão | PEP 8 |
| Aspas | Simples (`'`) |
| Views | Class-Based Views sempre que possível |
| Linter | ruff/flake8 com regras PEP 8 |
| Signals | Concentrados em `signals.py` por app |
| Models | `created_at`/`updated_at` padronizados via mixin `TimeStampedModel` |

## Segurança

### Listagens

Toda `ListView`/consulta agregada filtra o queryset pelo escopo do usuário (ver [architecture.md](architecture.md)), nunca confiando apenas em esconder botões/links na interface.

### Objetos individuais

Toda `DetailView`/`UpdateView`/`DeleteView` valida, no `get_object()`, se o registro acessado pertence ao escopo do usuário logado — mesmo que o ID venha direto na URL (proteção contra IDOR). Acesso fora do escopo retorna 404/403, nunca vaza dado.

### Infraestrutura

- CSRF, proteção de sessão e cabeçalhos de segurança padrão do Django habilitados.
- Senhas com hash nativo (PBKDF2).
- Validadores padrão do Django (`AUTH_PASSWORD_VALIDATORS`):
  - `UserAttributeSimilarityValidator`
  - `MinimumLengthValidator` com `min_length=8`
  - `CommonPasswordValidator`
  - `NumericPasswordValidator`

## Paginação

`paginate_by = 20` itens por página como padrão em todas as `ListView`.

## Sessão

- `SESSION_COOKIE_AGE` padrão do Django (2 semanas / 1.209.600 segundos).
- Sessão persiste ao fechar o navegador (sem `SESSION_EXPIRE_AT_BROWSER_CLOSE`).

## Performance

| Regra | Detalhe |
|---|---|
| Páginas comuns | < 2s |
| Tarefas pesadas | Processadas via Celery, fora do ciclo de request |
| Índices | Em campos usados para escopo e filtro (`line_manager`, `area`, `ciclo`, `usuario`) |
| Queries | `select_related`/`prefetch_related` nas queries de listagem e dashboard |
| Paginação | Obrigatória em toda listagem |
| Cálculos pesados | Aderência e agregações de dashboard via Celery, não no request síncrono |

## Auditabilidade

- Log de auditoria é **append-only** (sem edição/exclusão, inclusive no admin do Django).
- Cada alteração de dado sensível gera **uma linha por campo** (`campo`, valor anterior, valor novo, autor nullable, timestamp).
- Tentativas de acesso negado por escopo são registradas **somente quando o registro existe no banco mas está fora do escopo** do usuário.

## Histórico

- Cada ciclo gera registros próprios de avaliação vinculados ao colaborador, preservando a evolução completa entre ciclos (nunca sobrescrevendo dado de ciclo anterior).
- PDI mantém histórico de mudança de status de cada ação.

## Banco de dados

- SQLite em desenvolvimento.
- Estrutura pronta para migração para PostgreSQL sem alterações de modelo.
- Usar apenas ORM padrão do Django — evitar recursos específicos de SQLite.

## Assíncrono

- Redis como broker/result backend do Celery.
- Celery Beat para tarefas agendadas (verificação diária de prazos).

## Manutenibilidade

- Apps pequenas e isoladas por domínio de negócio.
- Sem camadas desnecessárias; usar recursos nativos do Django sempre que possível.
