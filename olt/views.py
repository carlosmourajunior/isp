from django.http import HttpResponse
from django.template import loader
from olt.utils import olt_connector
from django.shortcuts import render


from olt.models import ONU, OltUsers

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
    connector.update_port_ocupation()
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
    olt_users_list = connector.get_itens_to_remove(slot, port)
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

def delete_user(request, slot, port):
    pon = f"1/1/{slot}/{port}"
    # ONU.objects.filter(pon=pon, onu=onu).delete()
    # removable_list = ONU.objects.filter(pon=pon)
    # template = loader.get_template('olt/removable_list.html')
    # context = {
    #     'removable_list': removable_list,
    # }
    print(f"Slot: {slot} Port: {port}")
    return HttpResponse({'status': 'ok'}, content_type='application/json')


def remover_ont(request, porta):
    connector = olt_connector()
    connector.remove_onu(porta)
    porta = porta.split("/")
    removable_list = connector.get_itens_to_remove(1, 16)
    template = loader.get_template('olt/removable_list.html')
    context = {
        'removable_list': removable_list,
    }
    return HttpResponse(template.render(context, request))