"""
Testes de regressão para ONU.update_cliente_fibra_status(). O match já foi
mac==serial AND nome==desc1, e isso descartava vínculos reais: desc1 é um
campo livre digitado na OLT (nome de cliente, modelo do aparelho, ou
literalmente "undefined") que quase nunca bate com o nome cadastrado no
IXC. Hoje o match é só por serial.
"""
from django.test import TestCase

from olt.models import ONU, ClienteFibraIxc


class UpdateClienteFibraStatusTests(TestCase):

    def test_marca_cliente_fibra_mesmo_com_desc1_diferente_do_nome_do_ixc(self):
        ClienteFibraIxc.objects.create(mac='ALCL:FBCC7E40', nome='90e57b10')
        onu = ONU.objects.create(
            pon='1/1/1/1', position=1, serial='ALCL:FBCC7E40', mac='',
            oper_state='up', admin_state='up', desc1='G140W-H',
        )

        onu.update_cliente_fibra_status()

        self.assertTrue(onu.cliente_fibra)

    def test_nao_marca_cliente_fibra_quando_serial_nao_existe_no_ixc(self):
        onu = ONU.objects.create(
            pon='1/1/1/2', position=2, serial='SEM:CADASTRO', mac='',
            oper_state='up', admin_state='up', desc1='qualquercoisa',
        )

        onu.update_cliente_fibra_status()

        self.assertFalse(onu.cliente_fibra)
