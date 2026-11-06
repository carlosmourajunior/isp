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
   Primeira vez, teste com o certificado de staging (não conta no limite do Let's Encrypt;
   o navegador vai avisar que não é confiável, é esperado): `ACME_CA=https://acme-staging-v02.api.letsencrypt.org/directory`.
   Quando `docker compose logs proxy` mostrar o certificado emitido, apague essa linha,
   `docker compose up -d --force-recreate proxy` e confira o cadeado. Deixe `HSTS_MAX_AGE`
   no padrão (300) até validar tudo; depois use `HSTS_MAX_AGE=31536000`.
3. GitHub → Variables: `VITE_API_URL=https://rede.exemplo.com.br/api` e rode o build de novo
   (Actions → build-push → Run workflow), para o frontend chamar a API pelo https.
4. `docker compose up -d` (sobe o `proxy`). Acompanhe a emissão: `docker compose logs -f proxy`.
5. Teste: `https://rede.exemplo.com.br/api/health/` e `https://rede.exemplo.com.br/api/docs/`.
6. Quando os parceiros já estiverem usando o https, feche o acesso direto:
   `WEB_PORT=127.0.0.1:8000` e `FRONTEND_PORT=127.0.0.1:3000` no `.env` e `docker compose up -d`.

## Monitoramento e alertas (Telegram)

Três peças, todas mandando para o mesmo chat do Telegram:

| O quê | Avisa quando | Onde |
|---|---|---|
| **CrowdSec** (no host) | varredura, força bruta no SSH ou no login, tentativa de explorar falha conhecida. **Bloqueia o IP por 4h** no firewall, inclusive nas portas do Docker | `deploy/seguranca/` |
| **Django** | 5 falhas de login do mesmo IP em 10 min, login de admin, IP fora da lista insistindo (POST ou 30 requisições em 10 min) | `isp/alertas.py` |
| **Watchtower** | uma imagem nova foi aplicada em produção | `docker-compose.yml` |

### 1. Bot do Telegram
1. No Telegram, fale com o **@BotFather** → `/newbot` → guarde o **token**.
2. Crie um grupo (ex.: "Alertas servidores"), adicione o bot e mande qualquer mensagem no grupo.
3. Descubra o id do grupo (número negativo):
   `curl -s "https://api.telegram.org/bot<TOKEN>/getUpdates" | grep -o '"chat":{"id":-[0-9]*'`

### 2. Django e watchtower
No `.env` do servidor:
```
TELEGRAM_BOT_TOKEN=<token>
TELEGRAM_CHAT_ID=<id do grupo>
ALERTA_ORIGEM=olt
WATCHTOWER_NOTIFICATION_URL=telegram://<token>@telegram?chats=<id do grupo>
```
Depois: `docker compose up -d` (recria web e watchtower com as variáveis novas).

### 3. CrowdSec (no host, uma vez por servidor)
```
cd /root/isp
TELEGRAM_BOT_TOKEN=<token> TELEGRAM_CHAT_ID=<id> ALERTA_ORIGEM=olt \
CROWDSEC_WHITELIST="177.22.126.0/24,<seu IP>,<IPs dos parceiros>" \
bash deploy/seguranca/instalar-crowdsec.sh
```
- **Lista branca:** ponha seus IPs e os dos parceiros, para nunca serem bloqueados.
- **Console (opcional, um painel para todos os servidores):** crie conta em app.crowdsec.net,
  copie a chave de "enroll" e rode o script com `CROWDSEC_ENROLL_KEY=<chave>`. Aceite o servidor no console.
- O mesmo script serve para os outros servidores (lê o SSH; o Caddy só se existir).

Comandos do dia a dia:
```
cscli decisions list            # IPs bloqueados agora
cscli alerts list               # o que foi detectado
cscli decisions delete -i 1.2.3.4   # desbloquear um IP
cscli metrics                   # o que está sendo lido
```

## Documentação da API
- Pública (para parceiros): `/api/docs/` (Swagger, dá para testar com o token), `/api/redoc/`
  (leitura) e `/api/schema/` (arquivo OpenAPI, para importar no Postman/Insomnia).
  Só mostra os endpoints de `olt/api_parceiros_urls.py`.
- Interna (todos os endpoints): `/api/docs/interno/`, para admin logado em `/admin/`.
