"""Cadastro no IXC das caixas só do projeto (olt/ixc_caixas.py). IXC simulado."""
import json
from unittest import mock

from django.contrib.auth.models import User
from rest_framework.test import APITestCase

from olt.models import CadastroCaixaIxc, Cto, Vistoria, VistoriaPorta

AMBIENTE = {'IXC_HOST': 'ixc.exemplo.com.br', 'IXC_TOKEN': 't', 'IXC_PERMITIR_ESCRITA': 'true'}
MODELO = {'codigo_estilo_caixa': '50r7nh0u', 'id': '1', 'status': 'A', 'id_transmissor': '1', 'id_interface': '',
          'descricao': 'CA_008', 'id_projeto': '1', 'id_tecnologia': '', 'capacidade': '8',
          'latitude': '-22.2762', 'longitude': '-46.1701', 'obs_caixa_ftth': '', 'cep': '', 'endereco': '',
          'numero': '', 'bairro': '', 'id_cidade': '3', 'ultima_atualizacao': '2020-12-15 11:35:29', 'idx': '',
          'tipo': 'P'}


def resposta(dados, code=200):
    r = mock.Mock(status_code=code, content=b'x', text=json.dumps(dados))
    r.json.return_value = dados
    r.raise_for_status = mock.Mock()
    return r


class IxcFake:
    def __init__(self):
        self.tabela = {'1': dict(MODELO)}
        self.posts = []

    def post(self, url, data, headers, timeout):
        corpo = json.loads(data)
        if headers.get('ixcsoft') == 'listar':
            campo = corpo['qtype'].split('.')[1]
            achados = [r for r in self.tabela.values() if str(r.get(campo)) == str(corpo['query'])]
            return resposta({'total': str(len(achados)), 'registros': achados})
        self.posts.append(corpo)
        novo_id = str(100 + len(self.posts))
        self.tabela[novo_id] = {**corpo, 'id': novo_id}
        return resposta({'type': 'success', 'message': 'Registro inserido com sucesso!', 'id': novo_id})


@mock.patch.dict('os.environ', AMBIENTE)
class CadastroCaixaTests(APITestCase):

    def setUp(self):
        self.client.force_authenticate(User.objects.create_user('admin', password='p', is_staff=True))
        Cto.objects.create(ixc_id='1', descricao='CA_008', latitude=-22.2762, longitude=-46.1701, id_projeto='1')
        self.nova = Cto.objects.create(origem='kmz', descricao='CA_300', kmz_nome='CA_300', kmz_portas=16,
                                       latitude=-22.2790, longitude=-46.1710, ramal='Ramal 01')
        self.fake = IxcFake()

    def chamar(self, url, dados):
        with mock.patch('olt.ixc_caixas.requests.post', side_effect=self.fake.post):
            return self.client.post(url, dados, format='json')

    def test_lista(self):
        r = self.client.get('/api/ctos/fora-do-ixc/').json()
        c = r['caixas'][0]
        self.assertEqual((c['descricao'], c['portas'], c['modelo']['descricao'], c['duplicada']), ('CA_300', 16, 'CA_008', None))
        self.assertTrue(r['pode_cadastrar'])

    def test_cadastra_copiando_o_modelo(self):
        v = Vistoria.objects.create(cto=self.nova)
        VistoriaPorta.objects.create(vistoria=v, porta=1, resultado='cliente', serial='S1')
        r = self.chamar('/api/ctos/fora-do-ixc/cadastrar/', {'itens': [{'cto': self.nova.id, 'descricao': 'CA_300'}]})
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(r.data['resultados'][0]['status'], 'ok', r.data)
        enviado = self.fake.posts[0]
        self.assertEqual((enviado['id_projeto'], enviado['id_cidade'], enviado['tipo'], enviado['capacidade']),
                         ('1', '3', 'P', '16'))
        self.assertNotIn('id', enviado)
        self.nova.refresh_from_db()
        self.assertEqual((self.nova.ixc_id, self.nova.origem), ('101', 'ixc'))
        self.assertEqual(Vistoria.objects.get().cto_id, self.nova.id)          # vistoria continua na mesma caixa
        self.assertEqual(self.client.get('/api/ctos/fora-do-ixc/').json()['caixas'], [])

    def test_recusa_duplicada_e_sem_nome(self):
        Cto.objects.create(ixc_id='7', descricao='CA_300', latitude=-22.2791, longitude=-46.1712)
        r = self.chamar('/api/ctos/fora-do-ixc/cadastrar/', {'itens': [{'cto': self.nova.id}]})
        self.assertEqual(r.data['resultados'][0]['status'], 'erro')
        self.assertIn('Vincule', r.data['resultados'][0]['mensagem'])
        sem_nome = Cto.objects.create(origem='kmz', descricao='Sem nome (-22.1, -46.1)', latitude=-22.2763,
                                      longitude=-46.1702)
        r = self.chamar('/api/ctos/fora-do-ixc/cadastrar/', {'itens': [{'cto': sem_nome.id}]})
        self.assertIn('nome', r.data['resultados'][0]['mensagem'])
        self.assertEqual(self.fake.posts, [])

    def test_vincular_existente(self):
        copia = Cto.objects.create(ixc_id='7', descricao='CA_300', latitude=-22.2791, longitude=-46.1712, capacidade=8)
        r = self.client.post('/api/ctos/fora-do-ixc/vincular/', {'cto': self.nova.id, 'ixc_cto': copia.id}, format='json')
        self.assertEqual(r.data['status'], 'ok')
        self.nova.refresh_from_db()
        copia.refresh_from_db()
        self.assertEqual((self.nova.ixc_id, self.nova.origem, copia.is_active, copia.ixc_id), ('7', 'ixc', False, None))

    def test_so_staff_e_com_escrita(self):
        self.client.force_authenticate(User.objects.create_user('u', password='p'))
        r = self.client.post('/api/ctos/fora-do-ixc/cadastrar/', {'itens': [{'cto': self.nova.id}]}, format='json')
        self.assertEqual(r.status_code, 403)
        self.assertEqual(CadastroCaixaIxc.objects.count(), 0)
