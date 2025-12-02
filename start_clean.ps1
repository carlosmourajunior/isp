# SCRIPT RÁPIDO DE DEPLOY COM SCHEDULER AUTOMÁTICO
# Para uso rápido sem verificações detalhadas

Write-Host "🚀 Iniciando o sistema completo..." -ForegroundColor Green

# 1. Deploy dos serviços principais
Write-Host "📋 Subindo serviços principais..." -ForegroundColor Yellow
docker compose -f docker-compose.yml -f docker-compose.security.yml -f docker-compose.firewall.yml up -d

# 2. Aguardar serviços ficarem prontos
Write-Host "⏳ Aguardando serviços inicializarem..." -ForegroundColor Yellow
Start-Sleep -Seconds 15

# 2.1. Aplicar migrations do banco de dados
Write-Host "🔧 Aplicando migrations do banco de dados..." -ForegroundColor Yellow
docker compose exec -T web python manage.py migrate --noinput

# 3. Verificar se há dados do sistema
Write-Host "📊 Verificando dados do sistema..." -ForegroundColor Yellow
try {
    $recordCount = docker compose exec -T web python manage.py shell -c "from olt.models import OltSystemStats; print(OltSystemStats.objects.count())" 2>$null | Select-Object -Last 1
    $recordCount = $recordCount -replace '\r|\n', ''
    
    if ([string]::IsNullOrEmpty($recordCount) -or [int]$recordCount -lt 1) {
        Write-Host "🔄 Nenhum dado encontrado, fazendo atualização inicial COMPLETA..." -ForegroundColor Cyan
        Write-Host "   (Isso pode levar alguns minutos - ONUs, Clientes, Portas, OLT...)" -ForegroundColor Gray
        docker compose exec web python manage.py collect_olt_periodic --once
    } else {
        Write-Host "✅ Dados do sistema encontrados: $recordCount registros da OLT" -ForegroundColor Green
    }
} catch {
    Write-Host "⚠️ Erro ao verificar dados, fazendo atualização inicial..." -ForegroundColor Yellow
    docker compose exec web python manage.py collect_olt_periodic --once
}

# 4. Iniciar scheduler de atualização completa (1 hora)
Write-Host "⏰ Iniciando atualização COMPLETA automática a cada 1 hora..." -ForegroundColor Yellow
docker compose -f docker-compose.scheduler.yml up -d

# 5. Status final
Write-Host ""
Write-Host "🎉 Sistema iniciado com sucesso!" -ForegroundColor Green
Write-Host ""
Write-Host "📊 Status dos serviços:" -ForegroundColor Cyan
docker compose ps
Write-Host ""
Write-Host "⚡ Status do scheduler:" -ForegroundColor Cyan
docker compose -f docker-compose.scheduler.yml ps
Write-Host ""
Write-Host "🔗 Acessos disponíveis:" -ForegroundColor Cyan
Write-Host "   📈 Dashboard OLT: http://localhost:8000" -ForegroundColor White
Write-Host "   📊 Grafana: http://localhost:3000 (admin/admin)" -ForegroundColor White
Write-Host "   🔍 Prometheus: http://localhost:9090" -ForegroundColor White
Write-Host ""
Write-Host "📋 Funcionalidades ativas:" -ForegroundColor Cyan
Write-Host "   ✅ Atualização automática COMPLETA: A cada 1 hora" -ForegroundColor Green
Write-Host "   ✅ Inclui: ONUs, Clientes, Portas, Dados OLT, MACs" -ForegroundColor Green
Write-Host "   ✅ Gráficos de performance: CPU e memória" -ForegroundColor Green
Write-Host "   ✅ Histórico: 7 dias de dados" -ForegroundColor Green
Write-Host "   ✅ Dashboard otimizado: Sem coleta automática" -ForegroundColor Green
Write-Host ""
Write-Host "🛠  Comandos úteis:" -ForegroundColor Cyan
Write-Host "   Ver logs scheduler: docker compose -f docker-compose.scheduler.yml logs -f" -ForegroundColor Gray
Write-Host "   Atualização manual completa: docker compose exec web python manage.py collect_olt_periodic --once" -ForegroundColor Gray
Write-Host "   Parar scheduler: docker compose -f docker-compose.scheduler.yml down" -ForegroundColor Gray