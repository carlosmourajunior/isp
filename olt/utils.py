# import netmiko library
from datetime import datetime
import time
from netmiko import ConnectHandler
from olt.models import ONU, ClienteFibraIxc, OltUsers
import re

class olt_connector():

    def __init__(self):
        self.nokia = {
            'device_type': 'alcatel_aos',
            'host': '192.168.133.10',
            'username': 'isadmin',
            'password': 'ANS#150',
            'verbose': False,
            'global_delay_factor': 2,
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

    def update_port(self, slot, pon):
        old_values = ONU.objects.filter(pon=f"1/1/{slot}/{pon}")
        old_values.delete()
        net_connect = self.connect()
        command = f"show equipment ont status pon 1/1/{slot}/{pon}"
        output = net_connect.send_command(command)
        self.update_values(output)
        self.disconnect(net_connect)

    def update_values(self, output):

        data_dict = self.create_dict_from_result(output)
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
    
    def update_all_mac_address(self):
        net_connect = self.connect()
        command = "show vlan bridge-port-fdb"
        output = net_connect.send_command(command)
        self.update_values(output)
        self.disconnect(net_connect)


    def create_mac_dict(self):

        data = '''
            1/1/1/1/52/14/1      200              e0:1f:ed:0e:d5:e1 200              learned 00:00:00:00:00:00
            1/1/1/1/54/14/1      200              e0:1f:ed:0f:eb:01 200              learned 00:00:00:00:00:00
            1/1/1/1/55/14/1      200              dc:d9:ae:f4:0c:51 200              learned 00:00:00:00:00:00
            1/1/1/1/56/14/1      200              78:17:35:ae:5e:ca 200              learned 00:00:00:00:00:00
            1/1/1/1/57/14/1      200              e0:1f:ed:17:7e:31 200              learned 00:00:00:00:00:00
            1/1/1/1/58/1/1       200              d8:38:0d:4d:4c:41 200              learned 00:00:00:00:00:00
            1/1/1/1/59/1/1       200              d8:38:0d:5b:4a:51 200              learned 00:00:00:00:00:00
            1/1/1/1/60/14/1      200              04:25:e0:eb:b8:04 200              learned 00:00:00:00:00:00
            1/1/1/1/61/14/1      200              78:91:e9:0d:ad:5c 200              learned 00:00:00:00:00:00
            1/1/1/1/63/14/1      200              cc:c2:e0:92:65:4c 200              learned 00:00:00:00:00:00
            1/1/1/1/64/1/1       200              c0:c9:e3:eb:0c:ad 200              learned 00:00:00:00:00:00
            1/1/1/1/65/1/1       200              e8:48:b8:34:b1:ed 200              learned 00:00:00:00:00:00
            1/1/1/1/66/1/1       200              e4:c3:2a:c9:4d:05 200              learned 00:00:00:00:00:00
            1/1/1/1/67/14/1      200              cc:c2:e0:9a:9c:67 200              learned 00:00:00:00:00:00
            1/1/1/1/68/14/1      200              e0:1f:ed:0f:e4:e1 200              learned 00:00:00:00:00:00
            1/1/1/1/69/14/1      200              e0:1f:ed:0f:e1:41 200              learned 00:00:00:00:00:00
            1/1/1/1/73/14/1      200              e0:1f:ed:11:4d:01 200              learned 00:00:00:00:00:00
            1/1/1/1/74/14/1      200              e0:1f:ed:0d:fc:81 200              learned 00:00:00:00:00:00
            1/1/1/1/75/1/1       200              d8:38:0d:4e:3a:a1 200              learned 00:00:00:00:00:00
            1/1/1/1/77/1/1       200              48:a9:8a:ac:92:f4 200              learned 00:00:00:00:00:00
            1/1/1/1/78/1/1       200              98:da:c4:21:bc:57 200              learned 00:00:00:00:00:00
            1/1/1/1/79/14/1      200              04:25:e0:93:22:64 200              learned 00:00:00:00:00:00
            1/1/1/1/80/14/1      200              04:25:e0:93:26:c4 200              learned 00:00:00:00:00:00
            1/1/1/1/81/14/1      200              04:25:e0:90:74:e4 200              learned 00:00:00:00:00:00
            1/1/1/1/83/14/1      200              cc:c2:e0:95:64:50 200              learned 00:00:00:00:00:00
            1/1/1/1/84/14/1      200              cc:c2:e0:95:d2:c0 200              learned 00:00:00:00:00:00
            1/1/1/1/85/14/1      200              cc:c2:e0:3b:77:87 200              learned 00:00:00:00:00:00
            1/1/1/1/86/14/1      200              e0:1f:ed:0f:5c:e1 200              learned 00:00:00:00:00:00
            1/1/1/1/89/14/1      200              cc:c2:e0:95:35:7c 200              learned 00:00:00:00:00:00

        '''

       # Define the regex pattern
        pattern = r"(\d+/\d+/\d+/\d+/\d+/\d+/\d+)\s+(\d+)\s+([a-f0-9:]+)\s+(\d+)\s+(\w+)\s+([0-9:]+)"

        # Find all matches in the data
        matches = re.findall(pattern, data)

        # Initialize an empty dictionary to store the data
        data_dict = {}

        # Iterate over each match
        for match in matches:
            # Add the match to the dictionary
            data_dict[match[0]] = {
                'status': match[1],
                'mac_address': match[2],
                'status_2': match[3],
                'learned': match[4],
                'time': match[5]
            }

        # Print the dictionary
        print(data_dict)


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
        

       



