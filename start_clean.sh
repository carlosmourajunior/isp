#!/bin/bash
# SCRIPT RÁPIDO DE DEPLOY COM SCHEDULER AUTOMÁTICO
# Para uso rápido sem verificações detalhadas

echo "🚀 Iniciando o sistema completo..."

# 1. Deploy dos serviços principais
echo "📋 Subindo serviços principais..."
docker compose -f docker-compose.yml -f docker-compose.security.yml -f docker-compose.firewall.yml up -d

# 2. Aguardar serviços ficarem prontos
echo "⏳ Aguardando serviços inicializarem..."
sleep 15

# 2.1. Aplicar migrations do banco de dados
echo "🔧 Aplicando migrations do banco de dados..."
docker compose exec -T web python manage.py migrate --noinput

# 3. Verificar se há dados históricos, se não houver, fazer atualização inicial
echo "📊 Verificando dados do sistema..."
RECORD_COUNT=$(docker compose exec -T web python manage.py shell -c "from olt.models import OltSystemStats; print(OltSystemStats.objects.count())" 2>/dev/null | tail -1 | tr -d '\r')

if [ -z "$RECORD_COUNT" ] || [ "$RECORD_COUNT" -lt "1" ]; then
    echo "🔄 Nenhum dado encontrado, fazendo atualização inicial COMPLETA..."
    echo "   (Isso pode levar alguns minutos - ONUs, Clientes, Portas, OLT...)"
    docker compose exec web python manage.py collect_olt_periodic --once
else
    echo "✅ Dados do sistema encontrados: $RECORD_COUNT registros da OLT"
fi

# 4. Iniciar scheduler de atualização completa (1 hora)
echo "⏰ Iniciando atualização COMPLETA automática a cada 1 hora..."
docker compose -f docker-compose.scheduler.yml up -d

# 5. Status final
echo ""
echo "🎉 Sistema iniciado com sucesso!"
echo ""
echo "📊 Status dos serviços:"
docker compose ps
echo ""
echo "⚡ Status do scheduler:"
docker compose -f docker-compose.scheduler.yml ps
echo ""
echo "🔗 Acessos disponíveis:"
echo "   � Dashboard OLT: http://localhost:8000"
echo "   �📊 Grafana: http://localhost:3000 (admin/admin)"  
echo "   🔍 Prometheus: http://localhost:9090"
echo ""
echo "📋 Funcionalidades ativas:"
echo "   ✅ Atualização automática COMPLETA: A cada 1 hora"
echo "   ✅ Inclui: ONUs, Clientes, Portas, Dados OLT, MACs"
echo "   ✅ Gráficos de performance: CPU e memória"
echo "   ✅ Histórico: 7 dias de dados"
echo "   ✅ Dashboard otimizado: Sem coleta automática"
echo ""
echo "🛠  Comandos úteis:"
echo "   Ver logs scheduler: docker compose -f docker-compose.scheduler.yml logs -f"
echo "   Atualização manual completa: docker compose exec web python manage.py collect_olt_periodic --once"
echo "   Parar scheduler: docker compose -f docker-compose.scheduler.yml down"