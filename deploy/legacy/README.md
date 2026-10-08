# Arquivo morto

Conteúdo movido para cá em 2026-08-27 durante a limpeza (Fase 0 do plano de modernização), sem deletar nada — histórico completo continua no `git log`. Nada aqui é usado pela aplicação em produção; se algo daqui for necessário de volta, é só mover para a raiz de novo.

## Por que cada coisa está aqui

- **`olt_connector_django_project_morto/`** — segundo projeto Django completo (settings/urls/wsgi/asgi) que sobrou de uma versão anterior do sistema. `manage.py` e o `docker-compose.yml` atual apontam para `isp.settings`/`isp.urls`, não para este. Tinha até `SECRET_KEY` hardcoded no próprio arquivo.
- **`docker-compose.monitoring.yml`** — versão antiga e completa da stack (app + Prometheus + Grafana + Alertmanager + exporters) de antes da consolidação em `docker-compose.yml`. Expunha porta do Postgres e do Redis diretamente, sem senha.
- **`docker-compose.security.yml`** e **`docker-compose.security.yml.new`** — camadas de hardening (senha via env var, remoção de portas expostas, healthchecks) que já foram incorporadas diretamente no `docker-compose.yml` atual. Ficaram redundantes.
- **`docker-compose.simple.yml`** — variante mínima alternativa da stack, sem uso identificado.
- **`docker-compose.firewall.yml`** — overlay que fechava as portas do Prometheus/Grafana/exporters. Perdeu o sentido porque esses serviços foram removidos do `docker-compose.yml` (a equipe não usa a stack de observabilidade — decisão de 2026-08-27).
- **`configure_firewall.sh`**, **`deploy_secure.sh`**, **`start_secure.sh`** — scripts de resposta a incidente/deploy que giravam em torno de proteger ou expor as portas do Grafana (3000) e Prometheus (9090), removidos pelo mesmo motivo.
- **`prometheus_views.py`**, **`alert_views.py`** — views Django que expunham `/api/metrics/` e `/api/alerts/*` (Prometheus client + integração com Alertmanager). Reintroduzidas por engano num merge com o `origin/master` em 2026-08-27 (a origin tinha 71 commits que incluíam essa stack, criada antes da decisão de não usá-la); removidas de novo no mesmo dia, junto com a dependência `prometheus-client` do `requirements.txt` e o `PrometheusMiddleware` do `MIDDLEWARE`.
- **`monitoring/`** — configs do Prometheus, Grafana (dashboards/provisioning) e Alertmanager que vieram junto no mesmo merge. Mesmo motivo.

Movidos em 2026-08-31 (limpeza geral de scripts soltos na raiz):

- **`security_scan.sh`**, **`quick_security_check.sh`**, **`malware_cleanup.sh`** — resposta ao incidente de malware Kinsing (mineração de cripto via Docker/Postgres exposto) de maio/2026. Detecção, checagem rápida e limpeza; `malware_cleanup.sh` só deve rodar se malware for detectado de novo, não é rotina.
- **`investigate_system.sh`**, **`investigate_data_loss.py`** — investigação de uma perda completa de dados no PostgreSQL, mesmo período. `backup_scripts/` (que ficou ativo) é plausivelmente resultado direto desse incidente.
- **`fix_system.ps1`**, **`fix_system.sh`** — scripts genéricos de "reiniciar tudo" da mesma época; hoje o equivalente é `make restart`/`make rebuild`.
- **`monitor_connections.py`** — monitor standalone de conexões do PostgreSQL, escrito durante a investigação de perda de dados; hoje esse tipo de coisa fica no log `db_connections.log` (logger `django.db` em `isp/settings.py`).
- **`manage_ips.ps1`**, **`manage_ips_realtime.ps1`**, **`sync_settings_ips.ps1`** — versões PowerShell (Windows) de gestão de IP permitido, redundantes com `add_ip.py` (que ficou ativo, usa o model `AllowedIP` direto) e com `olt/startup.py::import_settings_ips()`, que já importa os IPs do settings automaticamente no boot da aplicação.
- **`init_app.sh`** — copiado pra imagem no `Dockerfile` mas nunca executado (o `ENTRYPOINT` só roda `entrypoint.sh`, que já faz migração/coleta de estático/setup de usuário sozinho). Código morto; removida também a linha `COPY`/`chmod` correspondente no `Dockerfile`.

## O que continua ativo

- `docker-compose.yml` (base) + `docker-compose.override.debug.yml` (overlay de debug local, uso explícito com `-f`).
- `add_ip.py` — CLI pra adicionar IP permitido (`docker-compose exec web python add_ip.py IP "descrição"`).
- `backup_scripts/` — backup/restore do Postgres com compressão e guia de crontab; mais completo que o `make backup` do Makefile.
- `quick_deploy.sh`, `test_secure_config.sh` — scripts de deploy/verificação ainda em uso, sem overlay de security/firewall (esses foram removidos, ver acima).
