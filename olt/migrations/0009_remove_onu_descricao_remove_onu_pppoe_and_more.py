# Generated by Django 4.0.8 on 2024-04-18 13:09

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('olt', '0008_onu_admin_state_onu_signal_rx'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='onu',
            name='descricao',
        ),
        migrations.RemoveField(
            model_name='onu',
            name='pppoe',
        ),
        migrations.RemoveField(
            model_name='onu',
            name='signal_rx',
        ),
        migrations.AddField(
            model_name='onu',
            name='desc1',
            field=models.CharField(default='', max_length=200, verbose_name='Descrição_1'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='onu',
            name='desc2',
            field=models.CharField(default='', max_length=300, verbose_name='Descrição_2'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='onu',
            name='olt_rx_sig',
            field=models.CharField(blank=True, default='0', max_length=200, null=True, verbose_name='OLT RX Signal'),
        ),
        migrations.AddField(
            model_name='onu',
            name='ont_olt',
            field=models.CharField(blank=True, default='0', max_length=200, null=True, verbose_name='Distancia'),
        ),
    ]
