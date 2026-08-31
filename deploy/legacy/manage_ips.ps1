# Script PowerShell para gerenciar IPs permitidos
param(
    [string]$Action = "help",
    [string]$IP,
    [string]$Description = "IP adicionado via PowerShell"
)

function Show-Help {
    Write-Host "GERENCIADOR DE IPs PERMITIDOS" -ForegroundColor Cyan
    Write-Host "=============================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "USO:" -ForegroundColor Yellow
    Write-Host "  .\manage_ips.ps1 -Action add -IP 'IP_ADDRESS' -Description 'DESCRICAO'"
    Write-Host "  .\manage_ips.ps1 -Action list"
    Write-Host "  .\manage_ips.ps1 -Action remove -IP 'IP_ADDRESS'"
    Write-Host "  .\manage_ips.ps1 -Action activate -IP 'IP_ADDRESS'"
    Write-Host "  .\manage_ips.ps1 -Action deactivate -IP 'IP_ADDRESS'"
    Write-Host ""
    Write-Host "EXEMPLOS:" -ForegroundColor Green
    Write-Host '  .\manage_ips.ps1 -Action add -IP "192.168.1.100" -Description "Meu PC"'
    Write-Host '  .\manage_ips.ps1 -Action add -IP "10.0.0.0/8" -Description "Rede interna"'
    Write-Host "  .\manage_ips.ps1 -Action list"
}

function Add-IP {
    param($IPAddress, $Desc)
    
    $Command = @"
from olt.models import AllowedIP
try:
    if AllowedIP.objects.filter(ip_address='$IPAddress').exists():
        print('❌ IP $IPAddress já existe!')
    else:
        AllowedIP.objects.create(ip_address='$IPAddress', description='$Desc', is_active=True)
        print('✅ IP $IPAddress adicionado com sucesso!')
except Exception as e:
    print(f'❌ Erro: {e}')
"@
    
    docker-compose exec web python manage.py shell -c $Command
}

function List-IPs {
    $Command = @"
from olt.models import AllowedIP
ips = AllowedIP.objects.all().order_by('ip_address')
print('\n📋 IPs PERMITIDOS:')
print('=' * 50)
for ip in ips:
    status = '🟢 ATIVO' if ip.is_active else '🔴 INATIVO'
    print(f'{status} {ip.ip_address} - {ip.description}')
print(f'\nTotal: {ips.count()} IPs')
"@
    
    docker-compose exec web python manage.py shell -c $Command
}

function Remove-IP {
    param($IPAddress)
    
    $Command = @"
from olt.models import AllowedIP
try:
    ip = AllowedIP.objects.get(ip_address='$IPAddress')
    ip.delete()
    print('✅ IP $IPAddress removido com sucesso!')
except AllowedIP.DoesNotExist:
    print('❌ IP $IPAddress não encontrado!')
except Exception as e:
    print(f'❌ Erro: {e}')
"@
    
    docker-compose exec web python manage.py shell -c $Command
}

function Set-IPStatus {
    param($IPAddress, $Active)
    
    $Command = @"
from olt.models import AllowedIP
try:
    ip = AllowedIP.objects.get(ip_address='$IPAddress')
    ip.is_active = $Active
    ip.save()
    status = 'ativado' if $Active else 'desativado'
    print(f'✅ IP $IPAddress {status} com sucesso!')
except AllowedIP.DoesNotExist:
    print('❌ IP $IPAddress não encontrado!')
except Exception as e:
    print(f'❌ Erro: {e}')
"@
    
    docker-compose exec web python manage.py shell -c $Command.Replace('$Active', $Active.ToString().ToLower())
}

# Execução baseada na ação
switch ($Action.ToLower()) {
    "add" {
        if (-not $IP) {
            Write-Host "❌ IP é obrigatório para adicionar!" -ForegroundColor Red
            Show-Help
            return
        }
        Add-IP -IPAddress $IP -Desc $Description
    }
    "list" {
        List-IPs
    }
    "remove" {
        if (-not $IP) {
            Write-Host "❌ IP é obrigatório para remover!" -ForegroundColor Red
            return
        }
        Remove-IP -IPAddress $IP
    }
    "activate" {
        if (-not $IP) {
            Write-Host "❌ IP é obrigatório!" -ForegroundColor Red
            return
        }
        Set-IPStatus -IPAddress $IP -Active $true
    }
    "deactivate" {
        if (-not $IP) {
            Write-Host "❌ IP é obrigatório!" -ForegroundColor Red
            return
        }
        Set-IPStatus -IPAddress $IP -Active $false
    }
    default {
        Show-Help
    }
}