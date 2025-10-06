"""
Comando para listar IPs permitidos
Execução: docker compose exec web python manage.py list_ips
"""
from django.core.management.base import BaseCommand
from olt.models import AllowedIP


class Command(BaseCommand):
    help = 'Lista todos os IPs permitidos'

    def add_arguments(self, parser):
        parser.add_argument(
            '--active-only',
            action='store_true',
            help='Mostra apenas IPs ativos',
        )
        parser.add_argument(
            '--inactive-only',
            action='store_true',
            help='Mostra apenas IPs inativos',
        )

    def handle(self, *args, **options):
        # Filtrar IPs
        ips = AllowedIP.objects.all()
        
        if options['active_only']:
            ips = ips.filter(is_active=True)
            title = '📋 IPs ATIVOS'
        elif options['inactive_only']:
            ips = ips.filter(is_active=False)
            title = '📋 IPs INATIVOS'
        else:
            title = '📋 TODOS OS IPs PERMITIDOS'

        ips = ips.order_by('ip_address')

        self.stdout.write(title)
        self.stdout.write('=' * 50)

        if not ips.exists():
            self.stdout.write('ℹ️ Nenhum IP encontrado.')
            return

        for ip in ips:
            status = '🟢 ATIVO' if ip.is_active else '🔴 INATIVO'
            created = ip.created_at.strftime('%d/%m/%Y %H:%M')
            
            self.stdout.write(f'{status} {ip.ip_address}')
            self.stdout.write(f'   📝 {ip.description}')
            self.stdout.write(f'   📅 Criado: {created}')
            self.stdout.write('')

        # Estatísticas
        total = ips.count()
        active_count = AllowedIP.objects.filter(is_active=True).count()
        inactive_count = AllowedIP.objects.filter(is_active=False).count()

        self.stdout.write('📊 ESTATÍSTICAS:')
        self.stdout.write(f'   • Total listado: {total}')
        self.stdout.write(f'   • Ativos no sistema: {active_count}')
        self.stdout.write(f'   • Inativos no sistema: {inactive_count}')
        self.stdout.write(f'   • Total geral: {active_count + inactive_count}')