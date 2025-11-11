#!/usr/bin/env python3
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'isp.settings')
django.setup()

from olt.models import ONU

print("=== Verificando PONs no banco de dados ===")
onus = ONU.objects.all()[:10]
print("Algumas PONs no banco:")
for onu in onus:
    print(f'ID: {onu.id}, PON: "{onu.pon}", Serial: {onu.serial}')

print(f"\nTotal de ONUs: {ONU.objects.count()}")

# Verificar PONs distintas
pons = ONU.objects.values_list('pon', flat=True).distinct()[:20]
print(f"\nPrimeiras 20 PONs distintas:")
for pon in pons:
    count = ONU.objects.filter(pon=pon).count()
    print(f'PON "{pon}": {count} ONUs')