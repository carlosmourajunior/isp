"""Retenção (olt/retencao.py): cada tipo de dado some no seu prazo, e só ele."""
from datetime import timedelta
from unittest import mock

from django.test import TestCase
from django.utils import timezone

from olt.models import Olt, OltSyslogMessage, OntEvent, OntSnapshot
from olt.retencao import limpar_dados_antigos


class RetencaoTests(TestCase):

    def setUp(self):
        self.agora = timezone.now()
        self.olt = Olt.objects.create(name='OLT', host='10.0.0.1', username='u', password='p')

        def evento(tipo, dias):
            return OntEvent.objects.create(olt=self.olt, occurred_at=self.agora - timedelta(days=dias),
                                           pon='1/1/1/1', position=1, event_type=tipo)

        for dias in (2, 10):
            OltSyslogMessage.objects.create(source_ip='10.0.0.1', received_at=self.agora - timedelta(days=dias), raw='x')
            OntSnapshot.objects.create(olt=self.olt, taken_at=self.agora - timedelta(days=dias * 20),
                                       pon='1/1/1/1', position=1, serial='S')
        self.rdi_novo, self.rdi_velho = evento('other', 2), evento('other', 10)
        self.queda_10d, self.queda_velha = evento('inativa', 10), evento('inativa', 200)
        self.gasp_10d = evento('dying_gasp', 10)

    def test_apaga_cada_tipo_no_seu_prazo(self):
        resultado = {d: n for d, _, n in limpar_dados_antigos(agora=self.agora)}

        self.assertEqual(OltSyslogMessage.objects.count(), 1)           # 10 dias > 7
        restantes = set(OntEvent.objects.values_list('id', flat=True))
        self.assertEqual(restantes, {self.rdi_novo.id, self.queda_10d.id, self.gasp_10d.id})
        self.assertEqual(OntSnapshot.objects.count(), 1)                # 200 dias > 180, 40 dias fica
        self.assertEqual(resultado['eventos "outro" (RDI, nível de sinal)'], 1)

    def test_dry_run_nao_apaga(self):
        limpar_dados_antigos(agora=self.agora, dry_run=True)
        self.assertEqual(OntEvent.objects.count(), 5)

    @mock.patch.dict('os.environ', {'RETENCAO_EVENTOS_QUEDA_DIAS': '5'})
    def test_prazo_configuravel(self):
        limpar_dados_antigos(agora=self.agora)
        self.assertFalse(OntEvent.objects.filter(id=self.queda_10d.id).exists())
