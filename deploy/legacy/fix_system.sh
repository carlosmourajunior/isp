#!/bin/bash
# Script para corrigir problemas do sistema Docker

echo "🔧 SCRIPT DE CORREÇÃO DO SISTEMA ISP"
echo "====================================="

echo ""
echo "1️⃣ Parando containers..."
docker-compose down

echo ""
echo "2️⃣ Verificando configuração do PostgreSQL..."
# Verificar se o PostgreSQL foi configurado corretamente
if [ -f "./data/postgres/postgresql.conf" ]; then
    echo "✅ Configuração do PostgreSQL encontrada"
else
    echo "❌ Configuração do PostgreSQL não encontrada"
fi

echo ""
echo "3️⃣ Iniciando banco de dados..."
docker-compose up -d db

echo ""
echo "4️⃣ Aguardando banco ficar pronto..."
sleep 30

echo ""
echo "5️⃣ Testando conexão com banco..."
docker-compose exec db psql -U postgres -c "SELECT version();" || {
    echo "❌ Erro na conexão com banco. Recriando volume..."
    docker-compose down -v
    docker volume prune -f
    echo "🔄 Reiniciando banco..."
    docker-compose up -d db
    sleep 30
}

echo ""
echo "6️⃣ Iniciando aplicação..."
docker-compose up -d web

echo ""
echo "7️⃣ Aplicando migrations..."
sleep 10
docker-compose exec web python manage.py migrate

echo ""
echo "8️⃣ Criando migration para IPs permitidos..."
docker-compose exec web python manage.py makemigrations olt --name add_allowed_ip_model

echo ""
echo "9️⃣ Aplicando nova migration..."
docker-compose exec web python manage.py migrate

echo ""
echo "🔟 Importando IPs permitidos..."
docker-compose exec web python manage.py import_allowed_ips

echo ""
echo "✅ CORREÇÕES APLICADAS COM SUCESSO!"
echo ""
echo "🔍 Para verificar o status:"
echo "   docker-compose logs web"
echo ""
echo "🌐 Para acessar o admin:"
echo "   http://seu-dominio/admin/olt/allowedip/"