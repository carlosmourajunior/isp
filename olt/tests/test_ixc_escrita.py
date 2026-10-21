"""
Correção da CTO no IXC (olt/ixc_escrita.py). O IXC é simulado: nenhum teste
escreve num IXC de verdade.
"""
import json
from unittest import mock

from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from olt.models import ClienteFibraIxc, CorrecaoIxc, Cto

REGISTRO = {'id': '555', 'mac': 'ALCL:B3FD63A5', 'id_caixa_ftth': '97', 'login': 'fulano',
            'id_contrato': '2639', 'senha': 'x', 'ultima_atualizacao': '2026-01-01 10:00:00'}

AMBIENTE = {'IXC_HOST': 'ixc.exemplo.com.br', 'IXC_TOKEN': 't', 'IXC_PERMITIR_ESCRITA': 'true'}


def resposta(dados, status_code=200):
    r = mock.Mock(status_code=status_code, content=b'x', text=json.dumps(dados))
    r.json.return_value = dados
    r.raise_for_status = mock.Mock()
    return r


class IxcFake:
    """Simula listar (POST) e alterar (PUT) do IXC guardando o registro em memória."""

    def __init__(self, registro, put_resposta=None, mexe_em=None):
        self.registro = dict(registro)
        self.put_resposta = put_resposta or {'type': 'success', 'message': 'Registro atualizado com sucesso!'}
        self.mexe_em = mexe_em or {}
        self.puts = []

    def post(self, url, data, headers, timeout):
        return resposta({'total': '1', 'registros': [dict(self.registro)]})

    def put(self, url, data, headers, timeout):
        enviado = json.loads(data)
        self.puts.append((url, enviado))
        if self.put_resposta.get('type') == 'success':
            self.registro = {**enviado, **self.mexe_em, 'ultima_atualizacao': '2026-10-21 10:40:00'}
        return resposta(self.put_resposta)


@mock.patch.dict('os.environ', AMBIENTE)
class CorrecaoIxcApiTests(APITestCase):

    def setUp(self):
        self.admin = User.objects.create_user('admin', password='p', is_staff=True)
        self.client.force_authenticate(self.admin)
        self.cto = Cto.objects.create(ixc_id='96', descricao='CA_096')
        ClienteFibraIxc.objects.create(mac='ALCL:B3FD63A5', nome='Fulano', id_caixa_ftth='97')
        self.url = reverse('api:vistoria_aplicar_correcao')

    def aplicar(self, fake, cto=None):
        with mock.patch('olt.ixc_escrita.requests.post', side_effect=fake.post), \
                mock.patch('olt.ixc_escrita.requests.put', side_effect=fake.put):
            return self.client.post(self.url, {'serial': 'ALCL:B3FD63A5', 'cto': (cto or self.cto).id})

    def test_corrige_enviando_registro_inteiro(self):
        fake = IxcFake(REGISTRO)
        r = self.aplicar(fake)
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data['status'], 'ok')
        url, enviado = fake.puts[0]
        self.assertTrue(url.endswith('/radpop_radio_cliente_fibra/555'))
        # Todos os campos de volta, só a caixa trocada
        self.assertEqual(enviado, {**REGISTRO, 'id_caixa_ftth': '96'})
        self.assertEqual(ClienteFibraIxc.objects.get().id_caixa_ftth, '96')
        c = CorrecaoIxc.objects.get()
        self.assertEqual((c.caixa_antes, c.usuario, c.registro_antes['login']), ('97', 'admin', 'fulano'))

    def test_outro_campo_alterado_vira_alerta(self):
        r = self.aplicar(IxcFake(REGISTRO, mexe_em={'senha': ''}))
        self.assertEqual(r.data['status'], 'alerta')
        self.assertEqual(r.data['outros_campos_alterados'], ['senha'])

    def test_ixc_recusa(self):
        r = self.aplicar(IxcFake(REGISTRO, put_resposta={'type': 'error', 'message': 'Sem permissão'}))
        self.assertEqual(r.status_code, status.HTTP_502_BAD_GATEWAY)
        self.assertIn('Sem permissão', r.data['mensagem'])
        self.assertEqual(ClienteFibraIxc.objects.get().id_caixa_ftth, '97')

    def test_cto_fora_do_ixc(self):
        so_kmz = Cto.objects.create(ixc_id=None, origem='kmz', descricao='CTO MC-01')
        fake = IxcFake(REGISTRO)
        r = self.aplicar(fake, cto=so_kmz)
        self.assertEqual(r.data['status'], 'erro')
        self.assertEqual(fake.puts, [])

    def test_ja_estava_certo_nao_envia(self):
        fake = IxcFake({**REGISTRO, 'id_caixa_ftth': '96'})
        r = self.aplicar(fake)
        self.assertEqual(r.data['status'], 'ok')
        self.assertEqual(fake.puts, [])

    def test_so_staff(self):
        self.client.force_authenticate(User.objects.create_user('bancada', password='p'))
        r = self.aplicar(IxcFake(REGISTRO))
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)

    @mock.patch.dict('os.environ', {'IXC_PERMITIR_ESCRITA': 'false'})
    def test_desligada_por_padrao(self):
        fake = IxcFake(REGISTRO)
        r = self.aplicar(fake)
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(fake.puts, [])
