# import netmiko library
from datetime import datetime
import time
from netmiko import ConnectHandler
from olt.models import ONU, ClienteFibraIxc, OltUsers
import re
from dotenv import load_dotenv
import os
from librouteros import connect
from librouteros.exceptions import LibRouterosError

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
        #send command
        olts = OltUsers.objects.all()
        olts.delete()

        for slot in range(3):
            for pon in range(17):
                command = f"show equipment ont status pon 1/1/{slot}/{pon}"
                output = net_connect.send_command(command)
                for line in iter(output.splitlines()):
                    if "count" in line:
                        new_olt_user = OltUsers()
                        new_olt_user.slot = slot
                        new_olt_user.port = pon
                        new_olt_user.users_connected = int(line.split(":")[1])
                        new_olt_user.last_updated = datetime.now()
                        new_olt_user.save()
                        print(f"1/1/{slot}/{pon} - {line}")  
        
        self.disconnect(net_connect)
    
    def get_itens_to_port(self, slot, pon, order_by='position'):
        old_values = ONU.objects.filter(pon=f"1/1/{slot}/{pon}").order_by(order_by)
        return old_values

    def update_all_ports(self):
        for slot in range(3):
            for pon in range(17):
                self.update_port(slot, pon)
            # self.get_mac_values()

    def update_port(self, slot, pon):
        old_values = ONU.objects.filter(pon=f"1/1/{slot}/{pon}")
        old_values.delete()
        net_connect = self.connect()
        command = f"show equipment ont status pon 1/1/{slot}/{pon}"
        output = net_connect.send_command(command)
        self.update_values(output)
        self.disconnect(net_connect)
    
    def get_mac_values(self):
        net_connect = self.connect()
        command = "environment inhibit-alarms"
        net_connect.write_channel(command)
        time.sleep(2)  # Aguarda um pouco para o comando ser processado
        command = "show vlan bridge-port-fdb"
        output = net_connect.send_command(command, read_timeout=1200)
        self.update_mac(output)
        self.disconnect(net_connect)
    
    def update_mac(self, output):
        try:
            if not output:
                return
            lines = output.strip().split('\n')
            for line in lines:
                print(f"Processing line: {line}")
                try:
                    data = extract_olt_info(line)
                    print(f"Data: {data}")

                    parts =  data['pon'].split('/')
                    pon = '/'.join(parts[:3])  # Take first 4 parts
                    position = parts[-1]  # Take last part      
        
                    onu = ONU.objects.filter(
                        pon=f"1/{pon}",
                        position=position
                    ).first()

                    if onu:
                        onu.mac = data['mac']
                        onu.save()
                        print(f"Updated MAC for ONU {onu}")
                    else:
                        print(f"ONU not found for PON {pon} and position {position}")
                            
                except Exception as ve:
                    print(f"Error parsing line '{line}': {str(ve)}")
                    continue
                    
        except Exception as e:
            print(f"Error updating MAC: {e}")

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
            new_onu.olt_rx_sig = data['olt_rx_sig']
            new_onu.ont_olt = data['ont_olt']
            new_onu.desc1 = data['desc1']
            new_onu.desc2 = data['desc2']
            new_onu.save()
            print(data)

                
    def remove_onu(self, pon):
       
        # ont_id = f"{queryset.first().pon}/{queryset.first().position}"
        net_connect = self.connect()
        command = f"configure equipment ont interface {pon} admin-state down\n"
        print(command)
        net_connect.write_channel(command)
        time.sleep(2)  # Aguarda um pouco para o comando ser processado
        output = net_connect.read_channel()
        print(output)
        command = f"configure equipment ont no interface {pon}\n"
        net_connect.write_channel(command)
        time.sleep(2)  # Aguarda um pouco para o comando ser processado
        output = net_connect.read_channel()
        print(output)
        self.disconnect(net_connect)           

    def create_mac_dict(self, data):
        print("create_mac_dict")
    
       # Define the regex pattern
        pattern = r"(\d+/\d+/\d+/\d+/\d+/\d+/\d+)\s+(\d+)\s+([a-f0-9:]+)\s+(\d+)\s+(\w+)\s+([0-9:]+)"

        # Find all matches in the data
        matches = re.findall(pattern, data)

        # Initialize an empty dictionary to store the data
        data_dict = {}

        # Iterate over each match
        for match in matches:
            # Add the match to the dictionary
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

        print(data_dict)
        return data_dict
        # Print the dictionary
        


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
        print("Conexão estabelecida com sucesso!")
        return api
    except LibRouterosError as e:
        print(f"Erro ao conectar ao MikroTik: {e}")
        return None

def get_nat_rules(api):
    try:
        # Executa o comando para listar as regras de NAT
        nat_rules = api(cmd='/ip/firewall/nat/print')
        return nat_rules
    except LibRouterosError as e:
        print(f"Erro ao buscar regras de NAT: {e}")
        return None

