"""
Funções de inicialização do sistema OLT
Executadas quando a aplicação Django é carregada
"""
import logging
from django.conf import settings
from ipaddress import ip_network, AddressValueError

logger = logging.getLogger(__name__)

"""
Funções de inicialização do sistema OLT
Executadas quando a aplicação Django é carregada
"""
import logging
from django.conf import settings

logger = logging.getLogger(__name__)

def import_settings_ips():
    """
    Importa automaticamente os IPs do settings.ALLOWED_IPS para a tabela AllowedIP
    Valida todos os IPs antes de importar e força aplicação imediata
    """
    try:
        # Importar aqui para evitar problemas de circular import
        from .models import AllowedIP
        from .ip_utils import validate_and_add_ip, force_refresh_allowed_ips
        
        # Obter IPs configurados no settings
        settings_ips = getattr(settings, 'ALLOWED_IPS', [])
        
        if not settings_ips:
            logger.info("📋 Nenhum IP configurado em ALLOWED_IPS no settings")
            return
            
        imported_count = 0
        updated_count = 0
        invalid_count = 0
        
        logger.info(f"📥 Importando {len(settings_ips)} IPs do settings...")
        
        for ip_entry in settings_ips:
            try:
                # Usar função de validação e adição
                success, message, ip_object = validate_and_add_ip(
                    ip_address=ip_entry,
                    description=f'Importado automaticamente do settings.py',
                    force_active=True
                )
                
                if success:
                    if "adicionado" in message:
                        imported_count += 1
                    elif "reativado" in message:
                        updated_count += 1
                    logger.info(f"✅ {ip_entry}: {message}")
                else:
                    invalid_count += 1
                    logger.warning(f"⚠️  {ip_entry}: {message}")
                
            except Exception as e:
                invalid_count += 1
                logger.error(f"❌ Erro ao processar IP {ip_entry}: {e}")
                continue
        
        # Forçar atualização do cache após importação
        if imported_count > 0 or updated_count > 0:
            logger.info(f"📥 Importação concluída: {imported_count} novos, {updated_count} reativados")
            
            # Atualizar cache imediatamente
            cache_success, cache_message, active_ips = force_refresh_allowed_ips()
            if cache_success:
                logger.info(f"🔄 {cache_message}")
            else:
                logger.error(f"❌ Erro ao atualizar cache: {cache_message}")
        else:
            logger.info("📋 Todos os IPs válidos do settings já estão importados e ativos")
            
        if invalid_count > 0:
            logger.warning(f"⚠️  {invalid_count} IPs com formato inválido foram ignorados")
            
    except Exception as e:
        logger.error(f"❌ Erro durante importação automática de IPs: {e}")

def cleanup_inactive_ips():
    """
    Remove IPs inativos que não estão mais no settings
    Mantém apenas IPs que estão no settings ou foram adicionados manualmente
    """
    try:
        from .models import AllowedIP
        
        settings_ips = getattr(settings, 'ALLOWED_IPS', [])
        
        # Encontrar IPs que não estão mais no settings e não foram adicionados manualmente
        inactive_ips = AllowedIP.objects.filter(
            description__contains='Importado automaticamente do settings.py'
        ).exclude(ip_address__in=settings_ips)
        
        if inactive_ips.exists():
            count = inactive_ips.count()
            inactive_ips.delete()
            logger.info(f"🧹 Removidos {count} IPs que não estão mais no settings")
            
            # Limpar cache após limpeza
            from django.core.cache import cache
            cache.delete('allowed_ips_cache')
            
    except Exception as e:
        logger.error(f"❌ Erro durante limpeza de IPs inativos: {e}")

def startup_tasks():
    """
    Executa todas as tarefas de inicialização do sistema
    """
    logger.info("🚀 Iniciando tarefas de startup do sistema OLT...")
    
    # Importar IPs do settings
    import_settings_ips()
    
    logger.info("✅ Tarefas de startup concluídas")