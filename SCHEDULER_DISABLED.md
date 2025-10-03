# SCHEDULER AUTOMÁTICO DESABILITADO

## ⚠️ IMPORTANTE: Sistema de Atualização Automática Desabilitado

O sistema de scheduler automático que executava atualizações a cada hora foi **DESABILITADO POR SEGURANÇA** devido a problemas de perda de dados.

## 🔧 Como Executar Atualizações Manualmente

### 1. Via Interface Web
- Acesse: http://localhost:8000/
- Faça login com admin/admin123
- Use o menu "Atualizar Dados" para executar atualizações específicas

### 2. Via API
```bash
# Atualização de clientes
curl -X POST http://localhost:8000/api/update-clientes/

# Atualização de ONUs
curl -X POST http://localhost:8000/api/update-onus/

# Atualização de ocupação de portas
curl -X POST http://localhost:8000/api/update-ports/
```

### 3. Via Linha de Comando
```bash
# Entrar no container
docker-compose exec web bash

# Executar atualizações específicas via Django shell
python manage.py shell -c "
from olt.tasks import update_clientes_task
update_clientes_task()
"
```

## 🛡️ Por que foi Desabilitado?

1. **Operações Perigosas**: Tasks automáticas executavam `DELETE` em massa
2. **Problemas de Migração**: Campos novos causavam erros após restarts
3. **Perda de Dados**: Execuções automáticas apagavam dados críticos
4. **Loops de Erro**: Falhas criavam ciclos infinitos de tentativas

## 🔄 Para Reabilitar (NÃO RECOMENDADO sem correções)

Se realmente precisar reabilitar o scheduler automático:

1. **Descomentar no docker-compose.yml** as linhas do serviço `scheduler`
2. **Descomentar no olt/scheduler.py** o código da função `schedule_hourly_update`
3. **Descomentar no olt/scheduler.py** o `scheduler.add_job` na função `start_scheduler`
4. **Executar**: `docker-compose up -d scheduler`

⚠️ **ATENÇÃO**: Só faça isso após:
- Implementar backup automático robusto
- Corrigir todas as operações de DELETE em massa
- Testar extensivamente em ambiente de desenvolvimento
- Implementar monitoramento em tempo real

## ✅ Sistema Mais Seguro

Agora o sistema:
- ✅ Não executa atualizações automáticas perigosas
- ✅ Permite atualizações manuais controladas
- ✅ Preserva dados entre restarts
- ✅ Evita loops de erro
- ✅ Mantém funcionalidade completa via interface web

## 📊 Monitoramento

Para monitorar o sistema:
```bash
# Ver status dos containers
docker-compose ps

# Ver logs
docker-compose logs -f web

# Verificar dados
docker-compose exec db psql -U postgres -d postgres -c "SELECT COUNT(*) FROM auth_user"
```