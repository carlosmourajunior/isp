"""
Anotações de documentação (OpenAPI/Swagger) dos endpoints de parceiros.

Ficam aqui, fora das views, para não mexer no comportamento delas: só descrevem
parâmetros e respostas. Importado por olt/api_parceiros_urls.py (que define quais
endpoints entram na documentação pública).
"""
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import (OpenApiExample, OpenApiParameter, OpenApiResponse, extend_schema,
                                   extend_schema_field, extend_schema_view, inline_serializer)
from rest_framework import serializers
from rest_framework_simplejwt.views import TokenRefreshView

from . import api_views
from .serializers import (ClienteFibraIxcSerializer, ONUDetailSerializer, ONUSerializer, OltSystemInfoSerializer,
                          OltTemperatureSerializer)

_aplicado = False

ERRO = inline_serializer('Erro', {'error': serializers.CharField()})
NAO_AUTENTICADO = OpenApiResponse(description='Token ausente, inválido ou expirado - renove em /api/auth/refresh/.')
OLT_PARAM = OpenApiParameter('olt', OpenApiTypes.INT, description='Filtra pela OLT (id). Sem ele, todas as OLTs.')


def aplicar():
    """Idempotente: decora as views uma vez só."""
    global _aplicado
    if _aplicado:
        return
    _aplicado = True

    extend_schema_field(OpenApiTypes.INT)(ONUSerializer.get_slot)
    extend_schema_field(OpenApiTypes.INT)(ONUSerializer.get_port)
    extend_schema_field(ClienteFibraIxcSerializer(allow_null=True))(ONUDetailSerializer.get_cliente_info)
    # Propriedades dos models expostas como ReadOnlyField: só o tipo, para a documentação.
    from .models import OltSlot, OltSystemInfo, OltTemperature
    for model, nome, tipo in ((OltSystemInfo, 'total_uptime_hours', OpenApiTypes.FLOAT),
                              (OltSlot, 'is_operational', OpenApiTypes.BOOL),
                              (OltTemperature, 'is_critical', OpenApiTypes.BOOL),
                              (OltTemperature, 'is_warning', OpenApiTypes.BOOL),
                              (OltTemperature, 'status', OpenApiTypes.STR)):
        extend_schema_field(tipo)(getattr(model, nome).fget)

    # ------------------------------------------------------------ autenticação
    extend_schema_view(post=extend_schema(
        tags=['Autenticação'], summary='Login (obter token)',
        description='Troca usuário e senha por um par de tokens JWT. `access` vale 60 min; `refresh`, 7 dias.',
        responses={200: inline_serializer('Login', {
            'access': serializers.CharField(), 'refresh': serializers.CharField(),
            'user_info': inline_serializer('LoginUsuario', {'username': serializers.CharField(),
                                                            'message': serializers.CharField()}),
        }), 401: OpenApiResponse(description='Usuário ou senha incorretos.')},
        examples=[OpenApiExample('Login', value={'username': 'parceiro', 'password': '********'}, request_only=True)],
    ))(api_views.CustomTokenObtainPairView)
    extend_schema_view(post=extend_schema(
        tags=['Autenticação'], summary='Renovar token',
        description='Envia o `refresh` e recebe um `access` novo (e um `refresh` novo - guarde-o, o antigo deixa de valer).',
    ))(TokenRefreshView)

    # -------------------------------------------------------------------- ONUs
    extend_schema_view(get=extend_schema(
        tags=['ONUs'], summary='Listar ONUs',
        description='Lista paginada. Sinais em dBm (`olt_rx_sig` = recebido na OLT, `ont_rx_sig`/`ont_tx_sig` = na ONU).',
        parameters=[
            OpenApiParameter('search', OpenApiTypes.STR, description='Busca em serial, MAC, descrição e PON.'),
            OpenApiParameter('ordering', OpenApiTypes.STR,
                             description='Campo de ordenação; prefixo `-` para decrescente. Ex.: `-olt_rx_sig`.'),
        ],
        responses={200: ONUSerializer(many=True), 401: NAO_AUTENTICADO},
    ))(api_views.ONUListAPIView)
    extend_schema_view(get=extend_schema(
        tags=['ONUs'], summary='Detalhe de uma ONU',
        description='Inclui `cliente_info` com o cliente fibra vinculado, quando houver.',
        responses={200: ONUDetailSerializer, 401: NAO_AUTENTICADO, 404: OpenApiResponse(description='ONU não existe.')},
    ))(api_views.ONUDetailAPIView)
    extend_schema(
        tags=['ONUs'], summary='Estatísticas das ONUs',
        responses={200: inline_serializer('OnuStats', {
            'total_onus': serializers.IntegerField(), 'onus_online': serializers.IntegerField(),
            'onus_offline': serializers.IntegerField(), 'clientes_fibra': serializers.IntegerField(),
            'onus_sinal_baixo': serializers.IntegerField(help_text='Sinal na OLT abaixo de -25 dBm.'),
            'estatisticas_por_slot': serializers.DictField(
                child=inline_serializer('OnuStatsSlot', {'total': serializers.IntegerField(),
                                                         'online': serializers.IntegerField(),
                                                         'offline': serializers.IntegerField()}),
                help_text='Chave `slot_N`.'),
            'percentual_online': serializers.FloatField(),
        }), 401: NAO_AUTENTICADO},
    )(api_views.onu_stats)
    extend_schema(
        tags=['ONUs'], summary='ONUs de uma PON',
        description='`pon` no formato `1/1/<slot>/<porta>`, com as barras codificadas (`1%2F1%2F1%2F5`).',
        parameters=[OpenApiParameter('pon', OpenApiTypes.STR, OpenApiParameter.PATH, description='Ex.: 1/1/1/5')],
        responses={200: inline_serializer('OnusDaPon', {'pon': serializers.CharField(),
                                                        'total_onus': serializers.IntegerField(),
                                                        'onus': ONUSerializer(many=True)}),
                   404: ERRO, 401: NAO_AUTENTICADO},
    )(api_views.onu_by_pon)
    extend_schema(
        tags=['ONUs'], summary='Buscar ONUs',
        description='Busca (contém, sem diferenciar maiúsculas) em serial, MAC, descrições e PON. Não é paginada.',
        parameters=[OpenApiParameter('q', OpenApiTypes.STR, required=True, description='Termo de busca.')],
        responses={200: inline_serializer('BuscaOnus', {'query': serializers.CharField(),
                                                        'total_resultados': serializers.IntegerField(),
                                                        'resultados': ONUDetailSerializer(many=True)}),
                   400: ERRO, 401: NAO_AUTENTICADO},
    )(api_views.onu_search)

    # ------------------------------------------------------------ portas / clientes
    extend_schema_view(get=extend_schema(
        tags=['Portas'], summary='Ocupação das portas PON',
        description='Quantidade de ONUs conectadas em cada porta (slot/porta) na última leitura.',
    ))(api_views.OltUsersListAPIView)
    extend_schema_view(get=extend_schema(
        tags=['Clientes fibra'], summary='Listar clientes fibra',
        description='Cadastro de clientes fibra. `mac` é o serial da ONU do cliente (casa com `serial` em /api/onus/).',
        parameters=[OpenApiParameter('search', OpenApiTypes.STR, description='Busca em nome, MAC e endereço.')],
    ))(api_views.ClienteFibraListAPIView)

    # --------------------------------------------------------------------- OLT
    extend_schema_view(get=extend_schema(
        tags=['OLT'], summary='Informações do sistema da OLT',
        description='Release, uptime e afins da OLT padrão (primeira ativa).',
    ))(api_views.OltSystemInfoAPIView)
    extend_schema_view(get=extend_schema(tags=['OLT'], summary='Placas (slots)'))(api_views.OltSlotListAPIView)
    extend_schema_view(get=extend_schema(tags=['OLT'], summary='Temperaturas'))(api_views.OltTemperatureListAPIView)
    extend_schema_view(get=extend_schema(tags=['OLT'], summary='Diagnóstico dos SFPs'))(api_views.OltSfpDiagnosticsListAPIView)
    extend_schema(
        tags=['OLT'], summary='Estatísticas da OLT',
        description='Resumo de placas e temperaturas de todas as OLTs, com as informações de sistema da OLT padrão.',
        responses={200: inline_serializer('OltStats', {
            'system_info': OltSystemInfoSerializer(allow_null=True),
            'slots_stats': inline_serializer('OltStatsSlots', {
                'total_slots': serializers.IntegerField(), 'operational_slots': serializers.IntegerField(),
                'offline_slots': serializers.IntegerField(),
                'slots_by_type': serializers.ListField(child=serializers.DictField()),
                'operational_percentage': serializers.FloatField()}),
            'temperature_stats': inline_serializer('OltStatsTemperaturas', {
                'critical_temperatures': serializers.IntegerField(help_text='75 °C ou mais.'),
                'warning_temperatures': serializers.IntegerField(help_text='De 70 a 75 °C.'),
                'normal_temperatures': serializers.IntegerField(), 'average_temperature': serializers.FloatField(),
                'max_temperature': serializers.FloatField(), 'min_temperature': serializers.FloatField(),
                'temperature_by_slot': serializers.ListField(child=serializers.DictField())}),
            'last_updated': serializers.DateTimeField(allow_null=True),
        }), 401: NAO_AUTENTICADO, 500: ERRO},
    )(api_views.olt_system_stats)
    extend_schema(
        tags=['OLT'], summary='Alertas de temperatura',
        responses={200: inline_serializer('AlertasTemperatura', {
            'critical_alerts': OltTemperatureSerializer(many=True), 'warning_alerts': OltTemperatureSerializer(many=True),
            'critical_count': serializers.IntegerField(), 'warning_count': serializers.IntegerField(),
        }), 401: NAO_AUTENTICADO, 500: ERRO},
    )(api_views.olt_temperature_alerts)


aplicar()
