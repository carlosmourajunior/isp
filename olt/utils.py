# import netmiko library
from netmiko import ConnectHandler
from olt.models import OltUsers

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
                        new_olt_user.save()
                        print(f"1/1/{slot}/{pon} - {line}")  
        
        self.disconnect(net_connect)
    
    def get_itens_to_remove(self, slot, pon):
        net_connect = self.connect()

        command = f"show equipment ont status pon 1/1/{slot}/{pon}"
        output = net_connect.send_command(command)
        removeble_list = []
        for line in iter(output.splitlines()):
            if "down" in line:
                new_list = []
                line_aux = line.split("  ")
                count = 0
                line_aux = [x for x in line_aux if x != '']
                for item in line_aux:
                    if count == 1:
                        ont_details = f'show vlan bridge-port-fdb {item}/14/1'
                        output_details = net_connect.send_command(ont_details)
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
                removeble_list.append(new_list)
        self.disconnect(net_connect)
        
        return removeble_list
    

    def remove_onu(self, porta):
       print(f"{porta}") 
        # net_connect = self.connect()
        # command = f"configure equipment ont interface {ont_id} admin-state down"
        # net_connect.send_command(command)
        # command = f"configure equipment ont interface {ont_id} admin-state down"
        # net_connect.send_command(command)
        # self.disconnect(net_connect)
                



                
        


