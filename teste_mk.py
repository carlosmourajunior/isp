from routeros_api import RouterOsApiPool

# Configurações de conexão
mikrotik_ip = '170.78.163.241'
username = 'carlos'
password = 'ibanezGAX()90'

# Conectando ao MikroTik
api_pool = RouterOsApiPool(mikrotik_ip, username=username, password=password, plaintext_login=True)
api = api_pool.get_api()

# Executando o comando ping com parâmetros convertidos para bytes
ping_params = {
    'address': '8.8.8.8'.encode('utf-8'),
    'src-address': '170.78.163.251'.encode('utf-8'),
    'count': '10'.encode('utf-8')
}

response = api.get_binary_resource('/').call('ping', ping_params)

# Exibindo o resultado
for reply in response:
    try:
        # Decodifica valores binários
        seq = reply.get(b'seq', b'0').decode('utf-8')
        time = reply.get(b'time', b'0').decode('utf-8')
        print(f"seq={seq} time={time}ms")
    except Exception as e:
        print(f"Erro ao decodificar resposta: {e}")

# Buscando todas as regras de NAT ativas
nat_rules = api.get_resource('/ip/firewall/nat').get()

# Exibindo as regras de NAT
print("\nRegras de NAT ativas:")
for rule in nat_rules:
    print(rule)

# Fechando a conexão
api_pool.disconnect()