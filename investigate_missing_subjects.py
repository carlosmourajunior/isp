#!/usr/bin/env python
"""
Script para investigar assuntos faltantes na API do IXC
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'isp.settings')
sys.path.insert(0, '/code')
django.setup()

def investigate_missing_subjects():
    """Investiga por que alguns assuntos não aparecem na API"""
    print("=== INVESTIGAÇÃO DE ASSUNTOS FALTANTES ===")
    
    try:
        from olt.client_utils import IxcOSClient
        
        client = IxcOSClient()
        
        # IDs que sabemos que existem no IXC
        ids_esperados = list(range(1, 18))  # IDs 1-17 baseado na imagem
        nomes_esperados = {
            1: "Instalação",
            2: "Instabilidade", 
            3: "Mudança de endereço",
            4: "Troca de equipamento de luga",
            5: "Problemas no Wi-Fi",
            6: "Cancelamento",
            7: "Sem conexão",
            8: "Visita Técnica",
            9: "Configuração de Roteador",
            10: "Passagem de cabo",
            11: "Configuração de Deco",
            12: "Sinal alto",
            13: "Atualização de Firmware",
            14: "Acesso Remoto",
            15: "Cadastro",
            16: "Financeiro",
            17: "Telefone"
        }
        
        print(f"🔍 Investigando {len(ids_esperados)} assuntos esperados...")
        
        # 1. Buscar todas as páginas de assuntos
        print(f"\n📋 === BUSCANDO TODAS AS PÁGINAS DE ASSUNTOS ===")
        
        todos_assuntos = {}
        pagina = 1
        
        while True:
            print(f"Buscando página {pagina}...")
            response = client.listar_assuntos(page=pagina, rp=100)
            
            if not response or not response.get('registros'):
                print(f"Página {pagina} vazia ou erro - parando")
                break
            
            registros = response.get('registros', [])
            print(f"  Encontrados {len(registros)} registros na página {pagina}")
            
            for assunto in registros:
                id_assunto = assunto.get('id')
                nome_assunto = assunto.get('assunto', '')
                ativo = assunto.get('ativo', 'N')
                
                if id_assunto:
                    todos_assuntos[int(id_assunto)] = {
                        'nome': nome_assunto,
                        'ativo': ativo,
                        'data': assunto
                    }
                    print(f"    ID {id_assunto}: {nome_assunto} (Ativo: {ativo})")
            
            # Verificar se há mais páginas
            total = int(response.get('total', 0))
            registros_processados = pagina * 100
            
            if registros_processados >= total:
                break
                
            pagina += 1
        
        print(f"✅ Total de assuntos encontrados na API: {len(todos_assuntos)}")
        
        # 2. Comparar com IDs esperados
        print(f"\n🔍 === COMPARAÇÃO COM ASSUNTOS ESPERADOS ===")
        
        encontrados = set(todos_assuntos.keys())
        esperados = set(ids_esperados)
        
        faltantes = esperados - encontrados
        extras = encontrados - esperados
        
        print(f"📊 Assuntos esperados: {len(esperados)}")
        print(f"📊 Assuntos encontrados: {len(encontrados)}")
        print(f"📊 Assuntos faltantes: {len(faltantes)}")
        print(f"📊 Assuntos extras: {len(extras)}")
        
        if faltantes:
            print(f"\n❌ ASSUNTOS FALTANTES:")
            for id_faltante in sorted(faltantes):
                nome_esperado = nomes_esperados.get(id_faltante, "Nome desconhecido")
                print(f"   ID {id_faltante}: {nome_esperado}")
        
        if extras:
            print(f"\n➕ ASSUNTOS EXTRAS (não esperados):")
            for id_extra in sorted(extras):
                assunto_data = todos_assuntos[id_extra]
                print(f"   ID {id_extra}: {assunto_data['nome']} (Ativo: {assunto_data['ativo']})")
        
        # 3. Verificar assuntos inativos
        print(f"\n⚠️ === ASSUNTOS INATIVOS ===")
        
        inativos = [id_ass for id_ass, data in todos_assuntos.items() if data['ativo'] != 'S']
        
        if inativos:
            print(f"Encontrados {len(inativos)} assuntos inativos:")
            for id_inativo in sorted(inativos):
                assunto_data = todos_assuntos[id_inativo]
                print(f"   ID {id_inativo}: {assunto_data['nome']} (Status: {assunto_data['ativo']})")
        else:
            print("✅ Todos os assuntos encontrados estão ativos")
        
        # 4. Tentar buscar assunto específico ID 1
        print(f"\n🎯 === TESTE DIRETO DO ASSUNTO ID 1 ===")
        
        try:
            import requests
            import base64
            
            # Tentar buscar o assunto ID 1 diretamente
            url = f"https://{client.host}/webservice/v1/su_oss_assunto/1"
            headers = {
                'Authorization': f'Basic {base64.b64encode(client.token).decode("utf-8")}',
                'Content-Type': 'application/json'
            }
            
            response = requests.get(url, headers=headers, verify=False)
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Assunto ID 1 encontrado via GET direto:")
                print(f"   Nome: {data.get('assunto', 'N/A')}")
                print(f"   Ativo: {data.get('ativo', 'N/A')}")
                print(f"   Dados completos: {data}")
            else:
                print(f"❌ Erro ao buscar assunto ID 1: Status {response.status_code}")
                print(f"   Resposta: {response.text}")
                
        except Exception as e:
            print(f"❌ Erro no teste direto: {e}")
        
        # 5. Verificar filtros na requisição
        print(f"\n🔧 === TESTE COM FILTROS DIFERENTES ===")
        
        # Testar sem filtros
        try:
            payload_sem_filtro = {
                'page': '1',
                'rp': '100',
                'sortname': 'su_oss_assunto.id',
                'sortorder': 'asc'
            }
            
            headers = client.headers.copy()
            headers['ixcsoft'] = 'listar'
            
            response = requests.post(client.subjects_url, data=payload_sem_filtro, headers=headers, verify=False)
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Teste sem filtro qtype: {data.get('total', 0)} registros")
                
                registros = data.get('registros', [])
                for registro in registros[:5]:  # Mostrar apenas os 5 primeiros
                    print(f"   ID {registro.get('id')}: {registro.get('assunto')} (Ativo: {registro.get('ativo')})")
            else:
                print(f"❌ Erro no teste sem filtro: {response.status_code}")
                
        except Exception as e:
            print(f"❌ Erro no teste sem filtro: {e}")
        
        # 6. Sugestões para correção
        print(f"\n💡 === SUGESTÕES PARA CORREÇÃO ===")
        
        if faltantes:
            print("1. Verificar se os assuntos faltantes estão ativos no IXC")
            print("2. Testar endpoint com filtros diferentes")
            print("3. Verificar permissões da API para o token usado")
            print("4. Considerar usar GET direto para IDs específicos")
        
        if inativos:
            print("5. Incluir assuntos inativos se necessário para histórico")
        
        return True
        
    except Exception as e:
        print(f"❌ ERRO NA INVESTIGAÇÃO: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_direct_subject_fetch():
    """Testa busca direta de assuntos específicos"""
    print(f"\n🔄 === TESTE DE BUSCA DIRETA ===")
    
    try:
        from olt.client_utils import IxcOSClient
        import requests
        import base64
        
        client = IxcOSClient()
        
        # Testar IDs específicos que sabemos que existem
        ids_teste = [1, 2, 6, 8, 17]
        
        for id_assunto in ids_teste:
            try:
                url = f"https://{client.host}/webservice/v1/su_oss_assunto/{id_assunto}"
                headers = {
                    'Authorization': f'Basic {base64.b64encode(client.token).decode("utf-8")}',
                    'Content-Type': 'application/json'
                }
                
                response = requests.get(url, headers=headers, verify=False)
                
                if response.status_code == 200:
                    data = response.json()
                    nome = data.get('assunto', 'N/A')
                    ativo = data.get('ativo', 'N/A')
                    print(f"   ✅ ID {id_assunto}: {nome} (Ativo: {ativo})")
                else:
                    print(f"   ❌ ID {id_assunto}: Status {response.status_code}")
                    
            except Exception as e:
                print(f"   ❌ ID {id_assunto}: Erro {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ ERRO NO TESTE DIRETO: {e}")
        return False

if __name__ == '__main__':
    print("🚀 INICIANDO INVESTIGAÇÃO DE ASSUNTOS FALTANTES")
    
    sucesso = investigate_missing_subjects()
    
    if sucesso:
        test_direct_subject_fetch()
        print("\n🎉 INVESTIGAÇÃO CONCLUÍDA!")
    else:
        print("\n❌ INVESTIGAÇÃO FALHOU")
        sys.exit(1)