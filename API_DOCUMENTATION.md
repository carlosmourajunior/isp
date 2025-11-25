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

**Parâmetros de filtro:**
- `oper_state`: Filtrar por status operacional (up/down)
- `admin_state`: Filtrar por status administrativo
- `cliente_fibra`: Filtrar por clientes fibra (true/false)
- `page`: Número da página (paginação - 50 ONUs por página)

**Formatos de PON reconhecidos:**
- Formato simples: `1/1/1/1`, `1/1/2/9`, `1/1/1/14`
- Formato GPON: `gpon-olt_1/1/1/1`
- Formato com slot/port: `slot_1/port_2`

**Exemplos:**
```
GET /api/onus/pon/1%2F1%2F1%2F1/
GET /api/onus/pon/1%2F1%2F1%2F1/?oper_state=up
GET /api/onus/pon/1%2F1%2F1%2F1/?cliente_fibra=true&page=2
GET /api/onus/pon/gpon-olt_1%2F1%2F1%2F1/
```

**Resposta:**
```json
{
    "count": 78,
    "next": "http://localhost:8000/api/onus/pon/1/1/1/1/?page=2",
    "previous": null,
    "results": {
        "pon": "1/1/1/1",
        "total_onus": 78,
        "results": [
            {
                "id": 11416,
                "pon": "1/1/1/1",
                "slot": "1",
                "port": "1",
                "position": 1,
                "mac": "24:2f:d0:bb:f8:1d",
                "serial": "OPTI:35029212",
                "oper_state": "up",
                "admin_state": "up",
                "olt_rx_sig": -19.8,
                "ont_olt": "1.1",
                "desc1": "douglas2ponto",
                "desc2": "douglas2ponto",
                "cliente_fibra": true,
                "cliente_info": {
                    "id": 1239,
                    "nome": "douglas2ponto",
                    "endereco": "Rua Exemplo, 123"
                }
            }
        ]
    }
}

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

### 13. Listar alarmes da OLT
```
GET /api/olt/alarms/
Authorization: Bearer <access_token>
```

**Parâmetros de filtro:**
- `severity`: Filtrar por severidade (major, critical, minor, warning, normal, cleared)
- `entity`: Filtrar por entidade específica
- `description`: Buscar na descrição do alarme
- `active_only`: Mostrar apenas alarmes ativos (true/false)
- `date_from`: Filtrar alarmes a partir de uma data (YYYY-MM-DD)
- `date_to`: Filtrar alarmes até uma data (YYYY-MM-DD)
- `ordering`: Ordenar por campo (-timestamp, severity, entity)
- `page`: Número da página (paginação)

**Exemplo:**
```
GET /api/olt/alarms/?severity=major&active_only=true&ordering=-timestamp
```

**Resposta:**
```json
{
    "count": 25,
    "next": "http://localhost:8000/api/olt/alarms/?page=2",
    "previous": null,
    "results": [
        {
            "id": 123,
            "entity": "[72/09/26 17:26:56] major alarm cleared for RCMG:19896C04 (cliente_nome)",
            "description": "PON 1/1/2/7/8 (service affecting) : Received optical signal too low",
            "severity": "major",
            "timestamp": "2025-11-10T22:06:40.123456Z",
            "is_active": false,
            "raw_alarm": "[72/09/26 17:26:56] major alarm cleared for ONU RCMG:19896C04 (cliente_nome) - PON 1/1/2/7/8 (service affecting) : Received optical signal too low"
        }
    ]
}
```

### 14. Estatísticas dos alarmes
```
GET /api/olt/alarms/stats/
Authorization: Bearer <access_token>
```

**Resposta:**
```json
{
    "total_alarms": 150,
    "active_alarms": 12,
    "by_severity": {
        "major": 8,
        "critical": 2,
        "minor": 25,
        "warning": 35,
        "normal": 45,
        "cleared": 35
    },
    "recent_alarms": 5,
    "trend": "stable"
}
```

### 15. Coletar novos alarmes da OLT
```
POST /api/olt/alarms/collect/
Authorization: Bearer <access_token>
```

**Resposta:**
```json
{
    "message": "Coleta de alarmes iniciada com sucesso",
    "job_id": "abc123",
    "status": "queued"
}
```

### 16. Atualizar dados do sistema OLT
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

### OLT Alarm
```json
{
    "id": 123,
    "entity": "[72/09/26 17:26:56] major alarm cleared for RCMG:19896C04 (cliente_nome)",
    "description": "PON 1/1/2/7/8 (service affecting) : Received optical signal too low",
    "severity": "major",
    "timestamp": "2025-11-10T22:06:40.123456Z",
    "is_active": false,
    "raw_alarm": "[72/09/26 17:26:56] major alarm cleared for ONU RCMG:19896C04 (cliente_nome) - PON 1/1/2/7/8 (service affecting) : Received optical signal too low"
}
```

**Campos de Alarme:**
- `id`: Identificador único do alarme
- `entity`: Entidade do alarme (formato: `[timestamp] severity alarm action for ONU serial (client)`)
- `description`: Descrição detalhada do alarme (tudo após o hífen no alarme bruto)
- `severity`: Severidade do alarme (major, critical, minor, warning, normal, cleared)
- `timestamp`: Data e hora da coleta do alarme (ISO 8601)
- `is_active`: Indica se o alarme está ativo (baseado na severidade)
- `raw_alarm`: Texto original completo do alarme como retornado pela OLT

**Severidades de Alarme:**
- `critical`: Alarme crítico que requer ação imediata
- `major`: Alarme importante que afeta o serviço
- `minor`: Alarme menor que não afeta significativamente o serviço
- `warning`: Aviso que pode indicar um problema futuro
- `normal`: Estado normal do sistema
- `cleared`: Alarme que foi resolvido/limpo

## Formatos Reconhecidos

### Formatos de PON
O sistema reconhece diversos formatos de identificação de PON:

**Formatos Suportados:**
- **Formato Básico**: `1/1/1/1`, `1/1/2/9`, `1/1/1/14`
- **Formato GPON**: `gpon-olt_1/1/1/1`
- **Formato Slot/Port**: `slot_1/port_2`
- **Formato Personalizado**: Qualquer string que identifique unicamente uma PON

**Codificação de URL:**
Como as PONs contêm barras (`/`), elas devem ser codificadas para uso em URLs:

```
PON Original    →  URL Encoded
1/1/1/1         →  1%2F1%2F1%2F1
1/1/2/16        →  1%2F1%2F2%2F16
gpon-olt_1/1/1/1 → gpon-olt_1%2F1%2F1%2F1
```

**Dica**: Use `urllib.parse.quote(pon, safe='')` em Python ou `encodeURIComponent()` em JavaScript para codificar PONs automaticamente.

### Formatos de Serial ONU
- **Alcatel/Nokia**: `ALCL:FBCBE83B`
- **Realtek**: `RCMG:3A980FCF`
- **Optical Networks**: `OPTI:35029212`
- **TP-Link**: `TPLG:12345678`
- **Fiberhome**: `FHTT:87654321`

### Exemplo de uso com curl

```bash
# 1. Obter token
curl -X POST http://177.22.126.78:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "password"}'

# 2. Usar o token para acessar dados
curl -X GET http://177.22.126.78:8000/api/onus/ \
  -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."

# 3. Filtrar ONUs online
curl -X GET "http://177.22.126.78:8000/api/onus/?oper_state=up" \
  -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."

# 4. Obter informações do sistema OLT
curl -X GET http://177.22.126.78:8000/api/olt/system-info/ \
  -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."

# 5. Obter estatísticas completas da OLT
curl -X GET http://177.22.126.78:8000/api/olt/system-stats/ \
  -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."

# 6. Listar alarmes da OLT
curl -X GET http://177.22.126.78:8000/api/olt/alarms/ \
  -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."

# 7. Filtrar alarmes major ativos
curl -X GET "http://177.22.126.78:8000/api/olt/alarms/?severity=major&active_only=true" \
  -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."

# 8. Obter estatísticas dos alarmes
curl -X GET http://177.22.126.78:8000/api/olt/alarms/stats/ \
  -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."

# 9. Coletar novos alarmes
curl -X POST http://177.22.126.78:8000/api/olt/alarms/collect/ \
  -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."

# 10. Listar ONUs de uma PON específica
curl -X GET "http://177.22.126.78:8000/api/onus/pon/1%2F1%2F1%2F1/" \
  -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."

# 11. Filtrar ONUs UP de uma PON
curl -X GET "http://177.22.126.78:8000/api/onus/pon/1%2F1%2F1%2F1/?oper_state=up" \
  -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."

# 12. Atualizar dados do sistema OLT
curl -X POST http://177.22.126.78:8000/api/olt/update-system-data/ \
  -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
```

### Exemplo de uso com Python requests

```python
import requests

# 1. Obter token
login_url = "http://177.22.126.78:8000/api/auth/login/"
login_data = {"username": "admin", "password": "password"}
response = requests.post(login_url, json=login_data)
tokens = response.json()
access_token = tokens['access']

# 2. Configurar headers com token
headers = {"Authorization": f"Bearer {access_token}"}

# 3. Buscar ONUs
onus_url = "http://177.22.126.78:8000/api/onus/"
onus_response = requests.get(onus_url, headers=headers)
onus_data = onus_response.json()

print(f"Total de ONUs: {onus_data['count']}")
for onu in onus_data['results']:
    print(f"ONU {onu['serial']}: {onu['oper_state']}")

# 4. Obter informações do sistema OLT
system_url = "http://177.22.126.78:8000/api/olt/system-info/"
system_response = requests.get(system_url, headers=headers)
system_data = system_response.json()

print(f"Versão OLT: {system_data['isam_release']}")
print(f"Uptime: {system_data['uptime_days']} dias")

# 5. Obter estatísticas completas da OLT
stats_url = "http://177.22.126.78:8000/api/olt/system-stats/"
stats_response = requests.get(stats_url, headers=headers)
stats_data = stats_response.json()

print(f"Slots operacionais: {stats_data['slots_stats']['operational_slots']}")
print(f"Temperatura média: {stats_data['temperature_stats']['average_temperature']}°C")

# 6. Buscar alarmes da OLT
alarms_url = "http://177.22.126.78:8000/api/olt/alarms/"
alarms_response = requests.get(alarms_url, headers=headers)
alarms_data = alarms_response.json()

print(f"Total de alarmes: {alarms_data['count']}")
for alarm in alarms_data['results'][:5]:  # Mostrar apenas os 5 primeiros
    print(f"Alarme {alarm['severity']}: {alarm['entity'][:50]}...")

# 7. Buscar alarmes major ativos
major_alarms_url = "http://177.22.126.78:8000/api/olt/alarms/?severity=major&active_only=true"
major_response = requests.get(major_alarms_url, headers=headers)
major_data = major_response.json()

print(f"Alarmes major ativos: {major_data['count']}")

# 8. Obter estatísticas dos alarmes
stats_alarms_url = "http://177.22.126.78:8000/api/olt/alarms/stats/"
stats_alarms_response = requests.get(stats_alarms_url, headers=headers)
stats_alarms_data = stats_alarms_response.json()

print(f"Total de alarmes: {stats_alarms_data['total_alarms']}")
print(f"Alarmes ativos: {stats_alarms_data['active_alarms']}")
print("Por severidade:", stats_alarms_data['by_severity'])

# 9. Coletar novos alarmes
collect_url = "http://177.22.126.78:8000/api/olt/alarms/collect/"
collect_response = requests.post(collect_url, headers=headers)
collect_data = collect_response.json()

print(f"Coleta de alarmes: {collect_data['message']}")

# 10. Atualizar dados do sistema OLT
update_url = "http://177.22.126.78:8000/api/olt/update-system-data/"
update_response = requests.post(update_url, headers=headers)
update_data = update_response.json()

print(f"Atualização: {update_data['message']}")

# 11. Buscar ONUs de uma PON específica
import urllib.parse

pon = "1/1/1/1"  # PON original
encoded_pon = urllib.parse.quote(pon, safe='')  # Codificação para URL
onu_pon_url = f"http://177.22.126.78:8000/api/onus/pon/{encoded_pon}/"
onu_pon_response = requests.get(onu_pon_url, headers=headers)
onu_pon_data = onu_pon_response.json()

print(f"ONUs na PON {pon}: {onu_pon_data['count']}")
if onu_pon_data['count'] > 0:
    results = onu_pon_data['results']
    if isinstance(results, dict) and 'results' in results:
        onus_list = results['results']
        print("Primeiras ONUs:")
        for onu in onus_list[:3]:
            print(f"  - {onu['serial']}: {onu['oper_state']} ({onu['desc1']})")

# 12. Filtrar ONUs por estado na PON
filter_url = f"http://177.22.126.78:8000/api/onus/pon/{encoded_pon}/?oper_state=up"
filter_response = requests.get(filter_url, headers=headers)
filter_data = filter_response.json()

print(f"ONUs UP na PON {pon}: {filter_data['count']}")
```

## Monitoramento de Alarmes em Tempo Real

### Exemplo de monitoramento contínuo
```python
import requests
import time
from datetime import datetime

def monitor_alarms():
    # Configuração
    base_url = "http://177.22.126.78:8000/api"
    
    # Obter token (implementar renovação automática em produção)
    login_response = requests.post(f"{base_url}/auth/login/", 
                                  json={"username": "admin", "password": "password"})
    access_token = login_response.json()['access']
    headers = {"Authorization": f"Bearer {access_token}"}
    
    last_check = datetime.now()
    
    while True:
        try:
            # 1. Verificar alarmes críticos e major ativos
            critical_alarms = requests.get(f"{base_url}/olt/alarms/?severity=critical&active_only=true", 
                                         headers=headers).json()
            major_alarms = requests.get(f"{base_url}/olt/alarms/?severity=major&active_only=true", 
                                       headers=headers).json()
            
            if critical_alarms['count'] > 0:
                print(f"🚨 CRÍTICO: {critical_alarms['count']} alarme(s) crítico(s) ativo(s)!")
                for alarm in critical_alarms['results']:
                    print(f"   - {alarm['entity']}")
                    
            if major_alarms['count'] > 0:
                print(f"⚠️  MAJOR: {major_alarms['count']} alarme(s) major ativo(s)")
            
            # 2. Coletar novos alarmes a cada 5 minutos
            if (datetime.now() - last_check).seconds >= 300:
                print("🔄 Coletando novos alarmes...")
                collect_response = requests.post(f"{base_url}/olt/alarms/collect/", headers=headers)
                print(f"   {collect_response.json()['message']}")
                last_check = datetime.now()
            
            # 3. Mostrar estatísticas gerais
            stats = requests.get(f"{base_url}/olt/alarms/stats/", headers=headers).json()
            print(f"📊 Total: {stats['total_alarms']} | Ativos: {stats['active_alarms']} | Tendência: {stats['trend']}")
            
        except Exception as e:
            print(f"❌ Erro no monitoramento: {e}")
        
        time.sleep(60)  # Verificar a cada minuto

# Executar monitoramento
if __name__ == "__main__":
    monitor_alarms()
```

### Exemplo de uso com diferentes formatos de PON
```python
import requests
import urllib.parse

def test_different_pon_formats():
    base_url = "http://177.22.126.78:8000/api"
    headers = {"Authorization": "Bearer YOUR_TOKEN_HERE"}
    
    # Diferentes formatos de PON para testar
    pon_formats = [
        "1/1/1/1",           # Formato básico
        "1/1/2/9",           # Formato básico
        "gpon-olt_1/1/1/1",  # Formato GPON
        "slot_1/port_2"      # Formato slot/port
    ]
    
    for pon in pon_formats:
        print(f"\n🔍 Testando PON: {pon}")
        
        # Codificar PON para URL
        encoded_pon = urllib.parse.quote(pon, safe='')
        url = f"{base_url}/onus/pon/{encoded_pon}/"
        
        print(f"URL: {url}")
        
        try:
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                data = response.json()
                count = data.get('count', 0)
                print(f"✅ {count} ONUs encontradas")
                
                # Aplicar filtros
                up_url = f"{url}?oper_state=up"
                up_response = requests.get(up_url, headers=headers)
                if up_response.status_code == 200:
                    up_count = up_response.json().get('count', 0)
                    print(f"📈 {up_count} ONUs UP")
            else:
                print(f"❌ Erro: {response.status_code}")
        except Exception as e:
            print(f"❌ Erro: {e}")

# Executar teste
if __name__ == "__main__":
    test_different_pon_formats()
```

### Exemplo de filtros avançados
```python
import requests
from datetime import datetime, timedelta

def advanced_alarm_filtering():
    base_url = "http://177.22.126.78:8000/api"
    headers = {"Authorization": "Bearer YOUR_TOKEN_HERE"}
    
    # 1. Alarmes das últimas 24 horas
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    recent_url = f"{base_url}/olt/alarms/?date_from={yesterday}&ordering=-timestamp"
    recent_alarms = requests.get(recent_url, headers=headers).json()
    
    print(f"Alarmes das últimas 24h: {recent_alarms['count']}")
    
    # 2. Alarmes de uma ONU específica
    onu_filter = "RCMG:19896C04"
    onu_url = f"{base_url}/olt/alarms/?entity={onu_filter}"
    onu_alarms = requests.get(onu_url, headers=headers).json()
    
    print(f"Alarmes da ONU {onu_filter}: {onu_alarms['count']}")
    
    # 3. Alarmes por descrição (ex: problemas de sinal)
    signal_url = f"{base_url}/olt/alarms/?description=optical signal"
    signal_alarms = requests.get(signal_url, headers=headers).json()
    
    print(f"Problemas de sinal óptico: {signal_alarms['count']}")
    
    # 4. Combinar múltiplos filtros
    complex_url = f"{base_url}/olt/alarms/?severity=major&active_only=true&date_from={yesterday}"
    complex_alarms = requests.get(complex_url, headers=headers).json()
    
    print(f"Alarmes major ativos das últimas 24h: {complex_alarms['count']}")
    
    return recent_alarms, onu_alarms, signal_alarms, complex_alarms

# Executar análise
if __name__ == "__main__":
    advanced_alarm_filtering()
```

## Referência Rápida de Endpoints

### Tabela de Endpoints Principais

| Método | Endpoint | Descrição | Paginação | Filtros |
|--------|----------|-----------|-----------|---------|
| GET | `/api/onus/` | Lista todas as ONUs | ✅ | oper_state, admin_state, cliente_fibra, search |
| GET | `/api/onus/{id}/` | Detalhes de uma ONU | ❌ | - |
| GET | `/api/onus/pon/{pon}/` | ONUs de uma PON específica | ✅ | oper_state, admin_state, cliente_fibra |
| GET | `/api/onus/stats/` | Estatísticas das ONUs | ❌ | - |
| GET | `/api/olt/alarms/` | Lista alarmes da OLT | ✅ | severity, entity, description, active_only, date_from, date_to |
| GET | `/api/olt/alarms/stats/` | Estatísticas dos alarmes | ❌ | - |
| POST | `/api/olt/alarms/collect/` | Coleta novos alarmes | ❌ | - |
| GET | `/api/olt/system-info/` | Informações do sistema OLT | ❌ | - |
| GET | `/api/olt/system-stats/` | Estatísticas completas da OLT | ❌ | - |

### Códigos de Status Comuns

| Código | Significado | Quando Ocorre |
|--------|-------------|---------------|
| 200 | OK | Sucesso na operação |
| 401 | Unauthorized | Token JWT inválido/ausente |
| 404 | Not Found | Recurso não encontrado |
| 400 | Bad Request | Parâmetros inválidos |
| 500 | Internal Server Error | Erro interno do servidor |

## Notas Importantes

### Autenticação
- Os tokens JWT têm validade limitada. Implemente renovação automática usando o endpoint `/api/auth/refresh/`
- Para aplicações web, também é possível usar autenticação por sessão do Django

### Performance
- Use paginação para listas grandes de dados
- Aplique filtros específicos para reduzir o volume de dados transferidos
- O endpoint de coleta de alarmes executa em background via RQ (Redis Queue)

### Monitoramento
- Configure alertas para alarmes críticos e major
- Monitore regularmente o status de conexão com a OLT
- Implemente logs para auditoria das operações

### Segurança
- Use HTTPS em produção
- Mantenha os tokens seguros e renove-os regularmente
- Limite o acesso aos endpoints administrativos
