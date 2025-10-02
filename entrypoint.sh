#!/bin/bash

# Aguarda o banco de dados estar disponível
echo "Aguardando o banco de dados estar disponível..."
while ! nc -z db 5432; do
    sleep 1
done

echo "Banco de dados disponível!"

# Aguarda o Redis estar disponível
echo "Aguardando o Redis estar disponível..."
while ! nc -z redis 6379; do
    sleep 1
done

echo "Redis disponível!"

# Executa as migrations
echo "Executando migrations..."
python manage.py migrate --noinput

# Coleta arquivos estáticos
echo "Coletando arquivos estáticos..."
python manage.py collectstatic --noinput

# Cria superuser se não existir (opcional)
echo "Verificando se existe superuser..."
python manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(is_superuser=True).exists():
    print('Criando superuser...')
    User.objects.create_superuser('admin', 'admin@admin.com', 'admin123')
    print('Superuser criado: admin/admin123')
else:
    print('Superuser já existe')
"

# Inicia o scheduler de tarefas automáticas
echo "Iniciando scheduler de tarefas automáticas..."
python manage.py setup_auto_updates --start

# Verifica status do scheduler
echo "Verificando status do scheduler..."
python manage.py setup_auto_updates --status

# Executa o comando passado como argumento
echo "Iniciando aplicação..."
exec "$@"