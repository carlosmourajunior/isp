#!/usr/bin/env python3
"""
Script para alterar a senha do usuário admin
"""

import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'olt_connector.settings')
django.setup()

from django.contrib.auth.models import User

def reset_admin_password():
    """Redefine a senha do usuário admin"""
    username = 'admin'
    new_password = 'admin123'
    
    try:
        user = User.objects.get(username=username)
        user.set_password(new_password)
        user.save()
        print(f"✅ Senha do usuário '{username}' alterada com sucesso!")
        print(f"   Username: {username}")
        print(f"   Password: {new_password}")
        return True
    except User.DoesNotExist:
        print(f"❌ Usuário '{username}' não encontrado!")
        return False
    except Exception as e:
        print(f"❌ Erro ao alterar senha: {e}")
        return False

if __name__ == "__main__":
    print("🔑 Alterando senha do usuário admin...")
    success = reset_admin_password()
    sys.exit(0 if success else 1)