"""
Testes do cliente do webservice do IXC (olt/client_utils.py). Não batem no
IXC de verdade - o requests.post é mockado - mas travam o contrato da
requisição (URL, headers, payload) e o comportamento em caso de falha, que
hoje é a parte sem nenhuma cobertura do sistema.
"""
import json
from unittest import mock

from django.test import SimpleTestCase
import requests

from olt.client_utils import search_ixc_page


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
