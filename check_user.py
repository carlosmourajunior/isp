#!/usr/bin/env python3
"""
Script para verificar e criar usuário para API
"""

import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'olt_connector.settings')
django.setup()

from django.contrib.auth.models import User

def check_and_create_user():
    """Verifica e cria usuário para API"""
    username = 'admin'
    password = 'admin123'
    email = 'admin@localhost'
    
    try:
        # Tentar obter o usuário existente
        try:
            user = User.objects.get(username=username)
            print(f"ℹ️  Usuário '{username}' encontrado:")
            print(f"   - Ativo: {user.is_active}")
            print(f"   - Staff: {user.is_staff}")
            print(f"   - Superuser: {user.is_superuser}")
            
            # Garantir que o usuário está ativo
            user.is_active = True
            user.is_staff = True
            user.is_superuser = True
            user.set_password(password)
            user.save()
            print(f"✅ Usuário '{username}' atualizado com sucesso!")
            
        except User.DoesNotExist:
            # Criar novo usuário
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                is_active=True,
                is_staff=True,
                is_superuser=True
            )
            print(f"✅ Usuário '{username}' criado com sucesso!")
        
        print(f"\n🔑 Credenciais da API:")
        print(f"   Username: {username}")
        print(f"   Password: {password}")
        
        # Testar autenticação
        from django.contrib.auth import authenticate
        auth_user = authenticate(username=username, password=password)
        if auth_user:
            print(f"✅ Autenticação testada com sucesso!")
        else:
            print(f"❌ Falha no teste de autenticação!")
            return False
            
        return True
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        return False

if __name__ == "__main__":
    print("👤 Verificando usuário da API...")
    print("=" * 40)
    success = check_and_create_user()
    sys.exit(0 if success else 1)