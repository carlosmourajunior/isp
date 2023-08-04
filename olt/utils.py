# import netmiko library
from datetime import datetime
from netmiko import ConnectHandler
from olt.models import ONU, OltUsers
import pandas as pd 

class olt_connector():

    def __init__(self):
        self.nokia = {
            'device_type': 'alcatel_aos',
            'host': '192.168.133.10',
            'username': 'isadmin',
            'password': 'ANS#150',
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


    def update_port_ocupation(self):

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
    
    def get_itens_to_remove(self, slot, pon):
        old_values = ONU.objects.filter(pon=f"1/1/{slot}/{pon}")
        old_values.delete()
        net_connect = self.connect()
        command = f"show equipment ont status pon 1/1/{slot}/{pon}"
        output = net_connect.send_command(command)
        self.update_values(output)
        self.disconnect(net_connect)
        
        return output
    

    def update_values(self, output):
        print(output)
        df = pd.DataFrame()
        for line in iter(output.splitlines()):
            if "down" in line or "up" in line:
                new_list = []
                line_aux = line.split("  ")
                count = 0
                line_aux = [x for x in line_aux if x != '']
                for item in line_aux:
                    if count == 1:
                        output_details = self.get_onu_detail(item)
                        found = False
                        for detail_line in iter(output_details.splitlines()):
                            if "learned" in detail_line:
                                mac_list = [x for x in detail_line.split(" ") if x != '']
                                mac = mac_list[2]
                                found = True
                        if not found:
                            new_list.append("MAC Não encontrado")
                        else:
                            new_list.append(mac)
                    new_list.append(item)
                    count += 1
                new_onu = ONU()
                new_onu.pon = new_list[0]
                new_onu.mac = new_list[1]
                new_onu.position = new_list[2].split("/")[-1]
                new_onu.serial = new_list[3].split(" ")[0]
                new_onu.oper_state = new_list[3].split(" ")[1]
                new_onu.pppoe = new_list[7]
                new_onu.descricao = new_list[8]
                new_onu.save()

    def remove_onu(self, queryset):
       pass
        # ont_id = f"{queryset.first().pon}/{queryset.first().position}"
        # net_connect = self.connect()
        # # command = f"configure equipment ont interface {ont_id} admin-state down"
        # # print(command)
        # # net_connect.send_command(command)
        # command = f"configure equipment ont no interface {ont_id}"
        # print(command)
        # net_connect.send_command(command)
        # self.disconnect(net_connect)              



                
        


