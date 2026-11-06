#!/usr/bin/env bash
# Instala e configura o CrowdSec no HOST (não em container), com:
#  - leitura do log do Caddy (container *-proxy-*) e do SSH (journald ou auth.log);
#  - bloqueio no firewall, inclusive na chain DOCKER-USER (o UFW não filtra portas
#    publicadas pelo Docker; o bouncer filtra);
#  - alerta no Telegram a cada IP bloqueado;
#  - lista branca dos seus IPs, para nunca se trancar fora.
#
# Serve para qualquer servidor (olt, Debian...): rode em cada um.
# Uso (como root):
#   TELEGRAM_BOT_TOKEN=123:abc TELEGRAM_CHAT_ID=-100123 \
#   CROWDSEC_WHITELIST="177.22.126.0/24,177.22.124.74" \
#   [CROWDSEC_ENROLL_KEY=chave-do-console] [ALERTA_ORIGEM=olt] \
#   bash deploy/seguranca/instalar-crowdsec.sh
# Pode rodar de novo para mudar token, chat ou lista branca.
set -euo pipefail

: "${TELEGRAM_BOT_TOKEN:?defina TELEGRAM_BOT_TOKEN}"
: "${TELEGRAM_CHAT_ID:?defina TELEGRAM_CHAT_ID}"
: "${CROWDSEC_WHITELIST:?defina CROWDSEC_WHITELIST (seus IPs/redes, separados por vírgula)}"
ORIGEM="${ALERTA_ORIGEM:-$(hostname)}"
AQUI="$(cd "$(dirname "$0")" && pwd)"

[ "$(id -u)" = 0 ] || { echo "Rode como root."; exit 1; }

echo "==> Pacotes"
if ! command -v cscli >/dev/null; then
  apt-get update -qq
  apt-get install -y -qq curl gnupg
  curl -fsSL https://install.crowdsec.net | sh
  apt-get install -y -qq crowdsec
fi
dpkg -s crowdsec-firewall-bouncer-iptables >/dev/null 2>&1 || apt-get install -y -qq crowdsec-firewall-bouncer-iptables

echo "==> Coleções (Linux, SSH, Caddy, varreduras HTTP e CVEs conhecidas)"
cscli collections install crowdsecurity/linux crowdsecurity/sshd crowdsecurity/caddy \
  crowdsecurity/base-http-scenarios crowdsecurity/http-cve --error

echo "==> Fontes de log"
mkdir -p /etc/crowdsec/acquis.d
cp "$AQUI/crowdsec/acquis-caddy-docker.yaml" /etc/crowdsec/acquis.d/caddy-docker.yaml
if [ -f /var/log/auth.log ]; then
  rm -f /etc/crowdsec/acquis.d/ssh-journal.yaml   # o acquis.yaml padrão já lê o auth.log
else
  cp "$AQUI/crowdsec/acquis-ssh-journal.yaml" /etc/crowdsec/acquis.d/ssh-journal.yaml
fi

echo "==> Lista branca"
{
  echo "name: local/whitelist-proprios"
  echo "description: IPs do administrador e da rede própria - nunca bloquear"
  echo "whitelist:"
  echo "  reason: ips proprios"
  echo "  ip:"
  echo "    - 127.0.0.1"
  echo "    - ::1"
  echo "  cidr:"
  echo "    - 172.16.0.0/12"
  IFS=',' read -ra ITENS <<< "$CROWDSEC_WHITELIST"
  for i in "${ITENS[@]}"; do
    i="$(echo "$i" | xargs)"; [ -z "$i" ] && continue
    case "$i" in */*) echo "    - $i";; *) echo "    - $i/32";; esac
  done
} > /etc/crowdsec/parsers/s02-enrich/whitelist-proprios.yaml

echo "==> Telegram"
python3 - "$AQUI/crowdsec/telegram.yaml" "$TELEGRAM_BOT_TOKEN" "$TELEGRAM_CHAT_ID" "$ORIGEM" \
  > /etc/crowdsec/notifications/telegram.yaml <<'PY'
import sys
modelo, token, chat, origem = sys.argv[1:5]
t = open(modelo).read()
print(t.replace('__TOKEN__', token).replace('__CHAT__', chat).replace('__ORIGEM__', origem), end='')
PY
chmod 600 /etc/crowdsec/notifications/telegram.yaml
cp "$AQUI/crowdsec/profiles.yaml" /etc/crowdsec/profiles.yaml

echo "==> Bouncer: bloquear também na chain DOCKER-USER"
B=/etc/crowdsec/bouncers/crowdsec-firewall-bouncer.yaml
sed -i -E 's/^#\s*-\s*DOCKER-USER/  - DOCKER-USER/' "$B"
grep -q 'DOCKER-USER' "$B" || sed -i -E 's/^(iptables_chains:)$/\1\n  - DOCKER-USER/' "$B"

if [ -n "${CROWDSEC_ENROLL_KEY:-}" ]; then
  echo "==> Console do CrowdSec"
  cscli console enroll -e context "$CROWDSEC_ENROLL_KEY" --name "$ORIGEM" --overwrite || true
fi

systemctl restart crowdsec
systemctl restart crowdsec-firewall-bouncer
systemctl enable -q crowdsec crowdsec-firewall-bouncer

echo "==> Teste do Telegram"
cscli notifications test telegram || echo "!! O teste falhou: confira token e chat id."

echo
cscli metrics show acquisition 2>/dev/null | head -20 || true
echo "Pronto. Ver bloqueios: cscli decisions list | Alertas: cscli alerts list"
