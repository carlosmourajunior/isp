# Generated by Django 4.0.8 on 2023-02-03 12:28

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('olt', '0004_placaonu'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='oltusers',
            options={'verbose_name': 'Porta', 'verbose_name_plural': 'Portas'},
        ),
        migrations.AlterModelOptions(
            name='placaonu',
            options={'verbose_name': 'Placa', 'verbose_name_plural': 'Placas'},
        ),
        migrations.AlterField(
            model_name='placaonu',
            name='chassi',
            field=models.CharField(default='1/1/1', max_length=20, verbose_name='Chassi'),
        ),
    ]
