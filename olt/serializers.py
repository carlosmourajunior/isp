from rest_framework import serializers
from .models import ONU, OltUsers, PlacaOnu, ClienteFibraIxc


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