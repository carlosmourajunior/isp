# API Documentation - Sistema OLT/ONT

Esta API permite acesso aos dados das ONTs (Optical Network Terminals) com autenticação JWT.

## Autenticação

### Obter Token JWT
```
POST /api/auth/login/
Content-Type: application/json

{
    "username": "seu_usuario",
    "password": "sua_senha"
}
```

**Resposta:**
```json
{
    "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "user_info": {
        "username": "seu_usuario",
        "message": "Login realizado com sucesso"
    }
}
```

### Renovar Token
```
POST /api/auth/refresh/
Content-Type: application/json

{
    "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

## Endpoints da API

### 1. Listar ONUs
```
GET /api/onus/
Authorization: Bearer <access_token>
```

**Parâmetros de filtro:**
- `oper_state`: Filtrar por status operacional (up/down)
- `admin_state`: Filtrar por status administrativo
- `cliente_fibra`: Filtrar por clientes fibra (true/false)
- `search`: Buscar por serial, MAC, descrição ou PON
- `ordering`: Ordenar por campo (position, olt_rx_sig, pon)
- `page`: Número da página (paginação)

**Exemplo:**
```
GET /api/onus/?oper_state=up&cliente_fibra=true&search=FHTT&page=1
```

### 2. Detalhes de uma ONU
```
GET /api/onus/{id}/
Authorization: Bearer <access_token>
```

### 3. Estatísticas das ONUs
```
GET /api/onus/stats/
Authorization: Bearer <access_token>
```

**Resposta:**
```json
{
    "total_onus": 150,
    "onus_online": 142,
    "onus_offline": 8,
    "clientes_fibra": 98,
    "onus_sinal_baixo": 5,
    "estatisticas_por_slot": {
        "slot_1": {
            "total": 75,
            "online": 71,
            "offline": 4
        },
        "slot_2": {
            "total": 75,
            "online": 71,
            "offline": 4
        }
    },
    "percentual_online": 94.67
}
```

### 4. ONUs por PON específica
```
GET /api/onus/pon/{pon}/
Authorization: Bearer <access_token>
```

**Exemplo:**
```
GET /api/onus/pon/gpon-olt_1%2F1%2F1%2F1/
```

### 5. Busca avançada de ONUs
```
GET /api/onus/search/?q={termo_busca}
Authorization: Bearer <access_token>
```

### 6. Listar informações das portas OLT
```
GET /api/olt-users/
Authorization: Bearer <access_token>
```

**Parâmetros de filtro:**
- `slot`: Filtrar por slot específico
- `ordering`: Ordenar por campo

### 7. Listar clientes fibra
```
GET /api/clientes-fibra/
Authorization: Bearer <access_token>
```

**Parâmetros de filtro:**
- `search`: Buscar por nome, MAC ou endereço

## Códigos de Resposta

- **200 OK**: Sucesso
- **400 Bad Request**: Parâmetros inválidos
- **401 Unauthorized**: Token JWT inválido ou ausente
- **404 Not Found**: Recurso não encontrado
- **500 Internal Server Error**: Erro interno do servidor

## Formato dos Dados

### ONU
```json
{
    "id": 1,
    "pon": "gpon-olt_1/1/1/1",
    "slot": "1",
    "port": "1",
    "position": 1,
    "mac": "48575443:12345678",
    "serial": "FHTT12345678",
    "oper_state": "up",
    "admin_state": "up",
    "olt_rx_sig": -18.5,
    "ont_olt": "1500",
    "desc1": "Cliente Nome",
    "desc2": "Informações adicionais",
    "cliente_fibra": true
}
```

### Exemplo de uso com curl

```bash
# 1. Obter token
curl -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "password"}'

# 2. Usar o token para acessar dados
curl -X GET http://localhost:8000/api/onus/ \
  -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."

# 3. Filtrar ONUs online
curl -X GET "http://localhost:8000/api/onus/?oper_state=up" \
  -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
```

### Exemplo de uso com Python requests

```python
import requests

# 1. Obter token
login_url = "http://localhost:8000/api/auth/login/"
login_data = {"username": "admin", "password": "password"}
response = requests.post(login_url, json=login_data)
tokens = response.json()
access_token = tokens['access']

# 2. Configurar headers com token
headers = {"Authorization": f"Bearer {access_token}"}

# 3. Buscar ONUs
onus_url = "http://localhost:8000/api/onus/"
onus_response = requests.get(onus_url, headers=headers)
onus_data = onus_response.json()

print(f"Total de ONUs: {onus_data['count']}")
for onu in onus_data['results']:
    print(f"ONU {onu['serial']}: {onu['oper_state']}")
```