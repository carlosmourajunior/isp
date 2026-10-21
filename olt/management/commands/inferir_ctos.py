"""
Roda a inferência de CTO por ONT (olt/cto_inference.py) e grava em
CtoInferencia. Só lê o banco - não toca na OLT nem no IXC.

    python manage.py inferir_ctos --olt 1
    python manage.py inferir_ctos            # todas as OLTs ativas
"""
from django.core.management.base import BaseCommand

from olt.cto_inference import run_inference
from olt.models import Olt


class Command(BaseCommand):
    help = 'Infere a CTO provável de cada ONT cruzando cadastro, PON, distância, geografia e quedas'

    def add_arguments(self, parser):
        parser.add_argument('--olt', type=int)
        parser.add_argument('--dias', type=int, default=30, help='Dias de eventos de queda considerados')

    def handle(self, *args, **options):
        olts = Olt.objects.filter(id=options['olt']) if options['olt'] else Olt.objects.filter(is_active=True)
        for olt in olts:
            r = run_inference(olt, dias_eventos=options['dias'])
            self.stdout.write(self.style.SUCCESS(f"\n{olt.name}: {r['onts']} ONTs, {r['ancoras']} âncoras (com CTO no cadastro), "
                                                 f"{r['eventos']} eventos de queda, {r['quedas_uteis']} quedas simultâneas úteis"))
            self.stdout.write(f"Status: {r['status']}")
            if r['divergencia_por_motivo']:
                self.stdout.write(f"Divergentes por motivo: {r['divergencia_por_motivo']}")
            self.stdout.write("PON(s) aprendida(s) por ramal:")
            for ramal, pons in r['ramais_com_pon'].items():
                self.stdout.write(f"  {ramal}: {', '.join(pons)}")
