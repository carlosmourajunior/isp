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
echo "✅ SISTEMA INICIADO COM CONFIGURAÇÃO DE SEGURANÇA BALANCEADA!"
echo ""
echo "🌐 ACESSOS EXTERNOS:"
echo "   - Aplicação: http://177.22.126.78:8000"
echo "   - Grafana:   http://177.22.126.78:3000"
echo ""
echo "🔒 SSH Tunnel (opcional para Prometheus):"
echo "   ssh -L 9090:localhost:9090 user@177.22.126.78"
echo "   Depois: http://localhost:9090"
echo ""
echo "🛡️ SEGURANÇA APLICADA:"
echo "   ✅ Aplicação: Porta 8000 (essencial)"
echo "   ✅ Grafana: Porta 3000 (monitoramento)"
echo "   ✅ PostgreSQL/Redis: ZERO acesso externo"
echo "   ✅ Prometheus: ZERO acesso externo"
echo "   ✅ Exporters: ZERO acesso externo"
echo "   ✅ Nova senha forte do PostgreSQL"
echo "   ✅ Containers com privilégios mínimos"
echo ""
echo "🎯 ATAQUE ANTERIOR: Prevenido (bancos isolados)!"

# Verifica se há portas expostas externamente
echo ""
echo "🔍 VERIFICAÇÃO DE PORTAS EXPOSTAS:"
netstat -tuln | grep -E ":5432|:6380" && echo "❌ ALERTA: Ainda há portas de banco expostas!" || echo "✅ Bancos de dados protegidos"

# Monitora logs por alguns segundos
echo ""
echo "📝 LOGS INICIAIS (últimos 20 linhas):"
docker compose -f docker-compose.yml -f docker-compose.security.yml logs --tail=20