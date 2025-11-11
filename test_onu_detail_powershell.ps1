# Script PowerShell para testar o endpoint de detalhes da ONU
# GET /api/onus/{id}/

# Configurações
$baseUrl = "http://localhost:8000/api"
$username = "testapi"
$password = "testapi123"
$onuId = 11428  # ID da ONU que queremos consultar

Write-Host "🔐 Fazendo login para obter token..." -ForegroundColor Yellow

# 1. Fazer login para obter token JWT
$loginBody = @{
    username = $username
    password = $password
} | ConvertTo-Json

try {
    $loginResponse = Invoke-RestMethod -Uri "$baseUrl/auth/login/" -Method POST -Body $loginBody -ContentType "application/json"
    
    Write-Host "✅ Login realizado com sucesso!" -ForegroundColor Green
    Write-Host "👤 Usuário: $($loginResponse.user_info.username)" -ForegroundColor Cyan
    
    # 2. Preparar headers com token
    $headers = @{
        "Authorization" = "Bearer $($loginResponse.access)"
        "Content-Type" = "application/json"
    }
    
    # 3. Testar endpoint de detalhes da ONU
    Write-Host "`n📡 Testando endpoint de detalhes da ONU..." -ForegroundColor Yellow
    Write-Host "URL: GET $baseUrl/onus/$onuId/" -ForegroundColor Gray
    Write-Host "="*60 -ForegroundColor Gray
    
    $onuResponse = Invoke-RestMethod -Uri "$baseUrl/onus/$onuId/" -Method GET -Headers $headers
    
    Write-Host "✅ Sucesso! ONU encontrada:" -ForegroundColor Green
    Write-Host "📋 Detalhes da ONU:" -ForegroundColor Cyan
    Write-Host "   • ID: $($onuResponse.id)"
    Write-Host "   • Serial: $($onuResponse.serial)"
    Write-Host "   • PON: $($onuResponse.pon)"
    Write-Host "   • Estado: $($onuResponse.oper_state)"
    Write-Host "   • Sinal RX: $($onuResponse.olt_rx_sig) dBm"
    Write-Host "   • Cliente: $($onuResponse.desc1)"
    Write-Host "   • Cliente Fibra: $($onuResponse.cliente_fibra)"
    
    if ($onuResponse.cliente_info) {
        Write-Host "`n📍 Informações do Cliente:" -ForegroundColor Cyan
        Write-Host "   • Nome: $($onuResponse.cliente_info.nome)"
        Write-Host "   • Endereço: $($onuResponse.cliente_info.endereco)"
        Write-Host "   • Caixa FTTH: $($onuResponse.cliente_info.id_caixa_ftth)"
    }
    
    Write-Host "`n📄 Resposta JSON completa:" -ForegroundColor Cyan
    $onuResponse | ConvertTo-Json -Depth 3 | Write-Host
    
    # 4. Testar com ID inexistente
    Write-Host "`n🔍 Testando com ID inexistente (99999)..." -ForegroundColor Yellow
    Write-Host "="*60 -ForegroundColor Gray
    
    try {
        $invalidResponse = Invoke-RestMethod -Uri "$baseUrl/onus/99999/" -Method GET -Headers $headers
        Write-Host "⚠️ Esperava erro 404, mas recebeu resposta!" -ForegroundColor Orange
    }
    catch {
        if ($_.Exception.Response.StatusCode -eq 404) {
            Write-Host "✅ Comportamento correto: 404 Not Found para ID inexistente" -ForegroundColor Green
        } else {
            Write-Host "❌ Erro inesperado: $($_.Exception.Response.StatusCode)" -ForegroundColor Red
        }
    }
    
} catch {
    Write-Host "❌ Erro durante o teste: $($_.Exception.Message)" -ForegroundColor Red
    if ($_.Exception.Response) {
        Write-Host "Status Code: $($_.Exception.Response.StatusCode)" -ForegroundColor Red
    }
}

Write-Host "`n🎯 Exemplo de uso com curl:" -ForegroundColor Yellow
Write-Host "="*60 -ForegroundColor Gray
Write-Host "# 1. Obter token"
Write-Host 'curl -X POST http://localhost:8000/api/auth/login/ \'
Write-Host '  -H "Content-Type: application/json" \'
Write-Host '  -d "{\"username\": \"testapi\", \"password\": \"testapi123\"}"'
Write-Host ""
Write-Host "# 2. Usar token para consultar ONU"
Write-Host "curl -X GET http://localhost:8000/api/onus/$onuId/ \"
Write-Host '  -H "Authorization: Bearer SEU_TOKEN_AQUI"'