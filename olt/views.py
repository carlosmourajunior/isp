from django.http import HttpResponse
from django.template import loader
from olt.utils import olt_connector
from django.shortcuts import render


from olt.models import OltUsers

def home(request):
    olt_users_list = OltUsers.objects.order_by('-users_connected')
    template = loader.get_template('olt/olt_users.html')
    context = {
        'olt_users_list': olt_users_list,
    }
    return HttpResponse(template.render(context, request))


def critical_users_list(request):
    olt_users_list = OltUsers.objects.filter(users_connected__gte=120).order_by('-users_connected')
    template = loader.get_template('olt/olt_users.html')
    context = {
        'olt_users_list': olt_users_list,
    }
    return HttpResponse(template.render(context, request))


def update(request):
    connector = olt_connector()
    connector.update_port_ocupation()
    olt_users_list = OltUsers.objects.order_by('-users_connected')
    template = loader.get_template('olt/olt_users.html')
    context = {
        'olt_users_list': olt_users_list,
    }
    return HttpResponse(template.render(context, request))

def removable_users_list(request, slot, port):
    connector = olt_connector()
    removable_list = connector.get_itens_to_remove(slot, port)
    template = loader.get_template('olt/removable_list.html')
    context = {
        'removable_list': removable_list,
    }
    return HttpResponse(template.render(context, request))


def remover_ont(request, porta):
    connector = olt_connector()
    connector.remove_onu(porta)
    porta = porta.split("/")
    removable_list = connector.get_itens_to_remove(porta[2], porta[3])
    template = loader.get_template('olt/removable_list.html')
    context = {
        'removable_list': removable_list,
    }
    return HttpResponse(template.render(context, request))