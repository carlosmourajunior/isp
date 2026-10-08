#!/bin/bash
# SCRIPT DE CONFIGURAÇÃO DE FIREWALL PARA SISTEMA ISP
# Criado em: $(date)

echo "🔥 Configurando Firewall de Segurança para Sistema ISP..."

# Verificar se ufw está instalado
if ! command -v ufw &> /dev/null; then
    echo "📦 Instalando ufw..."
    apt update && apt install ufw -y
fi

# Backup da configuração atual
echo "💾 Fazendo backup da configuração atual..."
mkdir -p /root/firewall_backups
ufw status verbose > /root/firewall_backups/ufw_status_$(date +%Y%m%d_%H%M%S).txt

# Resetar configurações
echo "🔄 Resetando configurações do firewall..."
ufw --force reset

# Políticas padrão
echo "📋 Configurando políticas padrão..."
ufw default deny incoming
ufw default allow outgoing

# Função para obter IP público atual
get_current_ip() {
    curl -s ifconfig.me 2>/dev/null || curl -s ipinfo.io/ip 2>/dev/null || echo "UNKNOWN"
}

CURRENT_IP=$(get_current_ip)
echo "🌐 Seu IP atual detectado: $CURRENT_IP"

# SSH - Configuração crítica
echo "🔐 Configurando acesso SSH..."
echo "ATENÇÃO: Configuração incorreta pode bloquear seu acesso!"
echo "Opções:"
echo "1) Permitir apenas do seu IP atual ($CURRENT_IP)"
echo "2) Permitir de uma rede específica (ex: 177.22.126.0/24)"
echo "3) Permitir de qualquer lugar (MENOS SEGURO)"

read -p "Escolha uma opção (1-3): " SSH_OPTION

case $SSH_OPTION in
    1)
        if [ "$CURRENT_IP" != "UNKNOWN" ]; then
            ufw allow from $CURRENT_IP to any port 22 comment "SSH - IP Atual"
            echo "✅ SSH permitido apenas do IP: $CURRENT_IP"
        else
            echo "❌ Não foi possível detectar seu IP. Configure manualmente."
            ufw allow 22/tcp comment "SSH - Temporário"
        fi
        ;;
    2)
        read -p "Digite a rede (ex: 192.168.1.0/24): " NETWORK
        ufw allow from $NETWORK to any port 22 comment "SSH - Rede"
        echo "✅ SSH permitido da rede: $NETWORK"
        ;;
    3)
        ufw allow 22/tcp comment "SSH - Global"
        echo "⚠️ SSH permitido de qualquer lugar (menos seguro)"
        ;;
    *)
        echo "❌ Opção inválida. SSH não configurado!"
        ;;
esac

# Serviços principais
echo "🌐 Configurando serviços principais..."
ufw allow 8000/tcp comment "Django ISP Application"
echo "✅ Porta 8000 (Aplicação ISP) - PERMITIDA"

# Grafana - Opção de restringir
echo "📊 Configurando Grafana..."
read -p "Restringir acesso ao Grafana por IP? (s/N): " RESTRICT_GRAFANA

if [ "$RESTRICT_GRAFANA" = "s" ] || [ "$RESTRICT_GRAFANA" = "S" ]; then
    echo "Opções para Grafana:"
    echo "1) Apenas seu IP atual ($CURRENT_IP)"
    echo "2) Rede específica"
    echo "3) Aberto para todos"
    
    read -p "Escolha (1-3): " GRAFANA_OPTION
    
    case $GRAFANA_OPTION in
        1)
            if [ "$CURRENT_IP" != "UNKNOWN" ]; then
                ufw allow from $CURRENT_IP to any port 3000 comment "Grafana - IP Restrito"
                echo "✅ Grafana restrito ao IP: $CURRENT_IP"
            else
                ufw allow 3000/tcp comment "Grafana - Aberto"
                echo "⚠️ IP não detectado, Grafana liberado"
            fi
            ;;
        2)
            read -p "Digite a rede para Grafana: " GRAFANA_NETWORK
            ufw allow from $GRAFANA_NETWORK to any port 3000 comment "Grafana - Rede"
            echo "✅ Grafana restrito à rede: $GRAFANA_NETWORK"
            ;;
        *)
            ufw allow 3000/tcp comment "Grafana Dashboard"
            echo "✅ Grafana aberto para todos"
            ;;
    esac
else
    ufw allow 3000/tcp comment "Grafana Dashboard"
    echo "✅ Grafana aberto para todos"
fi

# Bloquear portas de monitoramento
echo "🚫 Bloqueando portas de monitoramento..."
ufw deny 9100/tcp comment "BLOCK: Node Exporter"
ufw deny 9090/tcp comment "BLOCK: Prometheus"
ufw deny 9121/tcp comment "BLOCK: Redis Exporter"
ufw deny 9187/tcp comment "BLOCK: Postgres Exporter"

# Bloquear portas de banco (segurança extra)
echo "🔒 Bloqueando bancos de dados..."
ufw deny 5432/tcp comment "BLOCK: PostgreSQL"
ufw deny 6379/tcp comment "BLOCK: Redis"

# Rate limiting para SSH
echo "⏱️ Configurando rate limiting..."
ufw limit ssh/tcp comment "SSH Rate Limiting"

# Logging
echo "📝 Habilitando logs..."
ufw logging on

# Ativar firewall
echo "🔥 Ativando firewall..."
ufw --force enable

# Status final
echo ""
echo "=========================================="
echo "✅ FIREWALL CONFIGURADO COM SUCESSO!"
echo "=========================================="
echo ""
ufw status verbose
echo ""
echo "📋 RESUMO DA CONFIGURAÇÃO:"
echo "🟢 PORTAS PERMITIDAS:"
echo "   - 22 (SSH): Configurado conforme escolha"
echo "   - 8000 (Aplicação ISP): Aberto"
echo "   - 3000 (Grafana): Configurado conforme escolha"
echo ""
echo "🔴 PORTAS BLOQUEADAS:"
echo "   - 9100 (Node Exporter)"
echo "   - 9090 (Prometheus)"
echo "   - 9121 (Redis Exporter)"
echo "   - 9187 (Postgres Exporter)"
echo "   - 5432 (PostgreSQL)"
echo "   - 6379 (Redis)"
echo ""
echo "💾 Backup salvo em: /root/firewall_backups/"
echo "🔧 Para desativar: ufw disable"
echo "📊 Para ver status: ufw status verbose"
echo ""
echo "⚠️ IMPORTANTE: Teste a conectividade antes de desconectar!"