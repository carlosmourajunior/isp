from django.contrib import admin
from django.shortcuts import redirect
from django.urls import reverse
from django.utils import timezone
from django.contrib.admin import register
from django.contrib import messages
from olt.models import ONU, Olt, OltUsers, PlacaOnu, AllowedIP, OntEvent, OltSyslogMessage, OntSnapshot, SchedulerConfig, Cto, ClienteFibraIxc, CtoInferencia, Vistoria, VistoriaPorta
from olt.utils import olt_connector


@register(Olt)
class OltCatalogAdmin(admin.ModelAdmin):
    # Senha nunca aparece na listagem nem é editável por aqui (fica só no
    # formulário do frontend, que grava via API - ver olt/serializers.py).
    list_display = ['name', 'vendor', 'host', 'is_active', 'created_at']
    list_filter = ['vendor', 'is_active']
    search_fields = ['name', 'host']
    exclude = ['password']
    ordering = ['name']


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


# Histórico/eventos de ocupação de CTO: só leitura, são gerados pelo sistema.
class ReadOnlyAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@register(OntEvent)
class OntEventAdmin(ReadOnlyAdmin):
    list_display = ('occurred_at', 'olt', 'pon', 'position', 'serial', 'event_type', 'is_clear', 'alarm_type')
    list_filter = ('olt', 'event_type', 'is_clear')
    search_fields = ('serial', 'pon')
    date_hierarchy = 'occurred_at'


@register(OltSyslogMessage)
class OltSyslogMessageAdmin(ReadOnlyAdmin):
    list_display = ('received_at', 'olt', 'source_ip', 'parsed', 'raw')
    list_filter = ('olt', 'parsed')
    search_fields = ('raw',)


@register(OntSnapshot)
class OntSnapshotAdmin(ReadOnlyAdmin):
    list_display = ('taken_at', 'olt', 'pon', 'position', 'serial', 'oper_state', 'olt_rx_sig', 'distance_km')
    list_filter = ('olt', 'oper_state')
    search_fields = ('serial', 'pon')


@register(SchedulerConfig)
class SchedulerConfigAdmin(admin.ModelAdmin):
    """Registro único: a lista redireciona direto para o formulário."""
    fields = ('enabled', 'interval_minutes', 'proxima_execucao', 'last_run_at', 'last_run_summary', 'processo_scheduler')
    readonly_fields = ('proxima_execucao', 'last_run_at', 'last_run_summary', 'processo_scheduler')

    def changelist_view(self, request, extra_context=None):
        obj = SchedulerConfig.load()
        return redirect(reverse('admin:olt_schedulerconfig_change', args=[obj.pk]))

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    @admin.display(description="Próxima execução")
    def proxima_execucao(self, obj):
        if not obj.enabled:
            return "Desligada"
        if not obj.next_run_at or obj.next_run_at <= timezone.now():
            return "Na próxima verificação (até 1 minuto)"
        return timezone.localtime(obj.next_run_at).strftime('%d/%m/%Y %H:%M')

    @admin.display(description="Processo do scheduler")
    def processo_scheduler(self, obj):
        if not obj.heartbeat_at:
            return "Sem sinal - o container 'scheduler' está rodando?"
        segundos = int((timezone.now() - obj.heartbeat_at).total_seconds())
        if obj.scheduler_alive():
            return f"Ativo (último sinal há {segundos}s)"
        return f"Sem sinal há {segundos // 60} min - o container 'scheduler' está rodando?"


@register(Cto)
class CtoAdmin(ReadOnlyAdmin):
    """CTOs vêm do IXC (sync_ctos_ixc) + KMZ (importar_kmz): só leitura."""
    list_display = ('descricao', 'tipo', 'origem', 'ixc_id', 'olt', 'ramal', 'portas_display', 'clientes_cadastro', 'kmz_splitter', 'kmz_match', 'is_active')
    list_filter = ('olt', 'origem', 'tipo', 'ramal', 'kmz_match', 'is_active', 'id_projeto')
    search_fields = ('descricao', 'ixc_id', 'kmz_nome')

    @admin.display(description="Portas")
    def portas_display(self, obj):
        return obj.portas

    @admin.display(description="Clientes no cadastro IXC")
    def clientes_cadastro(self, obj):
        if not obj.ixc_id:
            return '-'
        return ClienteFibraIxc.objects.filter(id_caixa_ftth=obj.ixc_id, is_active=True).count()


@register(CtoInferencia)
class CtoInferenciaAdmin(ReadOnlyAdmin):
    """Resultado de manage.py inferir_ctos."""
    list_display = ('pon', 'position', 'serial', 'cliente_nome', 'distance_km', 'cto_cadastro', 'cto_provavel',
                    'score', 'cto_alternativa', 'score_alternativa', 'status')
    list_filter = ('olt', 'status', 'pon')
    search_fields = ('serial', 'cliente_nome', 'cto_provavel__descricao', 'cto_cadastro__descricao')
    list_select_related = ('cto_cadastro', 'cto_provavel', 'cto_alternativa')
    readonly_fields = ('motivos_provavel', 'motivos_cadastro', 'motivos_alternativa')

    @staticmethod
    def _motivos(obj, chave):
        motivos = obj.motivos or {}
        if isinstance(motivos, list):  # formato antigo
            return "; ".join(motivos) if chave == 'provavel' else ''
        return "; ".join(motivos.get(chave, [])) or '-'

    @admin.display(description="Por que a CTO provável")
    def motivos_provavel(self, obj):
        return self._motivos(obj, 'provavel')

    @admin.display(description="Por que a CTO do cadastro perdeu")
    def motivos_cadastro(self, obj):
        return self._motivos(obj, 'cadastro')

    @admin.display(description="Por que a 2ª candidata")
    def motivos_alternativa(self, obj):
        return self._motivos(obj, 'alternativa')


class VistoriaPortaInline(admin.TabularInline):
    model = VistoriaPorta
    extra = 0
    fields = ('porta', 'resultado', 'metodo', 'cliente_nome', 'serial', 'pon', 'position', 'reconexao_confirmada', 'observacao')
    readonly_fields = fields
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@register(Vistoria)
class VistoriaAdmin(admin.ModelAdmin):
    """Vistorias são feitas pela tela do frontend; aqui é consulta."""
    list_display = ('cto', 'olt', 'tecnico', 'usuario', 'iniciada_em', 'finalizada_em')
    list_filter = ('olt',)
    search_fields = ('cto__descricao', 'tecnico', 'portas__cliente_nome', 'portas__serial')
    readonly_fields = ('cto', 'olt', 'usuario', 'iniciada_em', 'finalizada_em')
    inlines = [VistoriaPortaInline]

    def has_add_permission(self, request):
        return False
