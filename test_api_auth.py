#!/usr/bin/env python
import os
import sys
import django

# Configure Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'isp.settings')
django.setup()

import requests
from django.contrib.sessions.models import Session
from django.contrib.auth import get_user_model

User = get_user_model()

def test_api_authentication():
    # Criar ou obter usuário
    user, created = User.objects.get_or_create(
        username='test_admin',
        defaults={
            'is_staff': True,
            'is_superuser': True
        }
    )
    
    if created:
        user.set_password('test123')
        user.save()
        print(f"Usuário criado: {user.username}")
    else:
        print(f"Usuário encontrado: {user.username}")
    
    # Testar login via Django session
    from django.test import Client
    client = Client()
    
    # Login
    login_success = client.login(username='test_admin', password='test123')
    print(f"Login bem-sucedido: {login_success}")
    
    if login_success:
        # Testar endpoint da API
        response = client.post('/api/olt/alarms/collect/')
        print(f"Status da resposta: {response.status_code}")
        print(f"Conteúdo da resposta: {response.json() if response.status_code != 500 else response.content}")
        
        # Verificar headers
        print(f"Headers da resposta: {dict(response.items())}")

if __name__ == '__main__':
    test_api_authentication()