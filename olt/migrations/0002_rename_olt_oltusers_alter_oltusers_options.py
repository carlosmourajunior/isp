# Generated by Django 4.0.8 on 2023-01-25 19:49

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('olt', '0001_initial'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='olt',
            new_name='OltUsers',
        ),
        migrations.AlterModelOptions(
            name='oltusers',
            options={'verbose_name': 'Ocupação da OLT', 'verbose_name_plural': 'Ocupação da OLT'},
        ),
    ]