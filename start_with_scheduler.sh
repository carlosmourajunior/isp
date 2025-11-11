#!/bin/bash

echo "🚀 === INICIANDO SISTEMA OLT COM COLETA AUTOMÁTICA ==="
echo

# 1. Subir serviços principais se não estiverem rodando
echo "📋 Verificando serviços principais..."
if ! docker compose ps | grep -q "web.*Up"; then
    echo "🔄 Iniciando serviços principais..."
    docker compose -f docker-compose.yml -f docker-compose.security.yml -f docker-compose.firewall.yml up -d
    echo "⏳ Aguardando serviços ficarem prontos..."
    sleep 10
else
    echo "✅ Serviços principais já estão rodando"
fi

# 2. Verificar se há dados históricos
echo
echo "📊 Verificando dados históricos..."
RECORD_COUNT=$(docker compose exec -T web python manage.py shell -c "from olt.models import OltSystemStats; print(OltSystemStats.objects.count())" 2>/dev/null | tail -1)
echo "📈 Registros históricos encontrados: $RECORD_COUNT"

# 3. Se há poucos dados, fazer uma coleta inicial
if [ "$RECORD_COUNT" -lt "2" ]; then
    echo "🔄 Fazendo coleta inicial de dados..."
    docker compose exec web python manage.py collect_olt_periodic --once
else
    echo "✅ Dados históricos suficientes encontrados"
fi

# 4. Iniciar coleta automática
echo
echo "⏰ Iniciando coleta automática a cada 1 hora..."
echo "📝 Logs serão salvos em ./logs/olt_scheduler.log"

# Verificar se o scheduler já está rodando
if docker ps | grep -q "isp_olt_scheduler"; then
    echo "⚠️ Scheduler já está rodando, parando primeiro..."
    docker compose -f docker-compose.scheduler.yml down
fi

# Iniciar o scheduler
docker compose -f docker-compose.scheduler.yml up -d

echo
echo "🎉 === SISTEMA INICIADO COM SUCESSO ==="
echo
echo "🔗 Acessos:"
echo "   Dashboard: http://localhost:8000"
echo "   Grafana: http://localhost:3000 (admin/admin)"
echo "   Prometheus: http://localhost:9090"
echo
echo "📋 Comandos úteis:"
echo "   Ver logs do scheduler: docker compose -f docker-compose.scheduler.yml logs -f"
echo "   Parar coleta automática: docker compose -f docker-compose.scheduler.yml down"
echo "   Coleta manual única: docker compose exec web python manage.py collect_olt_periodic --once"
echo "   Status dos serviços: docker compose ps"
echo
echo "⏰ A coleta automática está configurada para executar a cada 1 hora"
echo "🎯 No dashboard, use o botão 'Atualizar OLT' para coletas manuais"