"""
Comando melhorado para importar IPs permitidos do settings.py
Execução: docker compose exec web python manage.py sync_allowed_ips
"""
from django.core.management.base import BaseCommand
from django.conf import settings
from olt.models import AllowedIP
from django.core.cache import cache


class Command(BaseCommand):
    help = 'Sincroniza IPs permitidos do settings.py com o banco de dados'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Força a sincronização mesmo se já existirem IPs no banco',
        )
        parser.add_argument(
            '--clear-cache',
            action='store_true',
            help='Limpa o cache após sincronização',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Mostra o que seria importado sem fazer alterações',
        )

    def handle(self, *args, **options):
        self.stdout.write('🔄 SINCRONIZAÇÃO DE IPs PERMITIDOS')
        self.stdout.write('=' * 40)
        
        # Obtém IPs do settings
        settings_ips = getattr(settings, 'ALLOWED_IPS', [])
        
        if not settings_ips:
            self.stdout.write(
                self.style.WARNING('⚠️ Nenhum IP encontrado em ALLOWED_IPS no settings.py')
            )
            return

        # Descrições padrão para IPs conhecidos
        ip_descriptions = {
            '127.0.0.1': 'Localhost',
            '::1': 'Localhost IPv6',
            '177.22.126.77': 'Servidor Principal',
            '177.22.126.64': 'Servidor Secundário',
            '172.16.0.0/12': 'Redes Docker Privadas',
            '192.168.0.0/16': 'Redes Privadas Locais',
            '10.0.0.0/8': 'Redes Privadas',
            '192.168.90.0/24': 'Rede Local Adicional',
            '131.221.240.101': 'Servidor de Inatel',
            '131.221.242.239': 'Servidor de Inatel 2', 
        }

        # Verifica se já existem IPs no banco
        existing_count = AllowedIP.objects.count()
        
        if existing_count > 0 and not options['force'] and not options['dry_run']:
            self.stdout.write(
                self.style.WARNING(
                    f'⚠️ Já existem {existing_count} IP(s) no banco de dados.\n'
                    'Use --force para sincronizar mesmo assim ou --dry-run para visualizar.'
                )
            )
            return

        self.stdout.write(f'📋 {len(settings_ips)} IP(s) encontrado(s) no settings.py:')
        for ip in settings_ips:
            description = ip_descriptions.get(ip, f'IP do settings - {ip}')
            self.stdout.write(f'   • {ip} - {description}')

        if options['dry_run']:
            self.stdout.write('\n🔍 DRY RUN - Nenhuma alteração foi feita.')
            return

        self.stdout.write('\n🚀 Iniciando sincronização...')

        created_count = 0
        updated_count = 0
        error_count = 0

        for ip in settings_ips:
            description = ip_descriptions.get(ip, f'IP do settings - {ip}')
            
            try:
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
                        self.style.SUCCESS(f'✅ Criado: {ip} - {description}')
                    )
                else:
                    # Atualiza descrição se forçado
                    if options['force']:
                        allowed_ip.description = description
                        allowed_ip.is_active = True
                        allowed_ip.save()
                        updated_count += 1
                        self.stdout.write(
                            self.style.WARNING(f'🔄 Atualizado: {ip} - {description}')
                        )
                    else:
                        self.stdout.write(
                            self.style.WARNING(f'⚠️ Já existe: {ip}')
                        )
                        
            except Exception as e:
                error_count += 1
                self.stdout.write(
                    self.style.ERROR(f'❌ Erro ao processar {ip}: {e}')
                )

        # Limpar cache se solicitado
        if options['clear_cache']:
            cache.delete('allowed_ips_list')
            self.stdout.write(
                self.style.SUCCESS('🗑️ Cache limpo!')
            )

        # Resumo
        self.stdout.write('')
        self.stdout.write('📊 RESUMO DA SINCRONIZAÇÃO:')
        self.stdout.write('=' * 30)
        
        if created_count > 0:
            self.stdout.write(
                self.style.SUCCESS(f'✅ {created_count} IP(s) criado(s)')
            )
        if updated_count > 0:
            self.stdout.write(
                self.style.SUCCESS(f'🔄 {updated_count} IP(s) atualizado(s)')
            )
        if error_count > 0:
            self.stdout.write(
                self.style.ERROR(f'❌ {error_count} erro(s)')
            )
        
        if created_count == 0 and updated_count == 0 and error_count == 0:
            self.stdout.write(
                self.style.WARNING('ℹ️ Nenhuma alteração necessária')
            )
        
        # Status final
        total_ips = AllowedIP.objects.filter(is_active=True).count()
        self.stdout.write('')
        self.stdout.write(
            self.style.SUCCESS(
                f'🎯 Total de IPs ativos no sistema: {total_ips}\n'
                '📝 Gerencie IPs através do Django Admin: /admin/olt/allowedip/'
            )
        )