"""
Sinais para gerenciar cache de IPs permitidos
"""
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.cache import cache
from olt.models import AllowedIP


@receiver(post_save, sender=AllowedIP)
def clear_allowed_ips_cache_on_save(sender, instance, **kwargs):
    """
    Limpa o cache de IPs permitidos quando um IP é salvo
    """
    cache.delete('allowed_ips_list')


@receiver(post_delete, sender=AllowedIP)  
def clear_allowed_ips_cache_on_delete(sender, instance, **kwargs):
    """
    Limpa o cache de IPs permitidos quando um IP é deletado
    """
    cache.delete('allowed_ips_list')