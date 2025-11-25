#!/usr/bin/env python
"""
Análise dos assuntos de Visita Técnica das OS
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'isp.settings')
sys.path.insert(0, '/code')
django.setup()

def analyze_visita_tecnica_subjects():
    """Analisa os assuntos de Visita Técnica"""
    from olt.models import OrdemServicoIxc
    from django.db.models import Count
    
    print("=== ANÁLISE DOS ASSUNTOS DE VISITA TÉCNICA ===")
    
    # 1. Buscar OS com 'visita' no assunto
    os_visita = OrdemServicoIxc.objects.filter(
        assunto_nome__icontains='visita'
    ).values('assunto_nome', 'id_assunto').annotate(
        total=Count('id')
    ).order_by('-total')
    
    total_visita = sum([os['total'] for os in os_visita])
    print(f'Total de OS com "visita" no assunto: {total_visita}')
    
    print('\n📋 Principais assuntos de Visita:')
    for i, os in enumerate(os_visita[:10], 1):
        print(f'{i:2d}. {os["assunto_nome"][:40]:40} - {os["total"]:3d} OS (ID: {os["id_assunto"]})')
    
    # 2. Buscar também por 'técnica'
    print('\n=== ASSUNTOS COM "TÉCNICA" ===')
    os_tecnica = OrdemServicoIxc.objects.filter(
        assunto_nome__icontains='técnica'
    ).values('assunto_nome', 'id_assunto').annotate(
        total=Count('id')
    ).order_by('-total')
    
    total_tecnica = sum([os['total'] for os in os_tecnica])
    print(f'Total de OS com "técnica" no assunto: {total_tecnica}')
    
    print('\n📋 Principais assuntos Técnicos:')
    for i, os in enumerate(os_tecnica[:10], 1):
        print(f'{i:2d}. {os["assunto_nome"][:40]:40} - {os["total"]:3d} OS (ID: {os["id_assunto"]})')
    
    # 3. Buscar outros termos relacionados
    termos = ['instalação', 'manutenção', 'reparo', 'verificação', 'diagnóstico']
    
    print('\n=== OUTROS ASSUNTOS RELACIONADOS ===')
    for termo in termos:
        os_termo = OrdemServicoIxc.objects.filter(
            assunto_nome__icontains=termo
        ).values('assunto_nome', 'id_assunto').annotate(
            total=Count('id')
        ).order_by('-total')
        
        if os_termo:
            total_termo = sum([os['total'] for os in os_termo])
            print(f'\n🔧 {termo.upper()} ({total_termo} OS):')
            for os in os_termo[:5]:
                print(f'   {os["assunto_nome"][:35]:35} - {os["total"]:3d} OS')
    
    # 4. Top 10 assuntos gerais
    print('\n=== TOP 10 ASSUNTOS MAIS COMUNS ===')
    top_assuntos = OrdemServicoIxc.objects.values(
        'assunto_nome', 'id_assunto'
    ).annotate(
        total=Count('id')
    ).order_by('-total')[:10]
    
    for i, os in enumerate(top_assuntos, 1):
        print(f'{i:2d}. {os["assunto_nome"][:40]:40} - {os["total"]:3d} OS')
    
    return os_visita, os_tecnica, top_assuntos

if __name__ == '__main__':
    analyze_visita_tecnica_subjects()