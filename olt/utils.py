# import netmiko library
import base64
from datetime import datetime
import time
import logging
from netmiko import ConnectHandler
from olt.models import ONU, ClienteFibraIxc, Olt, OltUsers, OltSystemInfo, OltSlot, OltTemperature, OltSfpDiagnostics, OntSnapshot
import re
from dotenv import load_dotenv
import os
from django.utils import timezone

# Carregar variáveis de ambiente do arquivo .env
load_dotenv()

logger = logging.getLogger('olt.connector')


def get_default_olt():
    """OLT usada quando nenhuma é escolhida explicitamente. Views de template
    legadas (olt/views.py) e admin actions (olt/admin.py) ainda instanciam os
    conectores sem escolher uma OLT - com uma só OLT ativa cadastrada isso
    reproduz o comportamento de antes do sistema virar multi-OLT."""
    return Olt.objects.filter(is_active=True).order_by('id').first()


def build_connect_kwargs(olt, extra=None):
    """Cria kwargs SSH (netmiko) compatíveis com a versão instalada de
    Paramiko/Netmiko a partir de um registro Olt."""
    kwargs = {
        'device_type': olt.device_type,
        'host': olt.host,
        'username': olt.username,
        'password': olt.password,
        'port': olt.ssh_port,
        'verbose': olt.verbose,
        'global_delay_factor': olt.global_delay_factor,
        'ssh_strict': False,
    }
    if extra:
        kwargs.update(extra)
    # Alguns ambientes antigos não aceitam esses argumentos de autenticação.
    for key in ('allow_agent', 'look_for_keys', 'use_keys'):
        kwargs.pop(key, None)
    return kwargs


def extract_olt_info(line):
    """Extract PON, port, and MAC from OLT output line."""
    pattern = r'(\d+/\d+/\d+/\d+)/(\d+)/\d+\s+\d+\s+([0-9a-f:]+)'
    match = re.search(pattern, line, re.IGNORECASE)

    if match:
        return {
            'pon': match.group(1),
            'port': match.group(2),
            'mac': match.group(3)
        }
    return None


def create_dict_from_result(data):
    '''
        1/1/1/14   1/1/1/14/90    RCMG:3A88390E up       up       -23.0       0.5           tomazpaiva                                        tomazpaiva                                        undefined
        1/1/1/14   1/1/1/14/91    ALCL:B3FD63A5 up       up       -22.3       0.8           vitorfrancisco                                    vitorfrancisco                                    undefined
        1/1/1/14   1/1/1/14/92    TPLG:00CEA2A8 up       up       -25.5       0.8           andressasantos                                    andressasantos                                    undefined
        1/1/1/14   1/1/1/14/93    RCMG:3A900F62 up       up       -23.7       0.6           wendersoncarvalho                                 wendersoncarvalho                                 undefined
        1/1/1/14   1/1/1/14/94    RCMG:3A88121C up       up       -23.5       0.8           harlenycobra                                      harlenycobra                                      undefined
        1/1/1/14   1/1/1/14/95    RCMG:3A900819 up       up       -23.5       0.4           mateusmarlise                                     mateusmarlise                                     undefined
        1/1/1/14   1/1/1/14/96    RCMG:19897186 up       down     invalid     invalid       sedeprefeitura02                                  sedeprefeitura02                                  undefined
        1/1/1/14   1/1/1/14/97    RCMG:3A9001A8 up       up       -26.9       0.6           iraidedasilva                                     iraidedasilva                                     undefined
        1/1/1/14   1/1/1/14/98    ALCL:B3FD7281 up       up       -23.4       0.6           PABX                                              Prefeitura                                        undefined
        1/1/1/14   1/1/1/14/99    RCMG:19897299 up       up       -22.0       0.6           zema                                              zema                                              undefined
        1/1/1/14   1/1/1/14/100   RCMG:3AB87E24 up       up       -23.4       0.4           associacaoborda                                   associacaoborda                                   undefined
        1/1/1/14   1/1/1/14/101   ALCL:F881EC74 up       up       -22.4       0.6           maurarezende                                      maurarezende                                      undefined
        1/1/1/14   1/1/1/14/102   SHLN:1201A090 up       up       -27.2       0.5           fb2efd70                                          fb2efd70                                          undefined
        1/1/1/14   1/1/1/14/103   ALCL:B3D6ADAF up       up       -21.9       0.3           gabrielescritorio                                 gabrielescritorio                                 undefined
        1/1/1/14   1/1/1/14/104   HWTC:03282910 up       up       -22.6       0.4           8ef83f14                                          8ef83f14                                          undefined
        1/1/1/14   1/1/1/14/106   RCMG:3A900D2B up       up       -22.7       0.5           thaisavo                                          thaisavo                                          undefined
        1/1/1/14   1/1/1/14/107   RCMG:3A9010EF up       up       -23.6       0.5           alexandremedeiros                                 alexandremedeiros                                 undefined
        1/1/1/14   1/1/1/14/108   HWTC:03297F70 up       up       -24.4       0.6           mariacaetano                                      mariacaetano                                      undefined
        1/1/1/14   1/1/1/14/109   RCMG:3A900ABB up       up       -24.4       0.5           tottiloja                                         tottiloja                                         undefined
        1/1/1/14   1/1/1/14/110   ALCL:F881C42C up       up       -28.8       0.7           veronicapaiva                                     veronicapaiva                                     undefined
        1/1/1/14   1/1/1/14/111   HWTC:032A1CA0 up       up       -22.8       0.8                                                                                                               undefined
        1/1/1/14   1/1/1/14/112   RCMG:3A9002FC up       up       -23.9       0.5           dorissantana                                      dorissantana                                      undefined
        1/1/1/14   1/1/1/14/113   HWTC:03282860 up       up       -23.8       0.4           cleitonclube                                      cleitonclube                                      undefined
        1/1/1/14   1/1/1/14/115   HWTC:03285540 up       up       -24.9       0.6           michelcasa                                        michelcasa                                        undefined
        1/1/1/14   1/1/1/14/116   RCMG:3A9016F8 up       down     invalid     invalid       dondokaateliealine                                dondokaateliealine                                undefined
        1/1/1/14   1/1/1/14/117   OPTI:35013849 up       up       -25.5       0.7           carolinacasa                                      carolinacasa                                      undefined
        1/1/1/14   1/1/1/14/118   ALCL:FBE0EB05 up       up       -23.2       0.7           departamentoeducacao                              departamentoeducacao                              undefined

    '''

    pattern = r'\s*(\d+/\d+/\d+/\d+)\s+(\d+/\d+/\d+/\d+/\d+)\s+(\w+:\w+)\s+(\w+)\s+(\w+|invalid)\s+([-.\d]+|invalid)\s+([-.\d]+|invalid)\s+(.*?)\s+(.*?)\s+(.*?)\s*'

    data_list = []
    matches = re.findall(pattern, data)
    for match in matches:
        pon = match[0]
        position = match[1].split("/")[-1]
        sernum = match[2]
        admin_status = match[3]
        oper_status = match[4]
        olt_rx_sig = match[5]
        ont_olt = match[6]
        desc1 = match[7]
        desc2 = match[8]

        data_list.append( {
            'pon': pon,
            'position': position,
            'sernum': sernum,
            'admin_status': admin_status,
            'oper_status': oper_status,
            'olt_rx_sig': olt_rx_sig,
            'ont_olt': ont_olt,
            'desc1': desc1,
            'desc2': desc2
        })
    return data_list


def parse_float(value):
    """'-23.0' -> -23.0; 'invalid'/'unknown'/vazio (ONU offline) -> None."""
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


COUNT_RE = re.compile(r'count\s*:\s*(\d+)', re.IGNORECASE)


def contagem_onts(output):
    """Linha "ont count : N" do `show equipment ont status pon` -> N (None se não veio)."""
    m = COUNT_RE.search(output or '')
    return int(m.group(1)) if m else None


def macs_do_fdb(output):
    """`show vlan bridge-port-fdb` -> {(pon, position): mac}. Se a ONU tiver mais
    de um MAC aprendido, fica o último (mesmo comportamento de antes)."""
    resultado = {}
    for line in (output or '').splitlines():
        data = extract_olt_info(line)
        if data:
            parts = data['pon'].split('/')
            resultado[(f"1/{'/'.join(parts[:3])}", int(parts[-1]))] = data['mac']
    return resultado


def parse_optics_output(output):
    """`show equipment ont optics` -> {(pon, position): (ont_rx, ont_tx)}.

    A OLT devolve 'unknown' para ONU offline; viram None para não exibir
    sinal velho.
    """
    def to_float(value):
        try:
            return float(value)
        except (ValueError, TypeError):
            return None

    result = {}
    for line in output.splitlines():
        match = re.match(r'\s*(\d+/\d+/\d+/\d+)/(\d+)\s+(\S+)\s+(\S+)', line)
        if match:
            pon, position, rx, tx = match.groups()
            result[(pon, int(position))] = (to_float(rx), to_float(tx))
    return result


class olt_connector():

    def __init__(self, olt=None):
        self.olt = olt or get_default_olt()
        if self.olt is None:
            raise ValueError('Nenhuma OLT ativa cadastrada')
        self.nokia = build_connect_kwargs(self.olt)

    def connect(self):
        # Connect to OLT
        net_connect = ConnectHandler(**self.nokia)
        net_connect.find_prompt()

        return net_connect

    def disconnect(self, net_connect):
        net_connect.disconnect()

    def get_onu_detail(self, item):
        net_connect = self.connect()
        ont_details = f'show vlan bridge-port-fdb {item}/14/1'
        output_details = net_connect.send_command(ont_details)
        self.disconnect(net_connect)

        return output_details

    def reset_placa_onu(self, queryset):
        pass
        # net_connect = self.connect()
        # placa = f"/{queryset.first().chassi}/{queryset.first().position}"
        # ont_details = f'show equipment slot lt:{placa} detail'.strip()
        # print(ont_details)
        # output_details = net_connect.send_command(ont_details)
        # print(output_details)
        # self.disconnect(net_connect)
        # print(output_details)
        # return output_details


    def update_port_ocupation(self, read_timeout=None, expect_string=None):
        if read_timeout is not None:
            self.read_timeout = read_timeout
        if expect_string is not None:
            self.expect_string = expect_string

        net_connect = self.connect()
        OltUsers.objects.filter(olt=self.olt).delete()

        for slot in range(1, self.olt.slot_count + 1):
            for pon in range(17):
                command = f"show equipment ont status pon 1/1/{slot}/{pon}"
                try:
                    output = net_connect.send_command(command)
                    for line in iter(output.splitlines()):
                        if "count" in line:
                            new_olt_user = OltUsers()
                            new_olt_user.olt = self.olt
                            new_olt_user.slot = slot
                            new_olt_user.port = pon
                            new_olt_user.users_connected = int(line.split(":")[1])
                            new_olt_user.last_updated = timezone.now()
                            new_olt_user.save()
                except Exception as e:
                    logger.warning(f"Falha ao ler ocupação da PON 1/1/{slot}/{pon} ({self.olt.name}): {e}")
                    continue

        self.disconnect(net_connect)

    def get_itens_to_port(self, slot, pon, order_by='position'):
        old_values = ONU.objects.filter(olt=self.olt, pon=f"1/1/{slot}/{pon}").order_by(order_by)
        return old_values

    def update_all_ports(self):
        """Lê todas as PONs numa conexão só (antes era uma conexão SSH por PON)."""
        net_connect = self.connect()
        resumo = {'criadas': 0, 'atualizadas': 0, 'removidas': 0, 'puladas': 0}
        try:
            for slot in range(1, self.olt.slot_count + 1):
                for pon in range(17):
                    pon_str = f"1/1/{slot}/{pon}"
                    try:
                        r = self._sync_pon(net_connect, pon_str)
                    except Exception as e:
                        logger.error(f"Falha ao atualizar PON {pon_str} ({self.olt.name}): {e}")
                        resumo['puladas'] += 1
                        # A sessão pode ter caído: reconecta e segue. As ONUs dessa PON ficam como estavam.
                        try:
                            self.disconnect(net_connect)
                        except Exception:
                            pass
                        net_connect = self.connect()
                        continue
                    for k in ('criadas', 'atualizadas', 'removidas'):
                        resumo[k] += r[k]
                    resumo['puladas'] += 0 if r['lida'] else 1
        finally:
            self.disconnect(net_connect)
        logger.info(f"ONUs {self.olt.name}: {resumo}")
        return resumo

    def update_optics(self):
        # Roda depois do update_all_ports (ONU nova só existe depois dele).
        net_connect = self.connect()
        try:
            output = net_connect.send_command("show equipment ont optics", read_timeout=600)
        except Exception as e:
            logger.error(f"Falha ao ler óptica das ONTs ({self.olt.name}): {e}")
            return
        finally:
            self.disconnect(net_connect)

        optics = parse_optics_output(output)
        onus = list(ONU.objects.filter(olt=self.olt))
        for onu in onus:
            onu.ont_rx_sig, onu.ont_tx_sig = optics.get((onu.pon, onu.position), (None, None))
        ONU.objects.bulk_update(onus, ['ont_rx_sig', 'ont_tx_sig'], batch_size=500)

    def update_port(self, slot, pon):
        return self.atualizar_pon(f"1/1/{slot}/{pon}")

    def atualizar_pon(self, pon_str, net_connect=None):
        """Relê uma PON da OLT e sincroniza as ONUs dela (usado também pela
        atualização individual de uma ONU)."""
        propria = net_connect is None
        net_connect = net_connect or self.connect()
        try:
            return self._sync_pon(net_connect, pon_str)
        finally:
            if propria:
                self.disconnect(net_connect)

    def _sync_pon(self, net_connect, pon_str):
        output = net_connect.send_command(f"show equipment ont status pon {pon_str}")
        linhas = create_dict_from_result(output)
        if linhas:
            self.save_snapshots(linhas)
        return self.reconciliar_pon(pon_str, linhas, contagem_onts(output))

    def reconciliar_pon(self, pon_str, linhas, contagem):
        """Sincroniza as ONUs de uma PON com o que a OLT respondeu, sem apagar tudo:

        - posição que já existia: atualiza no lugar (mantém o id e o MAC);
          se o serial mudou, é outra ONU naquela posição e o MAC/sinal da ONU velha é zerado;
        - posição nova: cria;
        - posição que sumiu: só remove quando a leitura está completa (a OLT informou
          "count" e o número bate com o que foi lido). Saída vazia, cortada ou com erro
          não apaga nada - as ONUs ficam como estavam até a próxima leitura boa.
        """
        r = {'pon': pon_str, 'lida': False, 'criadas': 0, 'atualizadas': 0, 'removidas': 0, 'aviso': ''}
        if contagem is None and not linhas:
            r['aviso'] = 'A OLT não devolveu a lista dessa PON - nada alterado.'
            return r
        completa = contagem is not None and contagem == len(linhas)
        if not completa:
            r['aviso'] = (f"Leitura incompleta ({len(linhas)} ONUs lidas, OLT informou {contagem}) - "
                          f"atualizei as lidas, sem remover nenhuma.")
            logger.warning(f"PON {pon_str} ({self.olt.name}): {r['aviso']}")
        r['lida'] = True

        existentes = {}
        for onu in ONU.objects.filter(olt=self.olt, pon=pon_str).order_by('id'):
            if onu.position in existentes:          # duplicata antiga na mesma posição
                onu.delete()
                continue
            existentes[onu.position] = onu
        seriais = {d['sernum'] for d in linhas}
        clientes = set(ClienteFibraIxc.objects.filter(mac__in=seriais, is_active=True).values_list('mac', flat=True))

        novas, alteradas = [], []
        for d in linhas:
            pos = int(d['position'])
            onu = existentes.pop(pos, None)
            if onu is None:
                onu = ONU(olt=self.olt, pon=pon_str, position=pos, mac='')
                novas.append(onu)
            else:
                if onu.serial != d['sernum']:
                    onu.mac, onu.ont_rx_sig, onu.ont_tx_sig = '', None, None
                alteradas.append(onu)
            onu.serial = d['sernum']
            onu.admin_state = d['admin_status']
            onu.oper_state = d['oper_status']
            onu.olt_rx_sig = parse_float(d['olt_rx_sig'])
            onu.ont_olt = d['ont_olt']
            onu.desc1 = d['desc1']
            onu.desc2 = d['desc2']
            onu.cliente_fibra = d['sernum'] in clientes

        ONU.objects.bulk_create(novas, batch_size=500)
        ONU.objects.bulk_update(alteradas, ['serial', 'admin_state', 'oper_state', 'olt_rx_sig', 'ont_olt', 'desc1',
                                            'desc2', 'cliente_fibra', 'mac', 'ont_rx_sig', 'ont_tx_sig'],
                                batch_size=500)
        if completa and existentes:
            ONU.objects.filter(id__in=[o.id for o in existentes.values()]).delete()
            r['removidas'] = len(existentes)
        r['criadas'], r['atualizadas'] = len(novas), len(alteradas)
        return r

    def get_mac_values(self):
        net_connect = self.connect()
        try:
            command = "environment inhibit-alarms"
            net_connect.write_channel(command)
            time.sleep(2)  # Aguarda um pouco para o comando ser processado
            command = "show vlan bridge-port-fdb"
            output = net_connect.send_command(command, read_timeout=1200)
            self.update_mac(output)
        except Exception as e:
            logger.error(f"Erro ao obter valores MAC ({self.olt.name}): {e}")
        finally:
            self.disconnect(net_connect)

    def update_mac(self, output):
        """Grava o MAC de cada ONU a partir da tabela de MACs da OLT. ONU que não
        aparece na tabela (offline / sem tráfego) fica sem MAC, como sempre foi.
        Se a leitura veio vazia (comando falhou/cortou), não mexe em nada."""
        macs = macs_do_fdb(output)
        if not macs:
            logger.error(f"Tabela de MACs vazia ({self.olt.name}) - MACs mantidos como estavam.")
            return 0
        alteradas = []
        for onu in ONU.objects.filter(olt=self.olt):
            novo = macs.get((onu.pon, onu.position), '')
            if (onu.mac or '') != novo:
                onu.mac = novo
                alteradas.append(onu)
        ONU.objects.bulk_update(alteradas, ['mac'], batch_size=500)
        logger.info(f"MAC {self.olt.name}: {len(macs)} ONUs na tabela, {len(alteradas)} alteradas")
        return len(alteradas)

    def mac_da_onu(self, pon_str, position, net_connect=None):
        """MAC de uma ONU só. Tenta a bridge-port da ONU (mesmo comando da tela de
        detalhe); se não vier nada, filtra a tabela inteira na própria OLT."""
        propria = net_connect is None
        net_connect = net_connect or self.connect()
        try:
            for comando in (f"show vlan bridge-port-fdb {pon_str}/{position}/14/1",
                            f"show vlan bridge-port-fdb | match exact:{pon_str}/{position}/"):
                output = net_connect.send_command(comando, read_timeout=40)
                mac = macs_do_fdb(output).get((pon_str, int(position)))
                if mac:
                    return mac, comando
            return '', comando
        finally:
            if propria:
                self.disconnect(net_connect)

    def update_values(self, output):
        """Compatibilidade: saída de uma PON -> reconcilia (ver reconciliar_pon)."""
        linhas = create_dict_from_result(output)
        if not linhas:
            return None
        self.save_snapshots(linhas)
        return self.reconciliar_pon(linhas[0]['pon'], linhas, contagem_onts(output))

    def save_snapshots(self, data_dict):
        # Histórico append-only: a tabela ONU só guarda o estado atual, isto
        # é o que permite saber quem já esteve em cada PON. Falha aqui não
        # pode derrubar o sync principal.
        try:
            taken_at = timezone.now()
            OntSnapshot.objects.bulk_create([
                OntSnapshot(
                    olt=self.olt,
                    taken_at=taken_at,
                    pon=data['pon'],
                    position=int(data['position']),
                    serial=data['sernum'],
                    admin_state=data['admin_status'],
                    oper_state=data['oper_status'],
                    olt_rx_sig=parse_float(data['olt_rx_sig']),
                    distance_km=parse_float(data['ont_olt']),
                )
                for data in data_dict
            ], batch_size=500)
        except Exception as e:
            logger.error(f"Falha ao gravar snapshot das ONTs ({self.olt.name}): {e}")

    def remove_onu(self, pon):
        net_connect = self.connect()
        try:
            command = f"configure equipment ont interface {pon} admin-state down\n"
            net_connect.write_channel(command)
            time.sleep(2)
            net_connect.read_channel()

            command = f"configure equipment ont no interface {pon}\n"
            net_connect.write_channel(command)
            time.sleep(2)
            net_connect.read_channel()
        except Exception as e:
            logger.error(f"Falha ao remover ONT {pon}: {e}")
        finally:
            self.disconnect(net_connect)

    def reset_onu(self, pon):
        net_connect = self.connect()
        try:
            # command = f"configure equipment ont interface {pon} admin-state down\n"
            command = f"admin equipment ont interface {pon} reboot with-active-image"
            net_connect.send_command(command)
            # time.sleep(2)
            # net_connect.read_channel()
        except Exception as e:
            logger.error(f"Falha ao reiniciar ONT {pon}: {e}")
        finally:
            self.disconnect(net_connect)

    def create_mac_dict(self, data):
        pattern = r"(\d+/\d+/\d+/\d+/\d+/\d+/\d+)\s+(\d+)\s+([a-f0-9:]+)\s+(\d+)\s+(\w+)\s+([0-9:]+)"
        matches = re.findall(pattern, data)
        data_dict = {}

        for match in matches:
            pon_value = match[0]
            parts = pon_value.split('/')
            first_five_parts = parts[:4]
            pon_first_five = '/'.join(first_five_parts)
            data_dict[match[0]] = {
                'pon': pon_first_five,
                'position': parts[-3] if len(parts) > 3 else None,
                'mac_address': match[2],
                'status_2': match[3],
                'learned': match[4],
                'time': match[5]
            }

        return data_dict


class OltSystemCollector:
    """Classe para coletar informações do sistema OLT"""

    def __init__(self, olt=None):
        self.olt = olt or get_default_olt()
        if self.olt is None:
            raise ValueError('Nenhuma OLT ativa cadastrada')
        self.nokia = build_connect_kwargs(self.olt)

    def connect(self):
        """Conecta à OLT"""
        net_connect = ConnectHandler(**self.nokia)
        net_connect.find_prompt()
        return net_connect

    def disconnect(self, net_connect):
        """Desconecta da OLT"""
        net_connect.disconnect()

    def collect_system_info(self):
        """Coleta informações do sistema (versão e uptime)"""
        net_connect = self.connect()
        try:
            # Coletar versão do sistema
            version_output = net_connect.send_command("show software-mngt version etsi")
            isam_release = self._parse_isam_release(version_output)

            # Coletar uptime
            uptime_output = net_connect.send_command("show core1-uptime")
            uptime_data = self._parse_uptime(uptime_output)

            # Atualizar ou criar registro (um por OLT)
            system_info, created = OltSystemInfo.objects.get_or_create(
                olt=self.olt,
                defaults={
                    'isam_release': isam_release,
                    'uptime_days': uptime_data['days'],
                    'uptime_hours': uptime_data['hours'],
                    'uptime_minutes': uptime_data['minutes'],
                    'uptime_seconds': uptime_data['seconds'],
                    'uptime_raw': uptime_data['raw']
                }
            )

            if not created:
                system_info.isam_release = isam_release
                system_info.uptime_days = uptime_data['days']
                system_info.uptime_hours = uptime_data['hours']
                system_info.uptime_minutes = uptime_data['minutes']
                system_info.uptime_seconds = uptime_data['seconds']
                system_info.uptime_raw = uptime_data['raw']
                system_info.save()

            return system_info

        except Exception as e:
            logger.error(f"Erro ao coletar informações do sistema ({self.olt.name}): {e}")
            return None
        finally:
            self.disconnect(net_connect)

    def collect_slot_info(self):
        """Coleta informações dos slots"""
        net_connect = self.connect()
        try:
            output = net_connect.send_command("show equipment slot")
            slots_data = self._parse_slots(output)

            # Usar transação atômica para evitar perda de dados
            from django.db import transaction
            with transaction.atomic():
                # Marcar todos os slots desta OLT como inativos primeiro
                OltSlot.objects.filter(olt=self.olt).update(is_active=False)

                # Inserir/atualizar novos dados
                for slot_data in slots_data:
                    slot_name = slot_data.pop('slot_name')
                    slot_data['is_active'] = True
                    OltSlot.objects.update_or_create(
                        olt=self.olt,
                        slot_name=slot_name,
                        defaults=slot_data
                    )

                # Remover apenas os que realmente não existem mais
                # (opcional - pode manter histórico)
                # OltSlot.objects.filter(olt=self.olt, is_active=False).delete()

            return OltSlot.objects.filter(olt=self.olt, is_active=True)

        except Exception as e:
            logger.error(f"Erro ao coletar informações dos slots ({self.olt.name}): {e}")
            return None
        finally:
            self.disconnect(net_connect)

    def collect_temperature_info(self):
        """Coleta informações de temperatura"""
        net_connect = self.connect()
        try:
            output = net_connect.send_command("show equipment temperature")
            temp_data = self._parse_temperature(output)

            # Usar transação atômica para evitar perda de dados
            from django.db import transaction
            with transaction.atomic():
                # Marcar todos os sensores desta OLT como inativos primeiro
                OltTemperature.objects.filter(olt=self.olt).update(is_active=False)

                # Inserir/atualizar novos dados
                for temp in temp_data:
                    slot_name = temp.pop('slot_name')
                    sensor_id = temp.pop('sensor_id')
                    temp['is_active'] = True
                    OltTemperature.objects.update_or_create(
                        olt=self.olt,
                        slot_name=slot_name,
                        sensor_id=sensor_id,
                        defaults=temp
                    )

                # Remover apenas os que realmente não existem mais
                # (opcional - pode manter histórico)
                # OltTemperature.objects.filter(olt=self.olt, is_active=False).delete()

            return OltTemperature.objects.filter(olt=self.olt, is_active=True)

        except Exception as e:
            logger.error(f"Erro ao coletar informações de temperatura ({self.olt.name}): {e}")
            return None
        finally:
            self.disconnect(net_connect)

    def collect_all_system_data(self):
        """Coleta todas as informações do sistema"""
        try:
            system_info = self.collect_system_info()
            slots = self.collect_slot_info()
            temperatures = self.collect_temperature_info()

            return {
                'system_info': system_info,
                'slots': slots,
                'temperatures': temperatures
            }
        except Exception as e:
            logger.error(f"Erro ao coletar dados do sistema ({self.olt.name}): {e}")
            return None

    def _parse_isam_release(self, output):
        """Extrai a versão ISAM do output"""
        try:
            match = re.search(r'isam-release\s*:\s*(\S+)', output)
            return match.group(1) if match else "Unknown"
        except Exception:
            return "Unknown"

    def _parse_uptime(self, output):
        """Extrai informações de uptime"""
        try:
            # Exemplo: "System Up Time         : 958 days, 12:26:47.46 (hr:min:sec)"
            match = re.search(r'(\d+)\s+days?,\s+(\d+):(\d+):(\d+)', output)
            if match:
                return {
                    'days': int(match.group(1)),
                    'hours': int(match.group(2)),
                    'minutes': int(match.group(3)),
                    'seconds': int(match.group(4)),
                    'raw': output.strip()
                }
            else:
                return {
                    'days': 0,
                    'hours': 0,
                    'minutes': 0,
                    'seconds': 0,
                    'raw': output.strip()
                }
        except Exception:
            return {
                'days': 0,
                'hours': 0,
                'minutes': 0,
                'seconds': 0,
                'raw': "Parse Error"
            }

    def _parse_slots(self, output):
        """Extrai informações dos slots"""
        slots = []
        try:
            # Buscar linhas com dados de slots
            lines = output.split('\n')
            for line in lines:
                line = line.strip()
                # Procura por linhas que contêm dados de slots (não cabeçalhos ou separadores)
                if any(prefix in line for prefix in ['acu:', 'nt-', 'lt:', 'vlt:']):
                    # Divide por espaços múltiplos para separar as colunas
                    parts = [part.strip() for part in line.split() if part.strip()]
                    if len(parts) >= 6:
                        # Reconstrói slot_name caso tenha sido dividido
                        slot_name = parts[0]
                        if not any(prefix in slot_name for prefix in ['acu:', 'nt-', 'lt:', 'vlt:']):
                            continue

                        actual_type = parts[1]
                        enabled = parts[2].lower() == 'yes'
                        error_status = parts[3]
                        availability = parts[4]
                        restart_count = int(parts[5]) if parts[5].isdigit() else 0

                        slots.append({
                            'slot_name': slot_name,
                            'actual_type': actual_type,
                            'enabled': enabled,
                            'error_status': error_status,
                            'availability': availability,
                            'restart_count': restart_count
                        })
        except Exception as e:
            logger.error(f"Erro ao fazer parse dos slots: {e}")

        return slots

    def _parse_temperature(self, output):
        """Extrai informações de temperatura"""
        temperatures = []
        try:
            lines = output.split('\n')
            for line in lines:
                line = line.strip()
                # Procura por linhas que contêm dados de temperatura
                if any(prefix in line for prefix in ['nt-', 'lt:', 'acu:']):
                    # Divide por espaços múltiplos para separar as colunas
                    parts = [part.strip() for part in line.split() if part.strip()]
                    if len(parts) >= 7:
                        try:
                            slot_name = parts[0]
                            # Verifica se é uma linha válida de dados
                            if not any(prefix in slot_name for prefix in ['nt-', 'lt:', 'acu:']):
                                continue

                            sensor_id = int(parts[1])
                            actual_temp = int(parts[2])
                            tca_low = int(parts[3])
                            tca_high = int(parts[4])
                            shutdown_low = int(parts[5])
                            shutdown_high = int(parts[6])

                            temperatures.append({
                                'slot_name': slot_name,
                                'sensor_id': sensor_id,
                                'actual_temp': actual_temp,
                                'tca_low': tca_low,
                                'tca_high': tca_high,
                                'shutdown_low': shutdown_low,
                                'shutdown_high': shutdown_high
                            })
                        except (ValueError, IndexError):
                            # Pular linhas com valores não numéricos ou insuficientes
                            continue
        except Exception as e:
            logger.error(f"Erro ao fazer parse da temperatura: {e}")

        return temperatures
