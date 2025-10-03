#!/bin/bash
# Script para investigar perda completa de dados no PostgreSQL

echo "🔍 INVESTIGAÇÃO DE PERDA COMPLETA DE DADOS"
echo "=========================================="
echo "Data: $(date)"
echo ""

# 1. Verificar se há múltiplas instâncias do PostgreSQL
echo "1️⃣ Verificando instâncias do PostgreSQL:"
echo "----------------------------------------"
docker ps -a | grep postgres
echo ""
netstat -tulpn | grep :5432 2>/dev/null || ss -tulpn | grep :5432
echo ""

# 2. Verificar logs do container do banco
echo "2️⃣ Logs recentes do banco de dados:"
echo "-----------------------------------"
docker-compose logs db --tail=50 --timestamps
echo ""

# 3. Verificar uso de memória e recursos
echo "3️⃣ Uso de recursos dos containers:"
echo "----------------------------------"
docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}"
echo ""

# 4. Verificar espaço em disco
echo "4️⃣ Espaço em disco:"
echo "-------------------"
df -h /
df -h ./data/
du -sh ./data/postgres/
echo ""

# 5. Verificar se há cron jobs ou tarefas automáticas
echo "5️⃣ Verificando cron jobs:"
echo "-------------------------"
crontab -l 2>/dev/null || echo "Nenhum cron job do usuário atual"
ls -la /etc/cron.d/ 2>/dev/null || echo "Sem acesso a /etc/cron.d/"
echo ""

# 6. Verificar processos que podem estar interferindo
echo "6️⃣ Processos relacionados ao Docker/PostgreSQL:"
echo "-----------------------------------------------"
ps aux | grep -E "(docker|postgres|postgresql)" | grep -v grep
echo ""

# 7. Verificar se há scripts executando limpeza
echo "7️⃣ Verificando se há scripts de limpeza rodando:"
echo "-----------------------------------------------"
ps aux | grep -E "(clean|prune|down.*-v)" | grep -v grep
echo ""

# 8. Verificar logs do sistema
echo "8️⃣ Logs do sistema (últimas 20 linhas relacionadas ao Docker):"
echo "-------------------------------------------------------------"
journalctl -u docker --no-pager --lines=20 2>/dev/null || echo "Sem acesso ao journalctl"
echo ""

# 9. Verificar integridade dos arquivos de dados
echo "9️⃣ Verificando integridade dos dados do PostgreSQL:"
echo "--------------------------------------------------"
ls -la data/postgres/ | head -10
echo "..."
echo "Total de arquivos na pasta de dados:"
find data/postgres/ -type f | wc -l
echo ""

# 10. Verificar se há volumes órfãos ou conflitos
echo "🔟 Verificando volumes Docker:"
echo "-----------------------------"
docker volume ls | grep -E "(postgres|isp)"
docker volume inspect $(docker-compose config --volumes) 2>/dev/null | grep -A5 -B5 Mountpoint || echo "Erro ao inspecionar volumes"
echo ""

echo "✅ Investigação concluída!"
echo ""
echo "🔍 PRÓXIMOS PASSOS:"
echo "1. Execute: docker-compose exec web python investigate_data_loss.py"
echo "2. Execute: docker-compose exec web python monitor_data_loss.py &"
echo "3. Monitore: docker-compose logs -f db web scheduler"
echo "4. Verifique se o problema se repete nos próximos minutos/horas"