import base64
import json
from django.http import HttpResponse
from django.template import loader
from olt.utils import connect_to_mikrotik, get_nat_rules, olt_connector
from django.shortcuts import render, redirect
from olt.models import ONU, ClienteFibraIxc, OltUsers
import requests
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.decorators import login_required
from librouteros import connect
from librouteros.query import Key
from dotenv import load_dotenv
import os
import subprocess
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from routeros_api import RouterOsApiPool
import django_rq
from django_rq import get_queue
from .tasks import update_all_onus, update_port_onus, update_users_task, update_mac_values_task


# Carregar variáveis de ambiente do arquivo .env
load_dotenv()

@login_required
def home(request):
    olt_users_list = OltUsers.objects.order_by('-users_connected')
    template = loader.get_template('olt/home.html')
    context = {
        'olt_users_list': olt_users_list,
    }
    return HttpResponse(template.render(context, request))


def critical_users_list(request):
    olt_users_list = OltUsers.objects.filter(users_connected__gte=120).order_by('-users_connected')
    template = loader.get_template('olt/home.html')
    context = {
        'olt_users_list': olt_users_list,
    }
    return HttpResponse(template.render(context, request))


def update_users(request):
    # Queue the task with metadata
    job = update_users_task.delay(
        user=request.user.username,
        menu_item='Atualizar Ocupação'
    )
    request.session['task_message'] = 'Atualização de usuários iniciada. Acompanhe o progresso na lista de tarefas.'
    request.session['job_id'] = job.id
    return redirect('olt:view_tasks')

def update_mac_values(request):
    # Queue the task with metadata
    job = update_mac_values_task.delay(
        user=request.user.username,
        menu_item='Atualizar MAC Address'
    )
    request.session['task_message'] = 'Atualização de MAC Address iniciada. Acompanhe o progresso na lista de tarefas.'
    request.session['job_id'] = job.id
    return redirect('olt:view_tasks')


def remove_onu(request):
    print(f'{request}')

def update_onus(request, slot, port):
    connector = olt_connector()
    olt_users_list = connector.get_itens_to_port(slot, port)
    template = loader.get_template('olt/home.html')
    context = {
        'olt_users_list': olt_users_list,
    }
    return HttpResponse(template.render(context, request))

def removable_users_list(request, slot, port):
    update_onus(request, slot, port)
    pon = f"1/1/{slot}/{port}"
    removable_list = ONU.objects.filter(pon=pon)
    template = loader.get_template('olt/removable_list.html')
    context = {
        'removable_list': removable_list,
    }
    return HttpResponse(template.render(context, request))

def delete(request, slot, port, position):
    pon = f"1/1/{slot}/{port}/{position}"
    # ONU.objects.filter(pon=pon, onu=onu).delete()
    # removable_list = ONU.objects.filter(pon=pon)
    # template = loader.get_template('olt/removable_list.html')
    # context = {
    #     'removable_list': removable_list,
    # }
    conector = olt_connector()
    conector.remove_onu(pon)
    print(f"configure equipment ont interface 1/1/{slot}/{port}/{position} admin-state down")
    print(f"configure equipment no interface 1/1/{slot}/{port}/{position}")

    response = update_values(request, port, slot)

    return response
    

def remover_ont(request, porta):
    connector = olt_connector()
    connector.remove_onu(porta)
    porta = porta.split("/")
    removable_list = connector.get_itens_to_port(1, 16)
    template = loader.get_template('olt/removable_list.html')
    context = {
        'removable_list': removable_list,
    }
    return HttpResponse(template.render(context, request))


def get_itens_to_port(request, slot, port):
    connector = olt_connector()
    old_values = connector.get_itens_to_port(slot, port)
    template = loader.get_template('olt/duplicates.html')
    context = {
        'duplicates': old_values,
        'slot': slot,
        'port': port,
    }
    return HttpResponse(template.render(context, request))

def update_values(request, port, slot):
    order_by = request.GET.get('sort', 'position')
    # Queue the task with metadata
    job = update_port_onus.delay(
        slot, port,
        user=request.user.username,
        menu_item=f'Atualizar ONUs da Porta {slot}/{port}'
    )
    request.session['task_message'] = f'Atualização de ONUs para porta {slot}/{port} iniciada.'
    request.session['job_id'] = job.id
    return redirect('olt:view_tasks')


def update_onus_all(request):
    # Queue the task with metadata
    job = update_all_onus.delay(
        user=request.user.username,
        menu_item='ONU Atualizar Todas'
    )
    request.session['task_message'] = 'Atualização de ONUs iniciada. Acompanhe o progresso na lista de tarefas.'
    request.session['job_id'] = job.id
    return redirect('olt:view_tasks')


def get_duplicated(request):
    onus = ONU.objects.all().order_by('serial')
    duplicates = []
    for onu in onus:
        serial_count = ONU.objects.filter(serial=onu.serial).count()
        if serial_count > 1:
            duplicates.append(onu)
    template = loader.get_template('olt/duplicates.html')
    context = {
        'duplicates': duplicates,
    }
    return HttpResponse(template.render(context, request))


def search_view(request):

    removable_list = []
    query = request.GET.get('q', '')
    print("Search query: " + query)

    if query:
        serial = ONU.objects.filter(serial__icontains=query)
        print(serial)
        mac = ONU.objects.filter(mac__icontains=query)
        print(mac)
        desc1 = ONU.objects.filter(desc1__icontains=query)
        print(desc1)
        desc2 = ONU.objects.filter(desc2__icontains=query)
        print(desc1)
        mac = ONU.objects.filter(mac__icontains=query)
        print(desc1)
    
        removable_list = serial.union(mac).union(desc1).union(desc2).union(mac)

    return render(request, 'olt/duplicates.html', {'query': query , 'duplicates': removable_list})

def listar_clientes(request):

    clientes = ClienteFibraIxc.objects.all()
    template = loader.get_template('olt/clientes_fibra.html')
    context = {
        'clientes': clientes,
    }
    return HttpResponse(template.render(context, request))

def update_clientes():
    clientes = ClienteFibraIxc.objects.all()
    for client in clientes:
        onu = ONU.objects.filter(serial__icontains=client.mac, desc1__icontains=client.nome)
        if onu.exists():
            onu = onu.first()
            onu.cliente_fibra = True
            onu.save()
            print(f'Cliente {client.nome} marcado como cliente de fibra.')

def search_ixc(request):

    response = search_ixc_page(request, 1)
    data = response.json()

    num_records = len(data['registros'])
    print(f'There are {num_records} records in this JSON file.')    
    total_de_paginas = int(data['total'])/100
    print(f'Total de páginas: {total_de_paginas}')

    # print(response.json())
    ClienteFibraIxc.objects.all().delete()
    for page in range(1, int(total_de_paginas+1)):
        response = search_ixc_page(request, page)
        data = response.json()
        print(f'Página {page} de {total_de_paginas}')
        
        for registro in data['registros']:
            ClienteFibraIxc.objects.create(
                mac=registro['mac'], 
                nome=registro['nome'],
            )

    update_clientes()

    clientes = ClienteFibraIxc.objects.all()

    template = loader.get_template('olt/clientes_fibra.html')
    context = {
        'clientes': clientes,
    }
    return HttpResponse(template.render(context, request))



def search_ixc_page(request, page):

    host = os.getenv('IXC_HOST')
    url = f"https://{host}/webservice/v1/radpop_radio_cliente_fibra"
    token = os.getenv('IXC_TOKEN').encode('utf-8')

    payload = {
        'qtype': 'radpop_radio_cliente_fibra.id',
        'query': '',
        'oper': '>',
        'page': page,
        'rp': '100',
        'sortname': 'radpop_radio_cliente_fibra.id',
        'sortorder': 'asc'
    }

    headers = {
        'ixcsoft': 'listar',
        'Authorization': 'Basic {}'.
        format(base64.b64encode(token).decode('utf-8')),
        'Content-Type': 'application/json'
    }

    response = requests.post(url, data=json.dumps(payload), headers=headers)

    return response


def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('login')
    else:
        form = UserCreationForm()
    return render(request, 'register.html', {'form': form})


def decode_value(value):
    if isinstance(value, bytes):
        encodings = ['utf-8', 'latin-1', 'iso-8859-1', 'cp1252']
        for encoding in encodings:
            try:
                return value.decode(encoding)
            except UnicodeDecodeError:
                continue
        return value.decode('utf-8', errors='replace')
    return value


def test_ping(api, address, count=15, src_address=None):
    try:
        print(f"Testando ping de {src_address} para {address}...")
        
        # Executando o comando ping com parâmetros convertidos para bytes
        ping_params = {
            'address': '8.8.8.8'.encode('utf-8'),
            'src-address': src_address.encode('utf-8'),
            'count': '10'.encode('utf-8')
        }

        ping_results = api.get_binary_resource('/').call('ping', ping_params)
        # print(f"Resultado do ping: {ping_results}")
        # Get last result for final statistics
        if ping_results:
            final_result = ping_results[-1]  # Get last ping response
            print(f"Resultado final do ping: {final_result}")
            # Extract and decode values
            packets_sent = int(decode_value(final_result.get('sent', '0')))
            packets_received = int(decode_value(final_result.get('received', '0')))
            packets_lost = int(decode_value(final_result.get('packet-loss', '0')))
            avg_rtt = decode_value(final_result.get('avg-rtt', '0ms')).replace('ms','')
            
            result_str = f"\nEstatísticas do Ping:\n"
            result_str += f"Pacotes: Enviados = {packets_sent}, "
            result_str += f"Recebidos = {packets_received}, "
            result_str += f"Perdidos = {packets_lost}\n"
            result_str += f"Tempo médio de ida e volta = {avg_rtt}ms\n"
            
            return result_str
        
    except Exception as e:
        return f"Erro no ping: {str(e)}"


@login_required
def mikrotik_info(request):
    # Buscar valores do .env
    hostname = os.getenv('MIKROTIK_HOST')
    username = os.getenv('MIKROTIK_USERNAME')
    password = os.getenv('MIKROTIK_PASSWORD')
    port = int(os.getenv('MIKROTIK_PORT'))
    timeout = int(os.getenv('MIKROTIK_TIMEOUT'))
    
    try:
        # Conectar ao Mikrotik usando RouterOsApiPool
        api_pool = RouterOsApiPool(hostname, username=username, password=password, plaintext_login=True)
        api = api_pool.get_api()
        nat_rules_data = []
        print('Conexão estabelecida com sucesso!')
        # Obtém as regras de NAT
        nat_resource = api.get_binary_resource('/ip/firewall/nat')
        nat_rules = nat_resource.call('print')

        print('Obtendo regras de NAT...')
        if nat_rules:
            print('Regras de NAT obtidas com sucesso!')
            for rule in nat_rules:
                
                relevant_info = {}
                for key in ['chain', 'action', 'src-address', 'dst-address', 'comment', 'to-addresses', 'disabled']:
                    try:
                        value = rule.get(key, b'N/A')
                        relevant_info[key] = decode_value(value)
                    except Exception as e:
                        relevant_info[key] = f"N/A"
                if str(relevant_info.get('action')) == 'src-nat' and str(relevant_info.get('disabled')) != 'true':

                    comment = relevant_info.get('comment', 'Não especificado')
                    src_address = relevant_info.get('src-address', 'Não especificado')
                    to_address = relevant_info.get('to-addresses', 'Não especificado')
                    
                    # Verifica as condições para marcar a linha como vermelho
                    mark_red = False
                    if (to_address.startswith('170') and 'corporativa' in comment.lower()) or \
                        (to_address.startswith('177') and 'turbonet' in comment.lower()):
                        mark_red = True
                    
                    # Testar conectividade com ping
                    print(f'Testando ping de {src_address} para {to_address}...')
                    ping_result = test_ping(api, '8.8.8.8', count=5, src_address=to_address)

                    # Adiciona os detalhes da regra à lista
                    nat_rules_data.append({
                        'comment': comment,
                        'src_address': src_address,
                        'to_address': to_address,
                        'mark_red': mark_red,
                        'ping_result': ping_result if ping_result else 'N/A'
                    })
        
        # Fecha a conexão
        api_pool.disconnect()

        # Ordenar a lista de regras de NAT por to_address
        nat_rules_data.sort(key=lambda x: x['to_address'])

        # Extrair dados relevantes
        mikrotik_data = {
            'hostname': hostname,
            'ip_address': hostname,  # IP do Mikrotik
            'nat_rules': nat_rules_data
        }
        
        return render(request, 'olt/mikrotik_info.html', {'mikrotik_data': mikrotik_data})
    except Exception as e:
        print(str(e))
        return render(request, 'olt/mikrotik_info.html', {'error': str(e)})
    

@login_required
def tasks_view(request):
    queue = django_rq.get_queue('default')
    jobs = []
    for job in queue.get_jobs():
        jobs.append({
            'id': job.id,
            'func_name': job.func_name,
            'status': job.get_status(),
            'created_at': job.created_at,
            'ended_at': job.ended_at if hasattr(job, 'ended_at') else None
        })
    return render(request, 'olt/tasks.html', {'jobs': jobs})


@login_required
def view_tasks(request):
    queue = get_queue('default')
    
    # Get all jobs from different states
    running_jobs = []
    
    # Get all jobs in the queue
    all_jobs = queue.jobs
    for job in all_jobs:
        if job is not None:
            status = job.get_status()
            if status in ['queued', 'started', 'deferred']:
                job_info = {
                    'id': job.id,
                    'func_name': job.func_name,
                    'status': status,
                    'created_at': job.created_at,
                    'user': job.meta.get('user', 'N/A'),
                    'menu_item': job.meta.get('menu_item', 'N/A'),
                    'started_at': job.meta.get('started_at', 'N/A')
                }
                running_jobs.append(job_info)
    
    # Get completed and failed jobs info
    finished_registry = queue.finished_job_registry
    failed_registry = queue.failed_job_registry
    
    finished_jobs = []
    for job_id in finished_registry.get_job_ids():
        job = queue.fetch_job(job_id)
        if job:
            finished_jobs.append({
                'id': job.id,
                'user': job.meta.get('user', 'N/A'),
                'menu_item': job.meta.get('menu_item', 'N/A'),
                'started_at': job.meta.get('started_at', 'N/A')
            })
    
    failed_jobs = []
    for job_id in failed_registry.get_job_ids():
        job = queue.fetch_job(job_id)
        if job:
            failed_jobs.append({
                'id': job.id,
                'user': job.meta.get('user', 'N/A'),
                'menu_item': job.meta.get('menu_item', 'N/A'),
                'started_at': job.meta.get('started_at', 'N/A')
            })
    
    # Get message from session if exists
    message = request.session.pop('task_message', None)
    job_id = request.session.pop('job_id', None)
    
    context = {
        'running_jobs': running_jobs,
        'finished_jobs': finished_jobs,
        'failed_jobs': failed_jobs,
        'message': message,
        'job_id': job_id
    }
    return render(request, 'olt/tasks.html', context)