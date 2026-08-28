#!/bin/bash
# TESTE DE CONFIGURAÇÃO SEGURA - VERSÃO ATUALIZADA
# Verifica se os arquivos estão usando variáveis corretamente

echo "🔍 VERIFICANDO CONFIGURAÇÃO SEGURA"
echo "=================================="

# 1. Verificar se há senhas hardcoded nos arquivos (excluindo .env)
echo "1. Verificando senhas hardcoded..."
if find . -name "*.yml" -o -name "*.sh" -o -name "*.py" | xargs grep -l "Redis2025SecureAuth\|PgSql_2025_Sec\|Grafana2025AdminSecure\|django-secure-7k2m9vLqR8xN3bF6hJpT9wYzC4sG7kM0nB5vL3xR8qPmK" 2>/dev/null | grep -v ".env"; then
    echo "❌ ERRO: Ainda há senhas hardcoded nos arquivos!"
    echo "Arquivos com senhas:"
    find . -name "*.yml" -o -name "*.sh" -o -name "*.py" | xargs grep -l "Redis2025SecureAuth\|PgSql_2025_Sec\|Grafana2025AdminSecure" 2>/dev/null | grep -v ".env"
    exit 1
else
    echo "✅ OK: Nenhuma senha hardcoded encontrada nos arquivos versionados"
fi

# 2. Verificar se .env tem as variáveis necessárias
echo ""
echo "2. Verificando variáveis no .env..."
VARS=("DB_PASSWORD" "REDIS_PASSWORD")
for var in "${VARS[@]}"; do
    if grep -q "^$var=" .env; then
        echo "✅ $var encontrado"
    else
        echo "❌ $var NÃO encontrado!"
    fi
done

# 3. Verificar se arquivos usam ${} syntax
echo ""
echo "3. Verificando uso de variáveis..."
if grep -r '${.*}' docker-compose*.yml | grep -v ".env"; then
    echo "✅ Variáveis de ambiente encontradas nos arquivos Docker"
else
    echo "❌ Nenhuma variável de ambiente encontrada!"
fi

# 4. Testar se docker-compose consegue ler as variáveis
echo ""
echo "4. Testando docker-compose config..."
if docker compose -f docker-compose.yml config > /dev/null 2>&1; then
    echo "✅ Configuração Docker válida"
else
    echo "❌ ERRO na configuração Docker!"
    exit 1
fi

echo ""
echo "✅ Configuração segura aplicada com sucesso!"
echo ""
echo "📋 PRÓXIMOS PASSOS:"
echo "1. Testar o sistema: docker compose -f docker-compose.yml up -d"
echo "2. Verificar logs: docker compose logs"
echo "3. Adicionar ao Git: git add . && git commit -m 'Security: Remove all hardcoded passwords'"