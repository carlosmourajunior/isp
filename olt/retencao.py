"""
Limpeza de dados antigos (roda 1x por dia no container `scheduler` e via
manage.py limpar_dados_antigos).

O syslog com msg-type all gera ~35 mil mensagens/dia por OLT, quase tudo RDI
e alarmes de nível de sinal que o sistema não usa. Retenção por uso:
- mensagens cruas (inclui comandos de CLI): só servem para reprocessar se o
  parser mudar -> curto;
- eventos 'other' (RDI, nível de sinal): só consulta -> curto;
- desconexões (LOS / ONT inativa) e dying gasp: base da inferência e do
  histórico do cliente -> longo;
- snapshots de ONT: histórico de distância/sinal -> longo.

Prazos configuráveis por variável de ambiente (dias).
"""
import logging
import os
from datetime import timedelta

from django.utils import timezone

from olt.models import OltSyslogMessage, OntEvent, OntSnapshot

logger = logging.getLogger(__name__)

LOTE = 5000


def _dias(var, padrao):
    try:
        return max(1, int(os.getenv(var, padrao)))
    except ValueError:
        return padrao


def politicas():
    """(descrição, queryset de candidatos, dias) - avaliado na hora para pegar o .env atual."""
    eventos_longos = OntEvent.TYPES_QUEDA + (OntEvent.TYPE_DYING_GASP,)
    return [
        ('mensagens cruas do syslog', OltSyslogMessage.objects.all(), 'received_at',
         _dias('RETENCAO_SYSLOG_BRUTO_DIAS', 7)),
        ('eventos "outro" (RDI, nível de sinal)', OntEvent.objects.exclude(event_type__in=eventos_longos), 'occurred_at',
         _dias('RETENCAO_EVENTOS_OUTROS_DIAS', 7)),
        ('desconexões e dying gasp', OntEvent.objects.filter(event_type__in=eventos_longos), 'occurred_at',
         _dias('RETENCAO_EVENTOS_QUEDA_DIAS', 180)),
        ('snapshots de ONT', OntSnapshot.objects.all(), 'taken_at',
         _dias('RETENCAO_SNAPSHOTS_DIAS', 180)),
    ]


def _apagar_em_lotes(qs):
    """Apaga por lotes de ids - um DELETE gigante travaria a tabela que o syslog está escrevendo."""
    total = 0
    while True:
        ids = list(qs.values_list('id', flat=True)[:LOTE])
        if not ids:
            return total
        apagados, _ = qs.model.objects.filter(id__in=ids).delete()
        total += len(ids)


def limpar_dados_antigos(agora=None, dry_run=False):
    """Devolve [(descrição, dias, quantidade)]."""
    agora = agora or timezone.now()
    resultado = []
    for descricao, qs, campo, dias in politicas():
        antigos = qs.filter(**{f'{campo}__lt': agora - timedelta(days=dias)})
        n = antigos.count() if dry_run else _apagar_em_lotes(antigos)
        resultado.append((descricao, dias, n))
    if not dry_run:
        logger.info("Limpeza de dados antigos: " + "; ".join(f"{d} (>{dias}d): {n}" for d, dias, n in resultado))
    return resultado
