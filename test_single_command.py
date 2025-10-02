#!/usr/bin/env python
"""
Script para executar comandos individuais da OLT
"""
import os
import sys
import django
from dotenv import load_dotenv
from netmiko import ConnectHandler

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'isp.settings')
django.setup()

# Carregar variáveis de ambiente
load_dotenv()

def execute_single_command(command):
    """Executa um comando específico da OLT"""
    
    # Configuração da OLT
    nokia = {
        'device_type': os.getenv('NOKIA_DEVICE_TYPE'),
        'host': os.getenv('NOKIA_HOST'),
        'username': os.getenv('NOKIA_USERNAME'),
        'password': os.getenv('NOKIA_PASSWORD'),
        'verbose': os.getenv('NOKIA_VERBOSE') == 'True',
        'global_delay_factor': int(os.getenv('NOKIA_GLOBAL_DELAY_FACTOR', 2)),
    }
    
    try:
        # Conectar à OLT
        print(f"Conectando à OLT para executar: {command}")
        net_connect = ConnectHandler(**nokia)
        net_connect.find_prompt()
        
        # Executar comando
        print(f"Executando comando: {command}")
        output = net_connect.send_command(command, read_timeout=60)
        print(output)
        
        # Desconectar
        net_connect.disconnect()
        print(f"Comando '{command}' executado com sucesso!")
        
        return output
        
    except Exception as e:
        print(f"Erro ao executar comando '{command}': {str(e)}")
        return None

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Uso: python test_single_command.py 'comando'")
        sys.exit(1)
    
    command = sys.argv[1]
    execute_single_command(command)