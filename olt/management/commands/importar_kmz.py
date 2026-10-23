"""
Importa o projeto da rede (KMZ/KML): enriquece as CTOs do IXC com ramal,
portas e splitter, marca a OLT e cria as caixas que só existem no KMZ
(origem 'kmz').

    python manage.py importar_kmz "data/kmz/Borda da mata.kml" --olt 1 --dry-run --detalhe
    python manage.py importar_kmz "data/kmz/Borda da mata.kml" --olt 1
    python manage.py importar_kmz /tmp/inconfidentes.kml            # sem OLT no sistema ainda

Rodar sync_ctos_ixc antes (o KMZ complementa o cadastro do IXC). Pode ser
rodado de novo sem duplicar nada.
"""
from collections import Counter

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from olt.kmz import (haversine_m, iter_placemarks, match_ctos, nome_para_exibir, normalize_name, parse_cto_placemark,
                     read_kml_bytes)
from olt.kmz_topologia import chave as chave_topologia, topologia
from olt.models import Cto, Olt

# Reimportação: caixa só-KMZ com mesmo nome até esta distância é a mesma caixa.
SAME_KMZ_BOX_M = 15


class Command(BaseCommand):
    help = 'Importa o KMZ do projeto da rede e casa as caixas com as CTOs do IXC'

    def add_arguments(self, parser):
        parser.add_argument('arquivo')
        parser.add_argument('--olt', type=int, help='id da OLT que atende essa rede (opcional: sem ele as caixas '
                                                    'entram sem OLT e mantêm a que já tinham)')
        parser.add_argument('--dry-run', action='store_true', help='Só mostra o resultado, não grava')
        parser.add_argument('--detalhe', action='store_true',
                            help='Lista as caixas sem par com a CTO do IXC mais próxima e a distância')
        parser.add_argument('--sem-criar', action='store_true',
                            help='Não cria as caixas que só existem no KMZ')

    def handle(self, *args, **options):
        olt = None
        if options['olt']:
            try:
                olt = Olt.objects.get(id=options['olt'])
            except Olt.DoesNotExist:
                raise CommandError(f"OLT {options['olt']} não existe")

        ixc_ctos = list(Cto.objects.filter(is_active=True, origem=Cto.ORIGEM_IXC))
        if not ixc_ctos:
            raise CommandError("Nenhuma CTO do IXC no banco - rode antes: python manage.py sync_ctos_ixc")

        kml_bytes = read_kml_bytes(options['arquivo'])
        kmz_ctos = [c for c in (parse_cto_placemark(p) for p in iter_placemarks(kml_bytes)) if c]
        topo = topologia(kml_bytes, kmz_ctos)
        for c in kmz_ctos:
            c['topologia'] = topo.get(chave_topologia(c))
        matches = match_ctos(kmz_ctos, ixc_ctos)

        # Uma CTO do IXC casada com duas caixas do KMZ fica com a mais próxima.
        best = {}
        for kmz, cto, metodo, dist in matches:
            if cto and (cto.pk not in best or (dist or 0) < (best[cto.pk][3] or 0)):
                best[cto.pk] = (kmz, cto, metodo, dist)
        casadas_ids = {id(v[0]) for v in best.values()}
        duplicadas = [k for k, cto, _, _ in matches if cto and id(k) not in casadas_ids]
        sem_par = [k for k, cto, _, _ in matches if not cto]

        metodos = Counter(m for _, _, m, _ in best.values())
        self.stdout.write(f"Caixas no KMZ: {len(kmz_ctos)} | casadas com o IXC: {len(best)} "
                          f"(por nome: {metodos.get('nome', 0)}, por coordenada: {metodos.get('coordenada', 0)}) | "
                          f"só no KMZ: {len(sem_par)} | duplicadas no KMZ (ignoradas): {len(duplicadas)}")
        self.stdout.write(f"Casadas por ramal: {dict(sorted(Counter(k['ramal'] or '(sem ramal)' for k, _, _, _ in best.values()).items()))}")
        self.stdout.write(f"Só no KMZ por tipo: {dict(Counter(k['tipo'] for k in sem_par))}"
                          f" | sem nome no KMZ: {sum(1 for k in kmz_ctos if not k['name'])}")
        com_topo = [k for k in kmz_ctos if k['topologia'] and k['tipo'] != 'CD']
        self.stdout.write(f"Topologia (CEO de cada caixa): {len(com_topo)} de {sum(1 for k in kmz_ctos if k['tipo'] != 'CD')} "
                          f"caixas | {dict(Counter(k['topologia']['metodo'] for k in com_topo))} | "
                          f"{len({k['topologia']['ceo'] for k in com_topo})} splitters de distribuição")
        if options['detalhe']:
            por_ceo = {}
            for k in com_topo:
                por_ceo.setdefault(k['topologia']['ceo'], []).append(nome_para_exibir(k))
            for ceo, nomes in sorted(por_ceo.items()):
                self.stdout.write(f"  {ceo:<28} ({len(nomes)}): {', '.join(sorted(nomes))}")
        if duplicadas:
            self.stdout.write("Duplicadas (mesmo nome, mesma CTO do IXC, mais longe): "
                              + ', '.join(f"{k['name']} ({k['ramal'] or 'sem ramal'})" for k in duplicadas))

        if options['detalhe']:
            com_coord = [c for c in ixc_ctos if c.latitude is not None and c.longitude is not None]
            self.stdout.write("\nSó no KMZ -> CTO do IXC mais próxima:")
            for k in sem_par:
                c, d = min(((c, haversine_m(k['lat'], k['lon'], c.latitude, c.longitude)) for c in com_coord),
                           key=lambda x: x[1], default=(None, None))
                perto = f"{c.descricao} (IXC {c.ixc_id}) a {d:.0f} m" if c else "nenhuma CTO do IXC com coordenada"
                self.stdout.write(f"  {nome_para_exibir(k):<32} {k['ramal'] or '(sem ramal)':<11} -> {perto}")

        if options['dry_run']:
            self.stdout.write(self.style.WARNING("--dry-run: nada gravado"))
            return

        criadas = atualizadas_kmz = 0
        with transaction.atomic():
            for kmz, cto, metodo, dist in best.values():
                self._aplicar_kmz(cto, kmz, olt, metodo)
                cto.save()

            if not options['sem_criar']:
                existentes = list(Cto.objects.filter(origem=Cto.ORIGEM_KMZ))
                for kmz in sem_par:
                    cto = next((c for c in existentes
                                if normalize_name(c.kmz_nome) == normalize_name(kmz['name'])
                                and c.latitude is not None
                                and haversine_m(kmz['lat'], kmz['lon'], c.latitude, c.longitude) <= SAME_KMZ_BOX_M), None)
                    if cto is None:
                        cto = Cto(origem=Cto.ORIGEM_KMZ, ixc_id=None)
                        criadas += 1
                    else:
                        atualizadas_kmz += 1
                    cto.descricao = nome_para_exibir(kmz)[:100]
                    cto.latitude, cto.longitude = kmz['lat'], kmz['lon']
                    cto.is_active = True
                    self._aplicar_kmz(cto, kmz, olt, 'so_kmz')
                    cto.save()

        self.stdout.write(self.style.SUCCESS(
            f"OLT {olt.name if olt else '(não informada)'}: {len(best)} CTOs do IXC enriquecidas com o KMZ, "
            f"{criadas} caixas só-KMZ criadas, {atualizadas_kmz} atualizadas"))

    @staticmethod
    def _aplicar_kmz(cto, kmz, olt, metodo):
        if olt is not None:
            cto.olt = olt
        cto.tipo = kmz['tipo']
        cto.ramal = kmz['ramal']
        cto.kmz_nome = kmz['name'][:100]
        cto.kmz_portas = kmz['portas']
        cto.kmz_splitter = kmz['splitter']
        cto.kmz_descricao = kmz['description']
        cto.kmz_match = metodo
        t = kmz.get('topologia') or {}
        cto.kmz_ceo = (t.get('ceo') or '')[:80]
        cto.kmz_ceo_saida = t.get('ceo_saida')
        cto.kmz_alimentacao = (t.get('alimentacao') or '')[:80]
        cto.kmz_cabo = (t.get('cabo') or '')[:120]
        cto.kmz_topologia = t.get('metodo') or ''
