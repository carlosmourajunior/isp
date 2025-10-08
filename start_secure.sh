#!/bin/bash

# SCRIPT DE INICIALIZAÇÃO SEGURA DO SISTEMA ISP
# Executa com configurações de segurança reforçadas

echo "🔒 INICIANDO SISTEMA ISP COM CONFIGURAÇÃO DE SEGURANÇA..."

# Verifica se arquivos de segurança existem
if [ ! -f "docker-compose.security.yml" ]; then
    echo "❌ ERRO: Arquivo docker-compose.security.yml não encontrado!"
    exit 1
fi

# Para qualquer instância rodando
echo "🛑 Parando instâncias em execução..."
docker compose down 2>/dev/null

# Remove imagens antigas (opcional, descomente se necessário)
# docker compose down --rmi all --volumes --remove-orphans

# Reconstrói com segurança
echo "🔧 Reconstruindo containers com configuração segura..."
docker compose -f docker-compose.yml -f docker-compose.security.yml build --no-cache

# Inicia com configuração segura
echo "🚀 Iniciando sistema com configuração de segurança..."
docker compose -f docker-compose.yml -f docker-compose.security.yml up -d

# Aguarda inicialização
echo "⏳ Aguardando inicialização dos serviços..."
sleep 10

# Verifica status
echo "📊 STATUS DOS SERVIÇOS:"
docker compose -f docker-compose.yml -f docker-compose.security.yml ps

echo ""
echo "✅ SISTEMA INICIADO COM CONFIGURAÇÃO DE SEGURANÇA!"
echo ""
echo "🌐 ACESSOS (APENAS LOCALHOST):"
echo "   - Aplicação: http://localhost:8000"
echo "   - Grafana:   http://localhost:3000"
echo "   - Prometheus: http://localhost:9090"
echo ""
echo "🔒 SEGURANÇA APLICADA:"
echo "   ✅ Nenhuma porta exposta externamente"
echo "   ✅ Nova senha forte do PostgreSQL"
echo "   ✅ Containers com privilégios mínimos"
echo "   ✅ Sistema de arquivos protegido"
echo "   ✅ Capacidades limitadas"
echo ""
echo "⚠️  IMPORTANTE: Acesse apenas via SSH tunnel ou VPN!"

# Verifica se há portas expostas externamente
echo ""
echo "🔍 VERIFICAÇÃO DE PORTAS EXPOSTAS:"
netstat -tuln | grep -E ":5432|:6380" && echo "❌ ALERTA: Ainda há portas de banco expostas!" || echo "✅ Bancos de dados protegidos"

# Monitora logs por alguns segundos
echo ""
echo "📝 LOGS INICIAIS (últimos 20 linhas):"
docker compose -f docker-compose.yml -f docker-compose.security.yml logs --tail=20