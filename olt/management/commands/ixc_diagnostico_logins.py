"""
Diagnóstico (só leitura): clientes com mais de um registro no IXC.

- Mesma ONU (serial) em mais de um registro de radpop_radio_cliente_fibra:
  hoje o sync fica com o último (maior id) - pode pegar um login cancelado.
- Mesmo contrato com mais de uma ONU: cada ONU é tratada sozinha (ok).

    python manage.py ixc_diagnostico_logins [--exemplos 15]
"""
from collections import Counter, defaultdict

from django.core.management.base import BaseCommand

from olt.client_utils import _fetch_all_registros
from olt.contrato import STATUS_CONTRATO, STATUS_INTERNET


class Command(BaseCommand):
    help = 'Conta ONUs com mais de um registro de cliente fibra e contratos com várias ONUs no IXC (só leitura)'

    def add_arguments(self, parser):
        parser.add_argument('--exemplos', type=int, default=15)

    def handle(self, *args, **options):
        fibra = _fetch_all_registros('radpop_radio_cliente_fibra', 'radpop_radio_cliente_fibra.id')
        contratos = {c['id']: c for c in _fetch_all_registros('cliente_contrato', 'cliente_contrato.id')}
        self.stdout.write(f"Registros de cliente fibra: {len(fibra)} | contratos: {len(contratos)}")

        por_serial = defaultdict(list)
        por_contrato = defaultdict(set)
        for r in fibra:
            serial = (r.get('mac') or '').strip()
            if serial:
                por_serial[serial].append(r)
            if r.get('id_contrato') and serial:
                por_contrato[r['id_contrato']].add(serial)

        def status(r):
            c = contratos.get(r.get('id_contrato'))
            if not c:
                return 'sem contrato'
            return (f"contrato {STATUS_CONTRATO.get(c.get('status'), c.get('status'))}, "
                    f"internet {STATUS_INTERNET.get(c.get('status_internet'), c.get('status_internet'))}")

        repetidos = {s: rs for s, rs in por_serial.items() if len(rs) > 1}
        # O caso perigoso: o registro que o sync escolhe (maior id) não é o de contrato ativo.
        perigosos = []
        for serial, rs in repetidos.items():
            escolhido = max(rs, key=lambda r: int(r.get('id') or 0))
            ativos = [r for r in rs if contratos.get(r.get('id_contrato'), {}).get('status') == 'A']
            if ativos and escolhido not in ativos:
                perigosos.append(serial)

        self.stdout.write(self.style.WARNING(
            f"\nONUs com mais de um registro de cliente fibra: {len(repetidos)}"
            f" | delas, o sync fica com um registro SEM contrato ativo (havendo um ativo): {len(perigosos)}"))
        self.stdout.write(f"Distribuição (registros por ONU): {dict(Counter(len(rs) for rs in repetidos.values()))}")
        for serial in (perigosos + [s for s in repetidos if s not in perigosos])[:options['exemplos']]:
            self.stdout.write(f"  {serial}{'  <- sync pega o errado' if serial in perigosos else ''}")
            for r in sorted(repetidos[serial], key=lambda r: int(r.get('id') or 0)):
                self.stdout.write(f"      id {r.get('id'):>6}  login {r.get('login') or r.get('nome') or '-':<25} "
                                  f"caixa {r.get('id_caixa_ftth') or '-':<6} {status(r)}")

        varias = {c: s for c, s in por_contrato.items() if len(s) > 1}
        self.stdout.write(f"\nContratos com mais de uma ONU: {len(varias)} "
                          f"(distribuição: {dict(Counter(len(s) for s in varias.values()))}) - cada ONU é tratada sozinha.")
