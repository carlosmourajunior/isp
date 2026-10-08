# Script PowerShell para sincronizar IPs do settings
# Executa o comando Django para importar IPs automaticamente

param(
    [switch]$Cleanup,
    [switch]$Force,
    [switch]$Help
)

if ($Help) {
    Write-Host "=== SINCRONIZAÇÃO DE IPS DO SETTINGS ===" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Este script sincroniza os IPs do settings.ALLOWED_IPS com a tabela AllowedIP" -ForegroundColor White
    Write-Host ""
    Write-Host "Uso:" -ForegroundColor Yellow
    Write-Host "  .\sync_settings_ips.ps1                 # Sincronização básica"
    Write-Host "  .\sync_settings_ips.ps1 -Cleanup        # Remove IPs obsoletos"
    Write-Host "  .\sync_settings_ips.ps1 -Force          # Força reativação"
    Write-Host "  .\sync_settings_ips.ps1 -Cleanup -Force # Limpeza completa"
    Write-Host ""
    Write-Host "Parâmetros:" -ForegroundColor Yellow
    Write-Host "  -Cleanup  Remove IPs que não estão mais no settings"
    Write-Host "  -Force    Força a reativação de IPs inativos"
    Write-Host "  -Help     Mostra esta ajuda"
    Write-Host ""
    exit 0
}

Write-Host "=== SINCRONIZAÇÃO DE IPS DO SETTINGS ===" -ForegroundColor Cyan
Write-Host "Data/Hora: $(Get-Date)" -ForegroundColor Gray
Write-Host ""

# Verificar se estamos no diretório correto
if (-not (Test-Path "docker-compose.yml")) {
    Write-Host "❌ Erro: Execute este script no diretório raiz do projeto (onde está o docker-compose.yml)" -ForegroundColor Red
    exit 1
}

# Verificar se os containers estão rodando
Write-Host "🔍 Verificando containers..." -ForegroundColor Yellow
$containers = docker ps --format "table {{.Names}}\t{{.Status}}" | Select-String "isp-web"

if (-not $containers) {
    Write-Host "❌ Container isp-web não está rodando!" -ForegroundColor Red
    Write-Host "💡 Execute: docker-compose up -d" -ForegroundColor Yellow
    exit 1
}

Write-Host "✅ Container isp-web está rodando" -ForegroundColor Green

# Construir comando
$command = "python manage.py sync_settings_ips"

if ($Cleanup) {
    $command += " --cleanup"
    Write-Host "🧹 Modo limpeza habilitado" -ForegroundColor Yellow
}

if ($Force) {
    $command += " --force"
    Write-Host "💪 Modo força habilitado" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "🚀 Executando sincronização..." -ForegroundColor Cyan

# Executar comando no container
try {
    docker-compose exec web $command
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host ""
        Write-Host "✅ Sincronização concluída com sucesso!" -ForegroundColor Green
        Write-Host ""
        Write-Host "💡 Dicas:" -ForegroundColor Yellow
        Write-Host "  - Os IPs são importados automaticamente quando o sistema inicia"
        Write-Host "  - Use o comando 'list_ips' para ver todos os IPs permitidos"
        Write-Host "  - Use o Django Admin para gerenciar IPs manualmente"
    } else {
        Write-Host ""
        Write-Host "❌ Erro durante a sincronização!" -ForegroundColor Red
    }
} catch {
    Write-Host "❌ Erro ao executar comando: $_" -ForegroundColor Red
    exit 1
}