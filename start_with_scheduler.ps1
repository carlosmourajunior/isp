# Script PowerShell para iniciar sistema OLT com coleta automática

Write-Host "🚀 === INICIANDO SISTEMA OLT COM COLETA AUTOMÁTICA ===" -ForegroundColor Green
Write-Host

# 1. Subir serviços principais se não estiverem rodando
Write-Host "📋 Verificando serviços principais..." -ForegroundColor Yellow
$webStatus = docker compose ps | Select-String "web.*Up"
if (-not $webStatus) {
    Write-Host "🔄 Iniciando serviços principais..." -ForegroundColor Cyan
    docker compose -f docker-compose.yml -f docker-compose.security.yml -f docker-compose.firewall.yml up -d
    Write-Host "⏳ Aguardando serviços ficarem prontos..." -ForegroundColor Yellow
    Start-Sleep -Seconds 10
} else {
    Write-Host "✅ Serviços principais já estão rodando" -ForegroundColor Green
}

# 2. Verificar se há dados históricos
Write-Host
Write-Host "📊 Verificando dados históricos..." -ForegroundColor Yellow
try {
    $recordCount = docker compose exec -T web python manage.py shell -c "from olt.models import OltSystemStats; print(OltSystemStats.objects.count())" 2>$null | Select-Object -Last 1
    Write-Host "📈 Registros históricos encontrados: $recordCount" -ForegroundColor Cyan
    
    # 3. Se há poucos dados, fazer uma coleta inicial
    if ([int]$recordCount -lt 2) {
        Write-Host "🔄 Fazendo coleta inicial de dados..." -ForegroundColor Cyan
        docker compose exec web python manage.py collect_olt_periodic --once
    } else {
        Write-Host "✅ Dados históricos suficientes encontrados" -ForegroundColor Green
    }
} catch {
    Write-Host "⚠️ Erro ao verificar dados históricos, continuando..." -ForegroundColor Yellow
}

# 4. Iniciar coleta automática
Write-Host
Write-Host "⏰ Iniciando coleta automática a cada 1 hora..." -ForegroundColor Yellow
Write-Host "📝 Logs serão salvos em ./logs/olt_scheduler.log" -ForegroundColor Gray

# Verificar se o scheduler já está rodando
$schedulerStatus = docker ps | Select-String "isp_olt_scheduler"
if ($schedulerStatus) {
    Write-Host "⚠️ Scheduler já está rodando, parando primeiro..." -ForegroundColor Yellow
    docker compose -f docker-compose.scheduler.yml down
}

# Iniciar o scheduler
docker compose -f docker-compose.scheduler.yml up -d

Write-Host
Write-Host "🎉 === SISTEMA INICIADO COM SUCESSO ===" -ForegroundColor Green
Write-Host
Write-Host "🔗 Acessos:" -ForegroundColor Cyan
Write-Host "   Dashboard: http://localhost:8000" -ForegroundColor White
Write-Host "   Grafana: http://localhost:3000 (admin/admin)" -ForegroundColor White
Write-Host "   Prometheus: http://localhost:9090" -ForegroundColor White
Write-Host
Write-Host "📋 Comandos úteis:" -ForegroundColor Cyan
Write-Host "   Ver logs do scheduler: docker compose -f docker-compose.scheduler.yml logs -f" -ForegroundColor Gray
Write-Host "   Parar coleta automática: docker compose -f docker-compose.scheduler.yml down" -ForegroundColor Gray
Write-Host "   Coleta manual única: docker compose exec web python manage.py collect_olt_periodic --once" -ForegroundColor Gray
Write-Host "   Status dos serviços: docker compose ps" -ForegroundColor Gray
Write-Host
Write-Host "⏰ A coleta automática está configurada para executar a cada 1 hora" -ForegroundColor Yellow
Write-Host "🎯 No dashboard, use o botão 'Atualizar OLT' para coletas manuais" -ForegroundColor Yellow