# 🔄 Sistema de Tarefas Automáticas

## ✅ Configuração Implementada

### 1. **Inicialização Automática**
- ✅ Script `entrypoint.sh` atualizado
- ✅ Verificação de conectividade (DB + Redis)
- ✅ Execução de migrations e collectstatic
- ✅ Início automático do scheduler

### 2. **Serviço Dedicado para Scheduler**
- ✅ Container `scheduler` separado
- ✅ Comando Django `run_scheduler` criado
- ✅ Restart automático em caso de falha
- ✅ Gerenciamento adequado de sinais (SIGTERM/SIGINT)

### 3. **Tarefas Automáticas Configuradas**
- ⏰ **Frequência**: A cada hora (minuto 0)
- 🔄 **Conteúdo**: 
  - Atualização de dados da OLT
  - Sincronização de ONUs
  - Atualização de MACs
  - Sincronização de clientes

## 🚀 Como Funciona

### Ao Subir o Sistema
1. **Entrypoint** verifica dependências
2. **Migrations** são executadas
3. **Static files** são coletados
4. **Scheduler** é iniciado automaticamente
5. **Aplicação** fica disponível

### Serviços Rodando
```bash
docker-compose ps
```
```
SERVICE      STATUS
db           Up (PostgreSQL)
redis        Up (Cache/Queue)
web          Up (Django App)
rq_worker    Up (Background Tasks)
scheduler    Up (Automatic Tasks)  ← NOVO!
```

## 🛠️ Comandos Úteis

### Verificar Status
```bash
# Status geral
docker-compose ps

# Logs do scheduler
docker-compose logs -f scheduler

# Status das tarefas agendadas
docker-compose exec web python manage.py setup_auto_updates --status
```

### Controle Manual
```bash
# Reiniciar scheduler
docker-compose restart scheduler

# Parar/iniciar serviços específicos
docker-compose stop scheduler
docker-compose start scheduler

# Executar tarefa manual
docker-compose exec web python manage.py setup_auto_updates --start
```

### Monitoramento
```bash
# Ver próximas execuções
docker-compose exec web python manage.py setup_auto_updates --status

# Acompanhar logs em tempo real
docker-compose logs -f scheduler rq_worker

# Verificar fila de tarefas
docker-compose exec web python manage.py shell -c "
from django_rq import get_queue
queue = get_queue('default')
print(f'Tarefas na fila: {len(queue)}')
print(f'Jobs executando: {len(queue.started_job_registry)}')
"
```

## 📊 Interface de Monitoramento

O sistema inclui endpoints para monitorar o scheduler:
- **Status**: `/scheduler-status/` (se configurado)
- **Admin Django**: Seção de tarefas agendadas
- **Logs**: Disponíveis via `docker-compose logs`

## ⚠️ Importante

1. **Dependencies**: O scheduler depende do Redis e PostgreSQL
2. **Timeout**: Tarefas têm timeout de 1 hora
3. **Logs**: Armazenados em `./data/logs/`
4. **Recovery**: Restart automático configurado
5. **Queue**: Usa Redis como backend de fila

## 🔧 Troubleshooting

### Scheduler não inicia
```bash
# Verificar logs
docker-compose logs scheduler

# Verificar conectividade
docker-compose exec scheduler nc -z redis 6379
docker-compose exec scheduler nc -z db 5432

# Reiniciar dependências
docker-compose restart redis db
```

### Tarefas não executam
```bash
# Verificar worker
docker-compose logs rq_worker

# Verificar fila
docker-compose exec web python manage.py setup_auto_updates --status

# Limpar fila (se necessário)
docker-compose exec web python manage.py shell -c "
from django_rq import get_queue
queue = get_queue('default')
queue.empty()
"
```

## 🎯 Benefícios

- ✅ **Automação Completa**: Zero intervenção manual
- ✅ **Resiliente**: Restart automático e recuperação de falhas
- ✅ **Monitorável**: Logs e status detalhados
- ✅ **Escalável**: Fácil ajuste de frequência e tarefas
- ✅ **Persistente**: Dados mantidos mesmo com restart
- ✅ **Isolado**: Scheduler em container separado