# Arquivo morto

Conteúdo movido para cá em 2026-08-27 durante a limpeza (Fase 0 do plano de modernização), sem deletar nada — histórico completo continua no `git log`. Nada aqui é usado pela aplicação em produção; se algo daqui for necessário de volta, é só mover para a raiz de novo.

## Por que cada coisa está aqui

- **`olt_connector_django_project_morto/`** — segundo projeto Django completo (settings/urls/wsgi/asgi) que sobrou de uma versão anterior do sistema. `manage.py` e o `docker-compose.yml` atual apontam para `isp.settings`/`isp.urls`, não para este. Tinha até `SECRET_KEY` hardcoded no próprio arquivo.
- **`docker-compose.monitoring.yml`** — versão antiga e completa da stack (app + Prometheus + Grafana + Alertmanager + exporters) de antes da consolidação em `docker-compose.yml`. Expunha porta do Postgres e do Redis diretamente, sem senha.
- **`docker-compose.security.yml`** e **`docker-compose.security.yml.new`** — camadas de hardening (senha via env var, remoção de portas expostas, healthchecks) que já foram incorporadas diretamente no `docker-compose.yml` atual. Ficaram redundantes.
- **`docker-compose.simple.yml`** — variante mínima alternativa da stack, sem uso identificado.
- **`docker-compose.firewall.yml`** — overlay que fechava as portas do Prometheus/Grafana/exporters. Perdeu o sentido porque esses serviços foram removidos do `docker-compose.yml` (a equipe não usa a stack de observabilidade — decisão de 2026-08-27).
- **`configure_firewall.sh`**, **`deploy_secure.sh`**, **`start_secure.sh`** — scripts de resposta a incidente/deploy que giravam em torno de proteger ou expor as portas do Grafana (3000) e Prometheus (9090), removidos pelo mesmo motivo.

## O que continua ativo

`docker-compose.yml` (base) + `docker-compose.override.debug.yml` (overlay de debug local, uso explícito com `-f`).
