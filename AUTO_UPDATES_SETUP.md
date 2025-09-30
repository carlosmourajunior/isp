# Atualizações Automáticas - Configuração e Uso

Este documento explica como configurar e usar o sistema de atualizações automáticas a cada hora.

## Visão Geral

O sistema foi configurado para executar automaticamente todas as atualizações (portas, ONUs, MACs e clientes) a cada hora, usando Django RQ Scheduler.

## Arquivos Criados/Modificados

### 1. `requirements.txt`
- Adicionado `django-rq-scheduler==2.1.0` para agendamento de tarefas

### 2. `isp/settings.py`
- Adicionado `django_rq_scheduler` aos `INSTALLED_APPS`

### 3. `olt/tasks.py`
- Adicionada função `hourly_update_task()` para execução automática
- Função executa toda a sequência de atualizações (portas → ONUs → MACs → clientes)

### 4. `olt/management/commands/setup_auto_updates.py`
- Comando Django para configurar agendamentos
- Permite listar, limpar e criar novos agendamentos

### 5. `docker-compose.yml`
- Adicionado serviço `rq_scheduler` para processar agendamentos

### 6. `setup_auto_updates.py`
- Script para facilitar a configuração inicial

## Como Usar

### 1. **Primeira Configuração (Execute uma única vez)**

```bash
# Rebuildar containers com as novas dependências
docker-compose down
docker-compose up --build -d

# Executar migrações e configurar agendamentos
docker-compose exec web python setup_auto_updates.py
```

### 2. **Verificar Agendamentos**

```bash
# Listar todos os agendamentos configurados
docker-compose exec web python manage.py setup_auto_updates --list

# Ver logs do scheduler
docker-compose logs rq_scheduler

# Ver logs do worker
docker-compose logs rq_worker
```

### 3. **Gerenciar Agendamentos**

```bash
# Recriar agendamentos (remove existentes e cria novos)
docker-compose exec web python manage.py setup_auto_updates

# Apenas remover agendamentos existentes
docker-compose exec web python manage.py setup_auto_updates --clear

# Listar agendamentos
docker-compose exec web python manage.py setup_auto_updates --list
```

## Agendamento Configurado

### Atualização Automática Horária
- **Frequência**: A cada hora (no minuto 0)
- **Cron**: `0 * * * *`
- **Sequência de execução**:
  1. 🔌 Atualização de Portas (`update_port_occupation_task`)
  2. 📡 Atualização de ONUs (`update_onus_task`)
  3. 🔗 Atualização de MACs (`update_mac_task`)
  4. 👥 Atualização de Clientes (`update_clientes_task`)

### Exemplos de Horários
- 09:00, 10:00, 11:00, 12:00, 13:00, etc.
- A sequência completa pode levar alguns minutos para ser concluída

## Monitoramento

### 1. **Dashboard do Django RQ**
- **URL**: http://localhost:8000/django-rq/
- Visualiza filas, jobs ativos, concluídos e falhas
- Permite cancelar jobs em execução

### 2. **Logs dos Containers**
```bash
# Ver todos os logs
docker-compose logs -f

# Logs específicos do scheduler
docker-compose logs -f rq_scheduler

# Logs específicos do worker
docker-compose logs -f rq_worker

# Logs da aplicação web
docker-compose logs -f web
```

### 3. **Verificar Status no Django Admin**
- **URL**: http://localhost:8000/admin/
- Navegar para "Django RQ Scheduler" → "Repeatable jobs"

## Estrutura dos Containers

```yaml
services:
  web:          # Aplicação Django principal
  db:           # PostgreSQL
  redis:        # Redis (broker para RQ)
  rq_worker:    # Processa jobs da fila
  rq_scheduler: # Agenda jobs periódicos (NOVO)
```

## Troubleshooting

### Problema: Agendamentos não executam
```bash
# Verificar se o scheduler está rodando
docker-compose ps

# Verificar logs do scheduler
docker-compose logs rq_scheduler

# Recriar agendamentos
docker-compose exec web python manage.py setup_auto_updates
```

### Problema: Jobs ficam em fila mas não executam
```bash
# Verificar se o worker está rodando
docker-compose logs rq_worker

# Reiniciar o worker
docker-compose restart rq_worker
```

### Problema: Erro ao configurar agendamentos
```bash
# Executar migrações manualmente
docker-compose exec web python manage.py migrate

# Tentar configurar novamente
docker-compose exec web python setup_auto_updates.py
```

## Personalização

### Alterar Frequência de Execução

Edite o arquivo `olt/management/commands/setup_auto_updates.py`:

```python
# Para executar a cada 30 minutos
cron_string='*/30 * * * *'

# Para executar a cada 2 horas
cron_string='0 */2 * * *'

# Para executar apenas às 8h e 20h
cron_string='0 8,20 * * *'
```

### Adicionar Novos Agendamentos

No mesmo arquivo, adicione novos jobs:

```python
# Exemplo: backup diário às 2h da manhã
RepeatableJob.objects.create(
    name='Backup Diário',
    callable='olt.tasks.backup_task',
    cron_string='0 2 * * *',
    enabled=True,
    queue='default'
)
```

## Comandos Úteis

```bash
# Parar tudo
docker-compose down

# Subir em background
docker-compose up -d

# Rebuild containers
docker-compose up --build -d

# Ver status dos containers
docker-compose ps

# Executar shell no container web
docker-compose exec web bash

# Executar comando Django
docker-compose exec web python manage.py <comando>
```

## Logs de Exemplo

Quando funcionando corretamente, você verá logs similares a:

```
rq_scheduler-1 | INFO 2025-09-30 13:00:00 Scheduling hourly_update_task
rq_worker-1    | INFO 2025-09-30 13:00:01 Processing job: hourly_update_task
rq_worker-1    | INFO 2025-09-30 13:00:02 Job completed: Atualização automática iniciada
```