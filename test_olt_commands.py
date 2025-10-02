#!/usr/bin/env python
"""
Script para testar comandos da OLT e analisar retornos
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

def test_olt_commands():
    """Testa os comandos da OLT para analisar os retornos"""
    
    # Configuração da OLT
    nokia = {
        'device_type': os.getenv('NOKIA_DEVICE_TYPE'),
        'host': os.getenv('NOKIA_HOST'),
        'username': os.getenv('NOKIA_USERNAME'),
        'password': os.getenv('NOKIA_PASSWORD'),
        'verbose': os.getenv('NOKIA_VERBOSE') == 'True',
        'global_delay_factor': int(os.getenv('NOKIA_GLOBAL_DELAY_FACTOR', 2)),
    }
    
    # Lista de comandos para testar
    commands = [
        "show software-mngt version etsi",
        "show software-mngt oswp",
        "show software-mngt oswp detail",
        "show equipment slot",
        "show equipment slot detail",
        "show equipment temperature",
        "show core1-uptime",
        "show equipment ont interface",
        "show equipment ont status pon",
        "show equipment diagnostics sfp detail"
    ]
    
    try:
        # Conectar à OLT
        print("Conectando à OLT...")
        net_connect = ConnectHandler(**nokia)
        net_connect.find_prompt()
        print("Conectado com sucesso!")
        
        # Executar cada comando
        for cmd in commands:
            print(f"\n{'='*60}")
            print(f"COMANDO: {cmd}")
            print(f"{'='*60}")
            
            try:
                output = net_connect.send_command(cmd, read_timeout=30)
                print(output)
                print(f"\n[INFO] Comando executado com sucesso!")
                
                # Salvar output em arquivo para análise
                filename = f"output_{cmd.replace(' ', '_').replace('/', '_')}.txt"
                with open(f"/tmp/{filename}", 'w') as f:
                    f.write(f"COMANDO: {cmd}\n")
                    f.write(f"{'='*60}\n")
                    f.write(output)
                    f.write(f"\n{'='*60}\n")
                print(f"[INFO] Output salvo em /tmp/{filename}")
                
            except Exception as e:
                print(f"[ERRO] Falha ao executar comando '{cmd}': {str(e)}")
        
        # Desconectar
        net_connect.disconnect()
        print("\nDesconectado da OLT.")
        
    except Exception as e:
        print(f"[ERRO] Falha ao conectar à OLT: {str(e)}")

if __name__ == "__main__":
    test_olt_commands()