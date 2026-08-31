"""
Testes do cliente do webservice do IXC (olt/client_utils.py). Não batem no
IXC de verdade - o requests.post é mockado - mas travam o contrato da
requisição (URL, headers, payload) e o comportamento em caso de falha, que
hoje é a parte sem nenhuma cobertura do sistema.
"""
import json
from unittest import mock

from django.test import SimpleTestCase, TestCase
import requests

from olt.client_utils import search_ixc_page, _formata_endereco, _build_cliente_lookup, update_clientes
from olt.models import ClienteFibraIxc


def _mock_response(status_code=200, json_data=None, text=''):
    response = mock.Mock()
    response.status_code = status_code
    response.json.return_value = json_data or {}
    response.text = text
    return response


@mock.patch.dict('os.environ', {'IXC_HOST': 'ixc.exemplo.com.br', 'IXC_TOKEN': 'token-de-teste'})
class SearchIxcPageTests(SimpleTestCase):

    @mock.patch('olt.client_utils.requests.post')
    def test_monta_url_headers_e_payload_corretos(self, mock_post):
        mock_post.return_value = _mock_response(200, {'total': '0', 'registros': []})

        search_ixc_page(3)

        self.assertEqual(mock_post.call_count, 1)
        args, kwargs = mock_post.call_args
        url = args[0] if args else kwargs.get('url')
        self.assertEqual(url, 'https://ixc.exemplo.com.br/webservice/v1/radpop_radio_cliente_fibra')

        self.assertEqual(kwargs['timeout'], 30)

        headers = kwargs['headers']
        self.assertEqual(headers['ixcsoft'], 'listar')
        self.assertTrue(headers['Authorization'].startswith('Basic '))

        payload = json.loads(kwargs['data'])
        self.assertEqual(payload['page'], 3)
        self.assertEqual(payload['qtype'], 'radpop_radio_cliente_fibra.id')
        self.assertEqual(payload['rp'], '100')

    @mock.patch('olt.client_utils.requests.post')
    def test_retorna_a_response_recebida(self, mock_post):
        fake_response = _mock_response(200, {'total': '1', 'registros': []})
        mock_post.return_value = fake_response

        resultado = search_ixc_page(1)

        self.assertIs(resultado, fake_response)

    @mock.patch('olt.client_utils.requests.post')
    def test_falha_de_rede_e_logada_e_repropagada(self, mock_post):
        mock_post.side_effect = requests.exceptions.ConnectionError('IXC fora do ar')

        with self.assertLogs('olt.connector', level='ERROR') as logs:
            with self.assertRaises(requests.exceptions.ConnectionError):
                search_ixc_page(1)

        self.assertTrue(any('IXC' in msg for msg in logs.output))


class FormataEnderecoTests(SimpleTestCase):

    def test_descarta_partes_vazias_e_o_placeholder_zero(self):
        self.assertEqual(_formata_endereco('Rua A', '', '0', 'Centro'), 'Rua A, Centro')

    def test_todas_as_partes_vazias_da_string_vazia(self):
        self.assertEqual(_formata_endereco('', '0', ''), '')


def _por_recurso(mapa):
    """Cria um side_effect pra requests.post que responde conforme o recurso na URL (.../webservice/v1/<recurso>)."""
    def side_effect(url, *args, **kwargs):
        recurso = url.rstrip('/').split('/')[-1]
        return _mock_response(200, mapa[recurso])
    return side_effect


@mock.patch.dict('os.environ', {'IXC_HOST': 'ixc.exemplo.com.br', 'IXC_TOKEN': 'token-de-teste'})
class BuildClienteLookupTests(SimpleTestCase):
    """
    Trava a cadeia radpop_radio_cliente_fibra.id_contrato -> cliente_contrato
    -> cliente que resolve o nome/endereço reais do cliente (ver
    olt/models.py ONU.update_cliente_fibra_status para o contexto do porquê
    o "nome" do radpop sozinho não é confiável).
    """

    @mock.patch('olt.client_utils.requests.post')
    def test_monta_nome_e_endereco_reais_a_partir_do_contrato(self, mock_post):
        mock_post.side_effect = _por_recurso({
            'cliente_contrato': {'total': '1', 'registros': [
                {'id': '2639', 'id_cliente': '2469'},
            ]},
            'cliente': {'total': '1', 'registros': [
                {
                    'id': '2469', 'razao': 'Luana Aparecida de Moraes Silva',
                    'endereco': 'Zona Rural', 'numero': 'SN', 'bairro': 'Bogari',
                    'complemento': 'Chácara Rancho Tropeiro', 'cidade': '2331', 'uf': '17',
                },
            ]},
        })

        lookup = _build_cliente_lookup()

        self.assertEqual(lookup, {
            '2639': {
                'nome': 'Luana Aparecida de Moraes Silva',
                'endereco': 'Zona Rural, SN, Chácara Rancho Tropeiro, Bogari',
            }
        })

    @mock.patch('olt.client_utils.requests.post')
    def test_contrato_sem_cliente_correspondente_e_ignorado(self, mock_post):
        mock_post.side_effect = _por_recurso({
            'cliente_contrato': {'total': '1', 'registros': [
                {'id': '999', 'id_cliente': '111'},
            ]},
            'cliente': {'total': '0', 'registros': []},
        })

        self.assertEqual(_build_cliente_lookup(), {})


@mock.patch.dict('os.environ', {'IXC_HOST': 'ixc.exemplo.com.br', 'IXC_TOKEN': 'token-de-teste'})
class UpdateClientesEnriquecimentoTests(TestCase):
    """update_clientes() de ponta a ponta: confirma que o nome/endereço gravados
    em ClienteFibraIxc vêm do cadastro real do cliente, não do login PPPoE/
    endereço vazio que o radpop_radio_cliente_fibra sozinho traria."""

    @mock.patch('olt.client_utils.requests.post')
    def test_usa_nome_e_endereco_do_cliente_quando_disponivel(self, mock_post):
        mock_post.side_effect = _por_recurso({
            'radpop_radio_cliente_fibra': {'total': '1', 'registros': [
                {
                    'mac': 'ALCL:FBCC7D34', 'nome': 'luanamoraes', 'id_contrato': '2639',
                    'latitude': '', 'longitude': '', 'endereco': '', 'numero': '',
                    'bairro': '', 'cidade': '0', 'id_caixa_ftth': '0',
                },
            ]},
            'cliente_contrato': {'total': '1', 'registros': [
                {'id': '2639', 'id_cliente': '2469'},
            ]},
            'cliente': {'total': '1', 'registros': [
                {
                    'id': '2469', 'razao': 'Luana Aparecida de Moraes Silva',
                    'endereco': 'Zona Rural', 'numero': 'SN', 'bairro': 'Bogari',
                    'complemento': 'Chácara Rancho Tropeiro', 'cidade': '2331', 'uf': '17',
                },
            ]},
        })

        update_clientes()

        cliente = ClienteFibraIxc.objects.get(mac='ALCL:FBCC7D34')
        self.assertEqual(cliente.nome, 'Luana Aparecida de Moraes Silva')
        self.assertEqual(cliente.endereco, 'Zona Rural, SN, Chácara Rancho Tropeiro, Bogari')

    @mock.patch('olt.client_utils.requests.post')
    def test_cai_para_dados_do_radpop_quando_nao_ha_contrato_correspondente(self, mock_post):
        mock_post.side_effect = _por_recurso({
            'radpop_radio_cliente_fibra': {'total': '1', 'registros': [
                {
                    'mac': 'HWTC:00000001', 'nome': 'loginqualquer', 'id_contrato': '999999',
                    'latitude': '', 'longitude': '', 'endereco': 'Rua Sem Cadastro', 'numero': '10',
                    'bairro': 'Centro', 'cidade': '0', 'id_caixa_ftth': '0',
                },
            ]},
            'cliente_contrato': {'total': '0', 'registros': []},
            'cliente': {'total': '0', 'registros': []},
        })

        update_clientes()

        cliente = ClienteFibraIxc.objects.get(mac='HWTC:00000001')
        self.assertEqual(cliente.nome, 'loginqualquer')
        self.assertEqual(cliente.endereco, 'Rua Sem Cadastro, 10, Centro')
