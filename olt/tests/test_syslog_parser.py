"""
Testes dos parsers de alarme de ONT.

- parse_ploam_log: amostra REAL de `show alarm log ont-ploam` (release 6.2).
- parse_ont_alarm: mensagens de syslog SINTÉTICAS (formato real ainda não
  capturado), usando os nomes de alarme reais. Substituir pelas reais
  quando as primeiras chegarem em OltSyslogMessage.
"""
from django.test import SimpleTestCase

from olt.syslog_parser import extract_hostname, parse_ont_alarm, parse_ploam_log
from olt.utils import parse_float

PLOAM_LOG_REAL = """
------------------------------------------------------------------------------------------------------------------------------
ont-ploam
------------------------------------------------------------------------------------------------------------------------------
                 index : 3371068                 last-updated-on : 1970-10-07:13:14:37
                   ont : 1/1/2/8/42
------------------------------------------------------------------------------------------------------------------------------
  current alarm status
------------------------------------------------------------------------------------------------------------------------------
    ont-ploam-loss-sig : no                   ont-ploam-loss-ack : no                    ont-ploam-loss-cd : no
ont-ploam-phy-eqpt-err : no               ont-ploam-startup-fail : no                ont-ploam-sig-degrade : no
    ont-ploam-disabled : no                    ont-ploam-err-msg : no                   ont-ploam-inactive : no
    ont-ploam-sig-fail : no                 ont-ploam-dying-gasp : no                 ont-ploam-deact-fail : no
         ont-ploam-oam : no                  ont-ploam-win-drift : no                        ont-ploam-rdi : yes
     ont-ploam-loss-ks : no                  ont-ploam-pwr-burst : no                   ont-ploam-rog-disa : no
  ont-ploam-diff-reach : no                       ont-ploam-looc : no
------------------------------------------------------------------------------------------------------------------------------
ont-ploam
------------------------------------------------------------------------------------------------------------------------------
                 index : 3371069                 last-updated-on : 1970-10-07:13:14:37
                   ont : 1/1/2/8/45
------------------------------------------------------------------------------------------------------------------------------
  current alarm status
------------------------------------------------------------------------------------------------------------------------------
    ont-ploam-loss-sig : no                   ont-ploam-loss-ack : no                    ont-ploam-loss-cd : no
ont-ploam-phy-eqpt-err : no               ont-ploam-startup-fail : no                ont-ploam-sig-degrade : no
    ont-ploam-disabled : no                    ont-ploam-err-msg : no                   ont-ploam-inactive : no
    ont-ploam-sig-fail : no                 ont-ploam-dying-gasp : no                 ont-ploam-deact-fail : no
         ont-ploam-oam : no                  ont-ploam-win-drift : no                        ont-ploam-rdi : no
     ont-ploam-loss-ks : no                  ont-ploam-pwr-burst : no                   ont-ploam-rog-disa : no
  ont-ploam-diff-reach : no                       ont-ploam-looc : no
"""


class ParsePloamLogTests(SimpleTestCase):

    def test_amostra_real(self):
        entradas = parse_ploam_log(PLOAM_LOG_REAL)
        self.assertEqual(len(entradas), 2)
        self.assertEqual(entradas[0]['index'], 3371068)
        self.assertEqual(entradas[0]['pon'], '1/1/2/8')
        self.assertEqual(entradas[0]['position'], 42)
        self.assertEqual(entradas[0]['active'], {'ont-ploam-rdi'})
        self.assertEqual(entradas[1]['position'], 45)
        self.assertEqual(entradas[1]['active'], set())

    def test_bloco_cortado_no_inicio_e_descartado(self):
        cortado = "ont-ploam-loss-sig : yes   ont-ploam-dying-gasp : no\n" + PLOAM_LOG_REAL
        self.assertEqual(len(parse_ploam_log(cortado)), 2)


class ParseOntAlarmTests(SimpleTestCase):

    def test_loss_sig_vira_los(self):
        evento = parse_ont_alarm("<131> ont-ploam ont:1/1/2/8/42 ont-ploam-loss-sig raised")
        self.assertEqual(evento['pon'], '1/1/2/8')
        self.assertEqual(evento['position'], 42)
        self.assertEqual(evento['event_type'], 'los')
        self.assertEqual(evento['alarm_type'], 'ont-ploam-loss-sig')
        self.assertFalse(evento['is_clear'])

    def test_dying_gasp(self):
        evento = parse_ont_alarm("ont 1/1/2/3/7 ont-ploam-dying-gasp")
        self.assertEqual(evento['event_type'], 'dying_gasp')

    def test_clear(self):
        evento = parse_ont_alarm("ont 1/1/1/14/90 ont-ploam-loss-sig cleared")
        self.assertTrue(evento['is_clear'])

    def test_rdi_nao_e_los(self):
        evento = parse_ont_alarm("ont 1/1/2/8/42 ont-ploam-rdi")
        self.assertEqual(evento['event_type'], 'other')

    def test_comando_de_cli_real_e_ignorado(self):
        """Mensagem real recebida da OLT (msg-type cli-config-chgs)."""
        real = ("<142>Oct 19 17:11:00 VIA01_OURO_FINO cli[334]: isadmin@177.22.126.64(5092) : "
                "[Parser, 3561] executeCommand, cmdstr: 'configure system syslog route isp-collector "
                "msg-type cli-config-chgs facility local1 emergency alert critical error warning notice information '")
        self.assertIsNone(parse_ont_alarm(real))

    def test_comando_de_cli_com_caminho_de_ont_e_ignorado(self):
        cmd = ("<142>Oct 19 17:11:00 VIA01_OURO_FINO cli[334]: isadmin@10.0.0.1(5092) : [Parser, 3561] "
               "executeCommand, cmdstr: 'configure equipment ont interface 1/1/2/8/42 admin-state down'")
        self.assertIsNone(parse_ont_alarm(cmd))

    def test_alarme_sem_ont_e_ignorado(self):
        self.assertIsNone(parse_ont_alarm("vlanport alarm on lt:1/1/1"))


class AlarmeRealBordaTests(SimpleTestCase):
    """Mensagens reais da OLT de Borda (VIA01BM), recebidas via syslog msg-type all."""

    TEXTO = ("<136>Oct 8 06:57:04 VIA01BM rOT1[291]: 70/10/08 06:57:04 major alarm occurred for "
             "ont 1/1/2/8/18 (service affecting) : Remote Defect Indication from ONT")
    TL1 = ('<136>Oct 8 06:57:04 VIA01BM rOT1[291]: ** 23442 REPT ALM ONT '
           '"ONT-1-1-2-8-18:MJ,RDI,SA,10-8,6-57-4:\\"Remote Defect Indication from ONT\\","')

    def test_formato_texto_gera_evento(self):
        evento = parse_ont_alarm(self.TEXTO)
        self.assertEqual(evento['pon'], '1/1/2/8')
        self.assertEqual(evento['position'], 18)
        self.assertEqual(evento['event_type'], 'other')
        self.assertEqual(evento['alarm_type'], 'Remote Defect Indication from ONT')
        self.assertFalse(evento['is_clear'])

    def test_formato_tl1_e_ignorado_para_nao_duplicar(self):
        self.assertIsNone(parse_ont_alarm(self.TL1))

    def test_alarme_encerrado(self):
        cleared = self.TEXTO.replace('alarm occurred', 'alarm cleared')
        self.assertTrue(parse_ont_alarm(cleared)['is_clear'])

    def test_perda_de_sinal_no_formato_texto(self):
        los = self.TEXTO.replace('Remote Defect Indication from ONT', 'Loss of signal')
        self.assertEqual(parse_ont_alarm(los)['event_type'], 'los')

    def test_hostname(self):
        self.assertEqual(extract_hostname(self.TEXTO), 'VIA01BM')


class ExtractHostnameTests(SimpleTestCase):

    def test_cabecalho_real(self):
        real = "<142>Oct 19 17:11:00 VIA01_OURO_FINO cli[334]: isadmin@177.22.126.64(5092) : [Parser, 3572] executeCommand end of command"
        self.assertEqual(extract_hostname(real), 'VIA01_OURO_FINO')

    def test_dia_com_um_digito(self):
        self.assertEqual(extract_hostname("<142>Oct  9 07:01:00 VIA01_BORDA eqpt: x"), 'VIA01_BORDA')

    def test_sem_cabecalho(self):
        self.assertEqual(extract_hostname("TESTE ont 1/1/2/8/42 ont-ploam-loss-sig"), '')


class ParseFloatTests(SimpleTestCase):

    def test_numero_e_invalid(self):
        self.assertEqual(parse_float('0.5'), 0.5)
        self.assertIsNone(parse_float('invalid'))
        self.assertIsNone(parse_float(None))
