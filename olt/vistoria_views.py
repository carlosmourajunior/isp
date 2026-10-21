"""
Vistoria de CTO: o técnico na caixa e a bancada no sistema conferem porta a
porta quem está ligado, identificando por etiqueta ou por desconexão (o
alarme de "ONT inativa" chega pelo syslog em segundos).

Endpoints novos (não alteram nenhum existente):
    GET/POST /api/vistorias/                       listar / iniciar (body: {cto, tecnico})
    GET      /api/vistorias/<id>/                  vistoria + portas + candidatos da caixa
    POST     /api/vistorias/<id>/portas/           registrar uma porta (upsert por número)
    DELETE   /api/vistorias/<id>/portas/<porta>/   desfazer o registro de uma porta
    POST     /api/vistorias/<id>/finalizar/        fecha e recalcula a inferência da OLT
    GET      /api/vistorias/<id>/eventos/?desde=   desconexões/reconexões ao vivo
    GET      /api/vistorias/clientes/?q=           busca cliente fora da lista de candidatos
    GET      /api/vistorias/correcoes/             cadastro IXC x campo + portas fantasma
"""
from collections import Counter
from datetime import timedelta

from django.db.models import Max, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .contrato import situacao_contrato
from .cto_views import papel
from .models import ONU, ClienteFibraIxc, Cto, CtoInferencia, OntEvent, OntSnapshot, Vistoria, VistoriaPorta

FANTASMA_OFFLINE_DIAS = 7


def _onu_por_serial(serials, olt_id=None):
    qs = ONU.objects.filter(serial__in=serials)
    if olt_id:
        qs = qs.filter(olt_id=olt_id)
    return {o.serial: o for o in qs}


def _ultima_vez_online(serials):
    return dict(OntSnapshot.objects.filter(serial__in=serials, oper_state='up')
                .values('serial').annotate(m=Max('taken_at')).values_list('serial', 'm'))


def _cliente_info(serial, cliente, onu, inferencia=None, ultimo_up=None, agora=None):
    """Dados de um cliente/ONT como a bancada precisa ver."""
    agora = agora or timezone.now()
    codigo, rotulo = situacao_contrato(cliente)
    online = bool(onu and (onu.oper_state or '').lower() == 'up')
    offline_ha_dias = None
    if onu and not online and ultimo_up:
        offline_ha_dias = (agora - ultimo_up).days
    fantasma = bool(onu) and not online and (
        codigo in ('inativo', 'sem_contrato')
        or (offline_ha_dias is not None and offline_ha_dias >= FANTASMA_OFFLINE_DIAS)
    )
    return {
        'serial': serial,
        'cliente_nome': cliente.nome if cliente else '',
        'endereco': (cliente.endereco or '') if cliente else '',
        'pon': onu.pon if onu else (inferencia.pon if inferencia else ''),
        'position': onu.position if onu else (inferencia.position if inferencia else None),
        'oper_state': onu.oper_state if onu else None,
        'online': online,
        'olt_rx_sig': onu.olt_rx_sig if onu else None,
        'ultimo_online': ultimo_up,
        'offline_ha_dias': offline_ha_dias,
        'contrato': codigo,
        'contrato_rotulo': rotulo,
        'fantasma_provavel': fantasma,
        'cto_provavel': ({'id': inferencia.cto_provavel_id, 'descricao': inferencia.cto_provavel.descricao}
                         if inferencia and inferencia.cto_provavel_id else None),
        'inferencia_status': inferencia.status if inferencia else None,
    }


def _vistoria_basico(v):
    return {
        'id': v.id,
        'cto': {'id': v.cto_id, 'descricao': v.cto.descricao, 'portas': v.cto.portas, 'ramal': v.cto.ramal},
        'olt_id': v.olt_id,
        'olt_nome': v.olt.name if v.olt_id else None,
        'usuario': v.usuario,
        'tecnico': v.tecnico,
        'observacao': v.observacao,
        'iniciada_em': v.iniciada_em,
        'finalizada_em': v.finalizada_em,
    }


def _porta_dict(p):
    return {
        'porta': p.porta,
        'resultado': p.resultado,
        'metodo': p.metodo,
        'serial': p.serial,
        'pon': p.pon,
        'position': p.position,
        'cliente_nome': p.cliente_nome,
        'reconexao_confirmada': p.reconexao_confirmada,
        'observacao': p.observacao,
        'registrado_em': p.registrado_em,
    }


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def vistoria_list(request):
    if request.method == 'POST':
        cto = get_object_or_404(Cto, pk=request.data.get('cto'))
        olt_id = cto.olt_id
        if olt_id is None:
            # CTO sem OLT pelo KMZ (ex.: Ouro Fino): a OLT onde a inferência mais a encontrou.
            mais_comum = Counter(CtoInferencia.objects.filter(Q(cto_provavel=cto) | Q(cto_cadastro=cto))
                                 .values_list('olt_id', flat=True)).most_common(1)
            olt_id = mais_comum[0][0] if mais_comum else None
        v = Vistoria.objects.create(cto=cto, olt_id=olt_id, usuario=request.user.get_username(),
                                    tecnico=(request.data.get('tecnico') or '')[:150])
        return Response(_vistoria_basico(v), status=status.HTTP_201_CREATED)

    qs = Vistoria.objects.select_related('cto', 'olt').prefetch_related('portas')
    if request.GET.get('cto'):
        qs = qs.filter(cto_id=request.GET['cto'])
    resultado = []
    for v in qs[:200]:
        item = _vistoria_basico(v)
        item['resumo'] = dict(Counter(p.resultado for p in v.portas.all()))
        resultado.append(item)
    return Response(resultado)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def vistoria_detail(request, pk):
    v = get_object_or_404(Vistoria.objects.select_related('cto', 'olt'), pk=pk)
    cto = v.cto
    agora = timezone.now()

    inferencias = {i.serial: i for i in CtoInferencia.objects.filter(Q(cto_provavel=cto) | Q(cto_cadastro=cto))
                   .select_related('cto_provavel')}
    cadastrados = {c.mac: c for c in ClienteFibraIxc.objects.filter(is_active=True, id_caixa_ftth=cto.ixc_id)} \
        if cto.ixc_id else {}
    serials = set(inferencias) | set(cadastrados)
    clientes = {c.mac: c for c in ClienteFibraIxc.objects.filter(is_active=True, mac__in=serials)}
    onus = _onu_por_serial(serials)
    ultimo_up = _ultima_vez_online(serials)
    portas_por_serial = {p.serial: p.porta for p in v.portas.all() if p.serial}

    candidatos = []
    for serial in serials:
        inf = inferencias.get(serial)
        onu = onus.get(serial)
        item = _cliente_info(serial, clientes.get(serial), onu, inf, ultimo_up.get(serial), agora)
        if inf is None:
            # Cadastrado aqui no IXC, mas a ONT nem aparece na OLT: provável contrato antigo.
            item['papel'] = 'sem_ont'
        else:
            item['papel'] = papel(inf, cto.id)
        item['cadastrado_aqui'] = serial in cadastrados
        item['porta_registrada'] = portas_por_serial.get(serial)
        candidatos.append(item)

    ordem = {'confirmado': 0, 'provavel': 1, 'veio_de_outra': 2, 'possivel': 3, 'suspeito': 4, 'sem_ont': 5}
    candidatos.sort(key=lambda c: (c['porta_registrada'] is not None, ordem.get(c['papel'], 9), c['cliente_nome']))

    dados = _vistoria_basico(v)
    dados['portas'] = [_porta_dict(p) for p in v.portas.all()]
    dados['candidatos'] = candidatos
    dados['pons'] = sorted({c['pon'] for c in candidatos if c['pon'] and c['papel'] not in ('suspeito', 'sem_ont')})
    return Response(dados)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def vistoria_porta_salvar(request, pk):
    v = get_object_or_404(Vistoria, pk=pk)
    try:
        numero = int(request.data.get('porta'))
    except (TypeError, ValueError):
        return Response({'error': 'porta inválida'}, status=status.HTTP_400_BAD_REQUEST)
    resultado = request.data.get('resultado')
    if not 1 <= numero <= 64 or resultado not in dict(VistoriaPorta.RESULTADO_CHOICES):
        return Response({'error': 'porta ou resultado inválido'}, status=status.HTTP_400_BAD_REQUEST)

    serial = (request.data.get('serial') or '').strip()
    if resultado == VistoriaPorta.RESULTADO_CLIENTE and not serial:
        return Response({'error': 'informe o serial do cliente'}, status=status.HTTP_400_BAD_REQUEST)
    if resultado != VistoriaPorta.RESULTADO_CLIENTE:
        serial = ''

    onu = ONU.objects.filter(serial=serial).first() if serial else None
    cliente = ClienteFibraIxc.objects.filter(mac=serial).first() if serial else None
    if serial:
        # O mesmo cliente não fica em duas portas da mesma vistoria.
        v.portas.filter(serial=serial).exclude(porta=numero).delete()

    metodo = request.data.get('metodo') or 'manual'
    porta, _ = VistoriaPorta.objects.update_or_create(vistoria=v, porta=numero, defaults={
        'resultado': resultado,
        'metodo': metodo if metodo in dict(VistoriaPorta.METODO_CHOICES) else 'manual',
        'serial': serial,
        'pon': onu.pon if onu else '',
        'position': onu.position if onu else None,
        'cliente_nome': (cliente.nome if cliente else '')[:255],
        'reconexao_confirmada': bool(request.data.get('reconexao_confirmada')),
        'observacao': (request.data.get('observacao') or '')[:255],
    })
    return Response(_porta_dict(porta))


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def vistoria_porta_remover(request, pk, porta):
    v = get_object_or_404(Vistoria, pk=pk)
    v.portas.filter(porta=porta).delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def vistoria_finalizar(request, pk):
    from .tasks import infer_ctos_task

    v = get_object_or_404(Vistoria.objects.select_related('cto', 'olt'), pk=pk)
    v.finalizada_em = timezone.now()
    v.observacao = (request.data.get('observacao') or v.observacao)
    v.save(update_fields=['finalizada_em', 'observacao'])
    job_id = None
    if v.olt_id:
        # O resultado de campo entra na inferência na hora, sem esperar o próximo ciclo.
        job = infer_ctos_task.delay(olt_id=v.olt_id, user=request.user.get_username(),
                                    menu_item=f"Inferência de CTOs após vistoria de {v.cto.descricao}")
        job_id = job.id
    dados = _vistoria_basico(v)
    dados['job_id'] = job_id
    return Response(dados)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def vistoria_eventos(request, pk):
    """Desconexões e reconexões desde `desde` (ISO, devolvido em `agora` na chamada anterior).

    A bancada chama sem `desde` para pegar o relógio do servidor, pede ao técnico
    para desconectar e consulta a cada ~2 s.
    """
    v = get_object_or_404(Vistoria.objects.select_related('cto'), pk=pk)
    agora = timezone.now()
    desde = parse_datetime(request.GET.get('desde') or '')
    if desde is None or v.olt_id is None:
        return Response({'agora': agora, 'eventos': []})

    eventos = list(OntEvent.objects.filter(olt_id=v.olt_id, occurred_at__gt=desde,
                                           event_type__in=OntEvent.TYPES_QUEDA).order_by('occurred_at')[:200])
    chaves = {(e.pon, e.position) for e in eventos}
    onus = {(o.pon, o.position): o for o in ONU.objects.filter(olt_id=v.olt_id, pon__in={p for p, _ in chaves})}
    serials = {e.serial or (onus.get((e.pon, e.position)).serial if onus.get((e.pon, e.position)) else '')
               for e in eventos} - {''}
    clientes = {c.mac: c for c in ClienteFibraIxc.objects.filter(mac__in=serials)}
    inferencias = {i.serial: i for i in CtoInferencia.objects.filter(olt_id=v.olt_id, serial__in=serials)
                   .select_related('cto_provavel')}
    candidatos = set(CtoInferencia.objects.filter(Q(cto_provavel=v.cto) | Q(cto_cadastro=v.cto))
                     .values_list('serial', flat=True))

    resultado = []
    for e in eventos:
        onu = onus.get((e.pon, e.position))
        serial = e.serial or (onu.serial if onu else '')
        item = _cliente_info(serial, clientes.get(serial), onu, inferencias.get(serial), agora=agora)
        item.update({
            'id': e.id,
            'ocorrido_em': e.occurred_at,
            'pon': e.pon,
            'position': e.position,
            'tipo': e.event_type,
            'alarme': e.alarm_type,
            'voltou': e.is_clear,
            'candidato_desta_cto': serial in candidatos,
        })
        resultado.append(item)
    return Response({'agora': agora, 'eventos': resultado})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def vistoria_buscar_cliente(request):
    """Cliente que não está na lista de candidatos (nome da etiqueta ou serial)."""
    termo = (request.GET.get('q') or '').strip()
    if len(termo) < 3:
        return Response([])
    clientes = list(ClienteFibraIxc.objects.filter(is_active=True)
                    .filter(Q(nome__icontains=termo) | Q(mac__icontains=termo)).order_by('nome')[:20])
    serials = {c.mac for c in clientes}
    onus = _onu_por_serial(serials)
    inferencias = {i.serial: i for i in CtoInferencia.objects.filter(serial__in=serials).select_related('cto_provavel')}
    agora = timezone.now()
    return Response([_cliente_info(c.mac, c, onus.get(c.mac), inferencias.get(c.mac), agora=agora) for c in clientes])


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def vistoria_correcoes(request):
    """O que a vistoria mostrou e o IXC precisa refletir.

    - clientes: identificados em campo numa CTO diferente da do cadastro;
    - portas_fantasma: portas com drop mas sem ONT ativa (a liberar).
    Vale sempre o registro mais recente de cada serial / porta.
    """
    ultimos = {}
    for vp in (VistoriaPorta.objects.filter(resultado=VistoriaPorta.RESULTADO_CLIENTE).exclude(serial='')
               .select_related('vistoria__cto').order_by('vistoria__iniciada_em', 'registrado_em')):
        ultimos[vp.serial] = vp
    clientes = {c.mac: c for c in ClienteFibraIxc.objects.filter(mac__in=ultimos)}
    ctos_ixc = {c.ixc_id: c for c in Cto.objects.exclude(ixc_id=None)}

    divergentes = []
    for serial, vp in ultimos.items():
        cto_campo = vp.vistoria.cto
        cliente = clientes.get(serial)
        id_cadastro = (cliente.id_caixa_ftth or '') if cliente else ''
        if id_cadastro and id_cadastro == cto_campo.ixc_id:
            continue
        cto_cad = ctos_ixc.get(id_cadastro)
        divergentes.append({
            'serial': serial,
            'cliente_nome': vp.cliente_nome or (cliente.nome if cliente else ''),
            'cto_cadastro': cto_cad.descricao if cto_cad else (id_cadastro if id_cadastro not in ('', '0') else None),
            'cto_campo': {'id': cto_campo.id, 'descricao': cto_campo.descricao, 'ixc_id': cto_campo.ixc_id},
            'porta': vp.porta,
            'vistoria_id': vp.vistoria_id,
            'vistoriado_em': vp.registrado_em,
        })

    fantasmas = {}
    for vp in (VistoriaPorta.objects.filter(resultado=VistoriaPorta.RESULTADO_SEM_ONT_ATIVA)
               .select_related('vistoria__cto').order_by('vistoria__iniciada_em')):
        fantasmas[(vp.vistoria.cto_id, vp.porta)] = vp
    # Se uma vistoria mais nova registrou outra coisa na mesma porta, ela deixa de ser fantasma.
    mais_recente = {}
    for vp in VistoriaPorta.objects.select_related('vistoria').order_by('vistoria__iniciada_em', 'registrado_em'):
        mais_recente[(vp.vistoria.cto_id, vp.porta)] = vp.id
    portas_fantasma = [{
        'cto': {'id': vp.vistoria.cto_id, 'descricao': vp.vistoria.cto.descricao},
        'porta': vp.porta,
        'observacao': vp.observacao,
        'vistoria_id': vp.vistoria_id,
        'vistoriado_em': vp.registrado_em,
    } for chave, vp in fantasmas.items() if mais_recente.get(chave) == vp.id]

    divergentes.sort(key=lambda d: d['vistoriado_em'], reverse=True)
    portas_fantasma.sort(key=lambda d: d['vistoriado_em'], reverse=True)
    return Response({'clientes': divergentes, 'portas_fantasma': portas_fantasma})
