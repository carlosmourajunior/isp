"""
Comando para adicionar IP individual com validação em tempo real
Execução: docker compose exec web python manage.py add_ip 192.168.1.100 "Descrição"
"""
from django.core.management.base import BaseCommand
from olt.ip_utils import validate_and_add_ip, force_refresh_allowed_ips


class Command(BaseCommand):
    help = 'Adiciona um IP à lista de permitidos com validação em tempo real'

    def add_arguments(self, parser):
        parser.add_argument('ip_address', type=str, help='IP ou range CIDR a ser adicionado')
        parser.add_argument('description', type=str, nargs='?', default='', help='Descrição do IP')
        parser.add_argument(
            '--inactive',
            action='store_true',
            help='Adiciona o IP como inativo',
        )
        parser.add_argument(
            '--refresh-cache',
            action='store_true',
            help='Força atualização do cache após adicionar',
        )

    def handle(self, *args, **options):
        ip_address = options['ip_address']
        description = options['description'] or f'Adicionado via comando add_ip'
        force_active = not options['inactive']

        self.stdout.write(
            self.style.SUCCESS(f'➕ Processando IP: {ip_address}')
        )
        
        # Usar função de validação e adição
        success, message, ip_object = validate_and_add_ip(
            ip_address=ip_address,
            description=description,
            force_active=force_active
        )
        
        if success:
            self.stdout.write(self.style.SUCCESS(message))
            
            # Mostrar status do IP
            if ip_object:
                status = '🟢 ATIVO' if ip_object.is_active else '🔴 INATIVO'
                self.stdout.write(f'   Status: {status}')
                self.stdout.write(f'   Descrição: {ip_object.description}')
                self.stdout.write(f'   Atualizado: {ip_object.updated_at.strftime("%d/%m/%Y %H:%M:%S")}')
        else:
            self.stdout.write(self.style.ERROR(message))
            return

        # Atualizar cache se solicitado
        if options['refresh_cache']:
            self.stdout.write(self.style.WARNING('🔄 Atualizando cache...'))
            cache_success, cache_message, active_ips = force_refresh_allowed_ips()
            
            if cache_success:
                self.stdout.write(self.style.SUCCESS(cache_message))
            else:
                self.stdout.write(self.style.ERROR(cache_message))
        
        self.stdout.write('')
        self.stdout.write(
            self.style.SUCCESS('✅ Operação concluída! IP está disponível imediatamente.')
        )