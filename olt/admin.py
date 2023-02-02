from django.contrib import admin
from django.contrib.admin import register
from olt.models import ONU, OltUsers


@admin.action(description='Atualizar Portas')
def update_olt_ports(modeladmin, request, queryset):
    from olt.utils import olt_connector
    connector = olt_connector()
    connector.update_port_ocupation()

@admin.action(description='Atualizar ONUs')
def update_olt_onu(modeladmin, request, queryset):
    from olt.utils import olt_connector
    connector = olt_connector()
    connector.update_port_ocupation()

@register(OltUsers)
class OltAdmin(admin.ModelAdmin):
    list_display = ['slot', 'port', 'users_connected']
    list_filter = ['slot', 'port', 'users_connected']

    ordering = ['users_connected']
    actions = [update_olt_ports]

@register(ONU)
class OnuAdmin(admin.ModelAdmin):
    list_display = ['pon', 'serial', 'pppoe']
    list_filter = ['pon', 'serial', 'pppoe']

    ordering = ['pon']
    actions = [update_olt_onu]