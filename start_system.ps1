# Script PowerShell para Inicialização do Sistema ISP
# Execute: .\start_system.ps1

param(
    [string]$Action = "start"
)

# Cores para output
function Write-ColoredOutput {
    param(
        [string]$Message,
        [string]$Color = "Green"
    )
    Write-Host $Message -ForegroundColor $Color
}

function Write-Header {
    param([string]$Message)
    Write-Host ""
    Write-Host "=" * 60 -ForegroundColor Blue
    Write-Host "  $Message" -ForegroundColor Blue
    Write-Host "=" * 60 -ForegroundColor Blue
}

function Test-Prerequisites {
    Write-Header "🔍 VERIFICANDO PRÉ-REQUISITOS"
    
    $prerequisites = @()
    
    # Verificar Docker
    try {
        $dockerVersion = docker --version 2>$null
        if ($LASTEXITCODE -eq 0) {
            Write-ColoredOutput "✓ Docker: $dockerVersion"
        } else {
            $prerequisites += "Docker não está instalado"
        }
    } catch {
        $prerequisites += "Docker não encontrado"
    }
    
    # Verificar Docker Compose
    try {
        $composeVersion = docker-compose --version 2>$null
        if ($LASTEXITCODE -eq 0) {
            Write-ColoredOutput "✓ Docker Compose: $composeVersion"
        } else {
            $prerequisites += "Docker Compose não está instalado"
        }
    } catch {
        $prerequisites += "Docker Compose não encontrado"
    }
    
    # Verificar Python
    try {
        $pythonVersion = python --version 2>$null
        if ($LASTEXITCODE -eq 0) {
            Write-ColoredOutput "✓ Python: $pythonVersion"
        } else {
            $prerequisites += "Python não está instalado"
        }
    } catch {
        $prerequisites += "Python não encontrado"
    }
    
    # Verificar se Docker está rodando
    try {
        docker info 2>$null | Out-Null
        if ($LASTEXITCODE -eq 0) {
            Write-ColoredOutput "✓ Docker daemon está rodando"
        } else {
            $prerequisites += "Docker daemon não está rodando"
        }
    } catch {
        $prerequisites += "Não foi possível verificar o Docker daemon"
    }
    
    if ($prerequisites.Count -gt 0) {
        Write-Host ""
        Write-ColoredOutput "❌ REQUISITOS NÃO ATENDIDOS:" "Red"
        foreach ($req in $prerequisites) {
            Write-ColoredOutput "  - $req" "Red"
        }
        return $false
    }
    
    Write-Host ""
    Write-ColoredOutput "✅ Todos os pré-requisitos atendidos!" "Green"
    return $true
}

function New-Directories {
    Write-Header "📁 CRIANDO DIRETÓRIOS"
    
    $directories = @(
        "data",
        "data\logs",
        "data\postgres", 
        "data\redis",
        "data\media",
        "data\staticfiles",
        "logs",
        "monitoring",
        "monitoring\prometheus",
        "monitoring\prometheus\rules",
        "monitoring\grafana",
        "monitoring\grafana\provisioning",
        "monitoring\grafana\provisioning\datasources",
        "monitoring\grafana\provisioning\dashboards",
        "monitoring\grafana\dashboards",
        "monitoring\alertmanager"
    )
    
    foreach ($dir in $directories) {
        if (!(Test-Path $dir)) {
            New-Item -ItemType Directory -Path $dir -Force | Out-Null
        }
        Write-ColoredOutput "✓ $dir"
    }
    
    Write-Host ""
    Write-ColoredOutput "✅ Diretórios criados com sucesso!"
}

function Test-EnvFile {
    Write-Header "⚙️ VERIFICANDO CONFIGURAÇÕES"
    
    if (!(Test-Path ".env")) {
        if (Test-Path ".env.example") {
            Copy-Item ".env.example" ".env"
            Write-ColoredOutput "✓ Arquivo .env criado a partir do .env.example"
        } else {
            # Criar .env básico
            $envContent = @"
# Django Settings
SECRET_KEY=change-this-secret-key-in-production
DEBUG=True
ALLOWED_HOSTS=*

# Database Settings  
DB_NAME=postgres
DB_USER=postgres
DB_PASSWORD=postgres
DB_HOST=db
DB_PORT=5432

# Redis Settings
REDIS_URL=redis://redis:6379/0
"@
            $envContent | Out-File -FilePath ".env" -Encoding UTF8
            Write-ColoredOutput "✓ Arquivo .env básico criado"
            Write-ColoredOutput "⚠️ Configure as variáveis de ambiente em .env conforme necessário" "Yellow"
        }
    } else {
        Write-ColoredOutput "✓ Arquivo .env já existe"
    }
}

function Start-System {
    Write-Header "🚀 INICIANDO SISTEMA"
    
    try {
        # Parar containers existentes
        Write-ColoredOutput "Parando containers existentes..."
        docker-compose down 2>$null | Out-Null
        
        # Construir e iniciar
        Write-ColoredOutput "Construindo e iniciando containers..."
        docker-compose up -d --build
        
        if ($LASTEXITCODE -eq 0) {
            Write-ColoredOutput "✅ Sistema iniciado com sucesso!"
        } else {
            Write-ColoredOutput "❌ Erro ao iniciar sistema" "Red"
            return $false
        }
        
    } catch {
        Write-ColoredOutput "❌ Erro ao iniciar sistema: $_" "Red"
        return $false
    }
    
    return $true
}

function Stop-System {
    Write-Header "🛑 PARANDO SISTEMA"
    
    try {
        docker-compose down
        if ($LASTEXITCODE -eq 0) {
            Write-ColoredOutput "✅ Sistema parado com sucesso!"
        } else {
            Write-ColoredOutput "❌ Erro ao parar sistema" "Red"
        }
    } catch {
        Write-ColoredOutput "❌ Erro ao parar sistema: $_" "Red"
    }
}

function Test-Services {
    Write-Header "⏳ VERIFICANDO SERVIÇOS"
    
    $services = @{
        "Django App" = "http://localhost:8000/api/health/"
        "Prometheus" = "http://localhost:9090/-/healthy"
        "Grafana" = "http://localhost:3000/api/health"
    }
    
    $maxAttempts = 15
    $attempt = 0
    
    while ($attempt -lt $maxAttempts) {
        $allReady = $true
        $attempt++
        
        Write-ColoredOutput "`nTentativa $attempt/$maxAttempts"
        
        foreach ($service in $services.GetEnumerator()) {
            try {
                $response = Invoke-WebRequest -Uri $service.Value -TimeoutSec 5 -UseBasicParsing 2>$null
                if ($response.StatusCode -eq 200) {
                    Write-ColoredOutput "✓ $($service.Key): Pronto"
                } else {
                    Write-ColoredOutput "⏳ $($service.Key): Aguardando... (Status: $($response.StatusCode))"
                    $allReady = $false
                }
            } catch {
                Write-ColoredOutput "⏳ $($service.Key): Aguardando..."
                $allReady = $false
            }
        }
        
        if ($allReady) {
            Write-Host ""
            Write-ColoredOutput "✅ Todos os serviços estão prontos!" "Green"
            return $true
        }
        
        Start-Sleep -Seconds 10
    }
    
    Write-Host ""
    Write-ColoredOutput "⚠️ Alguns serviços podem ainda estar inicializando" "Yellow"
    return $false
}

function Show-AccessInfo {
    Write-Header "🌐 INFORMAÇÕES DE ACESSO"
    
    $info = @"

📱 APLICAÇÃO PRINCIPAL
• Django Admin:       http://localhost:8000/admin/
• API:               http://localhost:8000/api/
• Health Check:      http://localhost:8000/api/health/

📊 MONITORAMENTO  
• Grafana:           http://localhost:3000/
  └─ Login:          admin / admin123
• Prometheus:        http://localhost:9090/
• Alertmanager:      http://localhost:9093/

📋 MÉTRICAS E LOGS
• Métricas:          http://localhost:8000/api/metrics/
• Status Alertas:    http://localhost:8000/api/alerts/status/
• Logs da App:       .\logs\

🔧 COMANDOS ÚTEIS (PowerShell)
• Ver status:        .\start_system.ps1 status
• Parar sistema:     .\start_system.ps1 stop
• Reiniciar:         .\start_system.ps1 restart
• Ver logs:          docker-compose logs -f

🔧 COMANDOS ÚTEIS (Makefile)
• Ver status:        make status
• Parar sistema:     make stop
• Reiniciar:         make restart
• Ver logs:          make logs
"@
    
    Write-ColoredOutput $info "Cyan"
}

function Show-Status {
    Write-Header "📊 STATUS DOS SERVIÇOS"
    docker-compose ps
}

function Show-Logs {
    Write-Header "📋 LOGS DO SISTEMA"
    docker-compose logs -f
}

# Função principal
function Main {
    switch ($Action.ToLower()) {
        "stop" {
            Stop-System
            return
        }
        "restart" {
            Stop-System
            Start-Sleep -Seconds 5
            if (Start-System) {
                Test-Services
                Show-AccessInfo
            }
            return
        }
        "status" {
            Show-Status
            return
        }
        "logs" {
            Show-Logs
            return
        }
        "help" {
            Write-Host @"
Sistema ISP - PowerShell Script

Uso: .\start_system.ps1 [comando]

Comandos disponíveis:
  start    - Iniciar sistema completo (padrão)
  stop     - Parar sistema
  restart  - Reiniciar sistema
  status   - Mostrar status dos serviços
  logs     - Mostrar logs em tempo real
  help     - Mostrar esta ajuda

Exemplos:
  .\start_system.ps1          # Iniciar sistema
  .\start_system.ps1 stop     # Parar sistema
  .\start_system.ps1 status   # Ver status
"@
            return
        }
    }
    
    # Inicialização completa (padrão)
    Write-ColoredOutput @"

╔══════════════════════════════════════════════════════════════╗
║                    SISTEMA ISP - INICIALIZAÇÃO               ║
║              Aplicação Principal + Monitoramento             ║
╚══════════════════════════════════════════════════════════════╝
"@ "Blue"
    
    # Verificar pré-requisitos
    if (!(Test-Prerequisites)) {
        exit 1
    }
    
    # Preparar ambiente
    New-Directories
    Test-EnvFile
    
    # Iniciar sistema
    if (!(Start-System)) {
        exit 1
    }
    
    # Aguardar serviços
    Test-Services
    
    # Mostrar informações
    Show-Status
    Show-AccessInfo
    
    Write-Host ""
    Write-ColoredOutput "🎉 SISTEMA INICIADO COM SUCESSO!" "Green"
    Write-ColoredOutput "Use '.\start_system.ps1 stop' para parar o sistema"
}

# Executar função principal
try {
    Main
} catch {
    Write-ColoredOutput "`n❌ Erro inesperado: $_" "Red"
    exit 1
}