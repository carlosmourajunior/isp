from rest_framework import serializers
from .models import (
    ONU, OltUsers, PlacaOnu, ClienteFibraIxc, 
    OltSystemInfo, OltSlot, OltTemperature, OltSfpDiagnostics
)


class ONUSerializer(serializers.ModelSerializer):
    slot = serializers.SerializerMethodField()
    port = serializers.SerializerMethodField()

    class Meta:
        model = ONU
        fields = [
            'id',
            'pon',
            'slot',
            'port',
            'position',
            'mac',
            'serial',
            'oper_state',
            'admin_state',
            'olt_rx_sig',
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
    class Meta:
        model = OltUsers
        fields = [
            'id',
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
    
    class Meta:
        model = OltSystemInfo
        fields = [
            'id',
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
    
    class Meta:
        model = OltSlot
        fields = [
            'id',
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
    
    class Meta:
        model = OltTemperature
        fields = [
            'id',
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
    class Meta:
        model = OltSfpDiagnostics
        fields = [
            'id',
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