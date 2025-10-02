# Sistema de Monitoramento ISP

## Visão Geral

Este sistema implementa um monitoramento completo para a aplicação ISP OLT Management, incluindo:

- **Logging estruturado** de acessos, performance e segurança
- **Health checks** e métricas de sistema
- **Monitoramento em tempo real** com Prometheus e Grafana
- **Alertas automáticos** para problemas críticos
- **Dashboards visuais** para análise de dados

## Componentes do Sistema

### 1. Logging Estruturado

#### Tipos de Logs
- **API Access**: Todos os acessos às APIs com tempos de resposta
- **Security**: Tentativas suspeitas de acesso e violações de segurança
- **Performance**: Requisições lentas e métricas de performance
- **General**: Logs gerais da aplicação Django

#### Localização dos Logs
```
logs/
├── django.log          # Logs gerais da aplicação
├── api_access.log      # Logs de acesso à API
├── security.log        # Logs de segurança
└── performance.log     # Logs de performance
```

#### Exemplo de Log de API
```
[2025-10-02 10:30:15] API_ACCESS: USER:admin IP:192.168.1.100 GET /api/onus/ STATUS:200 TIME:85.2ms
```

### 2. Health Checks

#### Endpoints Disponíveis

| Endpoint | Descrição | Uso |
|----------|-----------|-----|
| `/api/health/` | Health check básico | Load balancers |
| `/api/health/detailed/` | Health check detalhado | Diagnóstico |
| `/api/health/readiness/` | Readiness probe | Kubernetes |
| `/api/health/liveness/` | Liveness probe | Kubernetes |

#### Exemplo de Health Check Detalhado
```json
{
  "status": "healthy",
  "timestamp": "2025-10-02T10:30:15Z",
  "service": "ISP OLT Management API",
  "version": "1.0.0",
  "checks": {
    "database": {
      "status": "healthy",
      "response_time_ms": 12.5,
      "version": "PostgreSQL 13.8"
    },
    "redis": {
      "status": "healthy", 
      "response_time_ms": 3.2,
      "connected_clients": 5
    },
    "disk": {
      "status": "healthy",
      "free_percent": 45.8,
      "free_gb": 23.4
    },
    "memory": {
      "status": "healthy",
      "used_percent": 67.2
    }
  },
  "response_time_ms": 18.7
}
```

### 3. Métricas Prometheus

#### Métricas da Aplicação
- `django_requests_total` - Total de requisições por método/endpoint/status
- `django_request_duration_seconds` - Tempo de resposta das requisições
- `django_db_connections_active` - Conexões ativas do banco de dados

#### Métricas de Sistema
- `system_memory_usage_percent` - Uso de memória do sistema
- `system_cpu_usage_percent` - Uso de CPU do sistema
- `system_disk_usage_percent` - Uso de disco do sistema

#### Métricas Específicas da OLT
- `olt_onus_total{status="online|offline"}` - Total de ONUs por status
- `olt_temperature_celsius{slot, sensor}` - Temperaturas da OLT

### 4. Alertas Automáticos

#### Tipos de Alertas

**Críticos (Critical)**
- Serviço indisponível
- PostgreSQL down
- Redis down
- Temperatura OLT > 80°C

**Avisos (Warning)**
- Alta taxa de erro (>5%)
- Tempo de resposta alto (>2s)
- Alto uso de CPU (>80%)
- Alto uso de memória (>85%)
- Pouco espaço em disco (<15%)
- Temperatura OLT > 75°C

#### Notificações
- **Email**: Para alertas críticos
- **Webhook**: Integração com sistemas externos
- **Log**: Todos os alertas são registrados

## Instalação e Configuração

### 1. Pré-requisitos

```bash
# Instalar dependências Python
pip install -r requirements.txt

# Docker e Docker Compose
docker --version
docker-compose --version
```

### 2. Configuração Inicial

```bash
# Criar diretórios necessários
mkdir -p logs data/logs

# Configurar variáveis de ambiente
cp .env.example .env
# Editar .env com suas configurações
```

### 3. Iniciar Monitoramento

```bash
# Usando o script automatizado
python setup_monitoring.py start

# Ou manualmente
docker-compose -f docker-compose.monitoring.yml up -d
```

### 4. Verificar Status

```bash
# Verificar serviços
python setup_monitoring.py status

# Ver logs
python setup_monitoring.py logs

# URLs de acesso
python setup_monitoring.py urls
```

## URLs de Acesso

| Serviço | URL | Credenciais |
|---------|-----|-------------|
| Django App | http://localhost:8000 | - |
| Prometheus | http://localhost:9090 | - |
| Grafana | http://localhost:3000 | admin/admin123 |
| Alertmanager | http://localhost:9093 | - |

## Dashboards Grafana

### Dashboard Principal - "ISP System Overview"

**Painéis incluídos:**
- Status geral do sistema
- Métricas de requisições HTTP
- Performance da aplicação
- Status das ONUs
- Temperaturas da OLT
- Uso de recursos do sistema

### Dashboard de APIs - "API Monitoring"

**Painéis incluídos:**
- Requisições por endpoint
- Tempos de resposta
- Taxa de erro
- Usuários mais ativos
- Status codes

### Dashboard de Infraestrutura - "Infrastructure"

**Painéis incluídos:**
- CPU, Memória, Disco
- Métricas do PostgreSQL
- Métricas do Redis
- Network I/O

## Configuração de Alertas

### 1. Email (SMTP)

Editar `monitoring/alertmanager/alertmanager.yml`:

```yaml
global:
  smtp_smarthost: 'seu-smtp.com:587'
  smtp_from: 'alertas@suaempresa.com'
  smtp_auth_username: 'usuario@suaempresa.com'
  smtp_auth_password: 'sua-senha'
```

### 2. Webhook Personalizado

```yaml
receivers:
  - name: 'webhook-custom'
    webhook_configs:
      - url: 'https://seu-webhook.com/alertas'
        send_resolved: true
```

### 3. Integração Slack

```yaml
receivers:
  - name: 'slack-alerts'
    slack_configs:
      - api_url: 'https://hooks.slack.com/services/SEU/WEBHOOK/URL'
        channel: '#alertas'
        title: 'Alerta Sistema ISP'
```

## Manutenção

### Logs Rotativos

Os logs são automaticamente rotacionados:
- Tamanho máximo: 10MB por arquivo
- Backup: 5-10 arquivos antigos mantidos
- Formato: JSON para segurança/performance, texto para API access

### Limpeza de Dados

```bash
# Limpar logs antigos (mais de 30 dias)
find logs/ -name "*.log.*" -mtime +30 -delete

# Limpar dados antigos do Prometheus (configurado para 30 dias)
# Automático via configuração
```

### Backup de Configurações

```bash
# Backup das configurações de monitoramento
tar -czf monitoring-backup-$(date +%Y%m%d).tar.gz monitoring/
```

## Troubleshooting

### Problemas Comuns

**Serviços não iniciam:**
```bash
# Verificar logs
docker-compose -f docker-compose.monitoring.yml logs

# Verificar portas em uso
netstat -tulpn | grep -E ":(3000|9090|9093)"
```

**Métricas não aparecem:**
```bash
# Testar endpoint de métricas
curl http://localhost:8000/api/metrics/

# Verificar configuração do Prometheus
curl http://localhost:9090/api/v1/targets
```

**Alertas não funcionam:**
```bash
# Testar alerta manual
curl -X POST http://localhost:8000/api/alerts/test/ \
  -H "Content-Type: application/json" \
  -d '{"type": "test", "severity": "warning"}'
```

### Logs de Debug

```bash
# Habilitar debug no Django
export DEBUG=True

# Ver logs em tempo real
tail -f logs/django.log

# Filtrar logs de API
grep "API_ACCESS" logs/api_access.log | tail -20
```

## Segurança

### Autenticação

- Grafana: Usuário admin/admin123 (alterar na produção)
- Prometheus: Sem autenticação (configurar reverse proxy)
- APIs: JWT token required

### Firewall

```bash
# Permitir apenas IPs necessários
iptables -A INPUT -p tcp --dport 3000 -s SEU_IP -j ACCEPT
iptables -A INPUT -p tcp --dport 9090 -s SEU_IP -j ACCEPT
```

### HTTPS

Configure um reverse proxy (nginx/traefik) para HTTPS:

```nginx
server {
    listen 443 ssl;
    server_name monitoring.suaempresa.com;
    
    location /grafana/ {
        proxy_pass http://localhost:3000/;
    }
    
    location /prometheus/ {
        proxy_pass http://localhost:9090/;
    }
}
```

## Expansão do Sistema

### Adicionar Novos Alertas

1. Editar `monitoring/prometheus/rules/alerts.yml`
2. Adicionar nova regra de alerta
3. Reiniciar Prometheus

### Adicionar Novas Métricas

1. Modificar `olt/prometheus_views.py`
2. Adicionar nova métrica
3. Atualizar função de coleta

### Integração com Sistemas Externos

O sistema suporta webhooks para integração com:
- Sistemas de ticketing (JIRA, ServiceNow)
- Notificações (Slack, Teams)
- SIEM (Splunk, ELK)

## Monitoramento de Performance

### Queries Úteis no Prometheus

```promql
# Taxa de requisições por minuto
rate(django_requests_total[1m])

# Percentil 95 do tempo de resposta
histogram_quantile(0.95, rate(django_request_duration_seconds_bucket[5m]))

# ONUs offline
olt_onus_total{status="offline"}

# Temperatura máxima por slot
max by (slot) (olt_temperature_celsius)
```

### Análise de Tendências

- Usar Grafana para análise histórica
- Configurar alertas baseados em tendências
- Monitorar crescimento de uso

## Suporte

Para suporte, verifique:
1. Logs da aplicação em `logs/`
2. Status dos serviços via health checks
3. Dashboards do Grafana para métricas visuais
4. Documentação específica de cada componente