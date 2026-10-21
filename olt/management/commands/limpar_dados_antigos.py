"""Apaga dados antigos conforme olt/retencao.py. Roda sozinho 1x por dia no
container `scheduler`; aqui é para rodar na mão ou conferir antes (--dry-run)."""
from django.core.management.base import BaseCommand

from olt.retencao import limpar_dados_antigos


class Command(BaseCommand):
    help = 'Apaga mensagens de syslog, eventos e snapshots mais antigos que a retenção'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Só conta, não apaga')

    def handle(self, *args, **options):
        for descricao, dias, n in limpar_dados_antigos(dry_run=options['dry_run']):
            acao = 'seriam apagados' if options['dry_run'] else 'apagados'
            self.stdout.write(f"{descricao} (retenção {dias} dias): {n} {acao}")
