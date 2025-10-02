# Sistema de Atualização Automática - OLT

## 🕐 Atualização Automática Horária

O sistema agora executa automaticamente a cada hora (no minuto 0) uma atualização completa que inclui:

### 📋 Sequência de Atualizações:
1. **Dados do Sistema OLT** (5min timeout)
   - Versão do software (ISAM release)
   - Uptime do sistema
   - Status dos slots
   - Temperaturas de todos os sensores

2. **Ocupação das Portas** (20min timeout)
   - Contagem de usuários por porta
   - Status das portas

3. **Informações das ONUs** (20min timeout)
   - Status operacional e administrativo
   - Sinais de recepção
   - Descrições e seriais

4. **Endereços MAC** (20min timeout)
   - Mapeamento MAC/ONU
   - Atualização de endereços

5. **Clientes Fibra** (20min timeout)
   - Sincronização com sistema IXC
   - Associação cliente/ONU

### ⚙️ Configuração:
- **Scheduler**: APScheduler rodando em background
- **Worker**: RQ Worker processando as tasks
- **Timeout Total**: Máximo 1 hora por ciclo completo
- **Logs**: Registra início/fim de cada execução

### 🎯 Tasks Disponíveis:
- `comprehensive_update_task`: Atualização completa (incluindo OLT)
- `update_all_data_task`: Atualização tradicional (compatibilidade)
- `update_olt_system_task`: Apenas dados da OLT
- `hourly_update_task`: Task automática horária

### 📊 Monitoramento:
- Dashboard com informações em tempo real
- Página de tarefas (`/tasks/`) mostra execução
- Status do scheduler (`/scheduler-status/`)
- Alertas de temperatura clicáveis

### 🔄 Execução Manual:
- **Botão "Atualizar Todos os Dados"**: Execução completa manual
- **Botão "Atualizar OLT"**: Apenas dados da OLT
- **API Endpoint**: `POST /api/olt/update-system-data/`

### 📈 Benefícios:
✅ Dados sempre atualizados automaticamente
✅ Monitoramento proativo de temperaturas
✅ Detecção automática de problemas de hardware
✅ Histórico de execuções para auditoria
✅ Possibilidade de execução manual quando necessário

### ⏰ Próxima Execução:
O sistema verifica automaticamente a cada minuto se chegou a hora da execução (minuto 0 de cada hora).