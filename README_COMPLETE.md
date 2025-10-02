# 🚀 Sistema ISP - OLT Management com Monitoramento Completo

Sistema completo de gerenciamento de OLT com monitoramento avançado, alertas automáticos e dashboards em tempo real.

## 📋 Características

### 🏗️ **Aplicação Principal**
- **Django 4.x** com REST API completa
- **PostgreSQL** para persistência de dados
- **Redis** para cache e filas
- **RQ Worker** para processamento assíncrono
- **Scheduler** para tarefas agendadas

### 📊 **Sistema de Monitoramento**
- **Prometheus** - Coleta de métricas
- **Grafana** - Dashboards visuais
- **Alertmanager** - Gestão de alertas
- **Node Exporter** - Métricas do sistema
- **Redis/PostgreSQL Exporters** - Métricas dos serviços

### 🔍 **Observabilidade**
- Logging estruturado (API, segurança, performance)
- Health checks completos
- Métricas personalizadas da OLT
- Alertas automáticos por email/webhook
- Monitoramento de disponibilidade

## 🚀 Instalação e Início Rápido

### 1. **Pré-requisitos**
```bash
# Docker e Docker Compose
docker --version
docker-compose --version

# Python 3.8+ (para scripts de gerenciamento)
python --version
```

### 2. **Instalação Automática**
```bash
# Clone o repositório
git clone <seu-repositorio>
cd isp

# Instalar sistema completo
python start_system.py
```

### 3. **Ou usando Makefile**
```bash
# Ver comandos disponíveis
make help

# Setup completo para desenvolvimento
make dev-setup

# Ou iniciar sistema
make start
```

## 🛠️ Comandos Principais

### **Script de Inicialização**
```bash
python start_system.py          # Instalar e iniciar tudo
python start_system.py stop     # Parar sistema
python start_system.py restart  # Reiniciar sistema
python start_system.py status   # Ver status
python start_system.py logs     # Ver logs
```

### **Makefile (Recomendado)**
```bash
make start          # Iniciar sistema
make stop           # Parar sistema
make restart        # Reiniciar sistema
make status         # Status dos serviços
make logs           # Logs em tempo real
make health         # Verificar saúde dos serviços
make urls           # Mostrar URLs de acesso
```

### **Gerenciamento Django**
```bash
make migrate        # Executar migrações
make createsuperuser # Criar usuário admin
make shell_plus     # Shell Django avançado
make manage ARGS="collectstatic --noinput"  # Comando Django
```

### **Monitoramento**
```bash
make test-health    # Testar health checks
make test-alerts    # Testar sistema de alertas
make metrics        # Ver métricas atuais
make monitor        # Abrir Grafana
```

### **Backup/Restore**
```bash
make backup         # Backup do banco
make restore FILE=backup.sql  # Restaurar backup
```

## 🌐 URLs de Acesso

### **Aplicação Principal**
| Serviço | URL | Credenciais |
|---------|-----|-------------|
| Django App | http://localhost:8000 | - |
| Admin Django | http://localhost:8000/admin/ | admin/admin123 |
| API REST | http://localhost:8000/api/ | JWT Token |
| Health Check | http://localhost:8000/api/health/ | Público |

### **Monitoramento**
| Serviço | URL | Credenciais |
|---------|-----|-------------|
| Grafana | http://localhost:3000/ | admin/admin123 |
| Prometheus | http://localhost:9090/ | - |
| Alertmanager | http://localhost:9093/ | - |

### **Métricas**
| Serviço | URL | Descrição |
|---------|-----|-----------|
| App Metrics | http://localhost:8000/api/metrics/ | Métricas da aplicação |
| Node Exporter | http://localhost:9100/metrics | Métricas do sistema |
| Redis Exporter | http://localhost:9121/metrics | Métricas do Redis |
| PostgreSQL Exporter | http://localhost:9187/metrics | Métricas do PostgreSQL |

## 📊 Dashboards Grafana

### **Dashboard Principal - "ISP System Overview"**
- Status geral do sistema
- Métricas de requisições HTTP
- Performance da aplicação
- Status das ONUs
- Temperaturas da OLT
- Uso de recursos

### **Dashboard de APIs - "API Monitoring"**
- Requisições por endpoint
- Tempos de resposta
- Taxa de erro
- Usuários mais ativos
- Status codes

### **Dashboard de Infraestrutura**
- CPU, Memória, Disco
- Métricas do PostgreSQL
- Métricas do Redis
- Network I/O

## 🚨 Sistema de Alertas

### **Alertas Críticos**
- ❌ Serviço indisponível
- ❌ PostgreSQL down
- ❌ Redis down
- 🌡️ Temperatura OLT > 80°C

### **Alertas de Aviso**
- ⚠️ Alta taxa de erro (>5%)
- ⚠️ Tempo de resposta alto (>2s)
- ⚠️ Alto uso de CPU (>80%)
- ⚠️ Alto uso de memória (>85%)
- ⚠️ Pouco espaço em disco (<15%)
- 🌡️ Temperatura OLT > 75°C

### **Configurar Notificações**

**Email SMTP** - Editar `monitoring/alertmanager/alertmanager.yml`:
```yaml
global:
  smtp_smarthost: 'seu-smtp.com:587'
  smtp_from: 'alertas@suaempresa.com'
  smtp_auth_username: 'usuario@suaempresa.com'
  smtp_auth_password: 'sua-senha'
```

**Webhook** - Para integração com Slack, Teams, etc:
```yaml
receivers:
  - name: 'webhook-slack'
    webhook_configs:
      - url: 'https://hooks.slack.com/services/SEU/WEBHOOK'
```

## 📁 Estrutura do Projeto

```
isp/
├── 📱 Aplicação
│   ├── isp/                    # Configurações Django
│   ├── olt/                    # App principal (ONUs, OLT)
│   ├── logs/                   # Logs da aplicação
│   └── data/                   # Dados persistentes
│
├── 📊 Monitoramento
│   ├── monitoring/
│   │   ├── prometheus/         # Configurações Prometheus
│   │   ├── grafana/           # Dashboards Grafana
│   │   └── alertmanager/      # Configurações alertas
│   │
├── 🐳 Docker
│   ├── docker-compose.yml     # Stack completa
│   ├── Dockerfile            # Imagem da aplicação
│   └── entrypoint.sh         # Script de entrada
│
└── 🛠️ Scripts
    ├── start_system.py       # Inicialização completa
    ├── Makefile             # Comandos de gerenciamento
    └── requirements.txt     # Dependências Python
```

## 📋 Logs e Arquivos

### **Logs da Aplicação**
```
logs/
├── django.log          # Logs gerais
├── api_access.log      # Acessos à API
├── security.log        # Eventos de segurança
└── performance.log     # Performance e latência
```

### **Dados Persistentes**
```
data/
├── postgres/          # Dados PostgreSQL
├── redis/             # Dados Redis
├── logs/              # Logs dentro dos containers
├── media/             # Arquivos de upload
└── staticfiles/       # Arquivos estáticos
```

## 🔧 Desenvolvimento

### **Configuração de Desenvolvimento**
```bash
# Setup completo
make dev-setup

# Restart rápido durante desenvolvimento
make dev-restart

# Ver logs da aplicação
make logs-app

# Shell Django avançado
make shell_plus
```

### **Executar Testes**
```bash
make test
make test-health
make test-alerts
```

### **Debug**
```bash
# Logs específicos
make logs-app          # App logs
make logs-db           # Database logs
make logs-monitoring   # Monitoring logs

# Status detalhado
make health
make status
```

## 🔒 Produção

### **Checklist de Produção**
```bash
# Verificar configurações
make production-check
```

### **Configurações Importantes**
1. **Alterar senhas padrão**:
   - Grafana: admin/admin123
   - Django: admin/admin123

2. **Configurar .env**:
   ```env
   DEBUG=False
   SECRET_KEY=sua-chave-secreta-forte
   ALLOWED_HOSTS=seu-dominio.com
   ```

3. **Configurar HTTPS** com reverse proxy (nginx/traefik)

4. **Configurar backup automático**:
   ```bash
   # Adicionar ao crontab
   0 2 * * * cd /path/to/isp && make backup
   ```

## 🆘 Troubleshooting

### **Problemas Comuns**

**Serviços não iniciam:**
```bash
make logs           # Ver logs de erro
make status         # Verificar status
docker system prune # Limpar Docker
```

**Métricas não aparecem:**
```bash
curl http://localhost:8000/api/metrics/  # Testar endpoint
curl http://localhost:9090/api/v1/targets # Ver targets Prometheus
```

**Alertas não funcionam:**
```bash
make test-alerts    # Testar sistema
curl http://localhost:9093/-/healthy     # Verificar Alertmanager
```

**Banco de dados com problemas:**
```bash
make logs-db        # Ver logs PostgreSQL
make sh web         # Entrar no container
python manage.py dbshell  # Shell do banco
```

### **Reset Completo**
```bash
make clean          # Limpar tudo
make dev-setup      # Reinstalar
```

## 📞 Suporte

### **Monitoramento em Tempo Real**
- **Grafana**: Dashboards visuais em http://localhost:3000
- **Prometheus**: Queries em http://localhost:9090
- **Logs**: `make logs` para logs em tempo real

### **Comandos de Diagnóstico**
```bash
make health         # Status geral
make test-health    # Testes completos
make metrics        # Métricas atuais
make status         # Status dos containers
```

---

**🎉 Sistema pronto para uso!** 

Execute `make help` para ver todos os comandos disponíveis ou `python start_system.py` para inicialização automática completa.