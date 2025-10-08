# 🔒 DOCUMENTAÇÃO DE SEGURANÇA - ACESSO À OLT

## ⚠️ IMPORTANTE: ACESSO RESTRITO À OLT

Este sistema implementa **múltiplas camadas de segurança** para proteger o acesso direto à OLT Nokia.

## 🛡️ CAMADAS DE SEGURANÇA IMPLEMENTADAS

### 1. **Middleware de Segurança OLT**
- **Arquivo**: `olt/security.py` → `OltSecurityMiddleware`
- **Função**: Intercepta todas as requisições para endpoints que acessam a OLT
- **Verificações**:
  - ✅ Usuário autenticado
  - ✅ Usuário é admin/staff
  - ✅ IP de origem é interno (frontend)

### 2. **Decoradores de Proteção**
- **`@frontend_only`**: Permite apenas acesso via IPs internos
- **`@olt_admin_required`**: Exige permissões de administrador

### 3. **Validação de IP de Origem**
IPs permitidos para acesso direto à OLT:
```
127.0.0.1        # Localhost
::1              # Localhost IPv6  
172.16.0.0/12    # Redes Docker internas
192.168.0.0/16   # Redes privadas locais
```

## 🚫 ENDPOINTS PROTEGIDOS (ACESSO DIRETO À OLT)

### **POST /api/olt/update-system-data/**
- **Função**: Conecta na OLT e coleta dados em tempo real
- **Proteção**: `@frontend_only` + `@olt_admin_required`
- **Requisitos**:
  - ✅ JWT Token válido
  - ✅ Usuário admin/staff
  - ✅ IP interno (frontend)

### **Resposta em caso de acesso negado:**
```json
{
    "error": "Acesso à OLT negado",
    "message": "Comandos diretos na OLT só podem ser executados via frontend autorizado",
    "client_ip": "203.0.113.10",
    "code": "OLT_ACCESS_DENIED"
}
```

## ✅ ENDPOINTS LIBERADOS (SOMENTE LEITURA)

Estes endpoints **NÃO** acessam a OLT diretamente, apenas consultam dados já coletados:

- **GET /api/olt/system-info/** - Informações do sistema
- **GET /api/olt/slots/** - Slots da OLT
- **GET /api/olt/temperatures/** - Temperaturas
- **GET /api/olt/sfp-diagnostics/** - Diagnósticos SFP
- **GET /api/olt/system-stats/** - Estatísticas
- **GET /api/olt/temperature-alerts/** - Alertas de temperatura
- **GET /api/olt/connection-status/** - Status da conexão (novo)
- **GET /api/onus/** - Lista de ONUs
- **GET /api/olt-users/** - Usuários da OLT

## 🎯 COMO FUNCIONA NA PRÁTICA

### **1. Acesso via Frontend (PERMITIDO)**
```bash
# Frontend fazendo requisição interna
curl -X POST http://localhost:8000/api/olt/update-system-data/ \
  -H "Authorization: Bearer TOKEN_JWT_ADMIN" \
  -H "Content-Type: application/json"

# ✅ RESULTADO: Sucesso - coleta dados da OLT
```

### **2. Acesso Externo Direto (BLOQUEADO)**
```bash
# API externa tentando acessar
curl -X POST http://177.22.126.77:8000/api/olt/update-system-data/ \
  -H "Authorization: Bearer TOKEN_JWT_ADMIN" \
  -H "Content-Type: application/json"

# ❌ RESULTADO: 403 Forbidden
{
    "error": "Acesso à OLT negado",
    "message": "Comandos diretos na OLT só podem ser executados via frontend autorizado",
    "code": "OLT_ACCESS_DENIED"
}
```

## 🔧 CONFIGURAÇÃO ADICIONAL

### **Adicionar novos IPs autorizados:**
Edite o arquivo `olt/security.py`:
```python
frontend_allowed_ips = [
    '127.0.0.1',
    '::1',
    '172.16.0.0/12',
    '192.168.0.0/16',
    '203.0.113.100',  # Novo IP autorizado
]
```

### **Adicionar novos endpoints protegidos:**
Edite a lista `olt_direct_urls` em `OltSecurityMiddleware`:
```python
self.olt_direct_urls = [
    '/api/olt/update-system-data/',
    '/api/olt/novo-endpoint-olt/',  # Novo endpoint
]
```

## 📊 MONITORAMENTO

### **Verificar tentativas de acesso bloqueadas:**
```bash
# Verificar logs de segurança
docker compose logs web | grep "OLT_ACCESS_DENIED"

# Verificar IPs que tentaram acesso
docker compose logs web | grep "client_ip"
```

### **Endpoint para verificar status (sem conectar na OLT):**
```bash
curl -X GET http://seu-dominio/api/olt/connection-status/ \
  -H "Authorization: Bearer TOKEN_JWT"
```

## 🚨 ALERTAS DE SEGURANÇA

O sistema registra automaticamente:
- ❌ Tentativas de acesso negadas
- 🔍 IPs de origem de cada requisição
- 👤 Usuários que tentaram acessar
- ⏰ Timestamps de todas as tentativas

## ✅ RESUMO DA PROTEÇÃO

1. **Múltiplas camadas** de verificação
2. **Apenas frontend** pode executar comandos diretos na OLT
3. **Apenas admins** têm permissão
4. **Logs completos** de todas as tentativas
5. **APIs de leitura** permanecem acessíveis
6. **Zero impacto** no funcionamento normal do sistema