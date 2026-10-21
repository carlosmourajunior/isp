"""
Testes do núcleo da inferência de CTO (olt/cto_inference.infer). Cenários
sintéticos, sem banco: CTOs e ONTs são objetos simples.
"""
from datetime import datetime, timedelta
from types import SimpleNamespace

from django.test import SimpleTestCase

from olt.cto_inference import Ont, detectar_quedas, infer


def cto(pk, ramal='', lat=None, lon=None, olt_id=1):
    return SimpleNamespace(pk=pk, descricao=f"CA_{pk:03d}", ramal=ramal, latitude=lat, longitude=lon, olt_id=olt_id)


def resultado_de(resultado, position):
    return next((status, ranking) for ont, status, ranking in resultado if ont.position == position)


class InferTests(SimpleTestCase):

    def setUp(self):
        # Duas CTOs no mesmo ramal/PON, separadas pela distância óptica.
        self.a = cto(1, 'Ramal 01')
        self.b = cto(2, 'Ramal 01')
        self.c = cto(3, 'Ramal 02')   # sem âncora própria, só o ramal
        pon = '1/1/1/1'
        self.onts = [
            Ont(pon, 1, 'S1', 1.2, cto_cadastro=self.a),
            Ont(pon, 2, 'S2', 1.2, cto_cadastro=self.a),
            Ont(pon, 3, 'S3', 1.3, cto_cadastro=self.a),
            Ont(pon, 4, 'S4', 2.5, cto_cadastro=self.b),
            Ont(pon, 5, 'S5', 2.6, cto_cadastro=self.b),
            Ont(pon, 6, 'S6', 1.2),                       # sem cadastro, perto da faixa da A
            Ont(pon, 7, 'S7', 2.5, cto_cadastro=self.a),  # cadastrada na A, mas na faixa da B
            Ont('1/1/1/2', 1, 'S8', 3.0, cto_cadastro=self.c),
            Ont('1/1/1/2', 2, 'S9', 3.0, cto_cadastro=self.c),
            Ont('1/1/9/9', 1, 'S10', 1.0),                # PON sem nenhuma âncora
        ]

    def test_ancora_coerente_fica_confirmada(self):
        resultado, *_ = infer(self.onts, [self.a, self.b, self.c])
        status, ranking = resultado_de(resultado, 1)
        self.assertEqual(status, 'confirmado')
        self.assertIs(ranking[0][1], self.a)

    def test_ont_sem_cadastro_vira_provavel_na_cto_da_faixa_certa(self):
        resultado, *_ = infer(self.onts, [self.a, self.b, self.c])
        status, ranking = resultado_de(resultado, 6)
        self.assertEqual(status, 'provavel')
        self.assertIs(ranking[0][1], self.a)

    def test_cadastro_contrariado_pela_distancia_vira_divergente(self):
        resultado, *_ = infer(self.onts, [self.a, self.b, self.c])
        status, ranking = resultado_de(resultado, 7)
        self.assertEqual(status, 'divergente')
        self.assertIs(ranking[0][1], self.b)

    def test_cadastro_sem_evidencia_contra_nao_vira_divergente(self):
        # CTO D só tem esta âncora: nada a favor nem contra. A tem evidência forte
        # (mesma PON, mesma faixa), mas isso sozinho não prova que o cadastro está errado.
        d = cto(4, '')
        self.onts.append(Ont('1/1/1/1', 8, 'S11', 1.2, cto_cadastro=d))
        resultado, *_ = infer(self.onts, [self.a, self.b, self.c, d])
        self.assertEqual(resultado_de(resultado, 8)[0], 'incerto')

    def test_pon_sem_ancoras_fica_sem_candidata(self):
        resultado, *_ = infer(self.onts, [self.a, self.b, self.c])
        status, _ = next((s, r) for o, s, r in resultado if o.pon == '1/1/9/9')
        self.assertEqual(status, 'sem_candidata')

    def test_ramal_aprende_a_pon_das_ancoras(self):
        _, _, pons_por_ramal, _ = infer(self.onts, [self.a, self.b, self.c])
        self.assertEqual(pons_por_ramal[(1, 'Ramal 01')], {'1/1/1/1'})

    def test_queda_simultanea_desempata(self):
        # S6 a 2.1 km: perto da faixa da B mas não o bastante para decidir sozinha
        # (sem quedas fica incerto); caindo junto com os clientes da B, vai para a B.
        self.onts[5].distance_km = 2.1
        resultado, *_ = infer(self.onts, [self.a, self.b, self.c])
        self.assertNotEqual(resultado_de(resultado, 6)[0], 'provavel')

        t0 = datetime(2026, 10, 20, 10, 0, 0)
        eventos = []
        for i in range(4):
            t = t0 + timedelta(hours=i)
            eventos += [('1/1/1/1', 4, t), ('1/1/1/1', 5, t + timedelta(seconds=1)), ('1/1/1/1', 6, t + timedelta(seconds=2))]
        resultado, *_ = infer(self.onts, [self.a, self.b, self.c], eventos)
        status, ranking = resultado_de(resultado, 6)
        self.assertIs(ranking[0][1], self.b)
        self.assertEqual(status, 'provavel')


class DetectarQuedasTests(SimpleTestCase):

    def test_agrupa_por_janela_e_descarta_queda_da_pon_inteira(self):
        t0 = datetime(2026, 10, 20, 10, 0, 0)
        eventos = [('P', 1, t0), ('P', 2, t0 + timedelta(seconds=2)),          # queda de 2 ONTs
                   ('P', 3, t0 + timedelta(minutes=5)),                         # isolada: descartada
                   ('Q', 1, t0), ('Q', 2, t0), ('Q', 3, t0)]                    # PON Q inteira: descartada
        quedas = detectar_quedas(eventos, {'P': 10, 'Q': 4})
        self.assertEqual(quedas, [('P', {1, 2})])

    def test_ont_instavel_fica_fora(self):
        t0 = datetime(2026, 10, 20, 10, 0, 0)
        # ONT 9 cai a cada minuto (instável); 1 e 2 caem juntas uma vez, com a 9 no meio.
        eventos = [('P', 9, t0 + timedelta(minutes=i)) for i in range(40)]
        eventos += [('P', 1, t0 + timedelta(minutes=5)), ('P', 2, t0 + timedelta(minutes=5, seconds=1))]
        quedas = detectar_quedas(eventos, {'P': 20})
        self.assertEqual(quedas, [('P', {1, 2})])
