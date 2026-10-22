"""Marcação ONU.cliente_fibra (olt/client_utils.marcar_clientes_fibra) e o diagnóstico."""
from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from olt.client_utils import marcar_clientes_fibra
from olt.models import ONU, ClienteFibraIxc, Olt


class ClienteFibraTests(TestCase):

    def setUp(self):
        self.olt = Olt.objects.create(name='OLT', host='10.0.0.1', username='u', password='p')

        def onu(pos, serial, mac='', oper='up', cf=False):
            return ONU.objects.create(olt=self.olt, pon='1/1/1/1', position=pos, serial=serial, mac=mac,
                                      oper_state=oper, desc1='', desc2='', cliente_fibra=cf)

        self.ativo = onu(1, 'ALCL:00000001', mac='aa:bb:cc:dd:ee:01')
        self.saiu = onu(2, 'ALCL:00000002', cf=True)          # registro apagado no IXC
        self.formato = onu(3, 'ALCL:00000003')                # IXC sem ":" e minúsculo
        self.nenhum = onu(4, 'ALCL:00000004', oper='down')
        ClienteFibraIxc.objects.create(mac='ALCL:00000001', nome='A', login='a')
        ClienteFibraIxc.objects.create(mac='ALCL:00000002', nome='B', login='b', is_active=False)
        ClienteFibraIxc.objects.create(mac='alcl00000003', nome='C', login='c')
        ClienteFibraIxc.objects.create(mac='ALCL:00000009', nome='D', login='d')

    def test_so_registro_ativo_marca(self):
        marcar_clientes_fibra()
        marcado = dict(ONU.objects.values_list('serial', 'cliente_fibra'))
        self.assertEqual(marcado, {'ALCL:00000001': True, 'ALCL:00000002': False,
                                   'ALCL:00000003': False, 'ALCL:00000004': False})
        self.saiu.update_cliente_fibra_status()
        self.saiu.refresh_from_db()
        self.assertFalse(self.saiu.cliente_fibra)

    def test_diagnostico(self):
        out = StringIO()
        call_command('diagnostico_onus', stdout=out)
        texto = out.getvalue()
        self.assertIn('ignorando maiúsculas/":" (diferença de formato, falso "Não"): 1', texto)
        self.assertIn('ALCL:00000003', texto)
        self.assertIn('Marcação desatualizada', texto)
        self.assertIn('sem ONU em nenhuma OLT do sistema: 1', texto)
        self.assertIn('Sem MAC e ONLINE (deveria ter MAC na tabela da OLT): 2', texto)
