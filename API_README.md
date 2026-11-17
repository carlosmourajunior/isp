# 🌐 API OLT/ONT - Sistema de Gerenciamento

Esta API REST permite acesso aos dados das ONTs (Optical Network Terminals) com autenticação JWT robusta.

## 🚀 Quick Start

### 1. Inicializar o ambiente Docker
```bash
cp .env.example .env          # ajuste os segredos
docker compose up -d --build  # as migrações rodam na subida do container web
docker compose exec web python manage.py createsuperuser
```
Depois cadastre as OLTs (menu OLTs do frontend ou `/admin/`).

### 2. Testar a API
```bash
# Testes automatizados
docker compose exec web python manage.py test olt

# Documentação interativa (Swagger), para testar as chamadas com o token
http://localhost:8000/api/docs/
```

## 📋 Endpoints Disponíveis

O sistema trabalha com **várias OLTs**: os registros trazem `olt` (id) e `olt_name`. A coluna
"`?olt=`" mostra quais endpoints filtram por OLT; os demais somam todas as OLTs.

| Método | Endpoint | Descrição | `?olt=` | Autenticação |
|--------|----------|-----------|---------|--------------|
| POST | `/api/auth/login/` | Obter token JWT | - | ❌ |
| POST | `/api/auth/refresh/` | Renovar token | - | ❌ |
| GET | `/api/onus/` | Listar ONUs com filtros | ✅ | ✅ |
| GET | `/api/onus/{id}/` | Detalhes de uma ONU | - | ✅ |
| GET | `/api/onus/stats/` | Estatísticas das ONUs (sem `?olt=`, soma todas as OLTs) | ✅ | ✅ |
| GET | `/api/onus/pon/{pon}/` | ONUs de uma PON, ex.: `/api/onus/pon/1/1/1/5/?olt=2` | ✅ | ✅ |
| GET | `/api/onus/search/` | Busca avançada | ✅ | ✅ |
| GET | `/api/olt-users/` | Ocupação das portas | ✅ | ✅ |
| GET | `/api/clientes-fibra/` | Lista clientes fibra | - | ✅ |
| GET | `/api/olt/system-info/` | Versão e uptime (sem `?olt=`, a OLT padrão) | ✅ | ✅ |
| GET | `/api/olt/slots/` | Placas (slots) | ✅ | ✅ |
| GET | `/api/olt/temperatures/` | Temperaturas por sensor | ✅ | ✅ |
| GET | `/api/olt/sfp-diagnostics/` | Diagnóstico de SFPs (vazio hoje) | ✅ | ✅ |
| GET | `/api/olt/system-stats/` | Resumo de placas e temperaturas (sem `?olt=`, soma todas as OLTs) | ✅ | ✅ |
| GET | `/api/olt/temperature-alerts/` | Alertas de temperatura (crítico ≥ 75 °C, aviso 70-74 °C) | ✅ | ✅ |

Detalhes, exemplos e limitações de cada um em `API_DOCUMENTATION.md`. Endpoints usados só pelo
frontend (OLTs, tarefas, CTOs, vistorias, sinal, desconexões...) não fazem parte do contrato de parceiros.

## 🔐 Autenticação

A API usa autenticação JWT (JSON Web Tokens):

1. **Login**: Envie credenciais para `/api/auth/login/`
2. **Token**: Use o `access_token` no header `Authorization: Bearer <token>`
3. **Renovação**: Use o `refresh_token` em `/api/auth/refresh/`

### Exemplo de Autenticação

```python
import requests

# 1. Fazer login
response = requests.post('http://localhost:8000/api/auth/login/', json={
    'username': 'admin',
    'password': 'admin123'
})

tokens = response.json()
access_token = tokens['access']

# 2. Usar token nas requisições
headers = {'Authorization': f'Bearer {access_token}'}
onus = requests.get('http://localhost:8000/api/onus/', headers=headers)
```

## 🔍 Filtros e Busca

### Filtros Disponíveis para ONUs
- `olt`: Id da OLT
- `pon`: PON exata (`1/1/<slot>/<porta>`); combine com `olt`, pois a mesma PON existe em cada OLT
- `oper_state`: Status operacional (up/down)
- `admin_state`: Status administrativo  
- `cliente_fibra`: Filtrar clientes fibra (true/false)
- `search`: Busca em serial, MAC, descrição, PON
- `ordering`: Ordenação (position, olt_rx_sig, pon)
- `page`: Paginação

### Exemplos de Uso
```bash
# ONUs online
GET /api/onus/?oper_state=up

# Buscar por serial
GET /api/onus/?search=FHTT12345

# Clientes fibra ordenados por sinal
GET /api/onus/?cliente_fibra=true&ordering=-olt_rx_sig

# ONUs offline de uma OLT
GET /api/onus/?olt=2&oper_state=down

# Paginação (50 por página)
GET /api/onus/?page=2

# Temperaturas de uma OLT
GET /api/olt/temperatures/?olt=2
```

## 📊 Estatísticas

O endpoint `/api/onus/stats/` soma **todas as OLTs** (use `?olt={id}` para uma só) e retorna:

```json
{
    "total_onus": 2577,
    "onus_online": 2343,
    "onus_offline": 234,
    "clientes_fibra": 2572,
    "onus_sinal_baixo": 714,
    "estatisticas_por_slot": {
        "slot_1": {"total": 1211, "online": 1123, "offline": 88},
        "slot_2": {"total": 1129, "online": 1012, "offline": 117}
    },
    "percentual_online": 90.92
}
```
As chaves `slot_N` são dinâmicas e juntam o mesmo slot de todas as OLTs.

## 🛠️ Desenvolvimento

### Estrutura dos Arquivos
```
olt/
├── api_views.py        # Views da API REST
├── api_urls.py         # URLs da API
├── serializers.py      # Serializers DRF
├── models.py          # Modelos de dados
└── ...

olt_connector/
├── settings.py        # Configurações Django + DRF
└── urls.py           # URLs principais
```

### Adicionando Novos Endpoints

1. **Criar serializer** em `olt/serializers.py`
2. **Criar view** em `olt/api_views.py`
3. **Adicionar URL** em `olt/api_urls.py`
4. **Testar** com `test_api.py`

### Exemplo de Nova View
```python
# olt/api_views.py
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def meu_endpoint(request):
    return Response({'mensagem': 'Olá da API!'})

# olt/api_urls.py
path('meu-endpoint/', api_views.meu_endpoint, name='meu_endpoint'),
```

## 🔧 Configuração

### Variáveis de Ambiente (.env)
```env
# Django
SECRET_KEY=sua-chave-secreta
DEBUG=True
ALLOWED_HOSTS=*

# Banco de dados
DB_NAME=postgres
DB_USER=postgres
DB_PASSWORD=postgres
DB_HOST=db
DB_PORT=5432

# Redis (a mesma senha deve constar na REDIS_URL)
REDIS_PASSWORD=troque-esta-senha
REDIS_URL=redis://:troque-esta-senha@redis:6379/0
```
Lista completa (e-mail, segurança, frontend) em `.env.example`. As credenciais das OLTs não ficam no
`.env`: são cadastradas por OLT no sistema (senha guardada criptografada).

### Configurações JWT (settings.py)
```python
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    # ... outras configurações
}
```

## 🚨 Segurança

### Em Produção:
1. **Altere** o `SECRET_KEY` 
2. **Defina** `DEBUG=False`
3. **Configure** `ALLOWED_HOSTS`
4. **Use** HTTPS
5. **Monitore** logs de acesso

### Boas Práticas:
- Tokens têm expiração (60 min)
- Refresh tokens são rotacionados
- Endpoints protegidos por autenticação
- Paginação para evitar sobrecarga

## 📚 Documentação Completa

Consulte o arquivo `API_DOCUMENTATION.md` para documentação detalhada com exemplos de todas as requisições e respostas.

## 🐛 Troubleshooting

### Problemas Comuns:

**401 Unauthorized**
- Verifique se o token está correto
- Token pode ter expirado (use refresh)

**403 Forbidden**
- Usuário não tem permissão
- Verifique se está autenticado

**500 Internal Server Error**
- Erro no servidor
- Verifique logs: `docker-compose logs web`

### Logs
```bash
# Logs da aplicação
docker-compose logs web

# Logs do banco
docker-compose logs db

# Logs em tempo real
docker-compose logs -f web
```

## 🤝 Contribuição

1. Fork o projeto
2. Crie sua feature branch
3. Commit suas mudanças
4. Push para a branch
5. Abra um Pull Request

---

## 📞 Suporte

Para dúvidas ou problemas, consulte:
- 📖 Documentação completa: `API_DOCUMENTATION.md`
- 🧪 Testes: `docker compose exec web python manage.py test olt`
- 🔎 Swagger: `/api/docs/` (parceiros) e `/api/docs/interno/` (todos os endpoints, admin logado)
- 🐛 Issues: Abra uma issue no repositório