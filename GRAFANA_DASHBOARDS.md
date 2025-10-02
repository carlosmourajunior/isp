# 📊 Dashboards Grafana - Sistema ISP

## 🚀 Como Acessar os Dashboards

### **1. Acesso ao Grafana**
- **URL**: http://localhost:3000
- **Usuário**: `admin`
- **Senha**: `admin123`

### **2. Dashboards Disponíveis**

#### **📈 ISP System Overview**
- **URL**: http://localhost:3000/d/isp-overview
- **Conteúdo**:
  - Requisições por segundo
  - Total de requisições
  - Tempo de resposta (percentis)
  - Uso do sistema (CPU/Memória)
  - Status das ONUs
  - Temperaturas da OLT

#### **🏗️ Infrastructure Monitoring**
- **URL**: http://localhost:3000/d/infrastructure
- **Conteúdo**:
  - CPU Usage
  - Memory Usage
  - Database Connections
  - Redis Connections
  - Disk Usage

#### **🔌 API Monitoring**
- **URL**: http://localhost:3000/d/api-monitoring
- **Conteúdo**:
  - Requisições por endpoint
  - Requisições por status code
  - Taxa de erro
  - Tempo de resposta por endpoint

## 🔧 Solução de Problemas

### **Problema 1: Dashboards Não Aparecem**

**Solução**:
```powershell
# Reiniciar Grafana
docker-compose restart grafana

# Aguardar 15 segundos
Start-Sleep -Seconds 15

# Verificar se está funcionando
Invoke-WebRequest -Uri "http://localhost:3000/api/health"
```

### **Problema 2: "No Data" nos Gráficos**

**Verificar se o Prometheus está coletando métricas**:
```powershell
# Testar métricas da aplicação
Invoke-WebRequest -Uri "http://localhost:8000/api/metrics/"

# Verificar targets do Prometheus
Invoke-RestMethod -Uri "http://localhost:9090/api/v1/targets"
```

**Gerar tráfego para ver dados**:
```powershell
# Fazer algumas requisições para gerar métricas
for ($i=1; $i -le 10; $i++) {
    Invoke-RestMethod -Uri "http://localhost:8000/api/health/"
    Start-Sleep -Seconds 1
}
```

### **Problema 3: Erro no Datasource**

**Verificar configuração**:
1. No Grafana, vá em **Configuration > Data Sources**
2. Verificar se o Prometheus está configurado como:
   - **URL**: `http://prometheus:9090`
   - **Access**: `Server (default)`

## 📋 Métricas Disponíveis

### **Métricas da Aplicação Django**
```promql
# Total de requisições
django_requests_total

# Tempo de resposta
django_request_duration_seconds

# Uso de sistema
system_cpu_usage_percent
system_memory_usage_percent
system_disk_usage_percent

# Conexões de banco
django_db_connections_active

# ONUs da OLT
olt_onus_total{status="online"}
olt_onus_total{status="offline"}

# Temperaturas da OLT
olt_temperature_celsius
```

### **Métricas de Sistema (Node Exporter)**
```promql
# CPU
100 - (avg(rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)

# Memória
(node_memory_MemTotal_bytes - node_memory_MemAvailable_bytes) / node_memory_MemTotal_bytes * 100

# Disco
(node_filesystem_size_bytes - node_filesystem_free_bytes) / node_filesystem_size_bytes * 100
```

### **Métricas do PostgreSQL**
```promql
# Conexões
pg_stat_database_numbackends

# Transações
rate(pg_stat_database_xact_commit[5m])
```

### **Métricas do Redis**
```promql
# Clientes conectados
redis_connected_clients

# Memória usada
redis_memory_used_bytes
```

## 🎯 Queries Úteis

### **Taxa de Erro da API**
```promql
(sum(rate(django_requests_total{status=~"5.."}[5m])) / sum(rate(django_requests_total[5m]))) * 100
```

### **Requisições por Endpoint**
```promql
sum(rate(django_requests_total[5m])) by (endpoint)
```

### **Tempo de Resposta (95th Percentile)**
```promql
histogram_quantile(0.95, rate(django_request_duration_seconds_bucket[5m])) * 1000
```

### **Uso de CPU**
```promql
100 - (avg(rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)
```

## 🔄 Atualizar Dashboards

### **Método 1: Reiniciar Container**
```powershell
docker-compose restart grafana
```

### **Método 2: Importar Manualmente**
1. No Grafana, vá em **Dashboards > Import**
2. Copie o conteúdo de um arquivo `.json` dos dashboards
3. Cole e clique em **Load**

## 📈 Personalização

### **Adicionar Novos Painéis**
1. Abra um dashboard existente
2. Clique em **Add Panel**
3. Configure a query Prometheus
4. Ajuste visualização e save

### **Criar Alertas**
1. Em qualquer painel, clique no título
2. **Edit > Alert**
3. Configure condições e notificações
4. Save

### **Templates/Variables**
1. **Dashboard Settings > Variables**
2. Adicionar variável (ex: `$instance`)
3. Usar na query: `django_requests_total{instance="$instance"}`

## 🎨 Temas e Aparência

### **Modo Escuro/Claro**
- **User Profile > Preferences > UI Theme**

### **Time Range Padrão**
- **Dashboard Settings > Time Options**

## 🔍 Troubleshooting Avançado

### **Verificar Logs do Grafana**
```powershell
docker-compose logs grafana --tail 50
```

### **Verificar Configuração de Datasource**
```powershell
# API do Grafana para listar datasources
$auth = [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes("admin:admin123"))
Invoke-RestMethod -Uri "http://localhost:3000/api/datasources" -Headers @{Authorization="Basic $auth"}
```

### **Testar Conectividade Prometheus**
```powershell
# Do container Grafana para Prometheus
docker-compose exec grafana wget -O- http://prometheus:9090/api/v1/targets
```

## 📊 Dashboards Recomendados

### **Para Desenvolvimento**
- **ISP System Overview** - Visão geral do sistema
- **API Monitoring** - Monitoramento das APIs

### **Para Produção**
- **Todos os dashboards** 
- **Infrastructure Monitoring** - Essencial para infraestrutura
- Configurar **alertas** para métricas críticas

### **Para Troubleshooting**
- **API Monitoring** - Para investigar problemas de performance
- **Infrastructure** - Para problemas de recursos

---

## 🎉 Resultado

Após seguir este guia, você terá:

✅ **3 dashboards funcionais** com métricas em tempo real  
✅ **Visualização de performance** da API  
✅ **Monitoramento de infraestrutura** completo  
✅ **Métricas específicas da OLT** (ONUs, temperaturas)  
✅ **Interface visual** para análise de dados  

**🔗 Links Rápidos:**
- **Grafana**: http://localhost:3000 (admin/admin123)
- **Prometheus**: http://localhost:9090
- **Métricas**: http://localhost:8000/api/metrics/