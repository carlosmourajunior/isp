# 🌐 API OLT/ONT - Sistema de Gerenciamento

Esta API REST permite acesso aos dados das ONTs (Optical Network Terminals) com autenticação JWT robusta.

## 🚀 Quick Start

### 1. Inicializar o ambiente Docker
```bash
# Construir e iniciar os containers
docker-compose up -d

# Executar migrações e criar superusuário
docker-compose exec web python init_api.py
```

### 2. Testar a API
```bash
# Testar endpoints básicos
docker-compose exec web python test_api.py

# Ou testar externamente
python test_api.py http://localhost:8000
```

## 📋 Endpoints Disponíveis

| Método | Endpoint | Descrição | Autenticação |
|--------|----------|-----------|--------------|
| POST | `/api/auth/login/` | Obter token JWT | ❌ |
| POST | `/api/auth/refresh/` | Renovar token | ❌ |
| GET | `/api/onus/` | Listar ONUs com filtros | ✅ |
| GET | `/api/onus/{id}/` | Detalhes de uma ONU | ✅ |
| GET | `/api/onus/stats/` | Estatísticas das ONUs | ✅ |
| GET | `/api/onus/pon/{pon}/` | ONUs por PON específica | ✅ |
| GET | `/api/onus/search/` | Busca avançada | ✅ |
| GET | `/api/olt-users/` | Informações das portas | ✅ |
| GET | `/api/clientes-fibra/` | Lista clientes fibra | ✅ |

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

# Paginação
GET /api/onus/?page=2
```

## 📊 Estatísticas

O endpoint `/api/onus/stats/` retorna:

```json
{
    "total_onus": 150,
    "onus_online": 142,
    "onus_offline": 8,
    "clientes_fibra": 98,
    "onus_sinal_baixo": 5,
    "estatisticas_por_slot": {
        "slot_1": {"total": 75, "online": 71, "offline": 4},
        "slot_2": {"total": 75, "online": 71, "offline": 4}
    },
    "percentual_online": 94.67
}
```

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
# Banco de dados
POSTGRES_DB=postgres
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_HOST=db
POSTGRES_PORT=5432

# Redis
REDIS_PORT=6380

# Django
SECRET_KEY=sua-chave-secreta
DEBUG=True
```

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
- 🧪 Testes: Execute `python test_api.py`
- 🐛 Issues: Abra uma issue no repositório