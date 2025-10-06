from django.contrib import admin
from django.contrib.admin import register
from django.contrib import messages
from olt.models import ONU, OltUsers, PlacaOnu, AllowedIP
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


@admin.action(description='Ativar IPs selecionados')
def activate_ips(modeladmin, request, queryset):
    updated = queryset.update(is_active=True)
    messages.success(request, f'{updated} IP(s) ativado(s) com sucesso!')

@admin.action(description='Desativar IPs selecionados')
def deactivate_ips(modeladmin, request, queryset):
    updated = queryset.update(is_active=False)
    messages.success(request, f'{updated} IP(s) desativado(s) com sucesso!')


@register(AllowedIP)
class AllowedIPAdmin(admin.ModelAdmin):
    list_display = ['ip_address', 'description', 'is_active', 'created_at', 'updated_at']
    list_filter = ['is_active', 'created_at', 'updated_at']
    search_fields = ['ip_address', 'description']
    list_editable = ['is_active', 'description']
    
    fieldsets = (
        (None, {
            'fields': ('ip_address', 'description', 'is_active'),
            'description': 'Configure IPs ou ranges que podem acessar o sistema'
        }),
    )
    
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['ip_address']
    actions = [activate_ips, deactivate_ips]
    
    def get_readonly_fields(self, request, obj=None):
        if obj:  # Editando um objeto existente
            return self.readonly_fields + ['created_at', 'updated_at']
        return self.readonly_fields
    
    def save_model(self, request, obj, form, change):
        """Adiciona uma mensagem de sucesso personalizada"""
        super().save_model(request, obj, form, change)
        if change:
            messages.success(request, f'IP {obj.ip_address} atualizado com sucesso!')
        else:
            messages.success(request, f'IP {obj.ip_address} adicionado com sucesso!')
