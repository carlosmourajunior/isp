from .models import ONU, ClienteFibraIxc

def update_clientes():
    """Função para atualizar a lista de clientes fibra do IXC"""
    # Limpa a tabela atual
    ClienteFibraIxc.objects.all().delete()
    
    try:
        # Pega todos os ONUs existentes
        onus = ONU.objects.all()
        
        # Cria novos registros de clientes para cada ONU com desc1 não vazio
        for onu in onus:
            if onu.desc1 and onu.desc1.strip():  # Se tem descrição e não está vazia
                ClienteFibraIxc.objects.create(
                    mac=onu.serial,
                    nome=onu.desc1
                )
                # Marca a ONU como tendo cliente fibra
                onu.cliente_fibra = True
                onu.save()
            else:
                # Se não tem descrição, marca como não tendo cliente fibra
                onu.cliente_fibra = False
                onu.save()
                
        return True
    except Exception as e:
        print(f"Erro ao atualizar clientes: {str(e)}")
        return False