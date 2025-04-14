from django.db import migrations, models

def clean_olt_rx_sig(apps, schema_editor):
    ONU = apps.get_model('olt', 'ONU')
    for onu in ONU.objects.all():
        try:
            onu.olt_rx_sig = float(onu.olt_rx_sig)
        except (ValueError, TypeError):
            onu.olt_rx_sig = 0.0  # Set a default value for invalid entries
        onu.save()

class Migration(migrations.Migration):

    dependencies = [
        ('olt', '0014_alter_onu_olt_rx_sig'),
    ]

    operations = [
        migrations.RunPython(clean_olt_rx_sig),
    ]