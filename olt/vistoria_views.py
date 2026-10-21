"""
Vistoria de CTO: o técnico na caixa e a bancada no sistema conferem porta a
porta quem está ligado, identificando por etiqueta ou por desconexão (o
alarme de "ONT inativa" chega pelo syslog em segundos).

Endpoints novos (não alteram nenhum existente):
    GET/POST /api/vistorias/                       listar / iniciar (body: {cto, tecnico})
    GET      /api/vistorias/<id>/                  vistoria + portas + candidatos da caixa
    POST     /api/vistorias/<id>/portas/           registrar (porta opcional; upsert por porta ou por serial)
    DELETE   /api/vistorias/<id>/portas/<porta>/   desfazer o registro de uma porta
    DELETE   /api/vistorias/<id>/registros/<rid>/  desfazer um registro (inclusive sem porta)
    POST     /api/vistorias/<id>/finalizar/        fecha e recalcula a inferência da OLT
    GET      /api/vistorias/<id>/eventos/?desde=   desconexões/reconexões ao vivo, com aviso de PON
    (listagens e correções aceitam ?olt=)
    GET      /api/vistorias/clientes/?q=           busca cliente fora da lista de candidatos
    GET      /api/vistorias/correcoes/             cadastro IXC x campo + portas fantasma
    POST     /api/vistorias/correcoes/aplicar/     corrige a CTO do cliente no próprio IXC (staff)
    GET      /api/vistorias/correcoes/historico/   correções já enviadas ao IXC
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
from .ixc_escrita import alterar_caixa, escrita_permitida
from .models import (ONU, ClienteFibraIxc, CorrecaoIxc, Cto, CtoInferencia, OntEvent, OntSnapshot, Vistoria,
                     VistoriaPorta)

FANTASMA_OFFLINE_DIAS = 7
# Quedas na mesma PON até esse intervalo são tratadas como simultâneas (rompimento, não o técnico).
JANELA_SIMULTANEA_S = 5


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
        'id': p.id,
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
    for campo in ('cto', 'olt'):
        if request.GET.get(campo):
            qs = qs.filter(**{f'{campo}_id': request.GET[campo]})
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
    portas_por_serial = {p.serial: p.porta for p in v.portas.all() if p.serial}  # porta pode ser None

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
        item['registrado'] = serial in portas_por_serial
        item['porta_registrada'] = portas_por_serial.get(serial)
        candidatos.append(item)

    ordem = {'confirmado': 0, 'provavel': 1, 'veio_de_outra': 2, 'possivel': 3, 'suspeito': 4, 'sem_ont': 5}
    candidatos.sort(key=lambda c: (c['registrado'], ordem.get(c['papel'], 9), c['cliente_nome']))

    dados = _vistoria_basico(v)
    dados['portas'] = [_porta_dict(p) for p in v.portas.all()]
    dados['candidatos'] = candidatos
    dados['pons'] = sorted({c['pon'] for c in candidatos if c['pon'] and c['papel'] not in ('suspeito', 'sem_ont')})
    return Response(dados)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def vistoria_porta_salvar(request, pk):
    """Registra uma porta ou um cliente da caixa.

    - com `porta`: upsert pelo número da porta;
    - sem `porta` e com cliente: upsert pelo serial (identificado por desconexão,
      porta desconhecida - se ele já tinha porta registrada, ela é mantida);
    - sem `porta` e sem cliente (ex.: drop sem ONT ativa): cria um registro novo.
    """
    v = get_object_or_404(Vistoria, pk=pk)
    bruto = request.data.get('porta')
    numero = None
    if bruto not in (None, '', 'null'):
        try:
            numero = int(bruto)
        except (TypeError, ValueError):
            return Response({'error': 'porta inválida'}, status=status.HTTP_400_BAD_REQUEST)
        if not 1 <= numero <= 64:
            return Response({'error': 'porta inválida'}, status=status.HTTP_400_BAD_REQUEST)
    resultado = request.data.get('resultado')
    if resultado not in dict(VistoriaPorta.RESULTADO_CHOICES):
        return Response({'error': 'resultado inválido'}, status=status.HTTP_400_BAD_REQUEST)

    serial = (request.data.get('serial') or '').strip()
    if resultado == VistoriaPorta.RESULTADO_CLIENTE and not serial:
        return Response({'error': 'informe o serial do cliente'}, status=status.HTTP_400_BAD_REQUEST)
    if resultado != VistoriaPorta.RESULTADO_CLIENTE:
        serial = ''

    onu = ONU.objects.filter(serial=serial).first() if serial else None
    cliente = ClienteFibraIxc.objects.filter(mac=serial).first() if serial else None
    metodo = request.data.get('metodo') or 'manual'
    dados = {
        'resultado': resultado,
        'metodo': metodo if metodo in dict(VistoriaPorta.METODO_CHOICES) else 'manual',
        'serial': serial,
        'pon': onu.pon if onu else '',
        'position': onu.position if onu else None,
        'cliente_nome': (cliente.nome if cliente else '')[:255],
        'reconexao_confirmada': bool(request.data.get('reconexao_confirmada')),
        'observacao': (request.data.get('observacao') or '')[:255],
    }

    if numero is not None:
        if serial:
            # O mesmo cliente não fica em dois registros da mesma vistoria.
            v.portas.filter(serial=serial).exclude(porta=numero).delete()
        registro, _ = VistoriaPorta.objects.update_or_create(vistoria=v, porta=numero, defaults=dados)
    elif serial:
        registro = v.portas.filter(serial=serial).first()
        if registro is None:
            registro = VistoriaPorta.objects.create(vistoria=v, porta=None, **dados)
        else:
            for campo, valor in dados.items():
                setattr(registro, campo, valor)
            registro.save()
    else:
        registro = VistoriaPorta.objects.create(vistoria=v, porta=None, **dados)
    return Response(_porta_dict(registro))


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def vistoria_porta_remover(request, pk, porta):
    v = get_object_or_404(Vistoria, pk=pk)
    v.portas.filter(porta=porta).delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def vistoria_registro_remover(request, pk, registro_id):
    v = get_object_or_404(Vistoria, pk=pk)
    v.portas.filter(id=registro_id).delete()
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

    Para separar a desconexão do técnico de quedas em outro ponto da rede, cada
    evento diz se é na PON da caixa e quantas ONTs da mesma PON caíram junto.
    """
    v = get_object_or_404(Vistoria.objects.select_related('cto'), pk=pk)
    agora = timezone.now()
    desde = parse_datetime(request.GET.get('desde') or '')
    # PONs da caixa: onde estão os clientes que a rede ou a vistoria colocam nela.
    pons_da_caixa = sorted(
        set(CtoInferencia.objects.filter(cto_provavel=v.cto).exclude(pon='').values_list('pon', flat=True))
        | set(v.portas.exclude(pon='').values_list('pon', flat=True))
    )
    if desde is None or v.olt_id is None:
        return Response({'agora': agora, 'pons_da_caixa': pons_da_caixa, 'eventos': []})

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

    # Quantas ONTs diferentes da mesma PON caíram até JANELA_SIMULTANEA_S antes/depois de cada queda.
    quedas = [e for e in eventos if not e.is_clear]

    def caiu_junto(evento):
        return len({(q.pon, q.position) for q in quedas
                    if q.pon == evento.pon
                    and abs((q.occurred_at - evento.occurred_at).total_seconds()) <= JANELA_SIMULTANEA_S})

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
            'mesma_pon_da_caixa': e.pon in pons_da_caixa,
            'caiu_junto': caiu_junto(e) if not e.is_clear else 1,
        })
        resultado.append(item)
    return Response({'agora': agora, 'pons_da_caixa': pons_da_caixa, 'eventos': resultado})


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
    olt_id = request.GET.get('olt')
    portas_qs = VistoriaPorta.objects.all()
    if olt_id:
        portas_qs = portas_qs.filter(vistoria__olt_id=olt_id)

    ultimos = {}
    for vp in (portas_qs.filter(resultado=VistoriaPorta.RESULTADO_CLIENTE).exclude(serial='')
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
    for vp in (portas_qs.filter(resultado=VistoriaPorta.RESULTADO_SEM_ONT_ATIVA)
               .select_related('vistoria__cto').order_by('vistoria__iniciada_em')):
        # Sem porta: cada registro é um drop diferente (chave pelo id).
        fantasmas[(vp.vistoria.cto_id, vp.porta or f'id{vp.id}')] = vp
    # Se uma vistoria mais nova registrou outra coisa na mesma porta, ela deixa de ser fantasma.
    mais_recente = {}
    for vp in portas_qs.select_related('vistoria').order_by('vistoria__iniciada_em', 'registrado_em'):
        mais_recente[(vp.vistoria.cto_id, vp.porta or f'id{vp.id}')] = vp.id
    portas_fantasma = [{
        'cto': {'id': vp.vistoria.cto_id, 'descricao': vp.vistoria.cto.descricao},
        'porta': vp.porta,
        'observacao': vp.observacao,
        'vistoria_id': vp.vistoria_id,
        'vistoriado_em': vp.registrado_em,
    } for chave, vp in fantasmas.items() if mais_recente.get(chave) == vp.id]

    divergentes.sort(key=lambda d: d['vistoriado_em'], reverse=True)
    portas_fantasma.sort(key=lambda d: d['vistoriado_em'], reverse=True)
    return Response({
        'clientes': divergentes,
        'portas_fantasma': portas_fantasma,
        # O frontend só mostra o botão de corrigir no IXC quando faz sentido.
        'escrita_ixc_permitida': escrita_permitida(),
        'pode_corrigir': escrita_permitida() and (request.user.is_staff or request.user.is_superuser),
    })


def _correcao_dict(c):
    return {
        'id': c.id,
        'serial': c.serial,
        'cliente_nome': c.cliente_nome,
        'caixa_antes': c.caixa_antes,
        'cto': {'id': c.cto_id, 'descricao': c.cto.descricao} if c.cto_id else None,
        'usuario': c.usuario,
        'status': c.status,
        'mensagem': c.mensagem,
        'outros_campos_alterados': c.outros_campos_alterados,
        'criado_em': c.criado_em,
    }


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def vistoria_aplicar_correcao(request):
    """Corrige a CTO do cliente no IXC. Body: {serial, cto}. Só staff, só com IXC_PERMITIR_ESCRITA."""
    if not (request.user.is_staff or request.user.is_superuser):
        return Response({'error': 'Só administradores podem alterar o IXC.'}, status=status.HTTP_403_FORBIDDEN)
    if not escrita_permitida():
        return Response({'error': 'Escrita no IXC desligada (IXC_PERMITIR_ESCRITA no .env do servidor).'},
                        status=status.HTTP_403_FORBIDDEN)
    serial = (request.data.get('serial') or '').strip()
    cto = get_object_or_404(Cto, pk=request.data.get('cto'))
    if not serial:
        return Response({'error': 'informe o serial'}, status=status.HTTP_400_BAD_REQUEST)
    porta = (VistoriaPorta.objects.filter(serial=serial, vistoria__cto=cto)
             .order_by('-vistoria__iniciada_em').first())
    correcao = alterar_caixa(serial, cto, request.user.get_username(), vistoria_porta=porta)
    codigo = status.HTTP_200_OK if correcao.status != 'erro' else status.HTTP_502_BAD_GATEWAY
    return Response(_correcao_dict(correcao), status=codigo)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def vistoria_historico_correcoes(request):
    qs = CorrecaoIxc.objects.select_related('cto')
    if request.GET.get('olt'):
        olt_id = request.GET['olt']
        qs = qs.filter(Q(vistoria_porta__vistoria__olt_id=olt_id) | Q(cto__olt_id=olt_id))
    return Response([_correcao_dict(c) for c in qs[:200]])
