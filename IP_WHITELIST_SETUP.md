# Configuração de Segurança - IP Whitelist

Este documento explica como a configuração de IP whitelist funciona no sistema e como ajustá-la.

## Visão Geral

O sistema agora possui um middleware de segurança que restringe o acesso apenas aos IPs autorizados. Isso protege tanto a aplicação web quanto a API REST.

## Arquivos Modificados

### 1. `isp/middleware.py`
Middleware customizado que:
- Intercepta todas as requisições HTTP
- Extrai o IP real do cliente (considerando proxies/load balancers)
- Verifica se o IP está na lista de IPs permitidos
- Bloqueia acesso se o IP não estiver autorizado

### 2. `isp/settings.py`
Configurações adicionadas:
- **ALLOWED_HOSTS**: Inclui `177.22.126.77` (IP do servidor)
- **ALLOWED_IPS**: Lista de IPs/ranges permitidos
- **MIDDLEWARE**: Inclui o `IPWhitelistMiddleware` como primeiro middleware

### 3. `.env`
Variáveis de ambiente para Docker:
- Configurações do Django
- Configurações do banco de dados PostgreSQL
- Configurações do Redis

## Configuração Atual de IPs Permitidos

```python
ALLOWED_IPS = [
    '127.0.0.1',        # Localhost
    '::1',              # Localhost IPv6
    '177.22.126.77',    # Servidor
    '172.16.0.0/12',    # Redes Docker privadas
    '192.168.0.0/16',   # Redes privadas locais
    '10.0.0.0/8',       # Redes privadas
]
```

## Como Adicionar Novos IPs

### Para IPs Individuais:
```python
ALLOWED_IPS = [
    # ... IPs existentes ...
    '203.0.113.45',     # Novo IP autorizado
]
```

### Para Ranges de IP (CIDR):
```python
ALLOWED_IPs = [
    # ... IPs existentes ...
    '203.0.113.0/24',   # Toda a rede 203.0.113.0 - 203.0.113.255
    '198.51.100.0/28',  # Rede menor: 198.51.100.0 - 198.51.100.15
]
```

## Executando com Docker

1. **Construir e iniciar os containers:**
```bash
docker-compose up --build
```

2. **Para executar em modo debug:**
```bash
docker-compose -f docker-compose.yml -f docker-compose.override.debug.yml up --build
```

3. **Verificar logs do middleware:**
```bash
docker-compose logs web
```

## Testando a Configuração

Execute o script de teste:
```bash
docker-compose exec web python test_ip_whitelist.py
```

## Headers HTTP Suportados

O middleware verifica os seguintes headers para detectar o IP real (útil com proxies):
- `X-Forwarded-For`
- `X-Real-IP`
- `X-Forwarded`
- `X-Cluster-Client-IP`
- `Forwarded-For`
- `Forwarded`

## Segurança Adicional

### Para Ambiente de Produção:
1. **Remover redes privadas amplas** da lista se não necessário
2. **Usar ranges específicos** em vez de redes muito amplas
3. **Configurar DEBUG=False** no arquivo `.env`
4. **Usar HTTPS** com certificados válidos
5. **Considerar rate limiting** adicional

### Exemplo de Configuração Mais Restritiva:
```python
ALLOWED_IPS = [
    '177.22.126.77',     # Apenas o servidor
    '203.0.113.10',      # IP específico do escritório
    '198.51.100.0/28',   # Range específico da empresa
]
```

## Troubleshooting

### Se você for bloqueado:
1. Verifique o IP atual: `curl ifconfig.me`
2. Adicione o IP à lista `ALLOWED_IPS`
3. Reinicie o container: `docker-compose restart web`

### Para desabilitar temporariamente:
Comente o middleware no `settings.py`:
```python
MIDDLEWARE = [
    # 'isp.middleware.IPWhitelistMiddleware',  # Comentado
    'django.middleware.security.SecurityMiddleware',
    # ... outros middlewares ...
]
```

### Logs úteis:
```bash
# Ver logs em tempo real
docker-compose logs -f web

# Ver logs específicos do middleware
docker-compose logs web | grep -i "IP"
```

## API Endpoints Protegidos

Todos os endpoints da API são protegidos pelo middleware:
- `/api/` - API REST
- `/admin/` - Django Admin
- Todas as views da aplicação

A proteção é aplicada **antes** de qualquer autenticação ou autorização do Django.