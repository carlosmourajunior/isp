"""
Endpoints da tela CTOs (olt/cto_views.py): ocupação estimada por CTO,
detalhe com o papel de cada cliente e a fila de inferências.
"""
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from olt.models import ONU, ClienteFibraIxc, Cto, CtoInferencia, Olt


class CtoApiTests(APITestCase):

    def setUp(self):
        self.client.force_authenticate(User.objects.create_user('u', password='p'))
        self.olt = Olt.objects.create(name='OLT Borda', host='10.0.0.1', username='u', password='p')
        self.a = Cto.objects.create(ixc_id='1', descricao='CA_001', olt=self.olt, ramal='Ramal 01',
                                    kmz_portas=4, latitude=-22.27, longitude=-46.17)
        self.b = Cto.objects.create(ixc_id='2', descricao='CA_002', olt=self.olt, ramal='Ramal 01', kmz_portas=8)
        ClienteFibraIxc.objects.create(mac='S1', nome='Ana', id_caixa_ftth='1')
        agora = timezone.now()

        def inf(position, status_, provavel, cadastro=None, oper='up'):
            ONU.objects.create(olt=self.olt, pon='1/1/1/1', position=position, mac='', serial=f'S{position}',
                               oper_state=oper, desc1='', desc2='')
            CtoInferencia.objects.create(olt=self.olt, pon='1/1/1/1', position=position, serial=f'S{position}',
                                         status=status_, cto_provavel=provavel, cto_cadastro=cadastro,
                                         score=5, calculado_em=agora, motivos={'provavel': ['x']})

        inf(1, 'confirmado', self.a, self.a)
        inf(2, 'provavel', self.a, oper='down')
        inf(3, 'divergente', self.a, self.b)   # cadastrado na B, rede aponta A
        inf(4, 'confirmado', self.a, self.a)
        inf(5, 'incerto', self.a)
        inf(6, 'confirmado', self.b, self.b)

    def test_exige_autenticacao(self):
        self.client.force_authenticate(None)
        for url in (reverse('api:cto_list'), reverse('api:cto_detail', args=[self.a.id]),
                    reverse('api:cto_inferencia_list'), reverse('api:cto_inferencia_resumo')):
            self.assertEqual(self.client.get(url).status_code, status.HTTP_401_UNAUTHORIZED)

    def test_lista_calcula_ocupacao(self):
        response = self.client.get(reverse('api:cto_list'), {'olt': self.olt.id})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ctos = {c['descricao']: c for c in response.data}
        a = ctos['CA_001']
        self.assertEqual((a['confirmados'], a['provaveis'], a['vindos_de_outra'], a['possiveis']), (2, 1, 1, 1))
        self.assertEqual(a['ocupadas'], 4)
        self.assertEqual(a['livres'], 0)
        self.assertEqual(a['situacao'], 'cheia')
        self.assertEqual(a['offline'], 1)
        self.assertEqual(a['cadastro_ixc'], 1)
        self.assertEqual(ctos['CA_002']['suspeitos'], 1)
        self.assertEqual(ctos['CA_002']['situacao'], 'livre')

    def test_vistoriado_conta_como_ocupada(self):
        CtoInferencia.objects.filter(serial='S5').update(status='vistoriado')
        ctos = {c['descricao']: c for c in self.client.get(reverse('api:cto_list')).data}
        self.assertEqual(ctos['CA_001']['confirmados'], 3)
        self.assertEqual(ctos['CA_001']['possiveis'], 0)

    def test_splitter_e_porta_inutilizada_mudam_a_capacidade(self):
        # CA_001: 4 portas, 4 ocupadas -> cheia
        url = reverse('api:cto_splitters', args=[self.a.id])
        self.assertEqual(self.client.post(url, {'portas': 6}).status_code, 400)   # só 4 ou 8
        r = self.client.post(url, {'portas': 8}).data
        self.assertEqual((r['portas'], r['portas_uteis'], r['splitters_extras']), (12, 12, [8]))
        r = self.client.post(reverse('api:cto_porta_inutilizada', args=[self.a.id]),
                             {'porta': 10, 'inutilizada': True}, format='json').data
        self.assertEqual((r['portas_uteis'], r['portas_inutilizadas']), (11, [10]))
        a = {c['descricao']: c for c in self.client.get(reverse('api:cto_list')).data}['CA_001']
        self.assertEqual((a['ocupadas'], a['livres'], a['situacao']), (4, 7, 'livre'))
        # Desfazer o splitter: a porta 10 deixa de existir
        r = self.client.delete(url).data
        self.assertEqual((r['portas'], r['portas_inutilizadas']), (4, []))
        self.assertEqual(Cto.objects.get(pk=self.a.pk).ajustado_por, 'u')

    def test_filtro_situacao(self):
        response = self.client.get(reverse('api:cto_list'), {'situacao': 'cheia'})
        self.assertEqual([c['descricao'] for c in response.data], ['CA_001'])

    def test_detalhe_mostra_papel_de_cada_cliente(self):
        response = self.client.get(reverse('api:cto_detail', args=[self.b.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        papeis = {c['serial']: c['papel'] for c in response.data['clientes']}
        self.assertEqual(papeis, {'S6': 'confirmado', 'S3': 'suspeito'})
        self.assertEqual(response.data['suspeitos'], 1)

    def test_fila_de_divergencias_e_resumo(self):
        response = self.client.get(reverse('api:cto_inferencia_list'), {'status': 'divergente'})
        self.assertEqual(response.data['count'], 1)
        item = response.data['results'][0]
        self.assertEqual(item['cto_cadastro']['descricao'], 'CA_002')
        self.assertEqual(item['cto_provavel']['descricao'], 'CA_001')

        resumo = self.client.get(reverse('api:cto_inferencia_resumo')).data
        self.assertEqual(resumo['onts'], 6)
        self.assertEqual(resumo['por_status']['confirmado'], 3)
