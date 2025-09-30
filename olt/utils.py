# import netmiko library
import base64
from datetime import datetime
import time
from netmiko import ConnectHandler
from olt.models import ONU, ClienteFibraIxc, OltUsers, OltSystemInfo, OltSlot, OltTemperature, OltSfpDiagnostics
import re
from dotenv import load_dotenv
import os
from librouteros import connect
from librouteros.exceptions import LibRouterosError
from django.utils import timezone

# Carregar variáveis de ambiente do arquivo .env
load_dotenv()

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

class olt_connector():

    def __init__(self):
        self.nokia = {
            'device_type': os.getenv('NOKIA_DEVICE_TYPE'),
            'host': os.getenv('NOKIA_HOST'),
            'username': os.getenv('NOKIA_USERNAME'),
            'password': os.getenv('NOKIA_PASSWORD'),
            'verbose': os.getenv('NOKIA_VERBOSE') == 'True',
            'global_delay_factor': int(os.getenv('NOKIA_GLOBAL_DELAY_FACTOR')),
        }

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
        olts = OltUsers.objects.all()
        olts.delete()

        for slot in range(3):
            for pon in range(17):
                command = f"show equipment ont status pon 1/1/{slot}/{pon}"
                try:
                    output = net_connect.send_command(command)
                    for line in iter(output.splitlines()):
                        if "count" in line:
                            new_olt_user = OltUsers()
                            new_olt_user.slot = slot
                            new_olt_user.port = pon
                            new_olt_user.users_connected = int(line.split(":")[1])
                            new_olt_user.last_updated = timezone.now()
                            new_olt_user.save()
                except Exception as e:
                    continue
        
        self.disconnect(net_connect)
    
    def get_itens_to_port(self, slot, pon, order_by='position'):
        old_values = ONU.objects.filter(pon=f"1/1/{slot}/{pon}").order_by(order_by)
        return old_values

    def update_all_ports(self):
        for slot in range(3):
            for pon in range(17):
                self.update_port(slot, pon)

    def update_port(self, slot, pon):
        old_values = ONU.objects.filter(pon=f"1/1/{slot}/{pon}")
        old_values.delete()
        net_connect = self.connect()
        command = f"show equipment ont status pon 1/1/{slot}/{pon}"
        try:
            output = net_connect.send_command(command)
            self.update_values(output)
        except Exception:
            pass
        finally:
            self.disconnect(net_connect)
    
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
            print(f"Erro ao obter valores MAC: {str(e)}")
        finally:
            self.disconnect(net_connect)
    
    def update_mac(self, output):
        try:
            if not output:
                return
            lines = output.strip().split('\n')
            for line in lines:
                try:
                    data = extract_olt_info(line)
                    if data:
                        parts = data['pon'].split('/')
                        pon = '/'.join(parts[:3])
                        position = parts[-1]
        
                        onu = ONU.objects.filter(
                            pon=f"1/{pon}",
                            position=position
                        ).first()

                        if onu:
                            onu.mac = data['mac']
                            onu.save()
                except Exception:
                    continue
        except Exception:
            pass

    def update_values(self, output):
        data_dict = {}
        try:
            data_dict = self.create_dict_from_result(output)
        except:
            pass

        for data in data_dict:
            new_onu = ONU()
            try:
                has_cliente = ClienteFibraIxc.objects.get(mac=data['sernum'], nome=data['desc1'])
                if has_cliente:
                    new_onu.cliente_fibra = True
            except:
                pass
            
            new_onu.pon = data['pon']
            new_onu.position = data['position']
            new_onu.serial = data['sernum']
            new_onu.admin_state = data['admin_status']
            new_onu.oper_state = data['oper_status']
            # Convert olt_rx_sig to float before saving
            try:
                new_onu.olt_rx_sig = float(data['olt_rx_sig'])
            except (ValueError, TypeError):
                new_onu.olt_rx_sig = None
            new_onu.ont_olt = data['ont_olt']
            new_onu.desc1 = data['desc1']
            new_onu.desc2 = data['desc2']
            new_onu.save()
            
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
        except Exception:
            pass
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
            print(e)
            pass
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

    def create_dict_from_result(self, data):


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
        

def connect_to_mikrotik(hostname, username, password, port):
    try:
        # Conecta ao MikroTik via API
        api = connect(
            host=hostname,
            username=username,
            password=password,
            port=port,
        )
        return api
    except LibRouterosError as e:
        return None

def get_nat_rules(api):
    try:
        # Executa o comando para listar as regras de NAT
        nat_rules = api(cmd='/ip/firewall/nat/print')
        return nat_rules
    except LibRouterosError as e:
        return None


class OltSystemCollector:
    """Classe para coletar informações do sistema OLT"""
    
    def __init__(self):
        self.nokia = {
            'device_type': os.getenv('NOKIA_DEVICE_TYPE'),
            'host': os.getenv('NOKIA_HOST'),
            'username': os.getenv('NOKIA_USERNAME'),
            'password': os.getenv('NOKIA_PASSWORD'),
            'verbose': os.getenv('NOKIA_VERBOSE') == 'True',
            'global_delay_factor': int(os.getenv('NOKIA_GLOBAL_DELAY_FACTOR', 2)),
        }
    
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
            
            # Atualizar ou criar registro
            system_info, created = OltSystemInfo.objects.get_or_create(
                id=1,  # Usando ID fixo pois só temos uma OLT
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
            print(f"Erro ao coletar informações do sistema: {str(e)}")
            return None
        finally:
            self.disconnect(net_connect)
    
    def collect_slot_info(self):
        """Coleta informações dos slots"""
        net_connect = self.connect()
        try:
            output = net_connect.send_command("show equipment slot")
            slots_data = self._parse_slots(output)
            
            # Limpar dados antigos
            OltSlot.objects.all().delete()
            
            # Inserir novos dados
            for slot_data in slots_data:
                OltSlot.objects.create(**slot_data)
            
            return OltSlot.objects.all()
            
        except Exception as e:
            print(f"Erro ao coletar informações dos slots: {str(e)}")
            return None
        finally:
            self.disconnect(net_connect)
    
    def collect_temperature_info(self):
        """Coleta informações de temperatura"""
        net_connect = self.connect()
        try:
            output = net_connect.send_command("show equipment temperature")
            temp_data = self._parse_temperature(output)
            
            # Limpar dados antigos
            OltTemperature.objects.all().delete()
            
            # Inserir novos dados
            for temp in temp_data:
                OltTemperature.objects.create(**temp)
            
            return OltTemperature.objects.all()
            
        except Exception as e:
            print(f"Erro ao coletar informações de temperatura: {str(e)}")
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
            print(f"Erro ao coletar dados do sistema: {str(e)}")
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
            print(f"Erro ao fazer parse dos slots: {str(e)}")
        
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
            print(f"Erro ao fazer parse da temperatura: {str(e)}")
        
        return temperatures
