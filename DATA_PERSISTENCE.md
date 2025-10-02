# Estrutura de Persistência de Dados

Este projeto está configurado para persistir todos os dados dos containers em diretórios locais.

## 📁 Estrutura de Diretórios

```
data/
├── postgres/     # Dados do banco PostgreSQL
├── redis/        # Dados do Redis (RDB + AOF)
├── media/        # Arquivos de mídia do Django
├── staticfiles/  # Arquivos estáticos coletados
└── logs/         # Logs da aplicação
```

version: "3.3"

services:
  db:          # Banco PostgreSQL
  web:         # Aplicação Django
  redis:       # Cache e fila de tarefas
  rq_worker:   # Worker para processar tarefas em background
  scheduler:   # Serviço dedicado para tarefas agendadas

## 🔄 **Scheduler de Tarefas**

O sistema inclui um serviço dedicado para executar tarefas automáticas:

### Funcionalidades
- ⏰ **Execução Automática**: Tarefas executam a cada hora
- 🔄 **Atualização Completa**: Inclui dados da OLT, ONUs, MACs e clientes
- 📊 **Monitoramento**: Status visível via interface web
- 🛡️ **Recuperação**: Restart automático em caso de falha

### Comandos Úteis
```bash
# Ver logs do scheduler
docker-compose logs -f scheduler

# Verificar status do scheduler
docker-compose exec web python manage.py setup_auto_updates --status

# Reiniciar apenas o scheduler
docker-compose restart scheduler
```

### PostgreSQL
- **Localização**: `./data/postgres`
- **Dados**: Todos os dados do banco são persistidos
- **Backup**: Copie o diretório `data/postgres` para backup completo

### Redis
- **Localização**: `./data/redis`
- **Configuração**: RDB + AOF habilitados
- **Snapshot**: A cada 60 segundos se houver pelo menos 1 mudança
- **AOF**: Sincronização a cada segundo

### Django - Arquivos de Mídia
- **Localização**: `./data/media`
- **Conteúdo**: Arquivos enviados pelos usuários
- **Configuração**: Mapeado para `/code/media` no container

### Django - Arquivos Estáticos
- **Localização**: `./data/staticfiles`
- **Conteúdo**: CSS, JS, imagens estáticas coletadas
- **Atualização**: Executado automaticamente no entrypoint

### Logs
- **Localização**: `./data/logs`
- **Conteúdo**: Logs da aplicação Django e workers
- **Rotação**: Configure conforme necessário

## 🛠️ Comandos Úteis

### Backup Completo
```bash
# Criar backup
tar -czf backup-$(date +%Y%m%d-%H%M%S).tar.gz data/

# Restaurar backup
tar -xzf backup-YYYYMMDD-HHMMSS.tar.gz
```

### Limpeza de Dados
```bash
# CUIDADO: Remove todos os dados persistidos
docker-compose down
Remove-Item -Recurse -Force data\*
```

### Verificar Espaço em Disco
```bash
# Windows PowerShell
Get-ChildItem -Path "data" -Recurse | Measure-Object -Property Length -Sum

# Linux/WSL
du -sh data/*
```

## 🔒 Política de Restart

Todos os containers estão configurados com `restart: unless-stopped` para:
- Reiniciar automaticamente em caso de falha
- Não reiniciar se parados manualmente
- Iniciar automaticamente após reboot do sistema

## ⚠️ Importante

1. **Backup Regular**: Faça backups regulares do diretório `data/`
2. **Espaço em Disco**: Monitore o espaço disponível
3. **Permissões**: O Docker precisa ter permissões de escrita no diretório
4. **Gitignore**: Os dados não são versionados (já configurado)

## 🚀 Como Usar

```bash
# Subir com persistência
docker-compose up -d

# Verificar volumes
docker-compose ps
docker volume ls

# Logs em tempo real
docker-compose logs -f web
```