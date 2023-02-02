# Generated by Django 4.0.8 on 2023-02-02 19:28

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('olt', '0002_rename_olt_oltusers_alter_oltusers_options'),
    ]

    operations = [
        migrations.CreateModel(
            name='ONU',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('pon', models.CharField(max_length=20, verbose_name='PON')),
                ('position', models.IntegerField(validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(128)], verbose_name='Posição')),
                ('mac', models.CharField(max_length=200, verbose_name='MAC')),
                ('serial', models.CharField(max_length=30, verbose_name='Serial')),
                ('oper_state', models.CharField(max_length=30, verbose_name='Status')),
                ('pppoe', models.CharField(max_length=200, verbose_name='PPPoE')),
                ('descricao', models.CharField(max_length=300, verbose_name='Descrição')),
            ],
            options={
                'verbose_name': 'ONU',
                'verbose_name_plural': 'ONUs',
            },
        ),
        migrations.AlterField(
            model_name='oltusers',
            name='port',
            field=models.IntegerField(validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(16)], verbose_name='Porta'),
        ),
        migrations.AlterField(
            model_name='oltusers',
            name='slot',
            field=models.IntegerField(validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(2)], verbose_name='Slot'),
        ),
    ]