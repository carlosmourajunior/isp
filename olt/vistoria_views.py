"""
Vistoria de CTO: o técnico na caixa e a bancada no sistema conferem porta a
porta quem está ligado, identificando por etiqueta ou por desconexão (o
alarme de "ONT inativa" chega pelo syslog em segundos).

Endpoints novos (não alteram nenhum existente):
    GET/POST /api/vistorias/                       listar (uma ficha por caixa) / iniciar ou retomar a
                                                   ficha da caixa (body: {cto, tecnico}) - olt/ficha_cto.py
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
    GET      /api/ixc/escrita/                     a escrita no IXC está ligada? este usuário pode?
"""
from collections import Counter, defaultdict
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
from .ficha_cto import abrir_ficha, consolidar, tirar_de_outras_caixas
from .ixc_escrita import alterar_caixa, escrita_permitida
from .verdade import caixa_no_ixc, correcao_pendente
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


def _chave_titular(cliente):
    """Mesmo titular = mesmo nome real do IXC. Sem contrato vinculado o "nome" é o
    próprio login, então não agrupa."""
    if cliente is None or not cliente.vinculado or not (cliente.nome or '').strip():
        return None
    return ' '.join(cliente.nome.upper().split())


def outros_logins_por_serial(clientes):
    """{serial: [{serial, login}, ...]} com os OUTROS logins/ONUs do mesmo titular.

    Um cliente com dois logins aparece duas vezes com o mesmo nome; na vistoria
    isso precisa ficar visível para a bancada não escolher o login errado.
    """
    chaves = {c.mac: _chave_titular(c) for c in clientes}
    nomes = {c.nome for c in clientes if chaves[c.mac]}
    grupos = defaultdict(list)
    for outro in ClienteFibraIxc.objects.filter(is_active=True, vinculado=True, nome__in=nomes):
        chave = _chave_titular(outro)
        if chave:
            grupos[chave].append({'serial': outro.mac, 'login': outro.login})
    return {serial: [o for o in grupos.get(chave, []) if o['serial'] != serial]
            for serial, chave in chaves.items() if chave}


def _cliente_info(serial, cliente, onu, inferencia=None, ultimo_up=None, agora=None, outros_logins=None):
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
        'login': (cliente.login or '') if cliente else '',
        'outros_logins': outros_logins or [],
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
        'cto': {
            'id': v.cto_id,
            'descricao': v.cto.descricao,
            'portas': v.cto.portas,
            'portas_base': v.cto.portas_base,
            'portas_manual': v.cto.portas_manual,
            'splitters_extras': v.cto.splitters_extras or [],
            'portas_inutilizadas': sorted(set(v.cto.portas_inutilizadas or [])),
            'ramal': v.cto.ramal,
        },
        'olt_id': v.olt_id,
        'olt_nome': v.olt.name if v.olt_id else None,
        'usuario': v.usuario,
        'tecnico': v.tecnico,
        'observacao': v.observacao,
        'iniciada_em': v.iniciada_em,
        'finalizada_em': v.finalizada_em,
        'sessao_iniciada_em': v.sessao_iniciada_em,
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
        'registrado_por': p.registrado_por,
    }


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def vistoria_list(request):
    if request.method == 'POST':
        # Uma ficha por caixa: se a caixa já foi vistoriada, retoma a mesma ficha.
        cto = get_object_or_404(Cto, pk=request.data.get('cto'))
        v, criada = abrir_ficha(cto, request.user.get_username(), tecnico=request.data.get('tecnico') or '')
        dados = _vistoria_basico(v)
        dados['continuacao'] = not criada
        dados['registros_anteriores'] = v.portas.count()
        return Response(dados, status=status.HTTP_201_CREATED if criada else status.HTTP_200_OK)

    qs = Vistoria.objects.select_related('cto', 'olt').prefetch_related('portas')
    for campo in ('cto', 'olt'):
        if request.GET.get(campo):
            qs = qs.filter(**{f'{campo}_id': request.GET[campo]})
    resultado, vistas = [], set()
    for v in qs[:400]:
        if v.cto_id in vistas:       # caixa ainda não consolidada: mostra só a ficha mais recente
            continue
        vistas.add(v.cto_id)
        item = _vistoria_basico(v)
        item['resumo'] = dict(Counter(p.resultado for p in v.portas.all()))
        resultado.append(item)
        if len(resultado) >= 200:
            break
    return Response(resultado)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def vistoria_detail(request, pk):
    v = get_object_or_404(Vistoria.objects.select_related('cto', 'olt'), pk=pk)
    principal = consolidar(v.cto)
    if principal and principal.id != v.id:
        # Esta era uma vistoria antiga da caixa: foi juntada na ficha.
        return Response({'redirecionar_para': principal.id}, status=status.HTTP_409_CONFLICT)
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
    outros = outros_logins_por_serial(list(clientes.values()))

    candidatos = []
    for serial in serials:
        inf = inferencias.get(serial)
        onu = onus.get(serial)
        item = _cliente_info(serial, clientes.get(serial), onu, inf, ultimo_up.get(serial), agora,
                             outros_logins=outros.get(serial))
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
        # O que o IXC dizia neste momento - se mudar depois, o IXC volta a valer.
        'caixa_ixc_no_registro': caixa_no_ixc(cliente) if serial else None,
        'registrado_por': request.user.get_username()[:150],
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
    if serial:
        tirar_de_outras_caixas(serial, v.cto)
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
    from .tasks import update_clientes_task

    v = get_object_or_404(Vistoria.objects.select_related('cto', 'olt'), pk=pk)
    v.finalizada_em = timezone.now()
    v.observacao = (request.data.get('observacao') or v.observacao)
    v.save(update_fields=['finalizada_em', 'observacao'])
    # Traz o IXC atualizado e, no fim, a sincronização recalcula a inferência - o
    # resultado de campo e o que mudou no IXC entram juntos, sem esperar o ciclo.
    job = update_clientes_task.delay(user=request.user.get_username(),
                                     menu_item=f"Sincronização com o IXC após vistoria de {v.cto.descricao}")
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

    outros = outros_logins_por_serial(list(clientes.values()))
    resultado = []
    for e in eventos:
        onu = onus.get((e.pon, e.position))
        serial = e.serial or (onu.serial if onu else '')
        item = _cliente_info(serial, clientes.get(serial), onu, inferencias.get(serial), agora=agora,
                             outros_logins=outros.get(serial))
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
    """Cliente que não está na lista de candidatos (nome da etiqueta, login ou serial)."""
    termo = (request.GET.get('q') or '').strip()
    if len(termo) < 3:
        return Response([])
    clientes = list(ClienteFibraIxc.objects.filter(is_active=True)
                    .filter(Q(nome__icontains=termo) | Q(mac__icontains=termo) | Q(login__icontains=termo))
                    .order_by('nome', 'login')[:20])
    serials = {c.mac for c in clientes}
    onus = _onu_por_serial(serials)
    inferencias = {i.serial: i for i in CtoInferencia.objects.filter(serial__in=serials).select_related('cto_provavel')}
    outros = outros_logins_por_serial(clientes)
    agora = timezone.now()
    return Response([_cliente_info(c.mac, c, onus.get(c.mac), inferencias.get(c.mac), agora=agora,
                                   outros_logins=outros.get(c.mac)) for c in clientes])


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
        id_cadastro = caixa_no_ixc(cliente)
        # Já está igual no IXC, ou o IXC mudou depois da vistoria (aí o IXC vale).
        if not correcao_pendente(vp, cliente):
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
        # O frontend mostra o botão sempre; desabilitado com o motivo quando não pode.
        'escrita_ixc_permitida': escrita_permitida(),
        'pode_corrigir': _estado_escrita(request.user)['pode_corrigir'],
        'motivo_sem_escrita': _estado_escrita(request.user)['motivo'],
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


def _estado_escrita(user):
    permitida = escrita_permitida()
    staff = bool(user.is_staff or user.is_superuser)
    if not permitida:
        motivo = 'Escrita no IXC desligada no servidor (IXC_PERMITIR_ESCRITA).'
    elif not staff:
        motivo = 'Só administradores podem alterar o IXC.'
    else:
        motivo = ''
    return {'permitida': permitida, 'pode_corrigir': permitida and staff, 'motivo': motivo}


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def ixc_escrita_estado(request):
    return Response(_estado_escrita(request.user))
