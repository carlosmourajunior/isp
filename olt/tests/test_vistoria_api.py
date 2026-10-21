"""
Vistoria de CTO (olt/vistoria_views.py): candidatos com fantasma provável,
registro de portas, eventos ao vivo, correções e efeito na inferência.
"""
from datetime import timedelta
from unittest import mock

from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from olt.contrato import situacao_contrato
from olt.models import ONU, ClienteFibraIxc, Cto, CtoInferencia, Olt, OntEvent, OntSnapshot, Vistoria


class SituacaoContratoTests(APITestCase):

    def test_regras(self):
        def c(**kw):
            return ClienteFibraIxc(mac='x', nome='x', vinculado=True, **kw)
        self.assertEqual(situacao_contrato(None)[0], 'sem_contrato')
        self.assertEqual(situacao_contrato(c(status_contrato='A', status_internet='A'))[0], 'ativo')
        self.assertEqual(situacao_contrato(c(status_contrato='A', status_internet='CA'))[0], 'bloqueado')
        self.assertEqual(situacao_contrato(c(status_contrato='I', status_internet='A'))[0], 'inativo')
        self.assertEqual(situacao_contrato(c(status_contrato='A', status_internet='D'))[0], 'inativo')


class VistoriaApiTests(APITestCase):

    def setUp(self):
        self.client.force_authenticate(User.objects.create_user('bancada', password='p'))
        self.olt = Olt.objects.create(name='OLT Borda', host='10.0.0.1', username='u', password='p')
        self.cto = Cto.objects.create(ixc_id='96', descricao='CA_096', olt=self.olt, kmz_portas=8)
        self.outra = Cto.objects.create(ixc_id='97', descricao='CA_097', olt=self.olt, kmz_portas=8)
        agora = timezone.now()

        def ont(pos, oper, contrato='A', caixa='96', provavel=None, status_inf='confirmado'):
            serial = f'S{pos}'
            ONU.objects.create(olt=self.olt, pon='1/1/2/8', position=pos, mac='', serial=serial,
                               oper_state=oper, desc1='', desc2='')
            ClienteFibraIxc.objects.create(mac=serial, nome=f'Cliente {pos}', id_caixa_ftth=caixa,
                                           vinculado=True, status_contrato=contrato, status_internet='A')
            CtoInferencia.objects.create(olt=self.olt, pon='1/1/2/8', position=pos, serial=serial,
                                         status=status_inf, cto_provavel=provavel or self.cto,
                                         cto_cadastro=Cto.objects.get(ixc_id=caixa), calculado_em=agora)

        ont(1, 'up')
        ont(2, 'down', contrato='I')                        # offline + contrato inativo = fantasma
        ont(3, 'down')                                     # offline, contrato ativo, sem histórico
        OntSnapshot.objects.create(olt=self.olt, taken_at=agora - timedelta(days=20), pon='1/1/2/8',
                                   position=3, serial='S3', oper_state='up')  # offline há 20 dias = fantasma
        ont(4, 'up', caixa='97', provavel=self.cto, status_inf='divergente')
        # Cadastrado na 96 mas a ONT não existe na OLT
        ClienteFibraIxc.objects.create(mac='SXX', nome='Antigo', id_caixa_ftth='96', vinculado=True, status_contrato='A')

        self.v = self.client.post(reverse('api:vistoria_list'), {'cto': self.cto.id, 'tecnico': 'João'}).data

    def test_inicia_com_olt_da_cto(self):
        self.assertEqual(self.v['olt_id'], self.olt.id)
        self.assertEqual(Vistoria.objects.get(id=self.v['id']).usuario, 'bancada')

    def test_candidatos_com_fantasma_provavel(self):
        dados = self.client.get(reverse('api:vistoria_detail', args=[self.v['id']])).data
        c = {x['serial']: x for x in dados['candidatos']}
        self.assertFalse(c['S1']['fantasma_provavel'])
        self.assertTrue(c['S2']['fantasma_provavel'])
        self.assertTrue(c['S3']['fantasma_provavel'])
        self.assertEqual(c['S3']['offline_ha_dias'], 20)
        self.assertEqual(c['S4']['papel'], 'veio_de_outra')
        self.assertEqual(c['SXX']['papel'], 'sem_ont')
        self.assertEqual(dados['pons'], ['1/1/2/8'])

    def test_registra_porta_e_nao_duplica_cliente(self):
        url = reverse('api:vistoria_porta_salvar', args=[self.v['id']])
        r = self.client.post(url, {'porta': 1, 'resultado': 'cliente', 'serial': 'S1', 'metodo': 'etiqueta'})
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data['cliente_nome'], 'Cliente 1')
        self.assertEqual(r.data['pon'], '1/1/2/8')
        # Mesmo cliente na porta 2: sai da porta 1
        self.client.post(url, {'porta': 2, 'resultado': 'cliente', 'serial': 'S1'})
        portas = self.client.get(reverse('api:vistoria_detail', args=[self.v['id']])).data['portas']
        self.assertEqual([p['porta'] for p in portas], [2])
        # Cliente sem serial é recusado
        self.assertEqual(self.client.post(url, {'porta': 3, 'resultado': 'cliente'}).status_code, 400)

    def test_cliente_sem_porta_e_depois_com_porta(self):
        url = reverse('api:vistoria_porta_salvar', args=[self.v['id']])
        # Identificado por desconexão, porta desconhecida
        r = self.client.post(url, {'resultado': 'cliente', 'serial': 'S1', 'metodo': 'desconexao'})
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertIsNone(r.data['porta'])
        # Reconexão confirmada: atualiza o mesmo registro, não duplica
        self.client.post(url, {'resultado': 'cliente', 'serial': 'S1', 'reconexao_confirmada': True})
        dados = self.client.get(reverse('api:vistoria_detail', args=[self.v['id']])).data
        self.assertEqual(len(dados['portas']), 1)
        self.assertTrue(dados['portas'][0]['reconexao_confirmada'])
        cand = {c['serial']: c for c in dados['candidatos']}
        self.assertTrue(cand['S1']['registrado'])
        self.assertIsNone(cand['S1']['porta_registrada'])
        # Depois a etiqueta mostra a porta 4: o registro sem porta vira porta 4
        self.client.post(url, {'porta': 4, 'resultado': 'cliente', 'serial': 'S1'})
        portas = self.client.get(reverse('api:vistoria_detail', args=[self.v['id']])).data['portas']
        self.assertEqual([p['porta'] for p in portas], [4])

    def test_drop_fantasma_sem_porta_e_remover_por_id(self):
        url = reverse('api:vistoria_porta_salvar', args=[self.v['id']])
        a = self.client.post(url, {'resultado': 'sem_ont_ativa'}).data
        self.client.post(url, {'resultado': 'sem_ont_ativa'})
        self.assertEqual(len(self.client.get(reverse('api:vistoria_detail', args=[self.v['id']])).data['portas']), 2)
        self.client.delete(reverse('api:vistoria_registro_remover', args=[self.v['id'], a['id']]))
        self.assertEqual(len(self.client.get(reverse('api:vistoria_detail', args=[self.v['id']])).data['portas']), 1)

    def test_eventos_avisam_pon_e_queda_simultanea(self):
        url = reverse('api:vistoria_eventos', args=[self.v['id']])
        inicio = self.client.get(url).data
        self.assertEqual(inicio['pons_da_caixa'], ['1/1/2/8'])
        agora = timezone.now()
        # Desconexão do técnico (PON da caixa) + duas ONTs de outra PON caindo juntas
        OntEvent.objects.create(olt=self.olt, occurred_at=agora, pon='1/1/2/8', position=1, event_type='inativa')
        OntEvent.objects.create(olt=self.olt, occurred_at=agora, pon='1/1/1/3', position=7, event_type='inativa')
        OntEvent.objects.create(olt=self.olt, occurred_at=agora + timedelta(seconds=2), pon='1/1/1/3',
                                position=9, event_type='inativa')
        eventos = self.client.get(url, {'desde': inicio['agora'].isoformat()}).data['eventos']
        por_pos = {(e['pon'], e['position']): e for e in eventos}
        self.assertTrue(por_pos[('1/1/2/8', 1)]['mesma_pon_da_caixa'])
        self.assertEqual(por_pos[('1/1/2/8', 1)]['caiu_junto'], 1)
        self.assertFalse(por_pos[('1/1/1/3', 7)]['mesma_pon_da_caixa'])
        self.assertEqual(por_pos[('1/1/1/3', 7)]['caiu_junto'], 2)

    def test_filtro_por_olt(self):
        outra_olt = Olt.objects.create(name='OLT OF', host='10.0.0.2', username='u', password='p')
        self.client.post(reverse('api:vistoria_porta_salvar', args=[self.v['id']]),
                         {'porta': 1, 'resultado': 'cliente', 'serial': 'S4'})
        self.assertEqual(len(self.client.get(reverse('api:vistoria_list'), {'olt': outra_olt.id}).data), 0)
        self.assertEqual(len(self.client.get(reverse('api:vistoria_list'), {'olt': self.olt.id}).data), 1)
        self.assertEqual(self.client.get(reverse('api:vistoria_correcoes'), {'olt': outra_olt.id}).data['clientes'], [])
        self.assertEqual(len(self.client.get(reverse('api:vistoria_correcoes'), {'olt': self.olt.id}).data['clientes']), 1)

    def test_eventos_ao_vivo(self):
        url = reverse('api:vistoria_eventos', args=[self.v['id']])
        inicio = self.client.get(url).data
        self.assertEqual(inicio['eventos'], [])
        OntEvent.objects.create(olt=self.olt, occurred_at=timezone.now(), pon='1/1/2/8', position=1,
                                serial='', event_type='inativa', alarm_type='ONT is inactive')
        OntEvent.objects.create(olt=self.olt, occurred_at=timezone.now(), pon='1/1/2/8', position=1,
                                serial='', event_type='other', alarm_type='Remote Defect Indication from ONT')
        r = self.client.get(url, {'desde': inicio['agora'].isoformat()}).data
        self.assertEqual(len(r['eventos']), 1)   # RDI não entra
        e = r['eventos'][0]
        self.assertEqual((e['serial'], e['cliente_nome'], e['voltou'], e['candidato_desta_cto']),
                         ('S1', 'Cliente 1', False, True))

    def test_correcoes_e_finalizar_recalcula(self):
        url = reverse('api:vistoria_porta_salvar', args=[self.v['id']])
        self.client.post(url, {'porta': 1, 'resultado': 'cliente', 'serial': 'S4'})   # cadastro diz 97
        self.client.post(url, {'porta': 2, 'resultado': 'cliente', 'serial': 'S1'})   # cadastro já diz 96
        self.client.post(url, {'porta': 5, 'resultado': 'sem_ont_ativa'})
        corr = self.client.get(reverse('api:vistoria_correcoes')).data
        self.assertEqual([c['serial'] for c in corr['clientes']], ['S4'])
        self.assertEqual(corr['clientes'][0]['cto_cadastro'], 'CA_097')
        self.assertEqual([(p['cto']['descricao'], p['porta']) for p in corr['portas_fantasma']], [('CA_096', 5)])

        with mock.patch('olt.tasks.infer_ctos_task.delay') as delay:
            delay.return_value.id = 'job-1'
            r = self.client.post(reverse('api:vistoria_finalizar', args=[self.v['id']]))
        self.assertIsNotNone(r.data['finalizada_em'])
        delay.assert_called_once()

    def test_inferencia_usa_vistoria(self):
        from olt.cto_inference import run_inference
        self.client.post(reverse('api:vistoria_porta_salvar', args=[self.v['id']]),
                         {'porta': 1, 'resultado': 'cliente', 'serial': 'S4'})
        run_inference(self.olt)
        inf = CtoInferencia.objects.get(serial='S4')
        self.assertEqual(inf.status, 'vistoriado')
        self.assertEqual(inf.cto_provavel, self.cto)

    def test_busca_cliente(self):
        r = self.client.get(reverse('api:vistoria_buscar_cliente'), {'q': 'Cliente 4'}).data
        self.assertEqual([c['serial'] for c in r], ['S4'])
        self.assertEqual(self.client.get(reverse('api:vistoria_buscar_cliente'), {'q': 'ab'}).data, [])
