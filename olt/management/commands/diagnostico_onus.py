"""
Confere se as marcações "cliente fibra" e "sem MAC" das ONUs estão certas.
Só lê, não altera nada.

    python manage.py diagnostico_onus            # resumo + até 10 exemplos por problema
    python manage.py diagnostico_onus --exemplos 30

Cliente fibra: a ONU é marcada quando o serial dela existe em ClienteFibraIxc.mac
(campo mac do radpop_radio_cliente_fibra do IXC). Aqui conferimos:
- marcação desatualizada (flag diferente do que o banco diz agora);
- ONU marcada só por um registro que saiu do IXC (is_active=False);
- serial que só bate com o IXC se ignorar maiúsculas/":" (diferença de formato);
- registros do IXC sem ONU em nenhuma OLT do sistema, e o formato do campo mac deles.

MAC: vem do "show vlan bridge-port-fdb" (tarefa "Atualização de MAC"). ONU offline
não aparece ali, então "sem MAC" + down é normal; "sem MAC" + up é o que interessa.
"""
import re
from collections import Counter, defaultdict

from django.core.management.base import BaseCommand
from django.db.models import Count, Max, Q

from olt.models import ONU, ClienteFibraIxc, Olt, OntSnapshot

SERIAL_RE = re.compile(r'^[A-Z]{4}:?[0-9A-F]{8}$')
MAC_RE = re.compile(r'^([0-9A-F]{2}[:-]?){5}[0-9A-F]{2}$')


def normaliza(valor):
    return re.sub(r'[^0-9A-Z]', '', (valor or '').upper())


def formato(valor):
    v = (valor or '').strip().upper()
    if not v:
        return 'vazio'
    if SERIAL_RE.match(v):
        return 'serial com ":"' if ':' in v else 'serial sem ":"'
    if MAC_RE.match(v):
        return 'MAC (não é serial)'
    return 'outro'


class Command(BaseCommand):
    help = 'Confere as marcações de cliente fibra e MAC das ONUs (somente leitura).'

    def add_arguments(self, parser):
        parser.add_argument('--exemplos', type=int, default=10)

    def secao(self, titulo):
        self.stdout.write('\n' + self.style.MIGRATE_HEADING(titulo))

    def lista(self, titulo, itens):
        itens = list(itens)
        estilo = self.style.WARNING if itens else self.style.SUCCESS
        self.stdout.write(estilo(f'  {titulo}: {len(itens)}'))
        for linha in itens[:self.n]:
            self.stdout.write(f'      {linha}')

    def handle(self, *args, **opts):
        self.n = opts['exemplos']
        onus = list(ONU.objects.select_related('olt').values(
            'id', 'olt__name', 'pon', 'position', 'serial', 'mac', 'oper_state', 'cliente_fibra'))
        ixc = list(ClienteFibraIxc.objects.values('mac', 'login', 'is_active', 'status_contrato', 'vinculado'))
        ativos = {c['mac'] for c in ixc if c['is_active']}
        inativos = {c['mac'] for c in ixc if not c['is_active']} - ativos
        ativos_norm = defaultdict(list)
        for c in ixc:
            if c['is_active']:
                ativos_norm[normaliza(c['mac'])].append(c['mac'])
        por_mac = {c['mac']: c for c in ixc}

        def onu_txt(o):
            return f"{o['olt__name']} {o['pon']}/{o['position']} {o['serial']} (oper {o['oper_state']})"

        # ------------------------------------------------------------------ geral
        self.secao('Visão geral')
        snaps = dict(OntSnapshot.objects.values('olt__name').annotate(m=Max('taken_at')).values_list('olt__name', 'm'))
        for olt in Olt.objects.order_by('name'):
            qs = ONU.objects.filter(olt=olt)
            c = qs.aggregate(total=Count('id'), cf=Count('id', filter=Q(cliente_fibra=True)),
                             up=Count('id', filter=Q(oper_state='up')),
                             sem_mac=Count('id', filter=Q(mac__isnull=True) | Q(mac='')))
            self.stdout.write(f"  {olt.name}{'' if olt.is_active else ' (inativa)'}: {c['total']} ONUs, "
                              f"{c['up']} up, {c['cf']} cliente fibra, {c['sem_mac']} sem MAC "
                              f"| última leitura de ONUs: {snaps.get(olt.name) or 'nunca'}")
        sem_olt = sum(1 for o in onus if not o['olt__name'])
        if sem_olt:
            self.stdout.write(self.style.WARNING(f'  {sem_olt} ONUs sem OLT associada (registros antigos)'))
        self.stdout.write(f"  IXC (radpop_radio_cliente_fibra): {len(ativos)} registros ativos, "
                          f"{len(inativos)} que saíram do IXC")

        # ---------------------------------------------------------- cliente fibra
        self.secao('Cliente fibra')
        desatualizada, so_inativo, formato_dif, sem_ixc_up, sem_ixc_down, contrato_inativo = [], [], [], [], [], []
        seriais_onu = set()
        for o in onus:
            s = o['serial']
            seriais_onu.add(normaliza(s))
            existe = s in ativos     # regra do sistema: só registro presente no IXC
            if o['cliente_fibra'] != existe:
                desatualizada.append(f"{onu_txt(o)}: marcada {o['cliente_fibra']}, banco diz {existe}")
            if s in inativos:
                so_inativo.append(onu_txt(o))
            elif s not in ativos:
                parecidos = ativos_norm.get(normaliza(s))
                if parecidos:
                    formato_dif.append(f"{onu_txt(o)} ~ IXC '{parecidos[0]}'")
                elif o['oper_state'] == 'up':
                    sem_ixc_up.append(onu_txt(o))
                else:
                    sem_ixc_down.append(onu_txt(o))
            else:
                c = por_mac[s]
                if c['status_contrato'] and c['status_contrato'] != 'A':
                    contrato_inativo.append(f"{onu_txt(o)} login {c['login']} contrato status {c['status_contrato']}")

        self.lista('Marcação desatualizada (flag ≠ banco; corrige no próximo sync de clientes)', desatualizada)
        self.lista('Serial só existe em registro que SAIU do IXC (deve ficar "Não")', so_inativo)
        self.lista('Serial só bate ignorando maiúsculas/":" (diferença de formato, falso "Não")', formato_dif)
        self.lista('ONLINE sem cadastro no IXC (cliente sem cliente fibra, ou serial errado no IXC)', sem_ixc_up)
        self.lista('Offline sem cadastro no IXC (ONU sobrando/retirada?)', sem_ixc_down)
        self.lista('No IXC com contrato não ativo (status ≠ A) mas a ONU está na OLT', contrato_inativo)

        orfaos = [c for c in ixc if c['is_active'] and normaliza(c['mac']) not in seriais_onu]
        self.lista('Registros ativos do IXC sem ONU em nenhuma OLT do sistema',
                   (f"'{c['mac']}' login {c['login']} ({formato(c['mac'])})" for c in orfaos))
        self.stdout.write('  Formato do campo mac no IXC (ativos): ' + ', '.join(
            f'{k}: {v}' for k, v in Counter(formato(c['mac']) for c in ixc if c['is_active']).most_common()))
        self.stdout.write('  Formato dos seriais das ONUs: ' + ', '.join(
            f'{k}: {v}' for k, v in Counter(formato(o['serial']) for o in onus).most_common()))
        dup = [m for m, n in Counter(normaliza(c['mac']) for c in ixc if c['is_active']).items() if n > 1 and m]
        self.lista('Mesmo serial em mais de um registro ativo do IXC', dup)

        # -------------------------------------------------------------------- MAC
        self.secao('MAC')
        sem_mac = [o for o in onus if not o['mac']]
        self.lista('Sem MAC e ONLINE (deveria ter MAC na tabela da OLT)',
                   (onu_txt(o) for o in sem_mac if o['oper_state'] == 'up'))
        self.stdout.write(f"  Sem MAC e offline (normal): {sum(1 for o in sem_mac if o['oper_state'] != 'up')}")
        com_mac_down = [o for o in onus if o['mac'] and o['oper_state'] != 'up']
        self.stdout.write(f'  Com MAC e offline (MAC lido antes de cair): {len(com_mac_down)}')
        macs = Counter(o['mac'].lower() for o in onus if o['mac'])
        repetidos = {m for m, n in macs.items() if n > 1}
        self.lista('Mesmo MAC em mais de uma ONU',
                   (f"{m}: " + ', '.join(onu_txt(o) for o in onus if (o['mac'] or '').lower() == m)
                    for m in sorted(repetidos)))
        invalidos = [o for o in onus if o['mac'] and not MAC_RE.match(o['mac'].upper())]
        self.lista('MAC em formato estranho', (f"{onu_txt(o)}: '{o['mac']}'" for o in invalidos))
        self.stdout.write('')
