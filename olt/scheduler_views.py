"""
Views para monitoramento do sistema de atualizações automáticas
"""
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from .scheduler import get_scheduler_status
from django_rq import get_queue


@login_required
def scheduler_status(request):
    """View para mostrar o status do scheduler"""
    try:
        scheduler_status_data = get_scheduler_status()
        queue = get_queue('default')
        
        # Informações da fila RQ
        queue_info = {
            'pending_jobs': len(queue),
            'failed_jobs': len(queue.failed_job_registry),
            'finished_jobs': len(queue.finished_job_registry),
        }
        
        context = {
            'scheduler': scheduler_status_data,
            'queue': queue_info,
            'title': 'Status das Atualizações Automáticas'
        }
        
        if request.headers.get('Accept') == 'application/json':
            return JsonResponse(context)
        
        return render(request, 'olt/scheduler_status.html', context)
        
    except Exception as e:
        error_context = {
            'error': str(e),
            'title': 'Erro no Sistema de Atualizações'
        }
        
        if request.headers.get('Accept') == 'application/json':
            return JsonResponse(error_context, status=500)
        
        return render(request, 'olt/scheduler_status.html', error_context)