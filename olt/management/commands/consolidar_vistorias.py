"""
Junta as vistorias antigas de cada caixa numa ficha só (olt/ficha_cto.py).

    python manage.py consolidar_vistorias --dry-run   # só mostra quantas caixas têm mais de uma
    python manage.py consolidar_vistorias

Fica o registro mais recente de cada porta e de cada cliente. A ficha também é
consolidada sozinha quando a caixa é aberta; este comando faz todas de uma vez.
"""
from django.core.management.base import BaseCommand
from django.db.models import Count

from olt.ficha_cto import consolidar
from olt.models import Cto, Vistoria, VistoriaPorta


class Command(BaseCommand):
    help = 'Junta as vistorias de cada CTO numa ficha única'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true')

    def handle(self, *args, **opts):
        ids = list(Vistoria.objects.values('cto').annotate(n=Count('id')).filter(n__gt=1).values_list('cto', flat=True))
        antes = VistoriaPorta.objects.filter(vistoria__cto__in=ids).count()
        self.stdout.write(f"Caixas com mais de uma vistoria: {len(ids)} ({antes} registros)")
        if opts['dry_run'] or not ids:
            return
        for cto in Cto.objects.filter(id__in=ids):
            consolidar(cto)
        depois = VistoriaPorta.objects.filter(vistoria__cto__in=ids).count()
        self.stdout.write(self.style.SUCCESS(
            f"{len(ids)} caixas consolidadas: {antes - depois} registros substituídos por outros mais novos, {depois} ficaram."))
