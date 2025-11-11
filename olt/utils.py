# import netmiko library
import base64
from datetime import datetime
import time
from netmiko import ConnectHandler
from olt.models import ONU, ClienteFibraIxc, OltUsers, OltSystemInfo, OltSlot, OltTemperature, OltSfpDiagnostics, OltAlarm
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

        for slot in range(1, 3):  # Slots 1 e 2 apenas
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
        """
        Coleta dados de TODOS os PONs e depois faz limpeza baseada no resultado completo
        """
        print("Iniciando coleta completa de todos os PONs...")
        
        # Lista para armazenar TODOS os seriais encontrados na OLT
        all_found_serials = []
        
        # Primeiro: coletar dados de TODOS os PONs sem fazer limpeza
        for slot in range(1, 3):  # slots 1, 2
            for pon in range(17):  # pons 0-16
                try:
                    pon_id = f"1/1/{slot}/{pon}"
                    
                    net_connect = self.connect()
                    command = f"show equipment ont status pon {pon_id}"
                    output = net_connect.send_command(command)
                    self.disconnect(net_connect)
                    
                    # Processar dados SEM fazer limpeza
                    found_serials = self.update_values_smart_no_cleanup(output, pon_id)
                    all_found_serials.extend(found_serials)
                    
                except Exception as e:
                    print(f"Erro ao coletar PON 1/1/{slot}/{pon}: {str(e)}")
                    continue
        
        print(f"Coleta completa finalizada. ONUs encontradas: {len(all_found_serials)}")
        
        # Segundo: fazer limpeza baseada em TODAS as ONUs encontradas
        self.cleanup_missing_onus(all_found_serials)

    def update_port(self, slot, pon):
        net_connect = self.connect()
        command = f"show equipment ont status pon 1/1/{slot}/{pon}"
        try:
            output = net_connect.send_command(command)
            self.update_values_smart(output, f"1/1/{slot}/{pon}")
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

    def update_values_smart_no_cleanup(self, output, pon_id):
        """
        Processa ONUs de um PON específico SEM fazer limpeza.
        Retorna listas de serials e MACs encontrados.
        """
        from django.utils import timezone
        
        data_dict = {}
        try:
            data_dict = self.create_dict_from_result(output)
        except:
            pass

        # Lista para retornar os seriais encontrados
        found_serials = []
        
        # Processar cada ONU encontrada
        for data in data_dict:
            try:
                found_serials.append(data['sernum'])
                
                # Encontrar ONU existente apenas pelo SERIAL
                existing_onu = ONU.objects.filter(serial=data['sernum']).first()
                
                if existing_onu:
                    # Atualizar ONU existente
                    existing_onu.pon = data['pon']
                    existing_onu.position = data['position']
                    existing_onu.serial = data['sernum']
                    # MAC não é atualizado aqui - processo separado
                    existing_onu.admin_state = data['admin_status']
                    existing_onu.oper_state = data['oper_status']
                    try:
                        existing_onu.olt_rx_sig = float(data['olt_rx_sig'])
                    except (ValueError, TypeError):
                        existing_onu.olt_rx_sig = None
                    existing_onu.ont_olt = data['ont_olt']
                    existing_onu.desc1 = data['desc1']
                    existing_onu.desc2 = data['desc2']
                    
                    # Verificar cliente fibra
                    try:
                        has_cliente = ClienteFibraIxc.objects.get(mac=data['sernum'], nome=data['desc1'])
                        existing_onu.cliente_fibra = True
                    except:
                        existing_onu.cliente_fibra = False
                    
                    existing_onu.save()
                else:
                    # Criar nova ONU
                    new_onu = ONU()
                    new_onu.pon = data['pon']
                    new_onu.position = data['position']
                    new_onu.serial = data['sernum']
                    # MAC será preenchido em processo separado
                    new_onu.mac = ""  # Campo vazio inicialmente
                    new_onu.admin_state = data['admin_status']
                    new_onu.oper_state = data['oper_status']
                    try:
                        new_onu.olt_rx_sig = float(data['olt_rx_sig'])
                    except (ValueError, TypeError):
                        new_onu.olt_rx_sig = None
                    new_onu.ont_olt = data['ont_olt']
                    new_onu.desc1 = data['desc1']
                    new_onu.desc2 = data['desc2']
                    
                    # Verificar cliente fibra
                    try:
                        has_cliente = ClienteFibraIxc.objects.get(mac=data['sernum'], nome=data['desc1'])
                        new_onu.cliente_fibra = True
                    except:
                        new_onu.cliente_fibra = False
                    
                    new_onu.save()
                    
            except Exception as e:
                print(f"Erro ao processar ONU {data.get('sernum', 'unknown')}: {str(e)}")
                continue
        
        return found_serials

    def update_values_smart(self, output, pon_filter=None):
        """
        Atualização inteligente de ONUs:
        - Atualiza ONUs existentes
        - Cria novas ONUs encontradas
        - Remove ONUs não encontradas na busca atual
        """
        from django.utils import timezone
        
        data_dict = {}
        try:
            data_dict = self.create_dict_from_result(output)
        except:
            pass

        # Lista de identificadores únicos encontrados na busca atual (serial e MAC)
        current_serials = [data['sernum'] for data in data_dict]
        current_macs = [data['mac'] for data in data_dict]
        
        # Processar cada ONU encontrada
        for data in data_dict:
            try:
                # Tentar encontrar ONU existente pelo SERIAL (identificador único)
                # O serial é o identificador mais confiável da ONU
                existing_onu = ONU.objects.filter(
                    serial=data['sernum']
                ).first()
                
                # Se não encontrar pelo serial, tentar pelo MAC (fallback)
                if not existing_onu and 'mac' in data and data['mac']:
                    existing_onu = ONU.objects.filter(
                        mac=data['mac']
                    ).first()
                
                if existing_onu:
                    # Atualizar ONU existente (incluindo posição que pode ter mudado)
                    existing_onu.pon = data['pon']  # Atualizar posição também
                    existing_onu.position = data['position']  # Atualizar posição também
                    existing_onu.serial = data['sernum']
                    existing_onu.mac = data['mac']  # Atualizar MAC também
                    existing_onu.admin_state = data['admin_status']
                    existing_onu.oper_state = data['oper_status']
                    try:
                        existing_onu.olt_rx_sig = float(data['olt_rx_sig'])
                    except (ValueError, TypeError):
                        existing_onu.olt_rx_sig = None
                    existing_onu.ont_olt = data['ont_olt']
                    existing_onu.desc1 = data['desc1']
                    existing_onu.desc2 = data['desc2']
                    
                    # Verificar cliente fibra
                    try:
                        has_cliente = ClienteFibraIxc.objects.get(mac=data['sernum'], nome=data['desc1'])
                        existing_onu.cliente_fibra = True
                    except:
                        existing_onu.cliente_fibra = False
                    
                    existing_onu.save()
                else:
                    # Criar nova ONU
                    new_onu = ONU()
                    new_onu.pon = data['pon']
                    new_onu.position = data['position']
                    new_onu.serial = data['sernum']
                    new_onu.mac = data['mac']  # Definir MAC também
                    new_onu.admin_state = data['admin_status']
                    new_onu.oper_state = data['oper_status']
                    try:
                        new_onu.olt_rx_sig = float(data['olt_rx_sig'])
                    except (ValueError, TypeError):
                        new_onu.olt_rx_sig = None
                    new_onu.ont_olt = data['ont_olt']
                    new_onu.desc1 = data['desc1']
                    new_onu.desc2 = data['desc2']
                    
                    # Verificar cliente fibra
                    try:
                        has_cliente = ClienteFibraIxc.objects.get(mac=data['sernum'], nome=data['desc1'])
                        new_onu.cliente_fibra = True
                    except:
                        new_onu.cliente_fibra = False
                    
                    new_onu.save()
                    
            except Exception as e:
                print(f"Erro ao processar ONU {data.get('sernum', 'unknown')}: {str(e)}")
                continue
        
        # Remover ONUs que não foram encontradas na busca atual (baseado no SERIAL e MAC)
        if pon_filter:
            # Se especificou um PON, remover apenas ONUs desse PON que não foram encontradas
            old_onus = ONU.objects.filter(pon=pon_filter)
            for onu in old_onus:
                # ONU deve ser removida apenas se nem serial nem MAC foram encontrados na busca atual
                # Considerar campos vazios/nulos como não encontrados
                serial_not_found = not onu.serial or onu.serial not in current_serials
                mac_not_found = not onu.mac or onu.mac not in current_macs
                
                if serial_not_found and mac_not_found:
                    print(f"Removendo ONU não encontrada no PON {pon_filter}: {onu.serial} - {onu.pon}/{onu.position}")
                    onu.delete()
                else:
                    print(f"Mantendo ONU encontrada no PON {pon_filter}: {onu.serial} - {onu.pon}/{onu.position}")
        else:
            # CUIDADO: Se não especificou PON específico, significa que coletamos dados de TODOS os PONs
            # Só devemos remover ONUs se temos certeza de que coletamos dados completos
            # Por segurança, não vamos remover nenhuma ONU quando não há filtro de PON
            # pois pode significar que não coletamos dados completos de todos os PONs
            print("Aviso: Coleta sem filtro de PON detectada. Por segurança, não removendo ONUs automaticamente.")
            print(f"ONUs encontradas nesta coleta: {len(current_serials)}")
            
            # Se quiser habilitar remoção automática sem filtro, descomente as linhas abaixo:
            # all_onus = ONU.objects.all()
            # for onu in all_onus:
            #     serial_not_found = not onu.serial or onu.serial not in current_serials
            #     mac_not_found = not onu.mac or onu.mac not in current_macs
            #     
            #     if serial_not_found and mac_not_found:
            #         print(f"Removendo ONU não encontrada: {onu.serial} - {onu.pon}/{onu.position}")
            #         onu.delete()
            #     else:
            #         print(f"Mantendo ONU encontrada: {onu.serial} - {onu.pon}/{onu.position}")

    def cleanup_missing_onus(self, all_found_serials):
        """
        Remove ONUs que estão no banco de dados mas não foram encontradas na coleta completa da OLT
        Utiliza apenas o SERIAL para identificação (MAC é atualizado em processo separado)
        """
        print("Iniciando limpeza de ONUs não encontradas na OLT...")
        
        # Buscar todas as ONUs no banco de dados
        all_db_onus = ONU.objects.all()
        removed_count = 0
        kept_count = 0
        
        for onu in all_db_onus:
            # Verificar se a ONU foi encontrada na coleta (apenas por SERIAL)
            serial_found = onu.serial and onu.serial in all_found_serials
            
            if not serial_found:
                # ONU não foi encontrada na OLT - deve ser removida
                print(f"Removendo ONU não encontrada na OLT: {onu.serial} - {onu.pon}/{onu.position}")
                onu.delete()
                removed_count += 1
            else:
                # ONU encontrada - manter no banco
                kept_count += 1
        
        print(f"Limpeza concluída. ONUs removidas: {removed_count}, ONUs mantidas: {kept_count}")
            
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
                # MAC não é processado aqui - será atualizado em processo separado
                'admin_status': admin_status,
                'oper_status': oper_status,
                'olt_rx_sig': olt_rx_sig,
                'ont_olt': ont_olt,
                'desc1': desc1,
                'desc2': desc2
            })
        return data_list

    def collect_all_alarms(self):
        """
        Coleta todos os tipos de alarmes da OLT
        """
        from olt.models import OltAlarm
        from django.utils import timezone
        import re
        
        alarm_commands = {
            'major': 'show alarm delta-log major',
            'critical': 'show alarm delta-log critical', 
            'log': 'show alarm log table',
            'current': 'show alarm current table'
        }
        
        net_connect = self.connect()
        collected_count = 0
        
        try:
            for alarm_type, command in alarm_commands.items():
                try:
                    print(f"Coletando alarmes {alarm_type}...")
                    output = net_connect.send_command(command)
                    alarms = self._parse_alarm_output(output, alarm_type)
                    
                    # Salvar alarmes no banco
                    for alarm_data in alarms:
                        OltAlarm.objects.create(**alarm_data)
                        collected_count += 1
                        
                except Exception as e:
                    print(f"Erro ao coletar alarmes {alarm_type}: {str(e)}")
                    continue
                    
        finally:
            self.disconnect(net_connect)
            
        # Limpar alarmes antigos
        OltAlarm.cleanup_old_records()
        
        print(f"Coleta de alarmes concluída. {collected_count} alarmes coletados.")
        return collected_count
    
    def _parse_alarm_output(self, output, alarm_type):
        """
        Processa a saída dos comandos de alarme com parsing melhorado
        """
        from django.utils import timezone
        from datetime import datetime
        import re
        
        alarms = []
        
        if not output or 'invalid token' in output.lower():
            return alarms
            
        lines = output.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith('=') or line.startswith('-'):
                continue
                
            try:
                # Parse específico baseado no tipo de alarme detectado
                alarm_data = self._parse_specific_alarm_format(line, alarm_type)
                
                if alarm_data:
                    alarms.append(alarm_data)
                
            except Exception as e:
                print(f"Erro ao processar linha de alarme: {line} - {str(e)}")
                continue
                
        return alarms
    
    def _parse_specific_alarm_format(self, line, alarm_type):
        """
        Parse específico para diferentes formatos de alarme
        """
        from django.utils import timezone
        import re
        
        # Formato: [72/09/26 17:08:14] major alarm cleared for ONU RCMG:19896C04 (goretegomes) - P…
        major_alarm_pattern = r'(\[[\d/\s:]+\])\s*(major|critical|minor|warning)\s*alarm\s*(cleared|raised)?\s*for\s*(?:ONU\s+)?([A-Z0-9:]+)\s*\(([^)]+)\)\s*-\s*(.*)'
        
        match = re.match(major_alarm_pattern, line, re.IGNORECASE)
        if match:
            timestamp_str = match.group(1)
            severity = match.group(2).lower()
            action = match.group(3) or 'active'  # 'cleared' ou 'raised' ou default 'active'
            onu_serial = match.group(4)
            client_name = match.group(5)
            remaining_content = match.group(6)
            
            # Extrair timestamp
            alarm_time = self._extract_timestamp_from_brackets(timestamp_str)
            
            # Montar entidade e descrição conforme especificação
            entity = f"{timestamp_str} {severity} alarm {action} for {onu_serial} ({client_name})"
            description = remaining_content.strip()
            
            return {
                'alarm_type': alarm_type,
                'severity': severity if severity in ['critical', 'major', 'minor', 'warning'] else 'minor',
                'entity': entity,
                'description': description,
                'alarm_time': alarm_time,
                'collected_at': timezone.now(),
                'is_active': action != 'cleared'  # Se foi 'cleared', não está ativo
            }
        
        # Fallback para o parsing antigo se não coincidir com o novo formato
        return self._parse_generic_alarm_format(line, alarm_type)
    
    def _parse_generic_alarm_format(self, line, alarm_type):
        """
        Parse genérico para alarmes que não seguem o formato específico
        """
        from django.utils import timezone
        
        # Processar descrição melhorada
        enhanced_description = self._enhance_alarm_description(line)
        
        # Parse básico para diferentes formatos de alarme
        alarm_data = {
            'alarm_type': alarm_type,
            'description': enhanced_description,
            'collected_at': timezone.now(),
            'is_active': True
        }
        
        # Extrair severidade do texto do alarme
        severity = self._extract_severity_from_text(line)
        if severity:
            alarm_data['severity'] = severity
        else:
            alarm_data['severity'] = 'minor'  # padrão
        
        # Extrair entidade (posição ONT se disponível)
        entity = self._extract_entity_from_text(line)
        if entity:
            alarm_data['entity'] = entity
        
        # Extrair timestamp se disponível
        alarm_time = self._extract_timestamp_from_text(line)
        if alarm_time:
            alarm_data['alarm_time'] = alarm_time
        
        # Extrair ID do alarme se disponível
        alarm_id = self._extract_alarm_id_from_text(line)
        if alarm_id:
            alarm_data['alarm_id'] = alarm_id
        
        return alarm_data
    
    def _extract_timestamp_from_brackets(self, timestamp_str):
        """
        Extrai timestamp do formato [72/09/26 17:08:14]
        """
        import re
        from datetime import datetime
        
        # Remover colchetes
        clean_timestamp = re.sub(r'[\[\]]', '', timestamp_str).strip()
        
        try:
            # Formato: 72/09/26 17:08:14
            if '/' in clean_timestamp and len(clean_timestamp.split('/')[0]) == 2:
                return datetime.strptime(f"20{clean_timestamp}", '%Y/%m/%d %H:%M:%S')
        except:
            pass
        
        return None
    
    def _parse_severity(self, severity_str):
        """
        Converte string de severidade para choices do modelo
        """
        severity_map = {
            'cr': 'critical',
            'critical': 'critical',
            'mj': 'major', 
            'major': 'major',
            'mn': 'minor',
            'minor': 'minor',
            'wa': 'warning',
            'warning': 'warning',
            'cl': 'clear',
            'clear': 'clear'
        }
        
        return severity_map.get(severity_str.lower(), 'minor')

    def _enhance_alarm_description(self, raw_description):
        """
        Melhora a descrição do alarme traduzindo posições ONT para informações da ONU
        """
        import re
        
        enhanced = raw_description
        
        # Procurar por padrão ont 1/1/slot/pon/position
        ont_pattern = r'ont (\d+/\d+/\d+/\d+/\d+)'
        matches = re.finditer(ont_pattern, enhanced)
        
        for match in matches:
            ont_position = match.group(1)
            try:
                # Extrair slot, pon e position da string
                parts = ont_position.split('/')
                if len(parts) >= 5:
                    slot = parts[2]
                    pon_num = parts[3] 
                    position = parts[4]
                    
                    # Montar string PON no formato usado no banco
                    pon_string = f"1/1/{slot}/{pon_num}"
                    
                    # Buscar ONU no banco
                    try:
                        onu = ONU.objects.get(pon=pon_string, position=int(position))
                        # Substituir ont position por informações da ONU
                        onu_info = f"ONU {onu.serial}"
                        if onu.desc1:
                            onu_info += f" ({onu.desc1})"
                        onu_info += f" - PON {pon_string}/{position}"
                        
                        enhanced = enhanced.replace(f"ont {ont_position}", onu_info)
                        
                    except ONU.DoesNotExist:
                        # Se não encontrou a ONU, pelo menos melhorar o formato
                        enhanced = enhanced.replace(f"ont {ont_position}", f"ONT PON {pon_string}/{position}")
                        
            except Exception as e:
                print(f"Erro ao processar posição ONT {ont_position}: {str(e)}")
                continue
        
        # Limpar formatação e melhorar legibilidade
        enhanced = self._clean_alarm_description(enhanced)
        
        return enhanced
    
    def _clean_alarm_description(self, description):
        """
        Limpa e melhora a formatação da descrição do alarme
        """
        import re
        
        # Remover linhas que são apenas contadores
        if re.match(r'^\s*\d+\s+ont-ani\s+', description):
            return f"Evento ONT-ANI: {description}"
        
        if re.match(r'^table count\s*:', description):
            return f"Contagem de tabela: {description}"
        
        # Melhorar formato de timestamp no início
        timestamp_pattern = r'^(\d{2}/\d{2}/\d{2}\s+\d{2}:\d{2}:\d{2})\s*'
        match = re.match(timestamp_pattern, description)
        if match:
            timestamp = match.group(1)
            rest = description[len(match.group(0)):]
            return f"[{timestamp}] {rest}"
        
        return description
    
    def _extract_severity_from_text(self, text):
        """
        Extrai a severidade do texto do alarme
        """
        import re
        
        # Padrões para identificar severidade
        if re.search(r'\bcritical\b', text, re.IGNORECASE):
            return 'critical'
        elif re.search(r'\bmajor\b', text, re.IGNORECASE):
            return 'major'
        elif re.search(r'\bminor\b', text, re.IGNORECASE):
            return 'minor'
        elif re.search(r'\bwarning\b', text, re.IGNORECASE):
            return 'warning'
        elif re.search(r'\bclear\b', text, re.IGNORECASE):
            return 'clear'
        
        return None
    
    def _extract_entity_from_text(self, text):
        """
        Extrai a entidade do texto do alarme
        """
        import re
        
        # Procurar por padrão ont position
        ont_match = re.search(r'ont (\d+/\d+/\d+/\d+/\d+)', text)
        if ont_match:
            return ont_match.group(1)
        
        # Procurar por outros padrões de entidade
        entity_patterns = [
            r'(ont-ani)',
            r'(pon \d+/\d+/\d+/\d+)',
            r'(slot \d+)',
        ]
        
        for pattern in entity_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return None
    
    def _extract_timestamp_from_text(self, text):
        """
        Extrai timestamp do texto do alarme
        """
        import re
        from datetime import datetime
        
        # Padrão para timestamp no formato da OLT
        timestamp_patterns = [
            r'(\d{2}/\d{2}/\d{2}\s+\d{2}:\d{2}:\d{2})',
            r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})',
            r'(\d{4}-\d{2}-\d{2}:\d{2}:\d{2}:\d{2})'
        ]
        
        for pattern in timestamp_patterns:
            match = re.search(pattern, text)
            if match:
                timestamp_str = match.group(1)
                try:
                    # Tentar diferentes formatos
                    if '/' in timestamp_str:
                        # Formato: 72/09/26 16:55:30
                        return datetime.strptime(f"20{timestamp_str}", '%Y/%m/%d %H:%M:%S')
                    elif ':' in timestamp_str and '-' in timestamp_str:
                        if len(timestamp_str) > 16:
                            # Formato: 1972-09-26:16:28:13
                            return datetime.strptime(timestamp_str, '%Y-%m-%d:%H:%M:%S')
                        else:
                            # Formato: 2024-09-26 16:28:13
                            return datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
                except:
                    continue
        
        return None
    
    def _extract_alarm_id_from_text(self, text):
        """
        Extrai ID do alarme do texto
        """
        import re
        
        # Procurar por números no início da linha que podem ser IDs
        match = re.match(r'^(\d+)\s+', text)
        if match:
            return match.group(1)
        
        return None
        

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
        """Coleta informações do sistema (versão, uptime, CPU, memória, modelo)"""
        net_connect = self.connect()
        try:
            # Coletar versão do sistema
            version_output = net_connect.send_command("show software-mngt version etsi")
            isam_release = self._parse_isam_release(version_output)
            
            # Coletar uptime
            uptime_output = net_connect.send_command("show core1-uptime")
            uptime_data = self._parse_uptime(uptime_output)
            
            # Coletar uso de CPU
            try:
                cpu_output = net_connect.send_command("show system core1-cpu")
                cpu_percent = self._parse_cpu_percent(cpu_output)
            except:
                cpu_percent = None
                
            try:
                cpu_load_output = net_connect.send_command("show system cpu-load nt-a detail")
                cpu_load = self._parse_cpu_load(cpu_load_output)
            except:
                cpu_load = None
            
            # Coletar uso de memória
            try:
                mem_output = net_connect.send_command("show system memory-usage nt-a detail")
                mem_percent = self._parse_mem_percent(mem_output)
            except:
                mem_percent = None
            
            # Coletar modelo da OLT
            try:
                slot_output = net_connect.send_command("show equipment slot")
                model = self._parse_olt_model(slot_output)
            except:
                model = "Unknown"
            
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
            
            # Retornar dados extras
            return {
                'system_info': system_info,
                'cpu_percent': cpu_percent,
                'cpu_load': cpu_load,
                'mem_percent': mem_percent,
                'model': model
            }
            
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
            
            # Usar transação atômica para evitar perda de dados
            from django.db import transaction
            with transaction.atomic():
                # Marcar todos como inativos primeiro
                OltSlot.objects.all().update(is_active=False)
                
                # Inserir/atualizar novos dados
                for slot_data in slots_data:
                    slot_data['is_active'] = True
                    OltSlot.objects.update_or_create(
                        slot_name=slot_data.get('slot_name'),
                        defaults=slot_data
                    )
                
                # Remover apenas os que realmente não existem mais
                # (opcional - pode manter histórico)
                # OltSlot.objects.filter(is_active=False).delete()
            
            return OltSlot.objects.filter(is_active=True)
            
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
            
            # Usar transação atômica para evitar perda de dados
            from django.db import transaction
            with transaction.atomic():
                # Marcar todos como inativos primeiro
                OltTemperature.objects.all().update(is_active=False)
                
                # Inserir/atualizar novos dados
                for temp in temp_data:
                    temp['is_active'] = True
                    OltTemperature.objects.update_or_create(
                        slot_name=temp.get('slot_name'),
                        sensor_id=temp.get('sensor_id'),
                        defaults=temp
                    )
                
                # Remover apenas os que realmente não existem mais
                # (opcional - pode manter histórico)
                # OltTemperature.objects.filter(is_active=False).delete()
            
            return OltTemperature.objects.filter(is_active=True)
            
            return OltTemperature.objects.all()
            
        except Exception as e:
            print(f"Erro ao coletar informações de temperatura: {str(e)}")
            return None
        finally:
            self.disconnect(net_connect)
    
    def collect_all_system_data(self):
        """Coleta todas as informações do sistema e salva no histórico"""
        try:
            # Importações necessárias
            from olt.models import OltSystemStats
            from django.db.models import Avg, Max
            
            sys_data = self.collect_system_info()
            slots = self.collect_slot_info()
            temperatures = self.collect_temperature_info()
            
            # Extrair dados
            system_info = sys_data.get('system_info') if isinstance(sys_data, dict) else sys_data
            cpu_percent = sys_data.get('cpu_percent') if isinstance(sys_data, dict) else None
            cpu_load = sys_data.get('cpu_load') if isinstance(sys_data, dict) else None
            mem_percent = sys_data.get('mem_percent') if isinstance(sys_data, dict) else None
            model = sys_data.get('model') if isinstance(sys_data, dict) else None
            
            # Calcular estatísticas de slots e temperatura
            total_slots = slots.count() if slots else 0
            operational_slots = slots.filter(
                enabled=True, 
                availability='available', 
                error_status='no-error'
            ).count() if slots else 0
            
            # Estatísticas de temperatura
            if temperatures and hasattr(temperatures, 'aggregate'):
                temp_stats = temperatures.aggregate(
                    avg_temp=Avg('actual_temp'),
                    max_temp=Max('actual_temp')
                )
                critical_temps = temperatures.filter(actual_temp__gte=75).count()
                warning_temps = temperatures.filter(actual_temp__gte=70, actual_temp__lt=75).count()
            else:
                temp_stats = {'avg_temp': None, 'max_temp': None}
                critical_temps = 0
                warning_temps = 0
            
            # Salvar no histórico
            
            stats_record = OltSystemStats.objects.create(
                cpu_percent=cpu_percent,
                cpu_load=cpu_load,
                mem_percent=mem_percent,
                model=model or "FX-4",
                uptime_days=system_info.uptime_days if system_info else 0,
                total_slots=total_slots,
                operational_slots=operational_slots,
                avg_temperature=temp_stats.get('avg_temp'),
                max_temperature=temp_stats.get('max_temp'),
                critical_temps=critical_temps,
                warning_temps=warning_temps
            )
            
            # Limpar registros antigos (mais de 7 dias)
            OltSystemStats.cleanup_old_records()
            
            return {
                'system_info': system_info,
                'cpu_percent': cpu_percent,
                'cpu_load': cpu_load,
                'mem_percent': mem_percent,
                'model': model,
                'slots': slots,
                'temperatures': temperatures,
                'stats_record': stats_record
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
    
    def _parse_cpu_percent(self, output):
        """Extrai percentual de uso de CPU do output"""
        try:
            # Buscar especificamente pelo padrão do seu equipamento:
            # "Usage                                133,736          26.75%"
            lines = output.split('\n')
            for line in lines:
                line = line.strip()
                if 'Usage' in line and '%' in line:
                    # Extrair o percentual da linha de Usage
                    match = re.search(r'Usage\s+[\d,]+\s+([\d.]+)%', line)
                    if match:
                        cpu_percent = float(match.group(1))
                        return int(round(cpu_percent))
                
                # Alternativa: procurar por "Busiest Core Utilization"
                if 'Busiest Core Utilization' in line and '%' in line:
                    match = re.search(r'Busiest Core Utilization\s+[\d,]+\s+([\d.]+)%', line)
                    if match:
                        cpu_percent = float(match.group(1))
                        return int(round(cpu_percent))
                        
        except Exception as e:
            print(f"Erro ao fazer parse de CPU: {str(e)}")
        
        return None
    
    def _parse_cpu_load(self, output):
        """Extrai load average do CPU"""
        try:
            # Buscar padrões de load average
            patterns = [
                r'Load\s*[Aa]verage\s*[:\s]*([\d\.]+)',
                r'Average\s*[Ll]oad\s*[:\s]*([\d\.]+)',
                r'CPU\s*[Ll]oad\s*[:\s]*([\d\.]+)',
                r'System\s*[Ll]oad\s*[:\s]*([\d\.]+)'
            ]
            
            for pattern in patterns:
                match = re.search(pattern, output, re.IGNORECASE)
                if match:
                    return float(match.group(1))
                    
        except Exception as e:
            print(f"Erro ao fazer parse de CPU load: {str(e)}")
        
        return None
    
    def _parse_mem_percent(self, output):
        """Extrai percentual de uso de memória"""
        try:
            # Buscar especificamente pelo padrão do seu equipamento:
            # "slot : nt-a                          total(mb) : 1563                           used(mb) : 1334                    used-portion(%) : 85"
            lines = output.split('\n')
            for line in lines:
                line = line.strip()
                if 'slot : nt-a' in line and 'used-portion(%)' in line:
                    # Extrair o percentual da linha
                    match = re.search(r'used-portion\(%\)\s*:\s*(\d+)', line)
                    if match:
                        mem_percent = int(match.group(1))
                        return mem_percent
                        
                # Formato alternativo: procurar por "used-portion(%)" em linha separada
                if 'used-portion(%)' in line:
                    match = re.search(r'used-portion\(%\)\s*:\s*(\d+)', line)
                    if match:
                        mem_percent = int(match.group(1))
                        return mem_percent
                        
        except Exception as e:
            print(f"Erro ao fazer parse de memória: {str(e)}")
        
        return None
    
    def _parse_olt_model(self, output):
        """Retorna modelo fixo da OLT"""
        # Modelo fixo conforme informado pelo usuário
        return "FX-4"
