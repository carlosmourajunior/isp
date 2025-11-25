#!/usr/bin/env python
"""
Script para testar a nova view de Visitas Técnicas
"""
import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'isp.settings')
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Criar diretório de logs se não existir
log_dir = r'E:\code\logs'
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

django.setup()

from olt.models import OrdemServicoIxc

def test_visitas_tecnicas_view():
    """Testa os dados da view de visitas técnicas"""
    print("🔍 Testando dados para a view de Visitas Técnicas...")
    
    # Simular a query da view
    queryset = OrdemServicoIxc.objects.filter(
        assunto_nome__icontains='visita'
    ).order_by('-data_abertura', '-id_ixc')
    
    total = queryset.count()
    abertas = queryset.filter(status='A').count()
    executadas = queryset.filter(status='X').count()
    fechadas = queryset.filter(status='F').count()
    
    print(f"\n📊 Estatísticas das Visitas Técnicas:")
    print(f"   Total: {total}")
    print(f"   Abertas: {abertas}")
    print(f"   Executadas: {executadas}")
    print(f"   Fechadas: {fechadas}")
    print(f"   Taxa de conclusão: {(fechadas/total*100):.1f}%" if total > 0 else "   Taxa de conclusão: 0%")
    
    # Mostrar as primeiras 5
    print(f"\n📋 Primeiras 5 Visitas Técnicas:")
    for i, os in enumerate(queryset[:5], 1):
        status_texto = {
            'A': 'Aberta',
            'X': 'Executada', 
            'F': 'Fechada'
        }.get(os.status, os.status)
        
        print(f"   {i}. {os.protocolo} - {status_texto}")
        print(f"      Data: {os.data_abertura}")
        print(f"      Técnico: {os.tecnico_nome or 'Não definido'}")
        print(f"      Assunto: {os.assunto_nome}")
        if os.mensagem:
            print(f"      Mensagem: {os.mensagem[:100]}...")
        print()
    
    # Testar filtros
    print("🔍 Testando filtros:")
    
    # Filtro por status
    abertas_filtradas = queryset.filter(status='A')
    print(f"   Filtro status='A': {abertas_filtradas.count()} resultados")
    
    # Filtro por busca
    search_test = queryset.filter(
        Q(protocolo__icontains='2024') |
        Q(tecnico_nome__icontains='tecnico') |
        Q(endereco__icontains='rua') |
        Q(mensagem__icontains='cliente')
    )
    print(f"   Filtro busca 'teste': {search_test.count()} resultados")

if __name__ == '__main__':
    from django.db.models import Q
    test_visitas_tecnicas_view()