"""
Testes de regressão para os parsers de texto que interpretam a saída de
comandos da OLT Nokia (netmiko/CLI). Não há API estruturada do lado da OLT:
qualquer mudança de firmware que altere o formato dessas linhas quebra o
parser sem avisar ninguém - esses testes existem para que a quebra apareça
aqui, e não como dado silenciosamente errado em produção.

As linhas de exemplo usadas abaixo são as mesmas que já estavam documentadas
como comentário dentro de olt/utils.py (create_dict_from_result.__doc__).
"""
from django.test import SimpleTestCase

from olt.models import Olt
from olt.utils import create_dict_from_result, extract_olt_info, build_connect_kwargs, parse_optics_output


class CreateDictFromResultTests(SimpleTestCase):
    """`show equipment ont status pon ...` -> lista de dicts por ONU."""

    def test_onu_online_com_cliente(self):
        linha = (
            "1/1/1/14   1/1/1/14/90    RCMG:3A88390E up       up       "
            "-23.0       0.5           tomazpaiva                                        "
            "tomazpaiva                                        undefined"
        )

        resultado = create_dict_from_result(linha)

        self.assertEqual(len(resultado), 1)
        onu = resultado[0]
        self.assertEqual(onu['pon'], '1/1/1/14')
        self.assertEqual(onu['position'], '90')
        self.assertEqual(onu['sernum'], 'RCMG:3A88390E')
        self.assertEqual(onu['admin_status'], 'up')
        self.assertEqual(onu['oper_status'], 'up')
        self.assertEqual(onu['olt_rx_sig'], '-23.0')
        self.assertEqual(onu['ont_olt'], '0.5')
        self.assertEqual(onu['desc1'], 'tomazpaiva')
        self.assertEqual(onu['desc2'], 'tomazpaiva')

    def test_onu_offline_sinal_invalid(self):
        """Quando a ONU está down, a OLT reporta sinal como a string 'invalid', não um número."""
        linha = (
            "1/1/1/14   1/1/1/14/96    RCMG:19897186 up       down     "
            "invalid     invalid       sedeprefeitura02                                  "
            "sedeprefeitura02                                  undefined"
        )

        resultado = create_dict_from_result(linha)

        self.assertEqual(len(resultado), 1)
        onu = resultado[0]
        self.assertEqual(onu['position'], '96')
        self.assertEqual(onu['admin_status'], 'up')
        self.assertEqual(onu['oper_status'], 'down')
        self.assertEqual(onu['olt_rx_sig'], 'invalid')
        self.assertEqual(onu['ont_olt'], 'invalid')
        self.assertEqual(onu['desc1'], 'sedeprefeitura02')

    def test_multiplas_linhas_geram_multiplos_registros(self):
        saida = "\n".join([
            "1/1/1/14   1/1/1/14/90    RCMG:3A88390E up       up       -23.0       0.5           tomazpaiva                                        tomazpaiva                                        undefined",
            "1/1/1/14   1/1/1/14/91    ALCL:B3FD63A5 up       up       -22.3       0.8           vitorfrancisco                                    vitorfrancisco                                    undefined",
        ])

        resultado = create_dict_from_result(saida)

        self.assertEqual(len(resultado), 2)
        self.assertEqual([onu['position'] for onu in resultado], ['90', '91'])
        self.assertEqual(resultado[1]['sernum'], 'ALCL:B3FD63A5')

    def test_linha_sem_correspondencia_nao_gera_registro(self):
        self.assertEqual(create_dict_from_result("cabeçalho qualquer sem PON"), [])
        self.assertEqual(create_dict_from_result(""), [])


class ExtractOltInfoTests(SimpleTestCase):
    """`show vlan bridge-port-fdb` -> PON/porta/MAC de uma linha da tabela FDB."""

    def test_extrai_pon_porta_e_mac(self):
        linha = "1/1/1/14/90/1234    5   aa:bb:cc:dd:ee:ff   learned"

        resultado = extract_olt_info(linha)

        self.assertEqual(resultado, {
            'pon': '1/1/1/14',
            'port': '90',
            'mac': 'aa:bb:cc:dd:ee:ff',
        })

    def test_linha_sem_padrao_retorna_none(self):
        self.assertIsNone(extract_olt_info("linha qualquer sem esse formato"))


class BuildConnectKwargsTests(SimpleTestCase):
    """kwargs de conexão SSH (netmiko) montados a partir de um registro Olt.
    Usa uma instância em memória (não salva no banco) - build_connect_kwargs
    só lê atributos do objeto, então SimpleTestCase (sem acesso a banco) basta."""

    def _olt(self, **overrides):
        defaults = dict(
            name='OLT Teste', device_type='alcatel_aos', host='192.168.1.1',
            username='admin', password='segredo', ssh_port=22,
            global_delay_factor=2, verbose=False,
        )
        defaults.update(overrides)
        return Olt(**defaults)

    def test_monta_kwargs_a_partir_da_olt(self):
        kwargs = build_connect_kwargs(self._olt())
        self.assertEqual(kwargs['device_type'], 'alcatel_aos')
        self.assertEqual(kwargs['host'], '192.168.1.1')
        self.assertEqual(kwargs['username'], 'admin')
        self.assertEqual(kwargs['password'], 'segredo')
        self.assertEqual(kwargs['port'], 22)
        self.assertEqual(kwargs['global_delay_factor'], 2)
        self.assertFalse(kwargs['verbose'])
        self.assertFalse(kwargs['ssh_strict'])

    def test_nunca_inclui_argumentos_incompativeis_com_paramiko_antigo(self):
        kwargs = build_connect_kwargs(self._olt(), extra={
            'allow_agent': True, 'look_for_keys': True, 'use_keys': True,
        })
        for chave_proibida in ('allow_agent', 'look_for_keys', 'use_keys'):
            self.assertNotIn(chave_proibida, kwargs)


class ParseOpticsOutputTests(SimpleTestCase):
    """`show equipment ont optics` -> sinal RX/TX da ONU por (pon, posição)."""

    def test_onu_online_e_offline(self):
        saida = (
            "1/1/1/1/1      -22.220         2.598           41.160          3.22        19608.0         -23.5\n"
            "1/1/1/1/3      unknown         unknown         unknown         unknown     unknown         invalid\n"
            "1/1/3/12/14    -18.922         2.080           34.809          3.22        11450.0         -21.6\n"
            "optics count : 378\n"
        )

        resultado = parse_optics_output(saida)

        self.assertEqual(resultado[('1/1/1/1', 1)], (-22.22, 2.598))
        self.assertEqual(resultado[('1/1/1/1', 3)], (None, None))
        self.assertEqual(resultado[('1/1/3/12', 14)], (-18.922, 2.08))
        self.assertEqual(len(resultado), 3)
