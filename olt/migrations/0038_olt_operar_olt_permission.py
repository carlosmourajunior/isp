from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('olt', '0037_cadastro_caixa_ixc'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='olt',
            options={
                'ordering': ['name'],
                'permissions': [('operar_olt', 'Pode remover e reiniciar ONUs na OLT')],
                'verbose_name': 'OLT',
                'verbose_name_plural': 'OLTs',
            },
        ),
    ]
