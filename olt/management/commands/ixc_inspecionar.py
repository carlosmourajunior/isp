"""
Diagnóstico: mostra os campos e alguns registros de uma tabela do IXC.
Só leitura - não grava nada. Útil para descobrir o formato de uma tabela
antes de escrever a importação.

    python manage.py ixc_inspecionar                      # tenta as tabelas de caixa FTTH
    python manage.py ixc_inspecionar rad_caixa_ftth --limite 5
    python manage.py ixc_inspecionar rad_caixa_ftth --id 96
"""
import json

from django.core.management.base import BaseCommand

from olt.client_utils import _ixc_list_request

# Nomes prováveis da tabela de caixas FTTH no IXC (varia entre versões).
CANDIDATAS_CAIXA = ['rad_caixa_ftth', 'caixa_ftth', 'radpop_caixa_ftth']


class Command(BaseCommand):
    help = 'Mostra campos e registros de exemplo de uma tabela do IXC (só leitura)'

    def add_arguments(self, parser):
        parser.add_argument('recurso', nargs='?', help='Tabela do IXC (ex.: rad_caixa_ftth)')
        parser.add_argument('--limite', type=int, default=3)
        parser.add_argument('--id', help='Mostra só o registro com este id')

    def handle(self, *args, **options):
        recursos = [options['recurso']] if options['recurso'] else CANDIDATAS_CAIXA
        for recurso in recursos:
            response = _ixc_list_request(recurso, f'{recurso}.id', page=1)
            try:
                data = response.json()
            except ValueError:
                self.stdout.write(f"{recurso}: HTTP {response.status_code}, resposta não é JSON: {response.text[:200]}")
                continue
            registros = data.get('registros') or []
            if response.status_code != 200 or data.get('type') == 'error':
                self.stdout.write(f"{recurso}: HTTP {response.status_code} - {str(data)[:300]}")
                continue

            self.stdout.write(self.style.SUCCESS(f"\n{recurso}: total {data.get('total')} registros"))
            if not registros:
                continue
            self.stdout.write("Campos: " + ', '.join(sorted(registros[0].keys())))
            if options['id']:
                registros = [r for r in registros if str(r.get('id')) == str(options['id'])] or \
                    ["(id não está na primeira página - aumente a busca ou use outro id)"]
            for registro in registros[:options['limite']]:
                self.stdout.write(json.dumps(registro, ensure_ascii=False, indent=2))
