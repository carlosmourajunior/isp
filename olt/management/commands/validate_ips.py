"""
Comando para validar todos os IPs existentes e atualizar cache em tempo real
"""
from django.core.management.base import BaseCommand
from olt.models import AllowedIP
from olt.ip_utils import validate_ip_address, force_refresh_allowed_ips


class Command(BaseCommand):
    help = 'Valida todos os IPs existentes e atualiza cache em tempo real'

    def add_arguments(self, parser):
        parser.add_argument(
            '--fix-invalid',
            action='store_true',
            help='Desativa IPs com formato inválido',
        )
        parser.add_argument(
            '--show-all',
            action='store_true',
            help='Mostra todos os IPs, incluindo inativos',
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('🔍 Validando todos os IPs no sistema...')
        )
        
        # Buscar todos os IPs (ativos e inativos se solicitado)
        if options['show_all']:
            all_ips = AllowedIP.objects.all()
        else:
            all_ips = AllowedIP.objects.filter(is_active=True)
        
        self.stdout.write(f"📋 Encontrados {all_ips.count()} IPs para validar")
        self.stdout.write("")
        
        valid_count = 0
        invalid_count = 0
        fixed_count = 0
        
        for ip_obj in all_ips:
            is_valid = validate_ip_address(ip_obj.ip_address)
            status_icon = "🟢" if ip_obj.is_active else "🔴"
            
            if is_valid:
                valid_count += 1
                self.stdout.write(
                    f"✅ {status_icon} {ip_obj.ip_address:<20} - {ip_obj.description}"
                )
            else:
                invalid_count += 1
                self.stdout.write(
                    self.style.ERROR(
                        f"❌ {status_icon} {ip_obj.ip_address:<20} - FORMATO INVÁLIDO - {ip_obj.description}"
                    )
                )
                
                if options['fix_invalid'] and ip_obj.is_active:
                    ip_obj.is_active = False
                    ip_obj.description = f"[DESATIVADO - FORMATO INVÁLIDO] {ip_obj.description}"
                    ip_obj.save()
                    fixed_count += 1
                    self.stdout.write(
                        self.style.WARNING(f"🔧 IP {ip_obj.ip_address} foi desativado automaticamente")
                    )
        
        # Resumo
        self.stdout.write("")
        self.stdout.write("=" * 60)
        self.stdout.write(f"📊 RESUMO DA VALIDAÇÃO:")
        self.stdout.write(f"   ✅ IPs válidos: {valid_count}")
        self.stdout.write(f"   ❌ IPs inválidos: {invalid_count}")
        
        if options['fix_invalid']:
            self.stdout.write(f"   🔧 IPs corrigidos: {fixed_count}")
        
        # Atualizar cache
        self.stdout.write("")
        self.stdout.write(self.style.WARNING('🔄 Atualizando cache...'))
        
        cache_success, cache_message, active_ips = force_refresh_allowed_ips()
        
        if cache_success:
            self.stdout.write(self.style.SUCCESS(cache_message))
        else:
            self.stdout.write(self.style.ERROR(cache_message))
        
        # Dicas finais
        self.stdout.write("")
        if invalid_count > 0 and not options['fix_invalid']:
            self.stdout.write(
                self.style.WARNING(
                    "💡 Use --fix-invalid para desativar automaticamente IPs com formato inválido"
                )
            )
        
        self.stdout.write(
            self.style.SUCCESS("✅ Validação concluída! Cache atualizado.")
        )