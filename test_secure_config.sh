#!/bin/bash
# TESTE DE CONFIGURAÇÃO SEGURA
# Verifica se os arquivos estão usando variáveis corretamente

echo "🔍 VERIFICANDO CONFIGURAÇÃO SEGURA"
echo "=================================="

# 1. Verificar se há senhas hardcoded nos arquivos
echo "1. Verificando senhas hardcoded..."
if grep -r "Redis2025SecureAuth\|PgSql_2025_Sec\|Grafana2025AdminSecure" docker-compose*.yml 2>/dev/null; then
    echo "❌ ERRO: Ainda há senhas hardcoded!"
    exit 1
else
    echo "✅ OK: Nenhuma senha hardcoded encontrada"
fi

# 2. Verificar se .env tem as variáveis necessárias
echo ""
echo "2. Verificando variáveis no .env..."
VARS=("DB_PASSWORD" "REDIS_PASSWORD" "GRAFANA_ADMIN_PASSWORD" "GRAFANA_ADMIN_USER")
for var in "${VARS[@]}"; do
    if grep -q "^$var=" .env; then
        echo "✅ $var encontrado"
    else
        echo "❌ $var NÃO encontrado!"
    fi
done

# 3. Testar se docker-compose consegue ler as variáveis
echo ""
echo "3. Testando docker-compose config..."
if docker compose -f docker-compose.yml -f docker-compose.security.yml config > /dev/null 2>&1; then
    echo "✅ Configuração Docker válida"
else
    echo "❌ ERRO na configuração Docker!"
    exit 1
fi

echo ""
echo "✅ Configuração segura aplicada com sucesso!"
echo ""
echo "📋 PRÓXIMOS PASSOS:"
echo "1. Testar o sistema: docker compose -f docker-compose.yml -f docker-compose.security.yml -f docker-compose.firewall.yml up -d"
echo "2. Verificar logs: docker compose logs"
echo "3. Adicionar ao Git: git add . && git commit -m 'Security: Remove hardcoded passwords'"