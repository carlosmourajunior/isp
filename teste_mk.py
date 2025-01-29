from librouteros import connect
from librouteros.query import Key
from dotenv import load_dotenv
import os

# Carregar variáveis de ambiente do arquivo .env
load_dotenv()

def test_mikrotik_connection():
    try:
        # Conectar ao Mikrotik
        api = connect(
            username=os.getenv('MIKROTIK_USERNAME'),
            password=os.getenv('MIKROTIK_PASSWORD'),
            host=os.getenv('MIKROTIK_HOST'),
            port=int(os.getenv('MIKROTIK_PORT')),
            timeout=int(os.getenv('MIKROTIK_TIMEOUT'))
        )

        # Buscar informações do Mikrotik
        system_resource = api.path('system', 'resource')
        resource_info = system_resource.get()

        # Extrair dados relevantes
        mikrotik_data = {
            'hostname': resource_info[0].get('identity', 'N/A'),
            'ip_address': os.getenv('MIKROTIK_HOST'),  # IP do Mikrotik
            'uptime': resource_info[0].get('uptime', 'N/A'),
            'version': resource_info[0].get('version', 'N/A'),
            # Adicione mais informações conforme necessário
        }

        print(mikrotik_data)
    except Exception as e:
        print(f"Erro ao conectar ao Mikrotik: {e}")

if __name__ == "__main__":
    test_mikrotik_connection()