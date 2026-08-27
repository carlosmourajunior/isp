#!/bin/bash

# SCRIPT DE INICIALIZAÇÃO AUTOMÁTICA DO BANCO DE DADOS
# Este script é executado automaticamente durante o build

echo "🔧 Iniciando configuração automática do banco de dados..."

# Aguarda o PostgreSQL estar pronto
echo "⏳ Aguardando PostgreSQL..."
while ! pg_isready -h db -p 5432 -U isp_db_admin -d postgres; do
    sleep 2
done

echo "✅ PostgreSQL está pronto!"

# Verifica se o banco já existe
if psql -h db -U isp_db_admin -d postgres -lqt | cut -d \| -f 1 | grep -qw isp_production_db; then
    echo "✅ Banco de dados isp_production_db já existe"
else
    echo "🔧 Criando banco de dados isp_production_db..."
    psql -h db -U isp_db_admin -d postgres -c "CREATE DATABASE isp_production_db OWNER isp_db_admin;"
    echo "✅ Banco de dados criado!"
fi

# Executa as migrações
echo "🔧 Executando migrações Django..."
python manage.py migrate

# Coleta arquivos estáticos
echo "🔧 Coletando arquivos estáticos..."
python manage.py collectstatic --noinput

# Cria superusuário se não existir
echo "🔧 Verificando superusuário..."
python manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@isp.local', 'admin123')
    print('✅ Superusuário admin criado!')
else:
    print('✅ Superusuário admin já existe!')
"

echo "🚀 Configuração completa! Iniciando aplicação..."

# Inicia o servidor
exec python manage.py runserver 0.0.0.0:8000