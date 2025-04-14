from django.http import HttpResponse
from django.template import loader
from olt.utils import connect_to_mikrotik, get_nat_rules, olt_connector
from django.shortcuts import render, redirect
from olt.models import ONU, ClienteFibraIxc, OltUsers
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.decorators import login_required
from routeros_api import RouterOsApiPool
from django_rq import get_queue
from .tasks import (
    update_all_data_task,
    update_onus_task,  # Changed from update_all_onus
    update_clientes_task,
    update_port_occupation_task,
    update_mac_task
)
from django.core.paginator import Paginator
from django.db.models import Q, FloatField, Count
from django.db.models.functions import Cast
import os
from dotenv import load_dotenv
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages


# Carregar variáveis de ambiente do arquivo .env
load_dotenv()

@login_required
def home(request):
    # Quantidade de ONUs sem MAC
    onus_without_mac = ONU.objects.filter(mac__isnull=True).count() + ONU.objects.filter(mac='').count()

    # Quantidade de ONUs sem cliente fibra
    onus_without_client = ONU.objects.filter(cliente_fibra=False).count()

    # Quantidade de clientes com sinal < -27
    # clients_signal_below_27_count = ONU.objects.filter(olt_rx_sig__lt=-27).count()

    # Quantidade de clientes com sinal < -29
    clients_signal_below_29_count = ONU.objects.filter(olt_rx_sig__lt=-29).count()

    # Quantidade de clientes com sinal entre -27 e -29
    clients_signal_below_27_count = ONU.objects.filter(olt_rx_sig__gte=-29, olt_rx_sig__lte=-27).count()

    # 5 portas com maior ocupação
    top_ports = OltUsers.objects.order_by('-users_connected')[:5]

    template = loader.get_template('olt/dashboard.html')
    context = {
        'onus_without_mac': onus_without_mac,
        'onus_without_client': onus_without_client,
        'clients_signal_below_27_count': clients_signal_below_27_count,
        'clients_signal_below_29_count': clients_signal_below_29_count,
        # 'clients_signal_between_27_and_29_count': clients_signal_between_27_and_29_count,
        'top_ports': top_ports,
    }
    return HttpResponse(template.render(context, request))


@login_required
def critical_users_list(request):
    """View para listar ocupação de todas as portas"""
    # Get query parameters
    search_query = request.GET.get('search', '')
    items_per_page = request.GET.get('per_page', 10)
    sort_by = request.GET.get('sort', 'slot')

    # Base query
    queryset = OltUsers.objects.all()

    # Apply search filter
    if search_query:
        queryset = queryset.filter(
            Q(slot__icontains=search_query) |
            Q(port__icontains=search_query) |
            Q(users_connected__icontains=search_query)
        )

    # Apply sorting
    queryset = queryset.order_by(sort_by)

    # Pagination
    paginator = Paginator(queryset, items_per_page)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'olt_users': page_obj,
        'title': 'Ocupação de Portas',
        'description': 'Lista de todas as portas da OLT e suas ocupações',
        'search_query': search_query,
        'items_per_page': items_per_page,
        'sort_by': sort_by
    }
    return render(request, 'olt/home.html', context)


def update_users(request):
    """View para atualizar ocupação de portas"""
    job = update_port_occupation_task.delay(
        user=request.user.username,
        menu_item='Atualização de Portas'
    )
    request.session['task_message'] = 'Atualização de portas iniciada. Acompanhe o progresso na lista de tarefas.'
    request.session['job_id'] = job.id
    return redirect('olt:view_tasks')


def update_mac_values(request):
    """View para atualizar endereços MAC"""
    job = update_mac_task.delay(
        user=request.user.username,
        menu_item='Atualização de MAC'
    )
    request.session['task_message'] = 'Atualização de MAC iniciada. Acompanhe o progresso na lista de tarefas.'
    request.session['job_id'] = job.id
    return redirect('olt:view_tasks')


def update_onus_all(request):
    """View para atualizar ONUs"""
    job = update_onus_task.delay(
        user=request.user.username,
        menu_item='Atualização de ONUs'
    )
    request.session['task_message'] = 'Atualização de ONUs iniciada. Acompanhe o progresso na lista de tarefas.'
    request.session['job_id'] = job.id
    return redirect('olt:view_tasks')


def update_values(request, port, slot):
    """View para atualizar valores de uma porta específica"""
    # Continua usando update_users pois precisamos da atualização completa da porta
    return update_users(request)


@login_required
def update_all_data(request):
    """View para iniciar a atualização de todos os dados"""
    # Inicia o job que fará todas as atualizações em sequência
    main_job = update_all_data_task.delay(
        user=request.user.username,
        menu_item='Atualizar Todos os Dados'
    )

    request.session['task_message'] = 'Atualização sequencial iniciada. Acompanhe o progresso na lista de tarefas.'
    request.session['job_id'] = main_job.id
    return redirect('olt:view_tasks')


@login_required
def list_onus_without_mac(request):
    """View para listar ONUs que não possuem MAC cadastrado"""
    # Get query parameters
    search_query = request.GET.get('search', '')
    items_per_page = request.GET.get('per_page', 10)
    sort_by = request.GET.get('sort', 'pon')
    
    # Base queryset
    onus_without_mac = ONU.objects.filter(Q(mac__isnull=True) | Q(mac=''))
    
    # Apply search if provided
    if search_query:
        onus_without_mac = onus_without_mac.filter(
            Q(pon__icontains=search_query) |
            Q(serial__icontains=search_query) |
            Q(mac__icontains=search_query) |  # Include MAC address in search
            Q(desc1__icontains=search_query) |
            Q(desc2__icontains=search_query) |
            Q(oper_state__icontains=search_query)
        )
    
    # Apply sorting
    onus_without_mac = onus_without_mac.order_by(sort_by)
    
    # Pagination
    paginator = Paginator(onus_without_mac, items_per_page)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'duplicates': page_obj,
        'title': 'ONUs sem MAC',
        'description': 'Lista de ONUs que não possuem endereço MAC cadastrado',
        'search_query': search_query,
        'items_per_page': items_per_page,
        'sort_by': sort_by
    }
    return render(request, 'olt/duplicates.html', context)


@login_required
def list_onus_without_client(request):
    """View para listar ONUs que não possuem cliente fibra associado"""
    # Get query parameters
    search_query = request.GET.get('search', '')
    items_per_page = request.GET.get('per_page', 10)
    sort_by = request.GET.get('sort', 'pon')
    
    # Base queryset
    onus_without_client = ONU.objects.filter(cliente_fibra=False)
    
    # Apply search if provided
    if search_query:
        onus_without_client = onus_without_client.filter(
            Q(pon__icontains=search_query) |
            Q(serial__icontains=search_query) |
            Q(mac__icontains=search_query) |  # Include MAC address in search
            Q(desc1__icontains=search_query) |
            Q(desc2__icontains=search_query) |
            Q(oper_state__icontains=search_query)
        )
    
    # Apply sorting
    onus_without_client = onus_without_client.order_by(sort_by)
    
    # Pagination
    paginator = Paginator(onus_without_client, items_per_page)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'duplicates': page_obj,
        'title': 'ONUs sem Cliente Fibra',
        'description': 'Lista de ONUs que não possuem cliente fibra associado',
        'search_query': search_query,
        'items_per_page': items_per_page,
        'sort_by': sort_by
    }
    return render(request, 'olt/duplicates.html', context)


@login_required
def get_duplicated(request):
    """View para listar ONUs duplicadas"""
    # Get query parameters
    search_query = request.GET.get('search', '')
    items_per_page = request.GET.get('per_page', 10)
    sort_by = request.GET.get('sort', 'serial')
    
    # Get duplicated ONUs
    duplicates = []
    base_query = ONU.objects.all()
    
    if search_query:
        base_query = base_query.filter(
            Q(pon__icontains=search_query) |
            Q(serial__icontains=search_query) |
            Q(mac__icontains=search_query) |  # Include MAC address in search
            Q(desc1__icontains=search_query) |
            Q(desc2__icontains=search_query) |
            Q(oper_state__icontains=search_query)
        )
    
    # Find duplicates
    for onu in base_query:
        if ONU.objects.filter(serial=onu.serial).count() > 1 and onu not in duplicates:
            duplicates.append(onu)
    
    # Convert list to queryset for proper sorting
    duplicates_ids = [onu.id for onu in duplicates]
    duplicates_queryset = ONU.objects.filter(id__in=duplicates_ids).order_by(sort_by)
    
    # Pagination
    paginator = Paginator(duplicates_queryset, items_per_page)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'duplicates': page_obj,
        'title': 'ONUs Duplicadas',
        'description': 'Lista de ONUs com número serial duplicado',
        'search_query': search_query,
        'items_per_page': items_per_page,
        'sort_by': sort_by
    }
    return render(request, 'olt/duplicates.html', context)


@login_required
def list_onus(request):
    """View para listar todas as ONUs"""
    # Get query parameters
    search_query = request.GET.get('search', '')
    items_per_page = request.GET.get('per_page', 10)
    sort_by = request.GET.get('sort', 'position')
    
    # Base query
    queryset = ONU.objects.all()
    
    # Apply search filter
    if search_query:
        queryset = queryset.filter(
            Q(serial__icontains=search_query) |
            Q(mac__icontains=search_query) |  # Include MAC address in search
            Q(desc1__icontains=search_query) |
            Q(desc2__icontains=search_query) |
            Q(pon__icontains=search_query)
        )
    
    # Apply sorting
    queryset = queryset.order_by(sort_by)
    
    # Pagination
    paginator = Paginator(queryset, items_per_page)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'onus': page_obj,
        'title': 'Lista de ONUs',
        'description': 'Lista completa de ONUs cadastradas',
        'search_query': search_query,
        'items_per_page': items_per_page,
        'sort_by': sort_by
    }
    return render(request, 'olt/list_onus.html', context)


@login_required
def list_onus_with_oper_state_down(request):
    """View para listar ONUs com oper_state 'down'"""
    # Get query parameters
    search_query = request.GET.get('search', '')
    items_per_page = request.GET.get('per_page', 10)
    sort_by = request.GET.get('sort', 'pon')

    # Base queryset
    onus_with_oper_state_down = ONU.objects.filter(oper_state='down')

    # Apply search if provided
    if search_query:
        onus_with_oper_state_down = onus_with_oper_state_down.filter(
            Q(pon__icontains=search_query) |
            Q(serial__icontains=search_query) |
            Q(mac__icontains=search_query) |
            Q(desc1__icontains=search_query) |
            Q(desc2__icontains=search_query)
        )

    # Apply sorting
    onus_with_oper_state_down = onus_with_oper_state_down.order_by(sort_by)

    # Pagination
    paginator = Paginator(onus_with_oper_state_down, items_per_page)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'onus': page_obj,
        'title': 'ONUs com Oper State Down',
        'description': 'Lista de ONUs com estado operacional "down"',
        'search_query': search_query,
        'items_per_page': items_per_page,
        'sort_by': sort_by
    }
    return render(request, 'olt/list_onus.html', context)


@login_required
def clients_signal_below_27(request):
    """View to list ONUs with signal below -27 dBm."""
    search_query = request.GET.get('search', '')
    items_per_page = request.GET.get('per_page', 10)
    sort_by = request.GET.get('sort', 'olt_rx_sig')

    queryset = ONU.objects.filter(olt_rx_sig__lt=-27)

    if search_query:
        queryset = queryset.filter(
            Q(serial__icontains=search_query) |
            Q(mac__icontains=search_query) |
            Q(desc1__icontains=search_query) |
            Q(desc2__icontains=search_query)
        )

    queryset = queryset.order_by(sort_by)

    paginator = Paginator(queryset, items_per_page)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'onus': page_obj,
        'title': 'Clientes com Sinal < -27',
        'description': 'Lista de ONUs com sinal abaixo de -27 dBm.',
        'search_query': search_query,
        'items_per_page': items_per_page,
        'sort_by': sort_by
    }
    return render(request, 'olt/list_onus.html', context)


@login_required
def clients_signal_below_29(request):
    """View to list ONUs with signal below -29 dBm."""
    search_query = request.GET.get('search', '')
    items_per_page = request.GET.get('per_page', 10)
    sort_by = request.GET.get('sort', 'olt_rx_sig')

    queryset = ONU.objects.filter(olt_rx_sig__lt=-29)

    if search_query:
        queryset = queryset.filter(
            Q(serial__icontains=search_query) |
            Q(mac__icontains=search_query) |
            Q(desc1__icontains=search_query) |
            Q(desc2__icontains=search_query)
        )

    queryset = queryset.order_by(sort_by)

    paginator = Paginator(queryset, items_per_page)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'onus': page_obj,
        'title': 'Clientes com Sinal < -29',
        'description': 'Lista de ONUs com sinal abaixo de -29 dBm.',
        'search_query': search_query,
        'items_per_page': items_per_page,
        'sort_by': sort_by
    }
    return render(request, 'olt/list_onus.html', context)


@login_required
def list_onus_signal_between_27_and_29(request):
    """View to list ONUs with signal levels between -27 and -29."""
    # Get query parameters
    search_query = request.GET.get('search', '')
    items_per_page = request.GET.get('per_page', 10)
    sort_by = request.GET.get('sort', 'olt_rx_sig')

    # Base queryset
    queryset = ONU.objects.filter(olt_rx_sig__gte=-29, olt_rx_sig__lte=-27)

    # Apply search filter
    if search_query:
        queryset = queryset.filter(
            Q(serial__icontains=search_query) |
            Q(mac__icontains=search_query) |
            Q(desc1__icontains=search_query) |
            Q(desc2__icontains=search_query)
        )

    # Apply sorting
    queryset = queryset.order_by(sort_by)

    # Pagination
    paginator = Paginator(queryset, items_per_page)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'onus': page_obj,
        'title': 'ONUs com Sinal entre -27 e -29',
        'description': 'Lista de ONUs com sinal entre -27 e -29 dBm.',
        'search_query': search_query,
        'items_per_page': items_per_page,
        'sort_by': sort_by
    }
    return render(request, 'olt/list_onus.html', context)


def get_itens_to_port(request, slot, port):
    """View para listar itens de uma porta específica"""
    connector = olt_connector()
    
    # Get query parameters
    search_query = request.GET.get('search', '')
    items_per_page = request.GET.get('per_page', 10)
    sort_by = request.GET.get('sort', 'position')
    
    # Get base queryset
    queryset = connector.get_itens_to_port(slot, port, order_by=sort_by)
    
    # Apply search filter if provided
    if search_query:
        queryset = queryset.filter(
            Q(serial__icontains=search_query) |
            Q(mac__icontains=search_query) |  # Include MAC address in search
            Q(desc1__icontains=search_query) |
            Q(desc2__icontains=search_query)
        )
    
    # Pagination
    paginator = Paginator(queryset, items_per_page)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'removable_list': page_obj,
        'slot': slot,
        'port': port,
        'search_query': search_query,
        'items_per_page': items_per_page,
        'sort_by': sort_by,
    }
    return render(request, 'olt/removable_list.html', context)


def remover_ont(request, porta):
    """View para remover uma ONT"""
    connector = olt_connector()
    connector.remove_onu(porta)
    porta = porta.split("/")
    removable_list = connector.get_itens_to_port(1, 16)
    template = loader.get_template('olt/removable_list.html')
    context = {
        'removable_list': removable_list,
    }
    return HttpResponse(template.render(context, request))


def delete(request, slot, port, position):
    """View para deletar uma ONT específica"""
    pon = f"1/1/{slot}/{port}/{position}"
    connector = olt_connector()
    connector.remove_onu(pon)

    # Remove a ONU correspondente do banco de dados
    ONU.objects.filter(pon=f"1/1/{slot}/{port}", position=position).delete()

    return redirect('olt:list_onus')


@login_required
def reset_onu(request, slot, port, position):
    """View para reiniciar uma ONT específica"""
    pon = f"1/1/{slot}/{port}/{position}"
    connector = olt_connector()
    
    print(f"Reiniciando ONU {pon}...")
    try:
        connector.reset_onu(pon)
        messages.success(request, f"ONU {pon} reiniciada com sucesso.")
    except Exception as e:
        print(e)
        messages.error(request, f"Erro ao reiniciar ONU {pon}: {str(e)}")
    return redirect('olt:list_onus')


def search_view(request):
    """View para busca geral"""
    query = request.GET.get('q', '')
    if not query:
        return redirect('olt:home')
    
    results = ONU.objects.filter(
        Q(serial__icontains=query) |
        Q(mac__icontains=query) |  # Include MAC address in search
        Q(desc1__icontains=query) |
        Q(desc2__icontains=query) |
        Q(pon__icontains=query)
    )
    
    context = {
        'duplicates': results,
        'title': 'Resultados da Busca',
        'description': f'Resultados para: {query}',
        'search_query': query
    }
    return render(request, 'olt/duplicates.html', context)


def search_ixc(request):
    """View para atualizar clientes fibra"""
    job = update_clientes_task.delay(
        user=request.user.username,
        menu_item='Atualização de Clientes Fibra'
    )
    request.session['task_message'] = 'Atualização de clientes fibra iniciada. Acompanhe o progresso na lista de tarefas.'
    request.session['job_id'] = job.id
    return redirect('olt:view_tasks')


def listar_clientes(request):
    """View para listar clientes fibra"""
    # Get query parameters
    search_query = request.GET.get('search', '')
    items_per_page = request.GET.get('per_page', 10)
    sort_by = request.GET.get('sort', 'nome')
    
    # Base query
    queryset = ClienteFibraIxc.objects.all()
    
    # Apply search filter
    if search_query:
        queryset = queryset.filter(
            Q(nome__icontains=search_query) |
            Q(mac__icontains=search_query)  # Include MAC address in search
        )
    
    # Apply sorting
    queryset = queryset.order_by(sort_by)
    
    # Pagination
    paginator = Paginator(queryset, items_per_page)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'clientes': page_obj,
        'title': 'Clientes Fibra',
        'description': 'Lista de clientes fibra cadastrados no sistema',
        'search_query': search_query,
        'items_per_page': items_per_page,
        'sort_by': sort_by
    }
    return render(request, 'olt/clientes_fibra.html', context)


def register(request):
    """View para registro de usuário"""
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('olt:login')
    else:
        form = UserCreationForm()
    return render(request, 'register.html', {'form': form})


@login_required
def mikrotik_info(request):
    """View para exibir informações do Mikrotik"""
    mikrotik_host = os.getenv('MIKROTIK_HOST')
    mikrotik_user = os.getenv('MIKROTIK_USERNAME')
    mikrotik_pass = os.getenv('MIKROTIK_PASSWORD')
    mikrotik_port = int(os.getenv('MIKROTIK_PORT', 8728))
    
    api = connect_to_mikrotik(mikrotik_host, mikrotik_user, mikrotik_pass, mikrotik_port)
    nat_rules = get_nat_rules(api) if api else []
    
    context = {
        'mikrotik_data': {
            'nat_rules': nat_rules
        }
    }
    return render(request, 'olt/mikrotik_info.html', context)


@login_required
def view_tasks(request):
    """View para monitoramento de tarefas"""
    queue = get_queue('default')
    
    # Get all jobs from different states
    running_jobs = []
    queued_jobs = []
    finished_jobs = []
    failed_jobs = []
    
    # Get started jobs
    started_registry = queue.started_job_registry
    for job_id in started_registry.get_job_ids()[:5]:  # Limita a 5 tarefas
        job = queue.fetch_job(job_id)
        if job is not None:
            job_info = {
                'id': job.id,
                'func_name': job.func_name,
                'status': job.get_status(),
                'created_at': job.created_at,
                'user': job.meta.get('user', 'N/A'),
                'menu_item': job.meta.get('menu_item', 'N/A'),
                'started_at': job.meta.get('started_at', 'N/A'),
                'current_step': job.meta.get('current_step', 'N/A')
            }
            running_jobs.append(job_info)
    
    # Get queued jobs
    for job in list(queue.jobs)[:5]:  # Limita a 5 tarefas
        if job is not None and job.get_status() in ['queued', 'deferred']:
            job_info = {
                'id': job.id,
                'func_name': job.func_name,
                'status': job.get_status(),
                'created_at': job.created_at,
                'user': job.meta.get('user', 'N/A'),
                'menu_item': job.meta.get('menu_item', 'N/A')
            }
            queued_jobs.append(job_info)
    
    # Get failed jobs
    failed_registry = queue.failed_job_registry
    for job_id in failed_registry.get_job_ids()[:5]:  # Limita a 5 tarefas
        job = queue.fetch_job(job_id)
        if job is not None:
            job_info = {
                'id': job.id,
                'func_name': job.func_name,
                'status': job.get_status(),
                'created_at': job.created_at,
                'user': job.meta.get('user', 'N/A'),
                'menu_item': job.meta.get('menu_item', 'N/A'),
                'started_at': job.meta.get('started_at', 'N/A'),
                'error_message': job.exc_info  # Adiciona mensagem de erro
            }
            failed_jobs.append(job_info)
    
    # Get finished jobs
    finished_registry = queue.finished_job_registry
    for job_id in finished_registry.get_job_ids()[:5]:  # Limita a 5 tarefas
        job = queue.fetch_job(job_id)
        if job is not None:
            job_info = {
                'id': job.id,
                'func_name': job.func_name,
                'status': job.get_status(),
                'created_at': job.created_at,
                'user': job.meta.get('user', 'N/A'),
                'menu_item': job.meta.get('menu_item', 'N/A'),
                'started_at': job.meta.get('started_at', 'N/A')
            }
            finished_jobs.append(job_info)
    
    context = {
        'running_jobs': running_jobs,
        'queued_jobs': queued_jobs,
        'finished_jobs': finished_jobs,
        'failed_jobs': failed_jobs,
        'message': request.session.pop('task_message', None)
    }
    return render(request, 'olt/tasks.html', context)


@login_required
def list_mac_addresses(request):
    """View para listar todos os MAC addresses cadastrados."""
    mac_addresses = ONU.objects.values_list('mac', flat=True)

    context = {
        'title': 'Lista de MAC Addresses',
        'description': 'Todos os MAC addresses cadastrados no sistema.',
        'mac_addresses': mac_addresses,
    }
    return render(request, 'olt/list_mac_addresses.html', context)


@login_required
def list_all_macs(request):
    """View para listar todos os MAC addresses com busca e paginação."""
    # Get query parameters
    search_query = request.GET.get('search', '')
    items_per_page = request.GET.get('per_page', 10)
    sort_by = request.GET.get('sort', 'mac')

    # Base query
    queryset = ONU.objects.all()

    # Apply search filter
    if search_query:
        queryset = queryset.filter(
            Q(mac__icontains=search_query) |
            Q(serial__icontains=search_query) |
            Q(desc1__icontains=search_query) |
            Q(desc2__icontains=search_query)
        )

    # Apply sorting
    queryset = queryset.order_by(sort_by)

    # Pagination
    paginator = Paginator(queryset, items_per_page)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'macs': page_obj,
        'title': 'Lista de MAC Addresses',
        'description': 'Todos os MAC addresses cadastrados no sistema.',
        'search_query': search_query,
        'items_per_page': items_per_page,
        'sort_by': sort_by
    }
    return render(request, 'olt/list_mac_addresses.html', context)


@login_required
def list_ftth_boxes_by_occupancy(request):
    """View to list FTTH boxes ordered by client occupancy."""
    # Get query parameters
    search_query = request.GET.get('search', '')
    items_per_page = request.GET.get('per_page', 10)

    # Base queryset
    queryset = ClienteFibraIxc.objects.values('id_caixa_ftth').annotate(
        client_count=Count('id_caixa_ftth')
    ).order_by('-client_count')

    # Apply search filter
    if search_query:
        queryset = queryset.filter(id_caixa_ftth__icontains=search_query)

    # Pagination
    paginator = Paginator(queryset, items_per_page)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'ftth_boxes': page_obj,
        'title': 'Caixas FTTH por Ocupação',
        'description': 'Lista de caixas FTTH ordenadas por número de clientes.',
        'search_query': search_query,
        'items_per_page': items_per_page
    }
    return render(request, 'olt/list_ftth_boxes.html', context)