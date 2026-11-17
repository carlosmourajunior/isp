# API Documentation - Sistema OLT/ONT

Esta API permite acesso aos dados das ONTs (Optical Network Terminals) e das OLTs com autenticação JWT.
O sistema trabalha com **várias OLTs** cadastradas: cada ONU, placa, sensor de temperatura e diagnóstico de
SFP pertence a uma OLT (`olt` = id, `olt_name` = nome cadastrado).

> **Documentação interativa:** `https://<domínio>/api/docs/` (Swagger - dá para testar as chamadas
> com o token), `https://<domínio>/api/redoc/` (leitura) e `https://<domínio>/api/schema/`
> (OpenAPI, para importar no Postman/Insomnia). Esta página é o resumo em texto.
>
> O IP de origem das chamadas precisa estar liberado pelo provedor.
>
> Revisada em 17/11/2026 contra o comportamento real da API com 2 OLTs cadastradas. Nessa revisão todos os
> endpoints de OLT passaram a aceitar `?olt=` e a rota `/api/onus/pon/{pon}/` foi corrigida.

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
`access` vale 60 minutos e `refresh` 7 dias.

### Renovar Token
```
POST /api/auth/refresh/
Content-Type: application/json

{
    "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```
A resposta traz um `access` novo e um `refresh` novo. Guarde o novo: o antigo deixa de valer.

## Várias OLTs: o que aceita `?olt=`

Todos os registros trazem `olt` (id) e `olt_name`. Os ids aparecem nesses campos (por exemplo em
`/api/olt/slots/`); a API de parceiros não tem uma listagem de OLTs. `?olt=` com valor que não é número
responde 400.

| Endpoint | `?olt={id}` | Sem o parâmetro |
|----------|-------------|-----------------|
| `/api/onus/` | filtra | Todas as OLTs |
| `/api/onus/{id}/` | - | O `id` é único entre todas as OLTs |
| `/api/onus/stats/` | filtra | Soma todas as OLTs |
| `/api/onus/pon/{pon}/` | filtra | ONUs da PON em todas as OLTs (a mesma PON existe em cada OLT) |
| `/api/onus/search/` | filtra | Busca em todas as OLTs |
| `/api/olt-users/` | filtra | Todas as OLTs |
| `/api/clientes-fibra/` | - | Cadastro do IXC, único para todas as OLTs |
| `/api/olt/system-info/` | escolhe a OLT (404 se não existir) | A OLT padrão (a ativa de menor id) |
| `/api/olt/slots/` | filtra | Todas as OLTs |
| `/api/olt/temperatures/` | filtra | Todas as OLTs |
| `/api/olt/sfp-diagnostics/` | filtra | Todas as OLTs |
| `/api/olt/system-stats/` | filtra placas e temperaturas e escolhe o `system_info` | Placas e temperaturas somadas de todas as OLTs; `system_info` e `last_updated` da OLT padrão |
| `/api/olt/temperature-alerts/` | filtra | Alertas de todas as OLTs; cada alerta traz `olt` e `olt_name` |

> Temperatura de uma OLT: `/api/olt/temperatures/?olt={id}` (sensor a sensor) ou
> `/api/olt/system-stats/?olt={id}` (resumo). Alertas de uma OLT: `/api/olt/temperature-alerts/?olt={id}`.

## Endpoints da API

### 1. Listar ONUs
```
GET /api/onus/
Authorization: Bearer <access_token>
```

Resposta paginada: `count`, `next`, `previous` e `results` (50 ONUs por página).

**Parâmetros de filtro:**
- `olt`: Filtrar por id da OLT
- `pon`: Filtrar por PON exata, no formato `1/1/<slot>/<porta>` (ex.: `1/1/1/5`). A mesma PON existe em
  mais de uma OLT; combine com `olt` para não misturar
- `oper_state`: Filtrar por status operacional (`up`/`down`)
- `admin_state`: Filtrar por status administrativo
- `cliente_fibra`: Filtrar por clientes fibra (true/false)
- `olt_rx_sig`, `ont_rx_sig`: sinal em dBm, com `__gt`, `__gte`, `__lt`, `__lte` (ex.: `olt_rx_sig__lt=-29`)
- `search`: Buscar por serial, MAC, descrição ou PON
- `ordering`: Ordenar por campo (position, olt_rx_sig, pon); prefixo `-` para decrescente
- `page`: Número da página

**Exemplos:**
```
GET /api/onus/?oper_state=up&cliente_fibra=true&search=FHTT&page=1
GET /api/onus/?olt=2&oper_state=down
GET /api/onus/?olt=1&pon=1/1/1/5
```

### 2. Detalhes de uma ONU
```
GET /api/onus/{id}/
Authorization: Bearer <access_token>
```
Inclui `cliente_info` com o cliente fibra vinculado, quando houver.

### 3. Estatísticas das ONUs
```
GET /api/onus/stats/
Authorization: Bearer <access_token>
```

**Resposta:**
```json
{
    "total_onus": 2577,
    "onus_online": 2343,
    "onus_offline": 234,
    "clientes_fibra": 2572,
    "onus_sinal_baixo": 714,
    "estatisticas_por_slot": {
        "slot_1": {"total": 1211, "online": 1123, "offline": 88},
        "slot_2": {"total": 1129, "online": 1012, "offline": 117},
        "slot_3": {"total": 112, "online": 97, "offline": 15}
    },
    "percentual_online": 90.92
}
```
> Sem `?olt=`, os números somam **todas as OLTs**, e como as OLTs têm slots com a mesma numeração,
> `slot_1` mistura o slot 1 de todas elas. Use `/api/onus/stats/?olt={id}` para os números de uma OLT.
> `onus_sinal_baixo` conta ONUs com sinal na OLT abaixo de -25 dBm. As chaves de
> `estatisticas_por_slot` são dinâmicas (`slot_N`): itere o objeto.

### 4. ONUs por PON específica
```
GET /api/onus/pon/{pon}/
Authorization: Bearer <access_token>
```
`pon` no formato `1/1/<slot>/<porta>`; as barras podem ir codificadas (`1%2F1%2F1%2F5`) ou não.
Como a mesma PON existe em cada OLT, sem `?olt=` a resposta traz as ONUs de todas elas:
```
GET /api/onus/pon/1/1/1/5/?olt=2
```
**Resposta:** `{"pon": "1/1/1/5", "total_onus": 12, "onus": [...]}`; 404 se a PON não tiver ONUs.
> Antes de 17/11/2026 esta rota respondia sempre 404. O filtro `/api/onus/?pon=1/1/1/5&olt=2` faz o
> mesmo e é paginado.

### 5. Busca avançada de ONUs
```
GET /api/onus/search/?q={termo_busca}
Authorization: Bearer <access_token>
```
Busca (contém, sem diferenciar maiúsculas) em serial, MAC, descrições e PON. Sem `?olt={id}`, em todas as
OLTs. Não é paginada.

### 6. Listar informações das portas OLT
```
GET /api/olt-users/
Authorization: Bearer <access_token>
```
Quantidade de ONUs conectadas em cada porta PON na última leitura.

**Parâmetros de filtro:**
- `olt`: Filtrar por id da OLT
- `slot`: Filtrar por slot específico
- `ordering`: Ordenar por campo (slot, port, users_connected, last_updated, olt__name)

### 7. Listar clientes fibra
```
GET /api/clientes-fibra/
Authorization: Bearer <access_token>
```
`mac` é o serial da ONU do cliente (casa com `serial` em `/api/onus/`).

**Parâmetros de filtro:**
- `search`: Buscar por nome, MAC ou endereço

### 8. Informações do sistema da OLT
```
GET /api/olt/system-info/
Authorization: Bearer <access_token>
```

**Resposta:**
```json
{
    "id": 1,
    "olt": 1,
    "olt_name": "OLT Borda da Mata",
    "isam_release": "R6.2.03",
    "uptime_days": 958,
    "uptime_hours": 12,
    "uptime_minutes": 26,
    "uptime_seconds": 47,
    "uptime_raw": "System Up Time         : 958 days, 12:26:47.46 (hr:min:sec)",
    "total_uptime_hours": 23004,
    "last_updated": "2026-11-17T11:34:08Z"
}
```
> Sem parâmetro retorna a **OLT padrão** (a ativa de menor id). Para as demais, use
> `/api/olt/system-info/?olt={id}` (404 se a OLT não existir). Confira `olt` e `olt_name` na resposta.

### 9. Listar slots (placas) da OLT
```
GET /api/olt/slots/
Authorization: Bearer <access_token>
```
Resposta paginada.

**Parâmetros de filtro:**
- `olt`: Filtrar por id da OLT
- `enabled`: Filtrar por slots habilitados (true/false)
- `availability`: Filtrar por disponibilidade
- `actual_type`: Filtrar por tipo
- `ordering`: slot_name, actual_type, restart_count

### 10. Listar temperaturas da OLT
```
GET /api/olt/temperatures/
Authorization: Bearer <access_token>
```
Resposta paginada, com um registro por sensor de cada placa.

**Parâmetros de filtro:**
- `olt`: Filtrar por id da OLT
- `slot_name`: Filtrar por slot específico (ex.: `lt:1/1/1`)
- `ordering`: slot_name, sensor_id, actual_temp

**Exemplo de item:**
```json
{
    "id": 21,
    "olt": 2,
    "olt_name": "OLT Ouro Fino",
    "slot_name": "lt:1/1/1",
    "sensor_id": 1,
    "actual_temp": 57,
    "tca_low": 90,
    "tca_high": 95,
    "shutdown_low": 110,
    "shutdown_high": 115,
    "is_critical": false,
    "is_warning": false,
    "status": "CRITICAL_LOW",
    "last_updated": "2026-11-17T11:46:29Z"
}
```

**Como interpretar a temperatura:**
- `actual_temp` está em °C.
- Os quatro limites que a OLT informa são uma **escada crescente**: `tca_low < tca_high <= shutdown_low <
  shutdown_high` (ex.: 90, 95, 110, 115). Cada sensor tem os seus; variam de 65 a 115 °C nas OLTs atuais.
- `status` diz o patamar mais alto já atingido: `NORMAL` (abaixo de `tca_low`), `WARNING_LOW` (a partir de
  `tca_low`), `WARNING_HIGH` (`tca_high`), `CRITICAL_LOW` (`shutdown_low`) e `CRITICAL_HIGH` (`shutdown_high`,
  a OLT desliga a placa).
- `is_critical` = `actual_temp >= tca_high` e `is_warning` = `actual_temp >= tca_high - 5`.
- `/api/olt/system-stats/` e `/api/olt/temperature-alerts/` usam limites **fixos** iguais para todos os
  sensores: **crítico a partir de 75 °C** e **aviso de 70 a 74 °C**. Um sensor com `tca_high` 80 e 72 °C
  aparece como aviso nesses dois endpoints e com `is_warning=false` aqui.
- Os três usam só sensores ativos (os que a coleta mais recente ainda encontrou na OLT).
> Antes de 17/11/2026 o `status` devolvia `CRITICAL_LOW` para qualquer sensor (tratava os limites "low"
> como mínimos). Quem filtrava por esse valor deve passar a usar `NORMAL`.

### 11. Diagnóstico dos SFPs
```
GET /api/olt/sfp-diagnostics/
Authorization: Bearer <access_token>
```
Resposta paginada. Filtros: `olt`; ordenação: interface, temperature, tx_power, rx_power.
> Nas OLTs atuais este endpoint está vazio (`count: 0`): nenhuma rotina de coleta preenche essa tabela.

### 12. Estatísticas do sistema OLT
```
GET /api/olt/system-stats/
Authorization: Bearer <access_token>
```

**Resposta:**
```json
{
    "system_info": {
        "olt": 1,
        "olt_name": "OLT Borda da Mata",
        "isam_release": "R6.2.03",
        "uptime_days": 308,
        "total_uptime_hours": 7397
    },
    "slots_stats": {
        "total_slots": 22,
        "operational_slots": 10,
        "offline_slots": 12,
        "operational_percentage": 45.45,
        "slots_by_type": [
            {"actual_type": "empty", "count": 11},
            {"actual_type": "fglt-d", "count": 5},
            {"actual_type": "fglt-b", "count": 2}
        ]
    },
    "temperature_stats": {
        "critical_temperatures": 0,
        "warning_temperatures": 0,
        "normal_temperatures": 35,
        "average_temperature": 48.3,
        "max_temperature": 69,
        "min_temperature": 31,
        "temperature_by_slot": [
            {
                "slot_name": "lt:1/1/1",
                "avg_temp": 50.7,
                "max_temp": 69,
                "sensor_count": 10
            }
        ]
    },
    "last_updated": "2026-11-17T11:34:08Z"
}
```
> Sem `?olt=`: `slots_stats` e `temperature_stats` **somam todas as OLTs** (e `temperature_by_slot` junta
> sensores de OLTs diferentes com o mesmo nome de slot), e `system_info` e `last_updated` são da OLT padrão.
> Com `?olt={id}`, tudo é daquela OLT. Limites: crítico a partir de 75 °C, aviso de 70 a 74 °C.
> Considera só placas e sensores ativos.

### 13. Alertas de temperatura
```
GET /api/olt/temperature-alerts/
Authorization: Bearer <access_token>
```

**Resposta:**
```json
{
    "critical_alerts": [],
    "warning_alerts": [],
    "critical_count": 0,
    "warning_count": 0
}
```
Cada alerta tem o mesmo formato de um item de `/api/olt/temperatures/` (inclui `olt` e `olt_name`).
Traz as temperaturas de **todas as OLTs** (use `?olt={id}` para uma só): **crítico a partir de 75 °C** e
**aviso de 70 a 74 °C**, limites fixos para todos os sensores, considerando só sensores ativos.

## Endpoints internos (fora do contrato de parceiros)

Estes endpoints existem para o frontend do sistema e **não** fazem parte da documentação pública
(`/api/docs/`). Podem mudar sem aviso. Alguns exigem usuário administrador ou que a chamada venha do
próprio frontend; não use em integrações. A documentação completa deles fica em `/api/docs/interno/`
(acessível com login de administrador em `/admin/`).

| Endpoint | Para que serve |
|----------|----------------|
| `GET /api/olts/`, `/api/olts/{id}/` | Cadastro das OLTs (criar, editar e remover só administradores). `host`, `username` e `ssh_port` só aparecem para administradores; a senha nunca é devolvida |
| `GET /api/olt/system-summary/` | Resumo por OLT: versão, uptime, placas e temperatura de cada OLT ativa, de uma vez |
| `GET /api/olt/connection-status/` | Idade da última coleta do sistema (com `?olt={id}`, de uma OLT; sem, a mais recente de qualquer uma) |
| `POST /api/olt/update-system-data/` | Coleta placas, temperaturas e sistema direto na OLT. Exige administrador e chamada vinda do frontend. `?olt={id}` escolhe a OLT; sem ele, a OLT padrão |
| `POST /api/tasks/update-all/` e demais `/api/tasks/...` | Disparam e listam as tarefas de atualização (por OLT) |
| `GET /api/scheduler/status/` | Estado da atualização automática |
| `/api/ctos/`, `/api/vistorias/`, `/api/sinal/...`, `/api/desconexoes/...`, `/api/ixc/...` | Telas de CTOs, vistorias, sinal óptico, desconexões e correções do IXC |

## Códigos de Resposta

- **200 OK**: Sucesso
- **400 Bad Request**: Parâmetros inválidos
- **401 Unauthorized**: Token JWT inválido ou ausente
- **403 Forbidden**: Sem permissão (ou IP não liberado)
- **404 Not Found**: Recurso não encontrado
- **500 Internal Server Error**: Erro interno do servidor

## Formato dos Dados

### ONU
```json
{
    "id": 1,
    "olt": 1,
    "olt_name": "OLT Borda da Mata",
    "pon": "1/1/1/1",
    "slot": 1,
    "port": 1,
    "position": 1,
    "mac": "48575443:12345678",
    "serial": "FHTT12345678",
    "oper_state": "up",
    "admin_state": "up",
    "olt_rx_sig": -18.5,
    "ont_rx_sig": -20.9,
    "ont_tx_sig": 2.5,
    "ont_olt": "1500",
    "desc1": "Cliente Nome",
    "desc2": "Informações adicionais",
    "cliente_fibra": true
}
```

> `pon` tem o formato `1/1/<slot>/<porta>`. `olt` é o id da OLT dona do registro e `olt_name` o nome
> cadastrado. A mesma `pon` e a mesma `position` se repetem em OLTs diferentes: identifique a ONU por
> `id` ou por `serial`, e sempre junto de `olt` quando usar `pon`.

### Exemplo de uso com curl

```bash
# 1. Obter token
curl -X POST https://<domínio>/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "password"}'

# 2. Listar as ONUs de uma OLT
curl -X GET "https://<domínio>/api/onus/?olt=2" \
  -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."

# 3. Filtrar ONUs offline de uma OLT
curl -X GET "https://<domínio>/api/onus/?olt=2&oper_state=down" \
  -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."

# 4. Temperaturas de uma OLT
curl -X GET "https://<domínio>/api/olt/temperatures/?olt=2" \
  -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."

# 5. Placas de uma OLT
curl -X GET "https://<domínio>/api/olt/slots/?olt=2" \
  -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."

# 6. Alertas de temperatura (todas as OLTs)
curl -X GET https://<domínio>/api/olt/temperature-alerts/ \
  -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
```

### Exemplo de uso com Python requests

```python
import requests

BASE = "https://<domínio>/api"

# 1. Obter token
response = requests.post(f"{BASE}/auth/login/", json={"username": "admin", "password": "password"})
access_token = response.json()["access"]
headers = {"Authorization": f"Bearer {access_token}"}


def listar(url, **params):
    """Percorre todas as páginas de um endpoint paginado."""
    while url:
        dados = requests.get(url, headers=headers, params=params).json()
        yield from dados["results"]
        url, params = dados["next"], {}


# 2. ONUs offline da OLT 2
for onu in listar(f"{BASE}/onus/", olt=2, oper_state="down"):
    print(f"{onu['olt_name']} {onu['pon']}/{onu['position']} {onu['serial']}")

# 3. Temperatura máxima de cada OLT (sensores de /olt/temperatures/)
maximas = {}
for sensor in listar(f"{BASE}/olt/temperatures/"):
    nome = sensor["olt_name"]
    maximas[nome] = max(maximas.get(nome, 0), sensor["actual_temp"])
print(maximas)

# 4. Alertas de temperatura de todas as OLTs
alertas = requests.get(f"{BASE}/olt/temperature-alerts/", headers=headers).json()
for a in alertas["critical_alerts"] + alertas["warning_alerts"]:
    print(f"{a['olt_name']} {a['slot_name']} sensor {a['sensor_id']}: {a['actual_temp']} °C")
```
