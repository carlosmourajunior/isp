"""
Endpoints da inferência de CTO (tela "CTOs" do frontend). Só leitura: os
dados vêm de Cto (IXC + KMZ) e CtoInferencia (manage.py inferir_ctos).

Endpoints novos - não alteram nenhum existente:
    GET /api/ctos/                      todas as CTOs com ocupação estimada (mapa/lista)
    GET /api/ctos/<id>/                 detalhe: clientes da CTO e o papel de cada um
    GET /api/cto-inferencias/           inferência por ONT, paginada (fila de divergências)
    GET /api/cto-inferencias/resumo/    contagens para os cards

Ocupação estimada = confirmados + prováveis + vindos de outra CTO (divergentes
cuja CTO provável é esta). Incertos não entram na conta; aparecem como
"possíveis" para mostrar a faixa de incerteza. A capacidade usada é a de portas
úteis: projeto + splitters adicionados em campo - portas inutilizadas.

Ajustes de campo (endpoints novos):
    POST   /api/ctos/<id>/splitters/           {portas: 4|8} adiciona um splitter
    DELETE /api/ctos/<id>/splitters/           desfaz o último splitter adicionado
    POST   /api/ctos/<id>/portas-inutilizadas/ {porta, inutilizada: true|false}
"""
from collections import Counter, defaultdict

from django.db.models import Max, Q
from django.shortcuts import get_object_or_404
from rest_framework import filters, generics, serializers
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status as http_status
from django.utils import timezone

from .models import ONU, ClienteFibraIxc, Cto, CtoInferencia

# Faixas de ocupação (ocupadas / portas).
QUASE_CHEIA = 0.75


def situacao(portas, ocupadas):
    if not portas:
        return 'sem_capacidade'
    if ocupadas > portas:
        return 'acima'
    if ocupadas == portas:
        return 'cheia'
    if ocupadas / portas >= QUASE_CHEIA:
        return 'quase_cheia'
    return 'livre'


def papel(inferencia, cto_id):
    """Papel do cliente em relação à CTO consultada."""
    if inferencia.cto_provavel_id == cto_id:
        return {
            'vistoriado': 'confirmado',     # confirmado em campo
            'confirmado': 'confirmado',
            'provavel': 'provavel',
            'divergente': 'veio_de_outra',   # cadastrado em outra CTO, rede aponta esta
            'incerto': 'possivel',
        }.get(inferencia.status, 'possivel')
    return 'suspeito'                        # cadastrado aqui, rede aponta outra


def _oper_states(olt_ids=None):
    qs = ONU.objects.all()
    if olt_ids is not None:
        qs = qs.filter(olt_id__in=olt_ids)
    return {(o.olt_id, o.pon, o.position): (o.oper_state, o.olt_rx_sig)
            for o in qs.only('olt_id', 'pon', 'position', 'oper_state', 'olt_rx_sig')}


def _ref(cto):
    return {'id': cto.id, 'descricao': cto.descricao} if cto else None


def _cto_basico(cto):
    return {
        'id': cto.id,
        'descricao': cto.descricao,
        'tipo': cto.tipo,
        'origem': cto.origem,
        'ixc_id': cto.ixc_id,
        'olt_id': cto.olt_id,
        'olt_nome': cto.olt.name if cto.olt_id else None,
        'ramal': cto.ramal,
        'latitude': cto.latitude,
        'longitude': cto.longitude,
        'portas': cto.portas,
        'portas_base': cto.portas_base,
        'portas_uteis': cto.portas_uteis,
        'splitters_extras': cto.splitters_extras or [],
        'portas_inutilizadas': sorted(set(cto.portas_inutilizadas or [])),
        'splitter': cto.kmz_splitter,
    }


def _contagens_por_cto(inferencias, oper):
    """Conta papéis e ONTs offline por CTO a partir das linhas de inferência."""
    contagens = defaultdict(Counter)
    for inf in inferencias:
        if inf.cto_provavel_id:
            p = papel(inf, inf.cto_provavel_id)
            contagens[inf.cto_provavel_id][p] += 1
            if p != 'possivel':
                estado = oper.get((inf.olt_id, inf.pon, inf.position), (None, None))[0]
                if (estado or '').lower() != 'up':
                    contagens[inf.cto_provavel_id]['offline'] += 1
        if inf.status == 'divergente' and inf.cto_cadastro_id:
            contagens[inf.cto_cadastro_id]['suspeito'] += 1
    return contagens


def _ocupacao(c, portas):
    ocupadas = c['confirmado'] + c['provavel'] + c['veio_de_outra']
    return {
        'confirmados': c['confirmado'],
        'provaveis': c['provavel'],
        'vindos_de_outra': c['veio_de_outra'],
        'possiveis': c['possivel'],
        'suspeitos': c['suspeito'],
        'offline': c['offline'],
        'ocupadas': ocupadas,
        'livres': (portas - ocupadas) if portas else None,
        'situacao': situacao(portas, ocupadas),
    }


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def cto_list(request):
    """Todas as CTOs ativas (sem paginação: o mapa precisa de todas, ~1000).

    Filtros: olt (id), ramal, tipo (CA/CTO/CD), origem (ixc/kmz), situacao,
    com_coordenadas=true, search (nome).
    """
    ctos = Cto.objects.filter(is_active=True).select_related('olt')
    olt_id = request.GET.get('olt')
    inferencias = CtoInferencia.objects.all()
    if olt_id:
        inferencias = inferencias.filter(olt_id=olt_id)
        # CTOs da OLT pelo KMZ + as que a inferência associou à OLT (sem KMZ, ex.: Ouro Fino).
        ctos = ctos.filter(Q(olt_id=olt_id) | Q(inferencias__olt_id=olt_id)).distinct()
    for campo in ('ramal', 'tipo', 'origem'):
        if request.GET.get(campo):
            ctos = ctos.filter(**{campo: request.GET[campo]})
    if request.GET.get('com_coordenadas') == 'true':
        ctos = ctos.filter(latitude__isnull=False, longitude__isnull=False)
    if request.GET.get('search'):
        ctos = ctos.filter(descricao__icontains=request.GET['search'])

    inferencias = list(inferencias.only('olt_id', 'pon', 'position', 'status', 'cto_provavel_id', 'cto_cadastro_id'))
    oper = _oper_states([int(olt_id)] if olt_id else None)
    contagens = _contagens_por_cto(inferencias, oper)
    cadastro = Counter(ClienteFibraIxc.objects.filter(is_active=True).exclude(id_caixa_ftth__in=['', '0'])
                       .values_list('id_caixa_ftth', flat=True))

    situacao_filtro = request.GET.get('situacao')
    resultado = []
    for cto in ctos:
        item = _cto_basico(cto)
        item.update(_ocupacao(contagens[cto.id], cto.portas_uteis))
        item['cadastro_ixc'] = cadastro.get(cto.ixc_id, 0) if cto.ixc_id else 0
        if situacao_filtro and item['situacao'] != situacao_filtro:
            continue
        resultado.append(item)
    return Response(resultado)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def cto_detail(request, pk):
    """Uma CTO e os clientes ligados a ela pela inferência ou pelo cadastro."""
    cto = get_object_or_404(Cto.objects.select_related('olt'), pk=pk)
    linhas = list(CtoInferencia.objects.filter(Q(cto_provavel=cto) | Q(cto_cadastro=cto, status='divergente'))
                  .select_related('cto_cadastro', 'cto_provavel', 'cto_alternativa', 'olt'))
    oper = _oper_states({linha.olt_id for linha in linhas})

    clientes = []
    for inf in linhas:
        estado, rx = oper.get((inf.olt_id, inf.pon, inf.position), (None, None))
        clientes.append({
            'id': inf.id,
            'serial': inf.serial,
            'olt_nome': inf.olt.name,
            'pon': inf.pon,
            'position': inf.position,
            'cliente_nome': inf.cliente_nome,
            'distance_km': inf.distance_km,
            'oper_state': estado,
            'olt_rx_sig': rx,
            'status': inf.status,
            'papel': papel(inf, cto.id),
            'cto_cadastro': _ref(inf.cto_cadastro),
            'cto_provavel': _ref(inf.cto_provavel),
            'cto_alternativa': _ref(inf.cto_alternativa),
            'score': inf.score,
            'motivos': inf.motivos,
        })
    ordem = {'confirmado': 0, 'provavel': 1, 'veio_de_outra': 2, 'possivel': 3, 'suspeito': 4}
    clientes.sort(key=lambda c: (ordem.get(c['papel'], 9), c['pon'], c['position']))

    contagens = _contagens_por_cto(linhas, oper)
    dados = _cto_basico(cto)
    dados.update(_ocupacao(contagens[cto.id], cto.portas_uteis))
    dados['cadastro_ixc'] = (ClienteFibraIxc.objects.filter(is_active=True, id_caixa_ftth=cto.ixc_id).count()
                             if cto.ixc_id else 0)
    dados['pons'] = sorted({c['pon'] for c in clientes if c['papel'] != 'suspeito'})
    dados['clientes'] = clientes
    dados['calculado_em'] = max((linha.calculado_em for linha in linhas), default=None)
    return Response(dados)


class CtoInferenciaSerializer(serializers.ModelSerializer):
    olt_nome = serializers.CharField(source='olt.name', read_only=True)
    cto_cadastro = serializers.SerializerMethodField()
    cto_provavel = serializers.SerializerMethodField()
    cto_alternativa = serializers.SerializerMethodField()

    class Meta:
        model = CtoInferencia
        fields = ['id', 'olt', 'olt_nome', 'pon', 'position', 'serial', 'cliente_nome', 'distance_km',
                  'cto_cadastro', 'cto_provavel', 'cto_alternativa', 'score', 'score_alternativa',
                  'status', 'motivos', 'calculado_em']

    def get_cto_cadastro(self, obj):
        return _ref(obj.cto_cadastro)

    def get_cto_provavel(self, obj):
        return _ref(obj.cto_provavel)

    def get_cto_alternativa(self, obj):
        return _ref(obj.cto_alternativa)


class CtoInferenciaListAPIView(generics.ListAPIView):
    """Inferência por ONT. Filtros: olt, status, pon; busca por serial, cliente e CTO."""
    serializer_class = CtoInferenciaSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['serial', 'cliente_nome', 'cto_cadastro__descricao', 'cto_provavel__descricao']
    ordering_fields = ['pon', 'position', 'serial', 'cliente_nome', 'score', 'status', 'distance_km']

    def get_queryset(self):
        qs = CtoInferencia.objects.select_related('olt', 'cto_cadastro', 'cto_provavel', 'cto_alternativa') \
            .order_by('pon', 'position')
        for campo in ('olt', 'status', 'pon'):
            valor = self.request.GET.get(campo)
            if valor:
                qs = qs.filter(**{campo: valor})
        return qs


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def cto_inferencia_resumo(request):
    """Contagens para os cards da tela. Filtro opcional: olt."""
    qs = CtoInferencia.objects.all()
    if request.GET.get('olt'):
        qs = qs.filter(olt_id=request.GET['olt'])
    por_status = Counter(qs.values_list('status', flat=True))
    return Response({
        'onts': sum(por_status.values()),
        'ancoras': qs.filter(cto_cadastro__isnull=False).count(),
        'por_status': {s: por_status.get(s, 0) for s, _ in CtoInferencia.STATUS_CHOICES},
        'calculado_em': qs.aggregate(m=Max('calculado_em'))['m'],
    })


SPLITTERS_PERMITIDOS = (4, 8)


def _registrar_ajuste(cto, request):
    cto.ajustado_em = timezone.now()
    cto.ajustado_por = request.user.get_username()
    cto.save(update_fields=['splitters_extras', 'portas_inutilizadas', 'ajustado_em', 'ajustado_por'])


def _resposta_ajuste(cto):
    return Response(_cto_basico(cto))


@api_view(['POST', 'DELETE'])
@permission_classes([IsAuthenticated])
def cto_splitters(request, pk):
    """Ampliar a caixa = instalar um splitter inteiro (4 ou 8 portas)."""
    cto = get_object_or_404(Cto.objects.select_related('olt'), pk=pk)
    extras = list(cto.splitters_extras or [])
    if request.method == 'DELETE':
        if not extras:
            return Response({'error': 'Nenhum splitter adicionado para desfazer.'}, status=http_status.HTTP_400_BAD_REQUEST)
        extras.pop()
    else:
        try:
            portas = int(request.data.get('portas'))
        except (TypeError, ValueError):
            portas = None
        if portas not in SPLITTERS_PERMITIDOS:
            return Response({'error': 'Splitter deve ser de 4 ou 8 portas.'}, status=http_status.HTTP_400_BAD_REQUEST)
        extras.append(portas)
    cto.splitters_extras = extras
    # Portas inutilizadas além do novo total deixam de existir.
    if cto.portas is not None:
        cto.portas_inutilizadas = [p for p in (cto.portas_inutilizadas or []) if p <= cto.portas]
    _registrar_ajuste(cto, request)
    return _resposta_ajuste(cto)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def cto_porta_inutilizada(request, pk):
    """Marca/desmarca uma porta como inutilizada (não recebe cliente)."""
    cto = get_object_or_404(Cto.objects.select_related('olt'), pk=pk)
    try:
        porta = int(request.data.get('porta'))
    except (TypeError, ValueError):
        return Response({'error': 'porta inválida'}, status=http_status.HTTP_400_BAD_REQUEST)
    if porta < 1 or (cto.portas is not None and porta > cto.portas):
        return Response({'error': f'A caixa tem {cto.portas} portas.'}, status=http_status.HTTP_400_BAD_REQUEST)
    inutilizadas = set(cto.portas_inutilizadas or [])
    marcar = request.data.get('inutilizada')
    marcar = marcar if isinstance(marcar, bool) else str(marcar).lower() in ('1', 'true', 'sim')
    if marcar:
        inutilizadas.add(porta)
    else:
        inutilizadas.discard(porta)
    cto.portas_inutilizadas = sorted(inutilizadas)
    _registrar_ajuste(cto, request)
    return _resposta_ajuste(cto)
