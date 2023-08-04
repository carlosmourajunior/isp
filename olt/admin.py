from django.contrib import admin
from django.contrib.admin import register
from olt.models import ONU, OltUsers, PlacaOnu
from olt.utils import olt_connector


@admin.action(description='Atualizar Portas')
def update_olt_ports(modeladmin, request, queryset):
    connector = olt_connector()
    connector.update_port_ocupation()

@admin.action(description='Atualizar ONUs')
def update_olt_onu(modeladmin, request, queryset):
    connector = olt_connector()
    connector.update_port_ocupation()

@admin.action(description='Reset da Placa')
def reset_placa_onu(modeladmin, request, queryset):
    connector = olt_connector()
    connector.reset_placa_onu(queryset)

@admin.action(description='Atualizar ONus')
def update_onus(modeladmin, request, queryset):
    connector = olt_connector()
    connector.get_itens_to_remove(queryset)

@admin.action(description='Ecluir ONus')
def excluir_onus(modeladmin, request, queryset):
    connector = olt_connector()
    connector.remove_onu(queryset)

@register(OltUsers)
class OltAdmin(admin.ModelAdmin):
    list_display = ['slot', 'port', 'users_connected']
    list_filter = ['slot', 'port', 'users_connected']

    ordering = ['users_connected']
    actions = [update_olt_ports]

 
@register(ONU)
class OnuAdmin(admin.ModelAdmin):
    list_display = [field.name for field in ONU._meta.get_fields()]
    list_filter = [field.name for field in ONU._meta.get_fields()]

    ordering = ['position']
    actions = [update_olt_onu, excluir_onus]


@register(PlacaOnu)
class PlacaAdmin(admin.ModelAdmin):
    list_display = ['chassi', 'position']
    list_filter = ['chassi', 'position']

    ordering = ['position']
    actions = [reset_placa_onu, update_onus]
