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

## HTTPS (domínio próprio)
O serviço `proxy` (Caddy) fica na frente de tudo e emite/renova o certificado sozinho.
Um domínio só: `https://<domínio>/api/...` vai para o Django, o resto para o frontend.

1. DNS: registro **A** do domínio (ex.: `rede.exemplo.com.br`) apontando para o IP do servidor.
   Portas **80** e **443** abertas no firewall/roteador (a 80 é usada na emissão do certificado).
2. `.env` do servidor:
   ```
   DOMAIN=rede.exemplo.com.br
   COMPOSE_PROFILES=prod,https
   HTTPS_ATIVO=true
   CSRF_TRUSTED_ORIGINS=https://rede.exemplo.com.br
   FRONTEND_URL=https://rede.exemplo.com.br
   API_PUBLIC_URL=https://rede.exemplo.com.br
   ```
3. GitHub → Variables: `VITE_API_URL=https://rede.exemplo.com.br/api` e rode o build de novo
   (Actions → build-push → Run workflow), para o frontend chamar a API pelo https.
4. `docker compose up -d` (sobe o `proxy`). Acompanhe a emissão: `docker compose logs -f proxy`.
5. Teste: `https://rede.exemplo.com.br/api/health/` e `https://rede.exemplo.com.br/api/docs/`.
6. Quando os parceiros já estiverem usando o https, feche o acesso direto:
   `WEB_PORT=127.0.0.1:8000` e `FRONTEND_PORT=127.0.0.1:3000` no `.env` e `docker compose up -d`.

## Documentação da API
- Pública (para parceiros): `/api/docs/` (Swagger, dá para testar com o token), `/api/redoc/`
  (leitura) e `/api/schema/` (arquivo OpenAPI, para importar no Postman/Insomnia).
  Só mostra os endpoints de `olt/api_parceiros_urls.py`.
- Interna (todos os endpoints): `/api/docs/interno/`, para admin logado em `/admin/`.
