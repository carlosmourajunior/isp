# AGENTS.md — Sistema ISP (Gestão de OLT/Fibra)

Guia de referência para agentes de IA (e humanos) trabalhando neste repositório.

## Regra obrigatória: mudanças na API

**Qualquer alteração na API (endpoints em `olt/api_urls.py`, views em `olt/api_views.py`,
serializers, ou qualquer mudança de contrato — request/response, status code, campo
novo/removido, autenticação, permissões) exige aprovação prévia do usuário antes de ser
implementada.**

Antes de tocar em qualquer código de API, o agente deve:
1. Descrever claramente o que vai mudar: endpoint(s) afetado(s), comportamento atual vs.
   novo, impacto no contrato (o frontend ou outros consumidores quebram?), e por quê.
2. Esperar a aprovação explícita do usuário.
3. Só então implementar.

Isso vale mesmo quando a mudança parece pequena ou for um "efeito colateral" de outra
tarefa (ex.: corrigir um bug em `olt/utils.py` que muda o formato de um campo retornado
por um endpoint). Na dúvida se algo conta como "mudança na API", tratar como se contasse e
descrever antes de agir.

## O que é este projeto

Sistema de gestão de rede de fibra óptica (ISP) para monitorar e operar OLTs Nokia/Alcatel
(via SSH/netmiko), cruzar dados com clientes cadastrados no ERP IXC, e expor tudo isso via
API para um frontend React. Cobre: ONUs conectadas, ocupação de portas, temperatura/SFP de
slots, alertas de sinal, disparo de sincronizações (RQ background jobs) e cadastro multi-OLT.

## Stack

- **Backend**: Django 4.x + Django REST Framework (não é FastAPI — sem async/Pydantic;
  ORM, migrations e admin vêm do próprio Django).
- **Auth**: JWT via `djangorestframework-simplejwt` (access 60 min, refresh 7 dias, rotação
  com blacklist).
- **Banco**: PostgreSQL 13.
- **Fila/cache**: Redis + `django-rq` (RQ) para jobs assíncronos que tocam a OLT via SSH
  (operações lentas/bloqueantes não podem rodar na request-response).
- **Scheduler**: APScheduler embutido (`olt/scheduler.py`) — hoje com o job automático
  horário **desabilitado por segurança**; disparos são manuais via API/frontend.
- **SSH para OLT**: `netmiko` (device_type `alcatel_aos`, definido por OLT cadastrada).
- **Frontend**: React 19 + Vite + TypeScript, TanStack Query + TanStack Table, Tailwind 4,
  React Router 7, axios com interceptor de refresh de JWT.
- **Infra**: Docker Compose (5 serviços: `db`, `redis`, `web`, `rq_worker`, `frontend`),
  gunicorn servindo o Django, Nginx servindo o build estático do React.

## Como subir o projeto

Pré-requisito: Docker Desktop rodando.

```bash
# primeira vez / configuração completa
make dev-setup        # build + start + migrate + createsuperuser + health check

# uso normal
make start             # docker compose up -d + health check
make stop              # docker compose down
make restart           # stop + start
make status            # docker compose ps
make logs              # logs de tudo, follow
make log               # logs só do container web
make sh                # shell dentro do container web
make manage ARGS="..." # atalho pra manage.py (ex: make manage ARGS="showmigrations")
make migrate
make test              # manage.py test dentro do container web
```

Sem `make`, equivalente direto:
```bash
docker compose up -d
docker compose exec web python manage.py migrate
docker compose exec web python manage.py test
```

URLs depois de subir:
- Frontend: http://localhost:3000
- API: http://localhost:8000/api/
- Admin Django: http://localhost:8000/admin/
- Health check: http://localhost:8000/api/health/

O container `web` roda [entrypoint.sh](entrypoint.sh), que **na subida** espera
db/redis ficarem disponíveis, roda `migrate`, `collectstatic` e garante um superuser
(`admin` / `admin123` se nenhum existir — **trocar em produção**). Isso só acontece
quando o comando do container é `gunicorn` ou `runserver` (não roda no `rq_worker`).

Variáveis de ambiente: copiar `.env.example` para `.env` e preencher. Pontos que exigem
atenção real (não são só placeholder de dev):
- `OLT_CREDENTIALS_KEY`: chave Fernet que criptografa a senha SSH das OLTs salvas no banco
  (model `Olt.password`, ver [olt/fields.py](olt/fields.py)). Gerar com
  `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`.
  **Nunca trocar depois de ter OLTs cadastradas** sem re-cadastrar as senhas.
- `REDIS_PASSWORD` / `REDIS_URL`: precisam bater entre si — `REDIS_URL` embute a senha.
- `IXC_HOST` / `IXC_TOKEN`: credenciais do ERP IXC usadas em
  [olt/client_utils.py](olt/client_utils.py) para trazer nome/endereço real do cliente.
- `VITE_API_URL`: build arg do frontend — mudar exige rebuild da imagem `frontend`
  (`make frontend-build`), não só restart.

## Arquitetura / fluxo de uma requisição

```
Frontend (axios, JWT no header Authorization: Bearer)
   → isp/urls.py → olt/api_urls.py → view (olt/api_views.py)
       → decorators de segurança (quando aplicável)
       → serializer (olt/serializers.py) ↔ model (olt/models.py) ↔ Postgres
   ← Response JSON
```

Duas famílias de endpoint em `olt/api_views.py`:
1. **Leitura simples** (maioria): `generics.ListAPIView`/`RetrieveAPIView` do DRF ou
   `@api_view` function-based, só consultam o Postgres (dados já coletados antes).
2. **Ações que tocam a OLT ao vivo** ou disparam trabalho pesado: não fazem o trabalho na
   própria request — chamam `.delay()` de uma task RQ (`olt/tasks.py`) e devolvem
   `202 Accepted` com `job_id`; o `rq_worker` (container separado, mesma imagem, comando
   `manage.py rqworker default`) consome a fila Redis e executa (`olt/utils.py`:
   `olt_connector`/`OltSystemCollector`, que abrem sessão SSH via netmiko na OLT).

Endpoint `update_olt_system_data` é a exceção que acessa a OLT **de forma síncrona** dentro
da request — por isso tem os decorators `@frontend_only` + `@olt_admin_required`
([olt/security.py](olt/security.py)) empilhados: só aceita IP interno/Docker e usuário
staff/superuser.

## Camadas de segurança (em ordem de execução, via MIDDLEWARE em isp/settings.py)

1. `CorsMiddleware` — origens permitidas vêm de `FRONTEND_URL`.
2. `IPWhitelistMiddleware` ([isp/middleware.py](isp/middleware.py)) — bloqueia por IP/CIDR
   fora da lista (`ALLOWED_IPS` em settings + tabela `AllowedIp` no banco).
3. `OltSecurityMiddleware` ([olt/security.py](olt/security.py)) — regras específicas de
   acesso a endpoints que tocam a OLT.
4. `MonitoringMiddleware` / `MetricsCollectionMiddleware` — logging de acesso/performance
   (`logs/api_access.log`, `logs/performance.log`).

Em cima disso, por endpoint: `IsAuthenticated` (padrão global do DRF), e quando necessário
`@frontend_only` (só IP interno) e/ou `@olt_admin_required` (staff/superuser).

Senha de OLT no banco é sempre criptografada em repouso (`EncryptedCharField`), nunca texto
puro — mesmo em dump/backup do Postgres.

## Padrões usados e por quê

- **Django + DRF, não FastAPI**: o projeto precisa de admin pronto, ORM com migrations
  versionadas, e integração nativa com fila (django-rq) — tudo isso é "bateria inclusa" no
  Django. FastAPI exigiria montar cada peça (ORM, migrations, admin) à parte.
- **Fila RQ/Redis para tudo que toca SSH na OLT**: operações via netmiko podem levar minutos
  (`read_timeout=600` em alguns pontos); rodar isso na thread da request travaria o
  worker do gunicorn. O padrão é: view dispara `.delay()`, devolve `job_id`, frontend faz
  polling em `tasks/` para acompanhar progresso (`job.meta` guarda `current_step`).
  Ver `_enqueue_task()` em [olt/api_views.py](olt/api_views.py) — se a task é "por OLT"
  (`olt_scoped=True`) e nenhuma `olt_id` vier no request, ela enfileira um job por OLT
  ativa, para já funcionar com N OLTs sem o frontend precisar escolher uma.
- **Multi-OLT via model `Olt`**: adicionado recentemente (migrations 0017-0019). Antes só
  existia uma OLT fixa via variáveis de ambiente (`NOKIA_*`, ainda no `.env.example` por
  compat com código legado em `olt/views.py`/`olt/admin.py`). `vendor`/`device_type` no
  model são o ponto de extensão para outros fabricantes além de Nokia/Alcatel.
  `get_default_olt()` (primeira OLT ativa) é o fallback para esse código legado.
  `Olt.slot_count` substitui qualquer número fixo de slots hardcoded.
- **Decorators de segurança em vez de permission_classes genéricas**: `@frontend_only` e
  `@olt_admin_required` existem porque só uma fração dos endpoints acessa a OLT
  diretamente — a maioria só lê o Postgres. Empilhar decorators nesses poucos endpoints
  evita restringir o resto da API por engano.
- **Scheduler automático desabilitado de propósito**: `olt/scheduler.py` mantém o código
  do cron horário, mas comentado — decisão de segurança para não bater na OLT
  automaticamente sem controle. Disparo hoje é manual (via API/frontend, endpoints
  `tasks/trigger-*`).
- **Frontend não fala com a OLT nem com o IXC diretamente**: sempre via API Django, que é
  quem guarda credenciais (criptografadas/env) e aplica os decorators de segurança acima.

## Testes

```bash
make test
# ou
docker compose exec web python manage.py test
docker compose exec web python manage.py test olt.tests.test_api_contract
```

Arquivos em [olt/tests/](olt/tests/):
- `test_api_contract.py` — contrato dos endpoints DRF (status codes, shape de resposta).
- `test_internal_api.py` — endpoints internos/restritos (frontend_only, olt_admin_required).
- `test_olt_crud.py` — CRUD do model `Olt` (multi-OLT).
- `test_parsers.py` — parsing de saída bruta de comandos SSH da OLT (regex em
  [olt/utils.py](olt/utils.py)).
- `test_ixc_client.py` — integração com IXC.
- `test_models.py` — models em geral.

Frontend não tem suite de testes configurada ainda (só `oxlint` para lint):
```bash
cd frontend && npm run lint
cd frontend && npm run build   # tsc -b && vite build — também serve como type-check
```

## Convenções de código observadas (seguir ao editar)

- Comentários no código são em português, curtos, e só explicam o *porquê* de decisões não
  óbvias (ex.: por que um fallback existe, por que um limite é "de sanidade" e não regra de
  negócio real). Não documentar o óbvio.
- Migrations novas devem ser geradas com `make makemigrations` (nunca editar migration já
  commitada) e revisadas antes de aplicar em produção — o projeto já teve uma migration de
  backfill dedicada (`0018_backfill_olt.py`) para popular dados ao migrar de "OLT única via
  .env" para "multi-OLT via tabela".
- Rotas da API ficam centralizadas em [olt/api_urls.py](olt/api_urls.py) com `app_name =
  'api'` — usar `name=` ao adicionar endpoint novo, seguindo o padrão dos existentes.
- Campos ordenáveis/filtráveis do DRF (`ordering_fields`, `filterset_fields`) devem ficar
  sincronizados entre as views que expõem o mesmo conjunto de colunas (ver comentário em
  `ONU_ORDERING_FIELDS` em [olt/api_views.py](olt/api_views.py) — reutilizado por 4 views
  de ONU diferentes).
- Não commitar `.env` (já está fora do controle de versão) nem logar/expor senha de OLT ou
  tokens do IXC/RQ em texto puro.

## Documentação complementar já existente no repo

- [API_DOCUMENTATION.md](API_DOCUMENTATION.md) / [API_README.md](API_README.md) — contrato
  detalhado dos endpoints.
- [OLT_SECURITY_DOCUMENTATION.md](OLT_SECURITY_DOCUMENTATION.md) — detalhes dos decorators
  e regras de acesso à OLT.
- [IP_WHITELIST_SETUP.md](IP_WHITELIST_SETUP.md) — configuração do `IPWhitelistMiddleware`.
- [backup_scripts/README.md](backup_scripts/README.md) — backup/restore do Postgres.

## Problema conhecido (não corrigido ainda)

`/api/health/detailed/` reporta Redis como "unhealthy" mesmo quando o Redis está saudável:
o check em [olt/health_views.py](olt/health_views.py) (`check_redis()`, e também
`get_system_metrics`) conecta em `redis://redis:6379/0` **sem senha**, ignorando
`REDIS_URL`/`REDIS_PASSWORD` usados pelo resto do sistema (RQ funciona normalmente, só o
health check está com a URL errada). Corrigir usando `settings.RQ_QUEUES['default']['URL']`
em vez da URL hardcoded.
