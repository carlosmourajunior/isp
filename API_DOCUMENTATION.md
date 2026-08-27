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

### 8. Informações do sistema OLT
```
GET /api/olt/system-info/
Authorization: Bearer <access_token>
```

**Resposta:**
```json
{
    "id": 1,
    "isam_release": "R6.2.03",
    "uptime_days": 958,
    "uptime_hours": 12,
    "uptime_minutes": 26,
    "uptime_seconds": 47,
    "uptime_raw": "System Up Time         : 958 days, 12:26:47.46 (hr:min:sec)",
    "total_uptime_hours": 23004,
    "last_updated": "2025-09-30T16:30:00Z"
}
```

### 9. Listar slots da OLT
```
GET /api/olt/slots/
Authorization: Bearer <access_token>
```

**Parâmetros de filtro:**
- `enabled`: Filtrar por slots habilitados (true/false)
- `availability`: Filtrar por disponibilidade
- `actual_type`: Filtrar por tipo

### 10. Listar temperaturas da OLT
```
GET /api/olt/temperatures/
Authorization: Bearer <access_token>
```

**Parâmetros de filtro:**
- `slot_name`: Filtrar por slot específico

### 11. Estatísticas completas do sistema OLT
```
GET /api/olt/system-stats/
Authorization: Bearer <access_token>
```

**Resposta:**
```json
{
    "system_info": {
        "isam_release": "R6.2.03",
        "uptime_days": 958,
        "total_uptime_hours": 23004
    },
    "slots_stats": {
        "total_slots": 9,
        "operational_slots": 4,
        "offline_slots": 5,
        "operational_percentage": 44.44,
        "slots_by_type": [
            {"actual_type": "fglt-b", "count": 2},
            {"actual_type": "ngfc-f", "count": 1}
        ]
    },
    "temperature_stats": {
        "critical_temperatures": 1,
        "warning_temperatures": 2,
        "normal_temperatures": 14,
        "average_temperature": 54.2,
        "max_temperature": 75,
        "min_temperature": 31,
        "temperature_by_slot": [
            {
                "slot_name": "nt-a",
                "avg_temp": 42.0,
                "max_temp": 52,
                "sensor_count": 3
            }
        ]
    }
}
```

### 12. Alertas de temperatura
```
GET /api/olt/temperature-alerts/
Authorization: Bearer <access_token>
```

### 13. Atualizar dados do sistema OLT
```
POST /api/olt/update-system-data/
Authorization: Bearer <access_token>
```

**Resposta:**
```json
{
    "message": "Dados do sistema OLT atualizados com sucesso",
    "system_info": {...},
    "slots_count": 9,
    "temperatures_count": 17
}
```

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
curl -X POST http://177.22.126.77:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "password"}'

# 2. Usar o token para acessar dados
curl -X GET http://177.22.126.77:8000/api/onus/ \
  -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."

# 3. Filtrar ONUs online
curl -X GET "http://177.22.126.77:8000/api/onus/?oper_state=up" \
  -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."

# 4. Obter informações do sistema OLT
curl -X GET http://177.22.126.77:8000/api/olt/system-info/ \
  -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."

# 5. Obter estatísticas completas da OLT
curl -X GET http://177.22.126.77:8000/api/olt/system-stats/ \
  -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."

# 6. Atualizar dados do sistema OLT
curl -X POST http://177.22.126.77:8000/api/olt/update-system-data/ \
  -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
```

### Exemplo de uso com Python requests

```python
import requests

# 1. Obter token
login_url = "http://177.22.126.77:8000/api/auth/login/"
login_data = {"username": "admin", "password": "password"}
response = requests.post(login_url, json=login_data)
tokens = response.json()
access_token = tokens['access']

# 2. Configurar headers com token
headers = {"Authorization": f"Bearer {access_token}"}

# 3. Buscar ONUs
onus_url = "http://177.22.126.77:8000/api/onus/"
onus_response = requests.get(onus_url, headers=headers)
onus_data = onus_response.json()

print(f"Total de ONUs: {onus_data['count']}")
for onu in onus_data['results']:
    print(f"ONU {onu['serial']}: {onu['oper_state']}")

# 4. Obter informações do sistema OLT
system_url = "http://177.22.126.77:8000/api/olt/system-info/"
system_response = requests.get(system_url, headers=headers)
system_data = system_response.json()

print(f"Versão OLT: {system_data['isam_release']}")
print(f"Uptime: {system_data['uptime_days']} dias")

# 5. Obter estatísticas completas da OLT
stats_url = "http://177.22.126.77:8000/api/olt/system-stats/"
stats_response = requests.get(stats_url, headers=headers)
stats_data = stats_response.json()

print(f"Slots operacionais: {stats_data['slots_stats']['operational_slots']}")
print(f"Temperatura média: {stats_data['temperature_stats']['average_temperature']}°C")

# 6. Atualizar dados do sistema OLT
update_url = "http://177.22.126.77:8000/api/olt/update-system-data/"
update_response = requests.post(update_url, headers=headers)
update_data = update_response.json()

print(f"Atualização: {update_data['message']}")
```