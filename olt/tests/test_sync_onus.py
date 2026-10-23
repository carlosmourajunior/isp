"""Sincronização das ONUs sem apagar tudo (olt/utils.reconciliar_pon / update_mac) e
atualização individual (/api/onus/<pk>/atualizar/). A OLT e o IXC são simulados."""
from unittest import mock

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APITestCase

from olt.client_utils import atualizar_cliente_fibra_do_ixc
from olt.models import ONU, ClienteFibraIxc, Olt, OntSnapshot
from olt.utils import contagem_onts, olt_connector

PON = '1/1/1/14'


def linha(pos, serial, oper='up', sinal='-23.0'):
    return (f"{PON}   {PON}/{pos}    {serial} up       {oper}       {sinal}       0.5           "
            f"desc{pos}                                        desc{pos}                                        undefined")


def saida(*linhas, count=None):
    corpo = '\n'.join(linhas)
    n = len(linhas) if count is None else count
    return f"{corpo}\n-----\nont count : {n}\n" if count != 'sem' else corpo


class ReconciliarPonTests(TestCase):

    def setUp(self):
        self.olt = Olt.objects.create(name='OLT', host='10.0.0.1', username='u', password='p')
        self.c = olt_connector(self.olt)
        self.a = ONU.objects.create(olt=self.olt, pon=PON, position=90, serial='RCMG:00000090', mac='aa:aa:aa:aa:aa:90',
                                    oper_state='up', desc1='', desc2='')
        self.b = ONU.objects.create(olt=self.olt, pon=PON, position=91, serial='ALCL:00000091', mac='aa:aa:aa:aa:aa:91',
                                    oper_state='up', desc1='', desc2='')
        ClienteFibraIxc.objects.create(mac='TPLG:00000092', nome='Nova', login='nova')

    def sync(self, texto):
        net = mock.Mock()
        net.send_command.return_value = texto
        return self.c._sync_pon(net, PON)

    def test_contagem(self):
        self.assertEqual(contagem_onts('xx\nont count : 27\n'), 27)
        self.assertIsNone(contagem_onts('Error : invalid parameter'))

    def test_atualiza_no_lugar_cria_e_remove(self):
        r = self.sync(saida(linha(90, 'RCMG:00000090', sinal='-25.1'), linha(92, 'TPLG:00000092')))
        self.assertEqual((r['criadas'], r['atualizadas'], r['removidas']), (1, 1, 1))
        a = ONU.objects.get(position=90)
        self.assertEqual((a.id, a.mac, a.olt_rx_sig), (self.a.id, 'aa:aa:aa:aa:aa:90', -25.1))  # id e MAC mantidos
        self.assertFalse(ONU.objects.filter(position=91).exists())
        self.assertTrue(ONU.objects.get(position=92).cliente_fibra)
        self.assertEqual(OntSnapshot.objects.count(), 2)

    def test_outra_onu_na_mesma_posicao_zera_mac(self):
        self.sync(saida(linha(90, 'HWTC:99999999'), linha(91, 'ALCL:00000091')))
        a = ONU.objects.get(position=90)
        self.assertEqual((a.id, a.serial, a.mac), (self.a.id, 'HWTC:99999999', ''))

    def test_saida_vazia_ou_com_erro_nao_apaga(self):
        r = self.sync('Error : connection lost')
        self.assertFalse(r['lida'])
        self.assertEqual(ONU.objects.count(), 2)

    def test_leitura_incompleta_nao_remove(self):
        r = self.sync(saida(linha(90, 'RCMG:00000090'), count=2))
        self.assertEqual(r['removidas'], 0)
        self.assertIn('incompleta', r['aviso'])
        self.assertEqual(ONU.objects.count(), 2)

    def test_pon_vazia_de_verdade_remove(self):
        r = self.sync('ont count : 0\n')
        self.assertEqual(r['removidas'], 2)

    def test_update_mac(self):
        fdb = (f"{PON}/90/14/1   100   aa:bb:cc:00:00:90   0   learned   00:01:00\n")
        self.c.update_mac(fdb)
        self.assertEqual(ONU.objects.get(position=90).mac, 'aa:bb:cc:00:00:90')
        self.assertEqual(ONU.objects.get(position=91).mac, '')        # não apareceu: offline
        self.c.update_mac('')                                          # leitura vazia: não mexe
        self.assertEqual(ONU.objects.get(position=90).mac, 'aa:bb:cc:00:00:90')


class AtualizarUmaOnuTests(APITestCase):

    def setUp(self):
        self.client.force_authenticate(User.objects.create_user('u', password='p'))
        self.olt = Olt.objects.create(name='OLT', host='10.0.0.1', username='u', password='p')
        self.onu = ONU.objects.create(olt=self.olt, pon=PON, position=90, serial='RCMG:00000090', mac='',
                                      oper_state='down', desc1='', desc2='')

    def test_da_olt(self):
        net = mock.Mock()
        net.send_command.side_effect = lambda cmd, **kw: (
            saida(linha(90, 'RCMG:00000090')) if 'status pon' in cmd
            else f"{PON}/90/14/1   100   aa:bb:cc:00:00:90   0   learned   00:01:00\n")
        with mock.patch.object(olt_connector, 'connect', return_value=net), \
                mock.patch.object(olt_connector, 'disconnect'):
            r = self.client.post(f'/api/onus/{self.onu.id}/atualizar/', {'fonte': 'olt'}, format='json')
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual((r.data['onu']['oper_state'], r.data['onu']['mac']), ('up', 'aa:bb:cc:00:00:90'))
        self.assertIn('MAC lido: aa:bb:cc:00:00:90.', r.data['mensagens'])

    def test_do_ixc(self):
        respostas = {
            'radpop_radio_cliente_fibra': [{'id': '1', 'mac': 'RCMG:00000090', 'nome': 'fulano', 'id_contrato': '7',
                                            'id_caixa_ftth': '96'}],
            'cliente_contrato': [{'id': '7', 'id_cliente': '3', 'status': 'A', 'status_internet': 'A'}],
            'cliente': [{'id': '3', 'razao': 'Fulano de Tal', 'endereco': 'Rua A', 'numero': '10'}],
        }
        with mock.patch('olt.client_utils._ixc_buscar', side_effect=lambda rec, campo, valor: respostas[rec]):
            r = self.client.post(f'/api/onus/{self.onu.id}/atualizar/', {'fonte': 'ixc'}, format='json')
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.data['onu']['cliente_fibra'])
        c = ClienteFibraIxc.objects.get()
        self.assertEqual((c.nome, c.login, c.id_caixa_ftth, c.status_contrato), ('Fulano de Tal', 'fulano', '96', 'A'))

    def test_do_ixc_nao_encontrado_desmarca(self):
        ClienteFibraIxc.objects.create(mac='RCMG:00000090', nome='X')
        ONU.objects.filter(pk=self.onu.pk).update(cliente_fibra=True)
        with mock.patch('olt.client_utils._ixc_buscar', return_value=[]):
            resultado = atualizar_cliente_fibra_do_ixc('RCMG:00000090')
        self.assertFalse(resultado['encontrado'])
        self.assertFalse(ONU.objects.get().cliente_fibra)
        self.assertFalse(ClienteFibraIxc.objects.get().is_active)
