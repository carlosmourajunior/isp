# 🚀 Sistema OLT - Coleta Automática e Gráficos

## ✨ Novas Funcionalidades Implementadas

### 🕐 **Atualização Automática Completa (Agendamento Periódico)**
O sistema agora atualiza **TODOS OS DADOS** automaticamente a cada **1 hora**:

**🔄 Dados Atualizados Automaticamente:**
- **ONUs**: Status, sinal, localização, MACs
- **Clientes**: Informações de fibra, contratos
- **Portas OLT**: Ocupação, usuários conectados
- **Sistema OLT**: CPU, memória, temperatura, slots
- **MACs**: Associações e validações
- **Histórico**: 7 dias de dados de performance

### 📊 **Gráficos de Performance**
Dashboard com gráficos interativos mostrando:
- Evolução da CPU e memória nos últimos 7 dias
- Estatísticas resumidas (atual, média, máxima)
- Dados em tempo real via Chart.js

### 🎯 **Dashboard Otimizado**
- **Não coleta dados automaticamente** ao abrir a página
- Mostra apenas dados históricos armazenados
- Atualização completa apenas ao clicar no botão **"Atualizar OLT"**
- Performance melhorada no carregamento
- Scheduler cuida da atualização automática em background

## 🛠 Como Usar

### 🚀 **Inicialização Rápida**

**Windows (PowerShell):**
```powershell
.\start_with_scheduler.ps1
```

**Linux/Mac:**
```bash
chmod +x start_with_scheduler.sh
./start_with_scheduler.sh
```

### 📋 **Comandos Manuais**

#### Iniciar todos os serviços:
```bash
docker compose -f docker-compose.yml -f docker-compose.security.yml -f docker-compose.firewall.yml up -d
```

#### Iniciar apenas a coleta automática:
```bash
docker compose -f docker-compose.scheduler.yml up -d
```

#### Fazer coleta única (manual):
```bash
docker compose exec web python manage.py collect_olt_periodic --once
```

#### Ver logs da coleta automática:
```bash
docker compose -f docker-compose.scheduler.yml logs -f olt-scheduler
```

#### Parar coleta automática:
```bash
docker compose -f docker-compose.scheduler.yml down
```

## 📈 **Endpoints da API**

### Dados dos Gráficos
```
GET /api/olt/chart-data/
```
Retorna dados formatados para Chart.js com histórico dos últimos 7 dias.

### Estatísticas da OLT
```
GET /api/olt/system-stats/
```
Retorna última medição da OLT (CPU, memória, modelo).

### Histórico Completo
```
GET /api/olt/system-history/
```
Retorna todos os registros históricos dos últimos 7 dias.

## 🗂 **Estrutura dos Dados**

### Modelo OltSystemStats
```python
- cpu_percent: int (0-100%)
- mem_percent: int (0-100%)  
- model: str (ex: "FX-4")
- uptime_days: int
- measured_at: datetime
```

### Retenção Automática
- Dados são mantidos por **7 dias**
- Limpeza automática de registros antigos
- Otimização com índices no banco

## 🎨 **Dashboard**

### Informações Exibidas:
1. **Sistema**: Versão, modelo, CPU, memória, uptime
2. **Slots**: Total, operacionais, offline
3. **Temperatura**: Média, máxima, alertas
4. **Gráficos**: CPU/memória dos últimos 7 dias
5. **Estatísticas**: Valores atuais e médios

### Botões de Ação:
- **"Atualizar OLT"**: Coleta manual de novos dados
- Acesso aos relatórios de ONUs e sinais

## 🔧 **Configuração Avançada**

### Alterar Intervalo de Coleta:
Edite o comando no `docker-compose.scheduler.yml`:
```yaml
command: python manage.py collect_olt_periodic --interval 7200  # 2 horas
```

### Coleta Manual via Código:
```python
from olt.utils import OltSystemCollector
collector = OltSystemCollector()
result = collector.collect_all_system_data()
```

### Verificar Dados Históricos:
```python
from olt.models import OltSystemStats
stats = OltSystemStats.objects.all().order_by('-measured_at')
latest = OltSystemStats.get_latest()
```

## 📊 **Monitoramento**

### Grafana Dashboards:
- URL: http://localhost:3000
- Login: admin/admin
- Métricas PostgreSQL, Redis, sistema

### Prometheus Metrics:
- URL: http://localhost:9090
- Coleta métricas do sistema e aplicação

### Logs:
```bash
# Logs da aplicação
docker compose logs -f web

# Logs do scheduler
docker compose -f docker-compose.scheduler.yml logs -f

# Logs específicos
tail -f logs/olt_scheduler.log
```

## 🚨 **Troubleshooting**

### Scheduler não inicia:
```bash
# Verificar se não há conflito
docker ps | grep scheduler

# Parar e reiniciar
docker compose -f docker-compose.scheduler.yml down
docker compose -f docker-compose.scheduler.yml up -d
```

### Gráficos não carregam:
1. Verificar autenticação no navegador
2. Conferir se há dados históricos:
   ```bash
   docker compose exec web python manage.py shell -c "from olt.models import OltSystemStats; print(OltSystemStats.objects.count())"
   ```

### Coleta falha:
1. Verificar conexão com OLT nas variáveis de ambiente
2. Testar coleta manual:
   ```bash
   docker compose exec web python manage.py collect_olt_periodic --once
   ```

## 📋 **Status dos Serviços**

```bash
docker compose ps                                    # Serviços principais
docker compose -f docker-compose.scheduler.yml ps   # Scheduler
```

## 🎯 **Resumo das Melhorias**

✅ **Performance**: Dashboard não coleta dados automaticamente  
✅ **Automação**: Coleta a cada 1 hora sem intervenção  
✅ **Visualização**: Gráficos interativos de 7 dias  
✅ **Histórico**: Dados preservados com limpeza automática  
✅ **Flexibilidade**: Coleta manual via botão quando necessário  
✅ **Monitoramento**: Logs e métricas completas