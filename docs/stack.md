# Stack Tecnológica

Stack definida para o Greenn People (v1).

## Camadas

| Camada | Tecnologia | Observação |
|---|---|---|
| Backend/Framework | Django 5.x | Full stack, sem DRF na v1. |
| Frontend | Django Template Language (DTL) + HTMX + Tailwind CSS | Interatividade sem SPA; toda lógica de permissão no servidor. |
| Build do Tailwind | Tailwind CLI standalone (binário, sem depender de Node.js) | Mantém o setup simples, um único comando de watch/build. |
| Banco de dados | SQLite (v1) → PostgreSQL (planejado) | Sem uso de recursos exclusivos de um banco, para migração tranquila. |
| Fila/Assíncrono | Celery + Redis | E-mails de lembrete e cálculo de aderência em background. |
| Agendamento | Celery Beat | Verificação periódica de prazos (diária). |
| Autenticação | Sistema nativo do Django, com `AbstractUser` customizado (`USERNAME_FIELD = 'email'`) | Sem django-allauth/MFA. |
| Hierarquia organizacional | Auto-relacionamento simples (self FK) em vez de biblioteca de árvore | Suficiente para a profundidade esperada (colaborador → líder → gerente). |
| Auditoria | Model próprio `AuditLog` (app `audit`), populado via signals | Sem biblioteca externa de versionamento. |
| E-mail | Backend de e-mail nativo do Django (console em dev, SMTP em produção) | Sem provedor transacional externo na v1. |
| Containerização | Docker/Docker Compose | Planejado apenas para as sprints finais. |
| Testes | Django TestCase / pytest-django | Planejado apenas para as sprints finais. |

## Princípios da stack

- **Simplicidade:** usar recursos nativos do Django sempre que possível.
- **Sem SPA:** frontend via templates Django + HTMX.
- **Assíncrono fora do request:** tarefas pesadas (e-mails, cálculo de aderência) via Celery.
- **Migração de banco:** estrutura pronta para PostgreSQL sem alterações de modelo.
