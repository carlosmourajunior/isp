"""
IP real do cliente.

O cabeçalho X-Forwarded-For pode ser enviado por qualquer um. Só vale quando a
requisição veio de um proxy nosso (o Caddy do HTTPS, na rede do Docker) - senão,
qualquer pessoa na internet passaria pelo filtro de IPs mandando
"X-Forwarded-For: 127.0.0.1" direto na porta 8000.

Proxies confiáveis: TRUSTED_PROXIES no .env (IPs/CIDRs separados por vírgula).
Padrão: localhost e a faixa de redes do Docker (172.16.0.0/12).
"""
import ipaddress
import os

_PADRAO = '127.0.0.1,::1,172.16.0.0/12'


def _redes():
    redes = []
    for item in os.getenv('TRUSTED_PROXIES', _PADRAO).split(','):
        item = item.strip()
        if not item:
            continue
        try:
            redes.append(ipaddress.ip_network(item, strict=False))
        except ValueError:
            continue
    return redes


def _confiavel(ip, redes):
    try:
        endereco = ipaddress.ip_address(ip)
    except ValueError:
        return False
    return any(endereco in rede for rede in redes)


def ip_do_cliente(request):
    remoto = (request.META.get('REMOTE_ADDR') or '').strip()
    redes = _redes()
    if not remoto or not _confiavel(remoto, redes):
        return remoto
    # Veio do nosso proxy: o cliente é o IP mais à direita que não é proxy nosso
    # (os da esquerda o próprio cliente pode ter inventado).
    encaminhados = [i.strip() for i in (request.META.get('HTTP_X_FORWARDED_FOR') or '').split(',') if i.strip()]
    for ip in reversed(encaminhados):
        if not _confiavel(ip, redes):
            return ip
    real = (request.META.get('HTTP_X_REAL_IP') or '').strip()
    if real:
        return real
    return encaminhados[0] if encaminhados else remoto
