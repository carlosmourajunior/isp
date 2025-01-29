# ISP Network Management Application

Aplicação para auxiliar ISPs de pequeno porte a ter um melhor controle de sua rede.

## Tecnologias Utilizadas

- **Python**
- **Django**
- **PostgreSQL**
- **Docker**
- **Bootstrap**

## Objetivo

O objetivo do projeto é criar uma interface gráfica para facilitar tarefas de gerenciamento de rede em provedores de internet.

## Funcionalidades

### OLT Nokia

- **Verificação de Portas Cheias**: Identificação de portas que atingiram sua capacidade máxima.
- **Listagem de Portas Sem Uso**: Exibição de portas aprovisionadas que estão sem uso.
- **Deleção de ONU**: Remoção de ONUs diretamente pela interface gráfica.
- **Envio de E-mail de Alerta**:
  - ONU com sinal muito baixo ( < -27 dBm)
  - Porta cheia
  - Porta sem uso

### Mikrotik

- **PPPoE**:
  - Quantidade de usuários por faixa de IP
  - Configurações de CGNAT:
    - Quantidade de IPs por saída
  - Alertas:
    - IPs PPPoE duplicados
    - Usuários desconectando com frequência
    - Faixa de IPs sobrecarregadas

## Configuração do Ambiente

### Pré-requisitos

- Docker
- Docker Compose

### Variáveis de Ambiente

Crie um arquivo `.env` na raiz do projeto e adicione as seguintes variáveis de ambiente:

```env
# .env
MIKROTIK_USERNAME=<seu_usuario>
MIKROTIK_PASSWORD=<sua_senha>
MIKROTIK_HOST=<seu_host>
MIKROTIK_PORT=<sua_porta>
MIKROTIK_TIMEOUT=<seu_timeout>

NOKIA_DEVICE_TYPE=<seu_device_type>
NOKIA_HOST=<seu_host>
NOKIA_USERNAME=<seu_usuario>
NOKIA_PASSWORD=<sua_senha>
NOKIA_VERBOSE=<True_ou_False>
NOKIA_GLOBAL_DELAY_FACTOR=<seu_delay_factor>

IXC_HOST=<seu_host>
IXC_TOKEN=<seu_token>