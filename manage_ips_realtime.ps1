# Script PowerShell para gerenciar IPs com validação em tempo real
# Inclui funcionalidades de validação, adição e atualização de cache

param(
    [string]$Action = "help",
    [string]$IP = "",
    [string]$Description = "",
    [switch]$Inactive,
    [switch]$RefreshCache,
    [switch]$FixInvalid,
    [switch]$ShowAll
)

function Show-Help {
    Write-Host "=== GERENCIAMENTO DE IPS COM VALIDAÇÃO EM TEMPO REAL ===" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Este script gerencia IPs permitidos com validação automática" -ForegroundColor White
    Write-Host ""
    Write-Host "Ações disponíveis:" -ForegroundColor Yellow
    Write-Host "  add        Adiciona um novo IP (com validação)"
    Write-Host "  list       Lista todos os IPs permitidos"
    Write-Host "  validate   Valida todos os IPs existentes"
    Write-Host "  sync       Sincroniza IPs do settings"
    Write-Host "  refresh    Atualiza cache de IPs"
    Write-Host ""
    Write-Host "Exemplos de uso:" -ForegroundColor Yellow
    Write-Host "  # Adicionar IP individual"
    Write-Host "  .\manage_ips_realtime.ps1 -Action add -IP '192.168.1.100' -Description 'Servidor teste'"
    Write-Host ""
    Write-Host "  # Adicionar range CIDR"
    Write-Host "  .\manage_ips_realtime.ps1 -Action add -IP '10.0.0.0/8' -Description 'Rede interna'"
    Write-Host ""
    Write-Host "  # Validar todos os IPs e corrigir inválidos"
    Write-Host "  .\manage_ips_realtime.ps1 -Action validate -FixInvalid"
    Write-Host ""
    Write-Host "  # Listar todos os IPs (incluindo inativos)"
    Write-Host "  .\manage_ips_realtime.ps1 -Action list -ShowAll"
    Write-Host ""
    Write-Host "  # Sincronizar com settings"
    Write-Host "  .\manage_ips_realtime.ps1 -Action sync"
    Write-Host ""
    Write-Host "  # Atualizar cache"
    Write-Host "  .\manage_ips_realtime.ps1 -Action refresh"
    Write-Host ""
    Write-Host "Parâmetros:" -ForegroundColor Yellow
    Write-Host "  -IP           IP ou range CIDR"
    Write-Host "  -Description  Descrição do IP"
    Write-Host "  -Inactive     Adiciona IP como inativo"
    Write-Host "  -RefreshCache Força atualização do cache"
    Write-Host "  -FixInvalid   Corrige IPs com formato inválido"
    Write-Host "  -ShowAll      Mostra todos os IPs (incluindo inativos)"
    Write-Host ""
}

function Test-DockerEnvironment {
    # Verificar se estamos no diretório correto
    if (-not (Test-Path "docker-compose.yml")) {
        Write-Host "❌ Erro: Execute este script no diretório raiz do projeto" -ForegroundColor Red
        return $false
    }

    # Verificar se o container web está rodando
    $webContainer = docker ps --format "table {{.Names}}\t{{.Status}}" | Select-String "isp-web"
    if (-not $webContainer) {
        Write-Host "❌ Container isp-web não está rodando!" -ForegroundColor Red
        Write-Host "💡 Execute: docker-compose up -d" -ForegroundColor Yellow
        return $false
    }

    return $true
}

# Verificar ação
if ($Action -eq "help" -or $Action -eq "" -or $Action -eq "h") {
    Show-Help
    exit 0
}

Write-Host "=== GERENCIAMENTO DE IPS - VALIDAÇÃO EM TEMPO REAL ===" -ForegroundColor Cyan
Write-Host "Data/Hora: $(Get-Date)" -ForegroundColor Gray
Write-Host "Ação: $Action" -ForegroundColor White
Write-Host ""

# Verificar ambiente Docker
if (-not (Test-DockerEnvironment)) {
    exit 1
}

# Executar ação solicitada
switch ($Action.ToLower()) {
    "add" {
        if (-not $IP) {
            Write-Host "❌ Erro: IP é obrigatório para adicionar" -ForegroundColor Red
            Write-Host "💡 Uso: .\manage_ips_realtime.ps1 -Action add -IP '192.168.1.1' -Description 'Servidor'" -ForegroundColor Yellow
            exit 1
        }

        Write-Host "➕ Adicionando IP: $IP" -ForegroundColor Cyan
        
        $command = "python manage.py add_ip '$IP'"
        if ($Description) {
            $command += " '$Description'"
        }
        if ($Inactive) {
            $command += " --inactive"
        }
        if ($RefreshCache) {
            $command += " --refresh-cache"
        }

        docker-compose exec web $command
    }

    "list" {
        Write-Host "📋 Listando IPs permitidos..." -ForegroundColor Cyan
        
        $command = "python manage.py list_ips"
        if ($ShowAll) {
            $command += " --all"
        }

        docker-compose exec web $command
    }

    "validate" {
        Write-Host "🔍 Validando todos os IPs..." -ForegroundColor Cyan
        
        $command = "python manage.py validate_ips"
        if ($FixInvalid) {
            $command += " --fix-invalid"
        }
        if ($ShowAll) {
            $command += " --show-all"
        }

        docker-compose exec web $command
    }

    "sync" {
        Write-Host "🔄 Sincronizando IPs do settings..." -ForegroundColor Cyan
        
        docker-compose exec web python manage.py sync_settings_ips
    }

    "refresh" {
        Write-Host "🔄 Atualizando cache de IPs..." -ForegroundColor Cyan
        
        docker-compose exec web python manage.py validate_ips
    }

    default {
        Write-Host "❌ Ação inválida: $Action" -ForegroundColor Red
        Write-Host "💡 Use -Action help para ver as opções disponíveis" -ForegroundColor Yellow
        exit 1
    }
}

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "✅ Operação concluída com sucesso!" -ForegroundColor Green
    Write-Host ""
    Write-Host "💡 Dicas:" -ForegroundColor Yellow
    Write-Host "  - Mudanças são aplicadas imediatamente (sem reiniciar)"
    Write-Host "  - Use 'validate' para verificar todos os IPs periodicamente"
    Write-Host "  - IPs inválidos podem ser corrigidos automaticamente"
} else {
    Write-Host ""
    Write-Host "❌ Erro durante a operação!" -ForegroundColor Red
}