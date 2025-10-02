from django.contrib.auth.models import User

# Verificar se já existe um superusuário
admin = User.objects.filter(is_superuser=True).first()
if admin:
    print(f'Superuser já existe: {admin.username}')
else:
    # Criar superusuário
    User.objects.create_superuser('admin', 'admin@isp.com', 'admin123')
    print('Superuser criado: admin')

# Criar usuário de teste se não existir
if not User.objects.filter(username='testuser').exists():
    User.objects.create_user('testuser', 'test@example.com', 'testpass123')
    print('Usuário de teste criado: testuser')
else:
    print('Usuário de teste já existe: testuser')