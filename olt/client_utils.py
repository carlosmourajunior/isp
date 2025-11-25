import base64
import json
# from .models import ONU, ClienteFibraIxc
import requests
import os
from datetime import datetime
from django.core.cache import cache
from .models import ONU, ClienteFibraIxc

def update_clientes():
    """Função para atualizar a lista de clientes fibra do IXC e atualizar o campo cliente_fibra nas ONUs."""

    response = search_ixc_page(1)
    # if response.status_code != 200:
    #     print(f"Error: {response.status_code} - {response.text}")
    #     return

    data = response.json()

    total_de_paginas = int(data['total'])/100

    # Usar transação atômica para evitar perda de dados
    from django.db import transaction
    with transaction.atomic():
        # Marcar todos como inativos primeiro
        ClienteFibraIxc.objects.all().update(is_active=False)
        
        for page in range(1, int(total_de_paginas+1)):
            response = search_ixc_page(page)
            data = response.json()
            
            for registro in data['registros']:
                cliente_data = {
                    'mac': registro['mac'],
                    'nome': registro['nome'],
                    'latitude': registro.get('latitude', ''),
                    'longitude': registro.get('longitude', ''),
                    'endereco': f"{registro.get('endereco', '')}, {registro.get('numero', '')}, {registro.get('bairro', '')}, {registro.get('cidade', '')}",
                    'id_caixa_ftth': registro.get('id_caixa_ftth', ''),
                    'is_active': True
                }
                ClienteFibraIxc.objects.update_or_create(
                    mac=registro['mac'],
                    defaults=cliente_data
                )
        
        # Remover apenas os que realmente não existem mais
        # (opcional - pode manter histórico marcando como inativo)
        # ClienteFibraIxc.objects.filter(is_active=False).delete()

    onus = ONU.objects.all()
    for onu in onus:
        onu.update_cliente_fibra_status()


def search_ixc_page(page):

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


class IxcOSClient:
    """Cliente para integração com API de Ordens de Serviço do IXC"""
    
    def __init__(self):
        self.host = os.getenv('IXC_HOST')
        self.token = os.getenv('IXC_TOKEN').encode('utf-8')
        self.base_url = f"https://{self.host}/webservice/v1/su_oss_chamado"
        self.subjects_url = f"https://{self.host}/webservice/v1/su_oss_assunto"
        self.headers = {
            'Authorization': f'Basic {base64.b64encode(self.token).decode("utf-8")}',
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        self._subjects_cache = None
    
    def listar_ordens_servico(self, page=1, rp=100, filtros=None):
        """
        Lista ordens de serviço do IXC com paginação
        Baseado na documentação oficial do IXC usando qtype/query/oper
        """
        # Payload base - buscar todas as OS por padrão
        payload = {
            'qtype': 'su_oss_chamado.id',
            'query': '0',
            'oper': '>',
            'page': str(page),
            'rp': str(rp),
            'sortname': 'su_oss_chamado.id',
            'sortorder': 'desc'
        }
        
        # Aplicar filtros baseado no exemplo oficial do IXC
        if filtros:
            # Para filtros de data, usar qtype específico para data_abertura
            if 'data_inicio' in filtros:
                payload['qtype'] = 'su_oss_chamado.data_abertura'
                payload['query'] = filtros['data_inicio']
                payload['oper'] = '>='
                
                # Se tem data_fim também, fazer consulta com range
                if 'data_fim' in filtros:
                    # Formato de range suportado pelo IXC
                    payload['query'] = f"{filtros['data_inicio']} TO {filtros['data_fim']}"
                    payload['oper'] = 'between'
            
            # Filtro por status
            elif 'status' in filtros:
                payload['qtype'] = 'su_oss_chamado.status'
                payload['query'] = filtros['status']
                payload['oper'] = '='
            
            # Filtro por tipo
            elif 'tipo' in filtros:
                payload['qtype'] = 'su_oss_chamado.tipo'
                payload['query'] = filtros['tipo']
                payload['oper'] = '='
            
            # Filtro por ID específico
            elif 'id_especifico' in filtros:
                payload['qtype'] = 'su_oss_chamado.id'
                payload['query'] = str(filtros['id_especifico'])
                payload['oper'] = '='
            
            # Filtro por range de IDs
            elif 'id_minimo' in filtros:
                payload['qtype'] = 'su_oss_chamado.id'
                payload['query'] = str(filtros['id_minimo'])
                payload['oper'] = '>='
        
        headers = self.headers.copy()
        headers['ixcsoft'] = 'listar'
        
        try:
            response = requests.post(self.base_url, data=payload, headers=headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Erro ao listar ordens de serviço: {e}")
            return None
    
    def obter_ordem_servico(self, id_os):
        """
        Obtém uma ordem de serviço específica pelo ID
        """
        url = f"{self.base_url}/{id_os}"
        
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Erro ao obter ordem de serviço {id_os}: {e}")
            return None
    
    def buscar_os_por_id(self, id_os):
        """
        Busca uma OS específica pelo ID usando filtros da API
        Retorna os dados da OS se encontrada, None caso contrário
        """
        try:
            # Usar filtro para buscar ID específico
            filtros = {'id_especifico': id_os}
            resultado = self.listar_ordens_servico(page=1, rp=1, filtros=filtros)
            
            if resultado and resultado.get('registros'):
                registros = resultado.get('registros', [])
                if len(registros) > 0:
                    os_data = registros[0]
                    
                    # Processar e salvar no banco se não existir
                    from .models import OrdemServicoIxc
                    from django.db import transaction
                    
                    id_ixc = int(os_data.get('id', 0))
                    if not OrdemServicoIxc.objects.filter(id_ixc=id_ixc).exists():
                        with transaction.atomic():
                            self._processar_registro_os(os_data)
                    
                    return os_data
            
            return None
            
        except Exception as e:
            print(f"Erro ao buscar OS {id_os}: {e}")
            return None
    
    def sincronizar_ordens_servico(self, limite_paginas=None):
        """
        Sincroniza ordens de serviço do IXC com o banco local
        """
        from .models import OrdemServicoIxc
        from django.db import transaction
        from datetime import datetime
        
        print("Iniciando sincronização de ordens de serviço...")
        
        # Primeira página para descobrir total
        primeira_pagina = self.listar_ordens_servico(page=1, rp=100)
        if not primeira_pagina:
            print("Erro ao obter primeira página")
            return False
        
        total_registros = int(primeira_pagina.get('total', 0))
        total_paginas = (total_registros // 100) + (1 if total_registros % 100 > 0 else 0)
        
        if limite_paginas:
            total_paginas = min(total_paginas, limite_paginas)
        
        print(f"Total de registros: {total_registros}, Páginas a processar: {total_paginas}")
        
        registros_processados = 0
        registros_atualizados = 0
        registros_criados = 0
        
        for pagina in range(1, total_paginas + 1):
            print(f"Processando página {pagina}/{total_paginas}...")
            
            dados = self.listar_ordens_servico(page=pagina, rp=100)
            if not dados or 'registros' not in dados:
                continue
            
            with transaction.atomic():
                for registro in dados['registros']:
                    try:
                        id_ixc = int(registro.get('id', 0))
                        if not id_ixc:
                            continue
                        
                        # Converter datas
                        data_abertura = self._converter_data(registro.get('data_abertura'))
                        data_agenda = self._converter_data(registro.get('data_agenda'))
                        data_execucao = self._converter_data(registro.get('data_hora_execucao'))
                        data_fechamento = self._converter_data(registro.get('data_fechamento'))
                        data_prazo_limite = self._converter_data(registro.get('data_prazo_limite'))
                        
                        # Converter valores financeiros
                        valor_total = self._converter_valor(registro.get('valor_total'))
                        valor_comissao = self._converter_valor(registro.get('valor_total_comissao'))
                        
                        # Dados da OS
                        id_assunto = self._converter_int(registro.get('id_assunto'))
                        assunto_nome = registro.get('assunto_nome')
                        
                        # Se assunto_nome está vazio mas temos id_assunto, buscar nome
                        if id_assunto and not assunto_nome:
                            assunto_nome = self.get_subject_name(id_assunto)
                        
                        dados_os = {
                            'protocolo': registro.get('protocolo'),
                            'tipo': registro.get('tipo', 'M'),
                            'status': registro.get('status', 'A'),
                            'prioridade': registro.get('prioridade', 'N'),
                            'id_cliente': self._converter_int(registro.get('id_cliente')),
                            'id_contrato': self._converter_int(registro.get('id_contrato_kit')),
                            'id_assunto': id_assunto,
                            'assunto_nome': assunto_nome,
                            'mensagem': registro.get('mensagem'),
                            'mensagem_resposta': registro.get('mensagem_resposta'),
                            'id_tecnico': self._converter_int(registro.get('id_tecnico')),
                            'tecnico_nome': registro.get('tecnico_nome'),
                            'endereco': registro.get('endereco'),
                            'bairro': registro.get('bairro'),
                            'cidade': registro.get('cidade'),
                            'referencia': registro.get('referencia'),
                            'data_abertura': data_abertura,
                            'data_agenda': data_agenda,
                            'data_execucao': data_execucao,
                            'data_fechamento': data_fechamento,
                            'data_prazo_limite': data_prazo_limite,
                            'valor_total': valor_total,
                            'valor_comissao': valor_comissao,
                        }
                        
                        # Criar ou atualizar registro
                        os_obj, created = OrdemServicoIxc.objects.update_or_create(
                            id_ixc=id_ixc,
                            defaults=dados_os
                        )
                        
                        if created:
                            registros_criados += 1
                        else:
                            registros_atualizados += 1
                        
                        registros_processados += 1
                        
                    except Exception as e:
                        print(f"Erro ao processar registro {registro.get('id', 'N/A')}: {e}")
                        continue
        
        print(f"Sincronização concluída:")
        print(f"- Registros processados: {registros_processados}")
        print(f"- Registros criados: {registros_criados}")
        print(f"- Registros atualizados: {registros_atualizados}")
        
        return True
    
    def _processar_registro_os(self, registro):
        """
        Processa um registro de OS da API e salva/atualiza no banco
        """
        from .models import OrdemServicoIxc
        
        try:
            id_ixc = int(registro.get('id', 0))
            if not id_ixc:
                return None
            
            # Converter datas
            data_abertura = self._converter_data(registro.get('data_abertura'))
            data_agenda = self._converter_data(registro.get('data_agenda'))
            data_execucao = self._converter_data(registro.get('data_hora_execucao'))
            data_fechamento = self._converter_data(registro.get('data_fechamento'))
            data_prazo_limite = self._converter_data(registro.get('data_prazo_limite'))
            
            # Converter valores financeiros
            valor_total = self._converter_valor(registro.get('valor_total'))
            valor_comissao = self._converter_valor(registro.get('valor_total_comissao'))
            
            # Dados da OS
            id_assunto = self._converter_int(registro.get('id_assunto'))
            assunto_nome = registro.get('assunto_nome')
            
            # Se assunto_nome está vazio mas temos id_assunto, buscar nome
            if id_assunto and not assunto_nome:
                assunto_nome = self.get_subject_name(id_assunto)
            
            dados_os = {
                'protocolo': registro.get('protocolo'),
                'tipo': registro.get('tipo', 'M'),
                'status': registro.get('status', 'A'),
                'prioridade': registro.get('prioridade', 'N'),
                'id_cliente': self._converter_int(registro.get('id_cliente')),
                'id_contrato': self._converter_int(registro.get('id_contrato_kit')),
                'id_assunto': id_assunto,
                'assunto_nome': assunto_nome,
                'mensagem': registro.get('mensagem'),
                'mensagem_resposta': registro.get('mensagem_resposta'),
                'id_tecnico': self._converter_int(registro.get('id_tecnico')),
                'tecnico_nome': registro.get('tecnico_nome'),
                'endereco': registro.get('endereco'),
                'bairro': registro.get('bairro'),
                'cidade': registro.get('cidade'),
                'referencia': registro.get('referencia'),
                'data_abertura': data_abertura,
                'data_agenda': data_agenda,
                'data_execucao': data_execucao,
                'data_fechamento': data_fechamento,
                'data_prazo_limite': data_prazo_limite,
                'valor_total': valor_total,
                'valor_comissao': valor_comissao,
            }
            
            # Criar ou atualizar registro
            os_obj, created = OrdemServicoIxc.objects.update_or_create(
                id_ixc=id_ixc,
                defaults=dados_os
            )
            
            return os_obj, created
            
        except Exception as e:
            print(f"Erro ao processar registro OS: {e}")
            return None
    
    def _converter_data(self, data_str):
        """Converte string de data do IXC para datetime"""
        if not data_str or data_str in ['', '0000-00-00', '0000-00-00 00:00:00']:
            return None
        
        try:
            # Tenta formatos comuns do IXC
            formatos = ['%Y-%m-%d %H:%M:%S', '%Y-%m-%d', '%d/%m/%Y %H:%M:%S', '%d/%m/%Y']
            for formato in formatos:
                try:
                    return datetime.strptime(data_str, formato)
                except ValueError:
                    continue
            
            print(f"Formato de data não reconhecido: {data_str}")
            return None
            
        except Exception as e:
            print(f"Erro ao converter data {data_str}: {e}")
            return None
    
    def _converter_valor(self, valor_str):
        """Converte string de valor do IXC para decimal"""
        if not valor_str or valor_str == '':
            return None
        
        try:
            # Remove caracteres não numéricos exceto vírgula e ponto
            valor_limpo = str(valor_str).replace(',', '.').replace(' ', '')
            return float(valor_limpo) if valor_limpo else None
        except (ValueError, TypeError):
            return None
    
    def _converter_int(self, valor):
        """Converte valor para int ou retorna None"""
        if not valor or valor == '':
            return None
        
        try:
            return int(valor)
        except (ValueError, TypeError):
            return None
    
    def listar_assuntos(self, page=1, rp=100, incluir_inativos=True):
        """
        Lista todos os assuntos de OS do IXC
        """
        try:
            if incluir_inativos:
                # Remover filtro de ID para pegar todos os registros
                payload = {
                    'page': str(page),
                    'rp': str(rp),
                    'sortname': 'su_oss_assunto.id',
                    'sortorder': 'asc'
                }
            else:
                payload = {
                    'qtype': 'su_oss_assunto.id',
                    'query': '0',
                    'oper': '>',
                    'page': str(page),
                    'rp': str(rp),
                    'sortname': 'su_oss_assunto.id',
                    'sortorder': 'asc'
                }
            
            headers = self.headers.copy()
            headers['ixcsoft'] = 'listar'
            
            response = requests.post(self.subjects_url, data=payload, headers=headers, timeout=30, verify=False)
            
            if response.status_code == 200:
                data = response.json()
                print(f"Assuntos obtidos: {data.get('total', 0)} registros")
                return data
            else:
                print(f"Erro ao listar assuntos: Status {response.status_code}")
                return None
                
        except Exception as e:
            print(f"Erro ao listar assuntos: {e}")
            return None
    
    def get_all_subjects(self):
        """
        Obtém todos os assuntos e cria um dicionário ID -> Nome
        Usa cache para evitar múltiplas consultas
        Inclui mapeamento manual para assuntos que não aparecem na API
        """
        # Verifica cache primeiro
        cache_key = 'ixc_subjects_cache'
        cached_subjects = cache.get(cache_key)
        
        if cached_subjects:
            print("Usando assuntos do cache")
            return cached_subjects
        
        # Se não tem cache, busca da API
        subjects_dict = {}
        page = 1
        
        try:
            while True:
                response = self.listar_assuntos(page=page, rp=100, incluir_inativos=True)
                if not response or not response.get('registros'):
                    break
                
                registros = response.get('registros', [])
                for assunto in registros:
                    id_assunto = assunto.get('id')
                    nome_assunto = assunto.get('assunto', '')
                    ativo = assunto.get('ativo', 'S')
                    
                    # Incluir todos os assuntos, mesmo inativos (útil para histórico)
                    if id_assunto and nome_assunto:
                        subjects_dict[str(id_assunto)] = nome_assunto
                        if ativo != 'S':
                            print(f"   Incluindo assunto inativo: ID {id_assunto} - {nome_assunto}")
                
                # Verifica se há mais páginas
                total = int(response.get('total', 0))
                registros_processados = page * 100
                
                if registros_processados >= total:
                    break
                    
                page += 1
            
            # Adicionar mapeamento manual para assuntos que não aparecem na API
            # Estes foram identificados como existentes no IXC mas não retornados pela API
            manual_subjects = {
                '1': 'Instalação',
                '2': 'Instabilidade',
                '3': 'Mudança de endereço',
                '4': 'Troca de equipamento de luga',
                '5': 'Problemas no Wi-Fi'
            }
            
            # Adicionar assuntos manuais que não estão na API
            for id_manual, nome_manual in manual_subjects.items():
                if id_manual not in subjects_dict:
                    subjects_dict[id_manual] = nome_manual
                    print(f"   Adicionado assunto manual: ID {id_manual} - {nome_manual}")
            
            # Salva no cache por 1 hora
            cache.set(cache_key, subjects_dict, 3600)
            print(f"Cache de assuntos atualizado: {len(subjects_dict)} assuntos (incluindo manuais)")
            
            return subjects_dict
            
        except Exception as e:
            print(f"Erro ao obter todos os assuntos: {e}")
            return {}
    
    def get_subject_name(self, subject_id):
        """
        Obtém o nome de um assunto específico pelo ID
        """
        if not subject_id:
            return None
            
        subjects = self.get_all_subjects()
        return subjects.get(str(subject_id))
    
    def atualizar_assuntos_os_vazios(self):
        """
        Atualiza OS que têm id_assunto mas assunto_nome vazio
        """
        from .models import OrdemServicoIxc
        
        print("Atualizando assuntos de OS vazios...")
        
        # Buscar OS com id_assunto preenchido mas assunto_nome vazio
        os_vazias = OrdemServicoIxc.objects.filter(
            id_assunto__isnull=False,
            assunto_nome__isnull=True
        ) | OrdemServicoIxc.objects.filter(
            id_assunto__isnull=False,
            assunto_nome=''
        )
        
        print(f"Encontradas {os_vazias.count()} OS com assuntos vazios")
        
        if os_vazias.count() == 0:
            return True
        
        # Obter todos os assuntos
        subjects = self.get_all_subjects()
        
        if not subjects:
            print("Nenhum assunto encontrado para atualização")
            return False
        
        # Atualizar OS
        atualizadas = 0
        
        for os_obj in os_vazias:
            if os_obj.id_assunto:
                subject_name = subjects.get(str(os_obj.id_assunto))
                if subject_name:
                    os_obj.assunto_nome = subject_name
                    os_obj.save(update_fields=['assunto_nome'])
                    atualizadas += 1
        
        print(f"Atualizadas {atualizadas} OS com nomes de assuntos")
        return True