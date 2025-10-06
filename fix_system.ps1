# Script PowerShell para corrigir problemas do sistema Docker ISP

Write-Host "SCRIPT DE CORRECAO DO SISTEMA ISP" -ForegroundColor Cyan
Write-Host "==================================" -ForegroundColor Cyan

Write-Host ""
Write-Host "1. Parando containers..." -ForegroundColor Yellow
docker-compose down

Write-Host ""
Write-Host "2. Verificando configuracao do PostgreSQL..." -ForegroundColor Yellow
if (Test-Path "./data/postgres/postgresql.conf") {
    Write-Host "Configuracao do PostgreSQL encontrada" -ForegroundColor Green
} else {
    Write-Host "Configuracao do PostgreSQL nao encontrada" -ForegroundColor Red
}

Write-Host ""
Write-Host "3. Iniciando banco de dados..." -ForegroundColor Yellow
docker-compose up -d db

Write-Host ""
Write-Host "4. Aguardando banco ficar pronto..." -ForegroundColor Yellow
Start-Sleep -Seconds 30

Write-Host ""
Write-Host "5. Testando conexao com banco..." -ForegroundColor Yellow
try {
    docker-compose exec db psql -U postgres -c "SELECT version();"
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Banco conectado com sucesso" -ForegroundColor Green
    } else {
        throw "Erro na conexao"
    }
} catch {
    Write-Host "Erro na conexao com banco. Recriando volume..." -ForegroundColor Red
    docker-compose down -v
    docker volume prune -f
    Write-Host "Reiniciando banco..." -ForegroundColor Yellow
    docker-compose up -d db
    Start-Sleep -Seconds 30
}

Write-Host ""
Write-Host "6. Iniciando aplicacao..." -ForegroundColor Yellow
docker-compose up -d web

Write-Host ""
Write-Host "7. Aguardando aplicacao..." -ForegroundColor Yellow
Start-Sleep -Seconds 15

Write-Host ""
Write-Host "8. Aplicando migrations..." -ForegroundColor Yellow
docker-compose exec web python manage.py migrate

Write-Host ""
Write-Host "9. Criando migration para IPs permitidos..." -ForegroundColor Yellow
docker-compose exec web python manage.py makemigrations olt --name add_allowed_ip_model

Write-Host ""
Write-Host "10. Aplicando nova migration..." -ForegroundColor Yellow
docker-compose exec web python manage.py migrate

Write-Host ""
Write-Host "11. Importando IPs permitidos..." -ForegroundColor Yellow
docker-compose exec web python manage.py import_allowed_ips

Write-Host ""
Write-Host "CORRECOES APLICADAS COM SUCESSO!" -ForegroundColor Green
Write-Host ""
Write-Host "Para verificar o status:" -ForegroundColor Cyan
Write-Host "   docker-compose logs web" -ForegroundColor White
Write-Host ""
Write-Host "Para acessar o admin:" -ForegroundColor Cyan
Write-Host "   http://seu-dominio/admin/olt/allowedip/" -ForegroundColor White
Write-Host ""
Write-Host "Para monitorar conexoes do banco:" -ForegroundColor Cyan
Write-Host "   docker-compose exec web python monitor_connections.py" -ForegroundColor White