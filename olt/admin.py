from django.contrib import admin
from django.contrib.admin import register
from olt.models import OltUsers


@admin.action(description='Mark selected stories as published')
def update_olt_ports(modeladmin, request, queryset):
    from olt.utils import olt_connector
    connector = olt_connector()
    connector.update_port_ocupation()
    

@register(OltUsers)
class OltAdmin(admin.ModelAdmin):
    list_display = ['slot', 'port', 'users_connected']
    list_filter = ['slot', 'port', 'users_connected']

    ordering = ['users_connected']
    actions = [update_olt_ports]

