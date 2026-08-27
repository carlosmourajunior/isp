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

if { [ "$1" = "python" ] && [ "$2" = "/code/manage.py" ] && [ "$3" = "runserver" ]; } || [ "$1" = "gunicorn" ]; then
    echo "Container web detectado - executando setup automático..."
    
    # Tenta primeiro com o usuário antigo para criar o novo
    echo "⏳ Verificando conexão com PostgreSQL..."
    
    # Tenta conectar com postgres/postgres primeiro
    if PGPASSWORD='postgres' psql -h db -U postgres -d postgres -c '\q' 2>/dev/null; then
        echo "✅ Conectando com usuário postgres original"
        
        # Cria o usuário se não existir
        echo "🔧 Criando usuário isp_db_admin se necessário..."
        PGPASSWORD='postgres' psql -h db -U postgres -d postgres -c "
        DO \$\$
        BEGIN
            IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'isp_db_admin') THEN
                CREATE USER isp_db_admin WITH PASSWORD '${DB_PASSWORD}';
                ALTER USER isp_db_admin CREATEDB SUPERUSER;
            END IF;
        END
        \$\$;"
        
        # Cria o banco se não existir
        if ! PGPASSWORD='postgres' psql -h db -U postgres -d postgres -lqt | cut -d \| -f 1 | grep -qw isp_production_db; then
            echo "🔧 Criando banco isp_production_db..."
            PGPASSWORD='postgres' psql -h db -U postgres -d postgres -c "CREATE DATABASE isp_production_db OWNER isp_db_admin;"
        fi
        
    # Se não conseguir com postgres, tenta com isp_db_admin
    elif PGPASSWORD='${DB_PASSWORD}' psql -h db -U isp_db_admin -d postgres -c '\q' 2>/dev/null; then
        echo "✅ Conectando com usuário isp_db_admin"
        
        # Cria o banco se não existir
        if ! PGPASSWORD='${DB_PASSWORD}' psql -h db -U isp_db_admin -d postgres -lqt | cut -d \| -f 1 | grep -qw isp_production_db; then
            echo "🔧 Criando banco isp_production_db..."
            PGPASSWORD='${DB_PASSWORD}' psql -h db -U isp_db_admin -d postgres -c "CREATE DATABASE isp_production_db OWNER isp_db_admin;"
        fi
    else
        echo "❌ Não foi possível conectar ao PostgreSQL"
        echo "Aguardando mais um pouco..."
        sleep 10
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