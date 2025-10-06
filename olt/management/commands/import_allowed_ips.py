"""
Comando para importar IPs permitidos do settings.py para o banco de dados.
Execução: python manage.py import_allowed_ips
"""
from django.core.management.base import BaseCommand
from django.conf import settings
from olt.models import AllowedIP


class Command(BaseCommand):
    help = 'Importa IPs permitidos do settings.py para o banco de dados'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Força a importação mesmo se já existirem IPs no banco',
        )

    def handle(self, *args, **options):
        # Verifica se já existem IPs no banco
        existing_count = AllowedIP.objects.count()
        
        if existing_count > 0 and not options['force']:
            self.stdout.write(
                self.style.WARNING(
                    f'Já existem {existing_count} IP(s) no banco de dados. '
                    'Use --force para importar mesmo assim.'
                )
            )
            return

        # Obtém IPs do settings
        settings_ips = getattr(settings, 'ALLOWED_IPS', [])
        
        if not settings_ips:
            self.stdout.write(
                self.style.WARNING('Nenhum IP encontrado em ALLOWED_IPS no settings.py')
            )
            return

        # Descrições padrão para IPs conhecidos
        ip_descriptions = {
            '127.0.0.1': 'Localhost',
            '::1': 'Localhost IPv6',
            '177.22.126.77': 'Servidor Principal',
            '172.16.0.0/12': 'Redes Docker Privadas',
            '192.168.0.0/16': 'Redes Privadas Locais',
            '10.0.0.0/8': 'Redes Privadas',
            '192.168.90.0/24': 'Rede Local Adicional',
        }

        created_count = 0
        updated_count = 0

        for ip in settings_ips:
            description = ip_descriptions.get(ip, f'Importado do settings - {ip}')
            
            allowed_ip, created = AllowedIP.objects.get_or_create(
                ip_address=ip,
                defaults={
                    'description': description,
                    'is_active': True
                }
            )
            
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'✓ Criado: {ip} - {description}')
                )
            else:
                # Atualiza apenas se forçado
                if options['force']:
                    allowed_ip.description = description
                    allowed_ip.is_active = True
                    allowed_ip.save()
                    updated_count += 1
                    self.stdout.write(
                        self.style.WARNING(f'↻ Atualizado: {ip} - {description}')
                    )

        # Resumo
        self.stdout.write('')
        if created_count > 0:
            self.stdout.write(
                self.style.SUCCESS(f'✅ {created_count} IP(s) importado(s) com sucesso!')
            )
        if updated_count > 0:
            self.stdout.write(
                self.style.SUCCESS(f'🔄 {updated_count} IP(s) atualizado(s)!')
            )
        
        if created_count == 0 and updated_count == 0:
            self.stdout.write(
                self.style.WARNING('Nenhum IP foi importado ou atualizado.')
            )
        
        self.stdout.write('')
        self.stdout.write(
            self.style.SUCCESS(
                '🎯 Agora você pode gerenciar os IPs através do Django Admin em:'
                '\n   /admin/olt/allowedip/'
            )
        )