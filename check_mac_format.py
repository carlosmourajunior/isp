#!/usr/bin/env python
import os
import sys
import django

# Configurar o Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'isp.settings')
django.setup()

from olt.models import ONU

print("=== VERIFICAÇÃO DE MACs NO BANCO DE DADOS ===")
print()

# Pegar algumas ONUs do PON 1/1/2/6 para verificar
onus = ONU.objects.filter(pon='1/1/2/6')[:5]

if onus:
    print(f"ONUs encontradas no PON 1/1/2/6: {len(onus)}")
    print()
    
    for onu in onus:
        mac_length = len(onu.mac) if onu.mac else 0
        has_colons = ':' in onu.mac if onu.mac else False
        print(f"Posição {onu.position}:")
        print(f"  Serial: {onu.serial}")
        print(f"  MAC: '{onu.mac}'")
        print(f"  Tamanho: {mac_length} caracteres")
        print(f"  Tem dois pontos: {has_colons}")
        print()
else:
    print("Nenhuma ONU encontrada no PON 1/1/2/6")
    
    # Verificar outras ONUs
    other_onus = ONU.objects.all()[:3]
    if other_onus:
        print("Verificando outras ONUs:")
        print()
        for onu in other_onus:
            mac_length = len(onu.mac) if onu.mac else 0
            has_colons = ':' in onu.mac if onu.mac else False
            print(f"PON {onu.pon}, Posição {onu.position}:")
            print(f"  Serial: {onu.serial}")
            print(f"  MAC: '{onu.mac}'")
            print(f"  Tamanho: {mac_length} caracteres")
            print(f"  Tem dois pontos: {has_colons}")
            print()