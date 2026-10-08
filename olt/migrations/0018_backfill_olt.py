"""
Cria a OLT existente ("OLT 1") com os valores que já estão no .env hoje
(NOKIA_HOST/NOKIA_USERNAME/NOKIA_PASSWORD/NOKIA_DEVICE_TYPE) e aponta todas
as linhas já existentes (ONUs, portas, slots, temperaturas, SFPs, system
info) pra ela. Sem isso, todo o histórico ficaria com olt=None depois da
migração anterior adicionar o campo.
"""
import os

from django.db import migrations


def criar_olt_e_vincular_dados_existentes(apps, schema_editor):
    Olt = apps.get_model('olt', 'Olt')
    ONU = apps.get_model('olt', 'ONU')
    OltUsers = apps.get_model('olt', 'OltUsers')
    OltSystemInfo = apps.get_model('olt', 'OltSystemInfo')
    OltSlot = apps.get_model('olt', 'OltSlot')
    OltTemperature = apps.get_model('olt', 'OltTemperature')
    OltSfpDiagnostics = apps.get_model('olt', 'OltSfpDiagnostics')

    tem_dado_existente = any([
        ONU.objects.exists(),
        OltUsers.objects.exists(),
        OltSystemInfo.objects.exists(),
        OltSlot.objects.exists(),
        OltTemperature.objects.exists(),
        OltSfpDiagnostics.objects.exists(),
    ])
    if not tem_dado_existente:
        # Banco novo (ex: suíte de testes) - não cria OLT "fantasma" à toa.
        return

    olt, _ = Olt.objects.get_or_create(
        name='OLT 1',
        defaults={
            'vendor': 'nokia_alcatel',
            'device_type': os.getenv('NOKIA_DEVICE_TYPE', 'alcatel_aos'),
            'host': os.getenv('NOKIA_HOST', ''),
            'username': os.getenv('NOKIA_USERNAME', ''),
            'password': os.getenv('NOKIA_PASSWORD', ''),
            'global_delay_factor': int(os.getenv('NOKIA_GLOBAL_DELAY_FACTOR', 2)),
            'verbose': os.getenv('NOKIA_VERBOSE') == 'True',
        },
    )

    ONU.objects.filter(olt__isnull=True).update(olt=olt)
    OltUsers.objects.filter(olt__isnull=True).update(olt=olt)
    OltSlot.objects.filter(olt__isnull=True).update(olt=olt)
    OltTemperature.objects.filter(olt__isnull=True).update(olt=olt)
    OltSfpDiagnostics.objects.filter(olt__isnull=True).update(olt=olt)
    # OneToOne: só um registro deveria existir (get_or_create(id=1) antigo).
    OltSystemInfo.objects.filter(olt__isnull=True).exclude(
        id__in=OltSystemInfo.objects.exclude(olt__isnull=True).values('id')
    ).update(olt=olt)


def reverter(apps, schema_editor):
    # Não desfaz o vínculo - reverter essa migração intencionalmente não
    # apaga a OLT nem desassocia os dados (evita perda de dado num rollback).
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('olt', '0017_olt_alter_oltsfpdiagnostics_interface_and_more'),
    ]

    operations = [
        migrations.RunPython(criar_olt_e_vincular_dados_existentes, reverter),
    ]
