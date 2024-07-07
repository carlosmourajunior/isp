import base64
import json
from django.http import HttpResponse
from django.template import loader
from olt.utils import olt_connector
from django.shortcuts import render, redirect
from olt.models import ONU, ClienteFibraIxc, OltUsers
import requests
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.decorators import login_required

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
    connector = olt_connector()
    connector.update_port_ocupation(read_timeout=600, expect_string='typ:isadmin>#')
    olt_users_list = OltUsers.objects.order_by('-users_connected')
    template = loader.get_template('olt/home.html')
    context = {
        'olt_users_list': olt_users_list,
    }
    return HttpResponse(template.render(context, request))

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

    connector = olt_connector()
    connector.update_port(slot, port)
    values = connector.get_itens_to_port(slot, port, order_by=order_by)
    template = loader.get_template('olt/duplicates.html')
    context = {
        'duplicates': values,
        'slot': slot,
        'port': port,
    }
    return HttpResponse(template.render(context, request))


def update_onus_all(request):
    connector = olt_connector()
    connector.update_all_ports()
    olt_users_list = OltUsers.objects.order_by('-users_connected')
    template = loader.get_template('olt/home.html')
    context = {
        'olt_users_list': olt_users_list,
    }
    return HttpResponse(template.render(context, request))


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
    
        removable_list = serial.union(mac).union(desc1)

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

    host = 'ixc.via01.com.br'
    url = f"https://{host}/webservice/v1/radpop_radio_cliente_fibra"
    token = "1:e1d85d1920bad8a5fa64a8e5b10eb397d25d22436d2c528ce4e1afec217f5815".encode('utf-8')

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
