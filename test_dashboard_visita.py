#!/usr/bin/env python
"""
Teste da dashboard com dados de Visita Técnica
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'isp.settings')
sys.path.insert(0, '/code')
django.setup()

def test_dashboard_data():
    """Testa os dados da dashboard"""
    from olt.models import OrdemServicoIxc
    from django.db.models import Count
    
    # Verificar Visita Técnica
    os_visita_tecnica = OrdemServicoIxc.objects.filter(assunto_nome__icontains='visita')
    visita_total = os_visita_tecnica.count()
    visita_abertas = os_visita_tecnica.filter(status='A').count()
    visita_fechadas = os_visita_tecnica.filter(status='F').count()
    ultimas_visita = os_visita_tecnica.order_by('-data_abertura')[:5]
    
    print('=== DADOS DA DASHBOARD - VISITA TÉCNICA ===')
    print(f'Total: {visita_total}')
    print(f'Abertas: {visita_abertas}') 
    print(f'Fechadas: {visita_fechadas}')
    
    if visita_total > 0:
        taxa = (visita_fechadas / visita_total * 100)
        print(f'Taxa conclusão: {taxa:.1f}%')
    else:
        print('Taxa conclusão: 0%')
    
    print('\n📋 Últimas 5 Visitas Técnicas:')
    for i, os in enumerate(ultimas_visita, 1):
        status_desc = {'A': 'Aberta', 'F': 'Fechada', 'X': 'Executada'}.get(os.status, os.status)
        data_str = os.data_abertura.strftime('%d/%m/%Y %H:%M')
        print(f'{i:2d}. {os.protocolo} - {data_str} - {status_desc}')
        print(f'    Cliente: {os.id_cliente}, Técnico: {os.tecnico_nome or "Não atribuído"}')
        if os.endereco:
            print(f'    Endereço: {os.endereco[:50]}...' if len(os.endereco) > 50 else f'    Endereço: {os.endereco}')
    
    return True

if __name__ == '__main__':
    test_dashboard_data()