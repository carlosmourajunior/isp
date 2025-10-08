"""
Comando para sincronizar IPs do settings.py com a tabela AllowedIP
"""
from django.core.management.base import BaseCommand
from django.conf import settings
from olt.models import AllowedIP
from ipaddress import ip_network, AddressValueError
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Sincroniza IPs do settings.ALLOWED_IPS com a tabela AllowedIP'

    def add_arguments(self, parser):
        parser.add_argument(
            '--cleanup',
            action='store_true',
            help='Remove IPs que não estão mais no settings',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Força a reativação de IPs inativos',
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('🚀 Iniciando sincronização de IPs do settings...')
        )
        
        # Obter IPs configurados no settings
        settings_ips = getattr(settings, 'ALLOWED_IPS', [])
        
        if not settings_ips:
            self.stdout.write(
                self.style.WARNING('⚠️  Nenhum IP configurado em ALLOWED_IPS no settings')
            )
            return
            
        self.stdout.write(f"📋 Encontrados {len(settings_ips)} IPs no settings")
        
        imported_count = 0
        updated_count = 0
        
        # Importar/atualizar IPs
        for ip_entry in settings_ips:
            try:
                # Validar se é um IP ou CIDR válido
                try:
                    ip_network(ip_entry, strict=False)
                except AddressValueError:
                    self.stdout.write(
                        self.style.WARNING(f"⚠️  IP inválido ignorado: {ip_entry}")
                    )
                    continue
                
                # Verificar se já existe
                allowed_ip, created = AllowedIP.objects.get_or_create(
                    ip_address=ip_entry,
                    defaults={
                        'description': f'Importado automaticamente do settings.py',
                        'is_active': True
                    }
                )
                
                if created:
                    imported_count += 1
                    self.stdout.write(
                        self.style.SUCCESS(f"✅ IP importado: {ip_entry}")
                    )
                else:
                    # Atualizar se estava inativo ou se forçado
                    if not allowed_ip.is_active or options['force']:
                        allowed_ip.is_active = True
                        if 'Importado automaticamente' not in allowed_ip.description:
                            allowed_ip.description = f'Sincronizado com settings.py - {allowed_ip.description}'
                        allowed_ip.save()
                        updated_count += 1
                        self.stdout.write(
                            self.style.SUCCESS(f"🔄 IP atualizado: {ip_entry}")
                        )
                    else:
                        self.stdout.write(f"📌 IP já existe e está ativo: {ip_entry}")
                
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"❌ Erro ao processar IP {ip_entry}: {e}")
                )
                continue
        
        # Limpeza opcional
        if options['cleanup']:
            self.stdout.write("🧹 Executando limpeza de IPs obsoletos...")
            
            # Encontrar IPs que não estão mais no settings
            obsolete_ips = AllowedIP.objects.filter(
                description__contains='Importado automaticamente do settings.py'
            ).exclude(ip_address__in=settings_ips)
            
            if obsolete_ips.exists():
                count = obsolete_ips.count()
                ips_list = list(obsolete_ips.values_list('ip_address', flat=True))
                obsolete_ips.delete()
                
                self.stdout.write(
                    self.style.WARNING(f"🗑️  Removidos {count} IPs obsoletos:")
                )
                for ip in ips_list:
                    self.stdout.write(f"   - {ip}")
            else:
                self.stdout.write("✅ Nenhum IP obsoleto encontrado")
        
        # Limpar cache
        try:
            from django.core.cache import cache
            cache.delete('allowed_ips_cache')
            self.stdout.write("🧹 Cache de IPs limpo")
        except Exception as e:
            self.stdout.write(
                self.style.WARNING(f"⚠️  Erro ao limpar cache: {e}")
            )
        
        # Resumo final
        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                f"✅ Sincronização concluída: {imported_count} novos, {updated_count} atualizados"
            )
        )
        
        if not options['cleanup']:
            self.stdout.write(
                self.style.WARNING(
                    "💡 Use --cleanup para remover IPs que não estão mais no settings"
                )
            )