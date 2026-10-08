# Deploy automático (GHCR + Watchtower)

Merge na `master` → GitHub Actions publica `isp-web` e `isp-frontend` no GHCR →
Watchtower no servidor puxa a imagem nova e recria `web`, `rq_worker` e `frontend`
(o `entrypoint.sh` roda `migrate` na subida do `web`).

## Configuração única no GitHub
- Settings → Secrets and variables → Actions → **Variables**: `VITE_API_URL`
  (URL pública da API, ex. `https://isp.exemplo.com/api`). Vai embutida no build do frontend.
- Os pacotes `isp-web` e `isp-frontend` nascem privados, vinculados ao repo.

## Configuração única no servidor
1. Token (PAT classic) com escopo `read:packages` e login:
   `echo $TOKEN | docker login ghcr.io -u carlosmourajunior --password-stdin`
   (grava em `~/.docker/config.json`, que o Watchtower monta para puxar imagens privadas).
2. No `.env` do servidor, para ignorar o `docker-compose.override.yml` (que é só de dev):
   `COMPOSE_FILE=docker-compose.yml`
3. `docker compose --profile prod up -d`
   (o profile `prod` liga o Watchtower; em dev ele não sobe).

## Dev local
`docker compose up -d --build` continua buildando do código e montando o repo em `/code`.

## Observações
- Rollback: `IMAGE_TAG=<sha> docker compose --profile prod up -d`, e pare o Watchtower
  antes, senão ele volta para `latest`.
- Em produção o código vem da imagem; já não há bind mount de `.:/code`.
