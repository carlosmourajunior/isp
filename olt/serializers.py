from rest_framework import serializers
from .models import (
    ONU, Olt, OltUsers, PlacaOnu, ClienteFibraIxc,
    OltSystemInfo, OltSlot, OltTemperature, OltSfpDiagnostics
)


class OltSerializer(serializers.ModelSerializer):
    """CRUD de OLTs. A senha SSH é write-only - nunca volta numa resposta de
    leitura (fica só criptografada no banco, ver olt/fields.py)."""
    password = serializers.CharField(write_only=True, style={'input_type': 'password'})

    class Meta:
        model = Olt
        fields = [
            'id',
            'name',
            'vendor',
            'device_type',
            'host',
            'username',
            'password',
            'ssh_port',
            'slot_count',
            'global_delay_factor',
            'verbose',
            'is_active',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']

    # Como chegar na OLT (IP, usuário e porta SSH) só aparece para administradores: a lista de OLTs
    # é aberta a qualquer usuário autenticado (popula o filtro de OLT das telas), mas o IP e o
    # usuário de acesso ao equipamento não devem ir para parceiros nem para usuários comuns.
    CAMPOS_DE_ACESSO = ('host', 'username', 'ssh_port')

    def to_representation(self, instance):
        dados = super().to_representation(instance)
        usuario = getattr(self.context.get('request'), 'user', None)
        if not (usuario and (usuario.is_staff or usuario.is_superuser)):
            for campo in self.CAMPOS_DE_ACESSO:
                dados.pop(campo, None)
        return dados

    def update(self, instance, validated_data):
        # Senha em branco no formulário de edição = mantém a senha atual.
        if not validated_data.get('password'):
            validated_data.pop('password', None)
        return super().update(instance, validated_data)


class ONUSerializer(serializers.ModelSerializer):
    slot = serializers.SerializerMethodField()
    port = serializers.SerializerMethodField()
    olt_name = serializers.CharField(source='olt.name', read_only=True, default=None)

    class Meta:
        model = ONU
        fields = [
            'id',
            'olt',
            'olt_name',
            'pon',
            'slot',
            'port',
            'position',
            'mac',
            'serial',
            'oper_state',
            'admin_state',
            'olt_rx_sig',
            'ont_rx_sig',
            'ont_tx_sig',
            'ont_olt',
            'desc1',
            'desc2',
            'cliente_fibra'
        ]

    def get_slot(self, obj):
        return obj.get_slot()

    def get_port(self, obj):
        return obj.get_port()


class OltUsersSerializer(serializers.ModelSerializer):
    olt_name = serializers.CharField(source='olt.name', read_only=True, default=None)

    class Meta:
        model = OltUsers
        fields = [
            'id',
            'olt',
            'olt_name',
            'slot',
            'port',
            'users_connected',
            'last_updated'
        ]


class PlacaOnuSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlacaOnu
        fields = [
            'id',
            'chassi',
            'position'
        ]


class ClienteFibraIxcSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClienteFibraIxc
        fields = [
            'id',
            'mac',
            'nome',
            'latitude',
            'longitude',
            'endereco',
            'id_caixa_ftth'
        ]


class ClienteFibraIxcInternalSerializer(serializers.ModelSerializer):
    """Versão do serializer de Clientes Fibra usada só pelo frontend interno (não é o contrato
    congelado de parceiros) - inclui o campo 'vinculado' usado pra filtrar registros sem contrato
    real no IXC (ver ONU.update_cliente_fibra_status / client_utils.update_clientes)."""

    class Meta:
        model = ClienteFibraIxc
        fields = [
            'id',
            'mac',
            'nome',
            'latitude',
            'longitude',
            'endereco',
            'id_caixa_ftth',
            'id_contrato',
            'vinculado',
        ]


class ONUDetailSerializer(ONUSerializer):
    """Serializer mais detalhado com informações do cliente fibra associado"""
    cliente_info = serializers.SerializerMethodField()

    class Meta(ONUSerializer.Meta):
        fields = ONUSerializer.Meta.fields + ['cliente_info']

    def get_cliente_info(self, obj):
        try:
            cliente = ClienteFibraIxc.objects.get(mac=obj.serial, nome=obj.desc1)
            return ClienteFibraIxcSerializer(cliente).data
        except ClienteFibraIxc.DoesNotExist:
            return None


class OltSystemInfoSerializer(serializers.ModelSerializer):
    total_uptime_hours = serializers.ReadOnlyField()
    olt_name = serializers.CharField(source='olt.name', read_only=True, default=None)

    class Meta:
        model = OltSystemInfo
        fields = [
            'id',
            'olt',
            'olt_name',
            'isam_release',
            'uptime_days',
            'uptime_hours', 
            'uptime_minutes',
            'uptime_seconds',
            'uptime_raw',
            'total_uptime_hours',
            'last_updated'
        ]


class OltSlotSerializer(serializers.ModelSerializer):
    is_operational = serializers.ReadOnlyField()
    olt_name = serializers.CharField(source='olt.name', read_only=True, default=None)

    class Meta:
        model = OltSlot
        fields = [
            'id',
            'olt',
            'olt_name',
            'slot_name',
            'actual_type',
            'enabled',
            'error_status',
            'availability',
            'restart_count',
            'is_operational',
            'last_updated'
        ]


class OltTemperatureSerializer(serializers.ModelSerializer):
    is_critical = serializers.ReadOnlyField()
    is_warning = serializers.ReadOnlyField()
    status = serializers.ReadOnlyField()
    olt_name = serializers.CharField(source='olt.name', read_only=True, default=None)

    class Meta:
        model = OltTemperature
        fields = [
            'id',
            'olt',
            'olt_name',
            'slot_name',
            'sensor_id',
            'actual_temp',
            'tca_low',
            'tca_high',
            'shutdown_low',
            'shutdown_high',
            'is_critical',
            'is_warning',
            'status',
            'last_updated'
        ]


class OltSfpDiagnosticsSerializer(serializers.ModelSerializer):
    olt_name = serializers.CharField(source='olt.name', read_only=True, default=None)

    class Meta:
        model = OltSfpDiagnostics
        fields = [
            'id',
            'olt',
            'olt_name',
            'interface',
            'vendor_name',
            'part_number',
            'serial_number',
            'temperature',
            'voltage',
            'tx_power',
            'rx_power',
            'last_updated'
        ]


class OltSystemStatsSerializer(serializers.Serializer):
    """Serializer para estatísticas do sistema OLT"""
    system_info = OltSystemInfoSerializer()
    slots_stats = serializers.DictField()
    temperature_stats = serializers.DictField()
    critical_temperatures = serializers.IntegerField()
    warning_temperatures = serializers.IntegerField()
    total_slots = serializers.IntegerField()
    operational_slots = serializers.IntegerField()
    offline_slots = serializers.IntegerField()