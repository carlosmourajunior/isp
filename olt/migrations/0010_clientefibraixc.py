# Generated by Django 4.0.8 on 2024-06-13 18:38

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('olt', '0009_remove_onu_descricao_remove_onu_pppoe_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='ClienteFibraIxc',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('mac', models.CharField(max_length=255)),
                ('nome', models.CharField(max_length=255)),
            ],
            options={
                'verbose_name': 'Cliente Fibra',
                'verbose_name_plural': 'Clientes Fibra',
            },
        ),
    ]