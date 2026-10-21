"""Sincroniza o cadastro de CTOs (rad_caixa_ftth) do IXC. Também roda junto
com a atualização de clientes (update_clientes_task)."""
from django.core.management.base import BaseCommand

from olt.client_utils import update_ctos


class Command(BaseCommand):
    help = 'Sincroniza as CTOs do IXC (rad_caixa_ftth)'

    def handle(self, *args, **options):
        total = update_ctos()
        self.stdout.write(self.style.SUCCESS(f"{total} CTOs sincronizadas do IXC"))
