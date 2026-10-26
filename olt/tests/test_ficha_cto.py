"""Ficha contínua da caixa (olt/ficha_cto.py) e edição pelo painel da CTO."""
from datetime import timedelta

from django.contrib.auth.models import User
from django.core.management import call_command
from django.utils import timezone
from rest_framework.test import APITestCase

from olt.ficha_cto import consolidar
from olt.models import ClienteFibraIxc, Cto, Olt, Vistoria, VistoriaPorta


class FichaTests(APITestCase):

    def setUp(self):
        self.client.force_authenticate(User.objects.create_user('ana', password='p'))
        self.olt = Olt.objects.create(name='OLT', host='10.0.0.1', username='u', password='p')
        self.cto = Cto.objects.create(ixc_id='1', descricao='CA_001', olt=self.olt, kmz_portas=8)
        self.outra = Cto.objects.create(ixc_id='2', descricao='CA_002', olt=self.olt, kmz_portas=8)
        for s in ('S1', 'S2', 'S3'):
            ClienteFibraIxc.objects.create(mac=s, nome=f'Cliente {s}', id_caixa_ftth='1')

    def porta(self, vid, **dados):
        return self.client.post(f'/api/vistorias/{vid}/portas/', dados, format='json')

    def test_segunda_vistoria_continua_a_primeira(self):
        r1 = self.client.post('/api/vistorias/', {'cto': self.cto.id, 'tecnico': 'João'}, format='json')
        self.assertEqual(r1.status_code, 201)
        vid = r1.data['id']
        self.porta(vid, porta=1, resultado='cliente', serial='S1', metodo='etiqueta')
        Vistoria.objects.filter(id=vid).update(finalizada_em=timezone.now())

        r2 = self.client.post('/api/vistorias/', {'cto': self.cto.id, 'tecnico': 'Pedro'}, format='json')
        self.assertEqual(r2.status_code, 200)
        self.assertEqual((r2.data['id'], r2.data['continuacao'], r2.data['registros_anteriores']), (vid, True, 1))
        self.assertIsNone(r2.data['finalizada_em'])
        self.assertEqual(r2.data['tecnico'], 'Pedro')
        d = self.client.get(f'/api/vistorias/{vid}/').data
        self.assertEqual([(p['porta'], p['serial'], p['registrado_por']) for p in d['portas']], [(1, 'S1', 'ana')])
        self.assertEqual(Vistoria.objects.count(), 1)

    def test_consolida_vistorias_antigas(self):
        agora = timezone.now()
        v1 = Vistoria.objects.create(cto=self.cto, olt=self.olt, observacao='primeira')
        v2 = Vistoria.objects.create(cto=self.cto, olt=self.olt, observacao='segunda')
        Vistoria.objects.filter(id=v1.id).update(iniciada_em=agora - timedelta(days=10))

        def reg(v, porta, serial, dias, resultado='cliente'):
            r = VistoriaPorta.objects.create(vistoria=v, porta=porta, resultado=resultado, serial=serial)
            VistoriaPorta.objects.filter(id=r.id).update(registrado_em=agora - timedelta(days=dias))

        reg(v1, 1, 'S1', 10)               # S1 na porta 1...
        reg(v1, 2, 'S2', 10)
        reg(v1, 3, '', 10, 'sem_ont_ativa')
        reg(v2, 4, 'S1', 1)                # ...depois achado na porta 4
        reg(v2, 2, '', 1, 'vazia')         # porta 2 ficou vazia
        reg(v2, None, 'S3', 1)             # S3 sem porta
        ficha = consolidar(self.cto)
        self.assertEqual(ficha.id, v2.id)
        self.assertEqual(Vistoria.objects.count(), 1)
        estado = sorted((r.porta or 0, r.resultado, r.serial) for r in ficha.portas.all())
        self.assertEqual(estado, [(0, 'cliente', 'S3'), (2, 'vazia', ''), (3, 'sem_ont_ativa', ''), (4, 'cliente', 'S1')])
        self.assertEqual(ficha.observacao, 'primeira\nsegunda')
        # Registro de vistoria antiga devolve para onde ir
        self.assertEqual(self.client.get(f'/api/vistorias/{v1.id}/').status_code, 404)   # foi juntada e removida

    def test_cliente_registrado_em_outra_caixa_sai_da_anterior(self):
        a = self.client.post('/api/vistorias/', {'cto': self.cto.id}, format='json').data['id']
        b = self.client.post('/api/vistorias/', {'cto': self.outra.id}, format='json').data['id']
        self.porta(a, porta=5, resultado='cliente', serial='S2')
        self.porta(b, porta=2, resultado='cliente', serial='S2')
        antigo = VistoriaPorta.objects.get(vistoria_id=a, porta=5)
        self.assertEqual((antigo.resultado, antigo.serial), ('nao_identificado', ''))
        self.assertIn('CA_002', antigo.observacao)

    def test_painel_capacidade_e_ficha(self):
        r = self.client.post(f'/api/ctos/{self.cto.id}/capacidade/', {'portas': 16}, format='json')
        self.assertEqual((r.data['portas_manual'], r.data['portas_base'], r.data['portas_projeto']), (16, 16, 8))
        self.client.post(f'/api/ctos/{self.cto.id}/portas-inutilizadas/', {'porta': 12, 'inutilizada': True}, format='json')
        r = self.client.post(f'/api/ctos/{self.cto.id}/capacidade/', {'portas': None}, format='json')
        self.assertEqual((r.data['portas_base'], r.data['portas_inutilizadas']), (8, []))   # porta 12 deixou de existir
        self.assertEqual(self.client.post(f'/api/ctos/{self.cto.id}/capacidade/', {'portas': 0}, format='json').status_code, 400)

        f = self.client.post(f'/api/ctos/{self.cto.id}/ficha/', format='json').data
        self.assertTrue(f['criada'])
        v = Vistoria.objects.get(id=f['vistoria_id'])
        self.assertIsNotNone(v.finalizada_em)        # ficha do painel não aparece como vistoria em andamento
        f2 = self.client.post(f'/api/ctos/{self.cto.id}/ficha/', format='json').data
        self.assertEqual((f2['vistoria_id'], f2['criada']), (v.id, False))

    def test_comando(self):
        Vistoria.objects.create(cto=self.cto)
        Vistoria.objects.create(cto=self.cto)
        call_command('consolidar_vistorias', verbosity=0)
        self.assertEqual(Vistoria.objects.filter(cto=self.cto).count(), 1)
