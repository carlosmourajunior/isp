"""
Comando para adicionar IP individual
Execução: docker compose exec web python manage.py add_ip 192.168.1.100 "Descrição"
"""
from django.core.management.base import BaseCommand
from olt.models import AllowedIP
from django.core.cache import cache
import ipaddress


class Command(BaseCommand):
    help = 'Adiciona um IP à lista de permitidos'

    def add_arguments(self, parser):
        parser.add_argument('ip_address', type=str, help='IP ou range CIDR a ser adicionado')
        parser.add_argument('description', type=str, nargs='?', default='', help='Descrição do IP')
        parser.add_argument(
            '--inactive',
            action='store_true',
            help='Adiciona o IP como inativo',
        )
        parser.add_argument(
            '--update',
            action='store_true',
            help='Atualiza o IP se já existir',
        )

    def handle(self, *args, **options):
        ip_address = options['ip_address']
        description = options['description'] or f'IP {ip_address} adicionado via comando'
        is_active = not options['inactive']

        self.stdout.write(f'➕ Adicionando IP: {ip_address}')
        
        # Validar IP/CIDR
        try:
            ipaddress.ip_network(ip_address, strict=False)
        except ValueError:
            self.stdout.write(
                self.style.ERROR(f'❌ Formato de IP inválido: {ip_address}')
            )
            return

        try:
            # Verificar se já existe
            if AllowedIP.objects.filter(ip_address=ip_address).exists():
                if options['update']:
                    ip_obj = AllowedIP.objects.get(ip_address=ip_address)
                    ip_obj.description = description
                    ip_obj.is_active = is_active
                    ip_obj.save()
                    
                    status = '🟢 ATIVO' if is_active else '🔴 INATIVO'
                    self.stdout.write(
                        self.style.SUCCESS(f'🔄 IP atualizado: {ip_address} - {status}')
                    )
                else:
                    self.stdout.write(
                        self.style.WARNING(f'⚠️ IP {ip_address} já existe! Use --update para atualizar.')
                    )
                    return
            else:
                # Criar novo IP
                AllowedIP.objects.create(
                    ip_address=ip_address,
                    description=description,
                    is_active=is_active
                )
                
                status = '🟢 ATIVO' if is_active else '🔴 INATIVO'
                self.stdout.write(
                    self.style.SUCCESS(f'✅ IP adicionado: {ip_address} - {status}')
                )

            # Limpar cache para aplicação imediata
            cache.delete('allowed_ips_list')
            self.stdout.write(
                self.style.SUCCESS('🔄 Cache limpo! Alteração aplicada imediatamente.')
            )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Erro ao adicionar IP: {e}')
            )