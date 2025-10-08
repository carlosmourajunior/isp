#!/bin/bash
set -e

echo "=== INICIANDO ENTRYPOINT ==="
echo "Argumentos recebidos: $@"

echo "Aguardando o banco de dados estar disponível..."
timeout=30
counter=0
while ! nc -z db 5432; do
    sleep 1
    counter=$((counter+1))
    if [ $counter -gt $timeout ]; then
        echo "Timeout aguardando banco de dados"
        exit 1
    fi
done

echo "Banco de dados disponível!"

echo "Aguardando o Redis estar disponível..."
counter=0
while ! nc -z redis 6379; do
    sleep 1
    counter=$((counter+1))
    if [ $counter -gt $timeout ]; then
        echo "Timeout aguardando Redis"
        exit 1
    fi
done

echo "Redis disponível!"

if [ "$1" = "python" ] && [ "$2" = "/code/manage.py" ] && [ "$3" = "runserver" ]; then
    echo "Container web detectado - executando setup automático..."
    
    # Aguarda especificamente o PostgreSQL com credenciais corretas
    echo "⏳ Aguardando PostgreSQL com credenciais corretas..."
    while ! PGPASSWORD='PgSql_2025_Sec_9vT8xK2mQ7nB3fH' psql -h db -U isp_db_admin -d postgres -c '\q' 2>/dev/null; do
        sleep 2
        echo "Aguardando..."
    done
    echo "✅ PostgreSQL pronto!"
    
    # Verifica se o banco existe, se não, cria
    if ! PGPASSWORD='PgSql_2025_Sec_9vT8xK2mQ7nB3fH' psql -h db -U isp_db_admin -d postgres -lqt | cut -d \| -f 1 | grep -qw isp_production_db; then
        echo "🔧 Criando banco de dados isp_production_db..."
        PGPASSWORD='PgSql_2025_Sec_9vT8xK2mQ7nB3fH' psql -h db -U isp_db_admin -d postgres -c "CREATE DATABASE isp_production_db OWNER isp_db_admin;"
        echo "✅ Banco criado!"
    else
        echo "✅ Banco isp_production_db já existe"
    fi
    
    echo "🔧 Executando migrations..."
    python manage.py migrate --noinput || echo "⚠️ Erro nas migrations"
    
    echo "🔧 Coletando arquivos estáticos..."
    python manage.py collectstatic --noinput || echo "⚠️ Erro no collectstatic"
    
    echo "🔧 Verificando superuser..."
    python manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(is_superuser=True).exists():
    print('Criando superuser admin...')
    User.objects.create_superuser('admin', 'admin@isp.local', 'admin123')
    print('✅ Superuser criado: admin/admin123')
else:
    print('✅ Superuser já existe')
" || echo "⚠️ Erro na verificação do superuser"

    echo "🚀 Setup inicial concluído!"
fi

echo "Iniciando aplicação: $@"
exec "$@"