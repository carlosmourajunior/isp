# ISP

Aplicação para auxiliar ISP de pequeno porte a ter um melhor controle de sua rede.

# Tecnologias

    # Python
    # Django
    # Bootstrap

# Objetivo

O Objetivo do projeto é criar uma interface gráfica para facilitar tarefas em seu provedor.

# Funcionalidades

    # OLT nokia
        - Verificação de portas cheias
        - Listagem de portas aprovisionadas mas que estão sem uso.
        - Deleção de ONU direto na interface gráfica
        - Envio de e-mail de alerta
            - ONU com sinal muito baixo ( < -27>)
            - Porta cheia
            - Porta sem uso

    # Mikrotik

        - PPPoE
            - Quantidade de usuários por faixa de IP
            - Configurações de CGNAT 
                - Quantidade de IPs por saída
            - Alertas
                - IPs PPPoE duplicados
                - Usuários desconectando com frequência
                - Faixa de IPs sobrecarregadas
                



