#!/bin/bash
# SCRIPT RÁPIDO DE DEPLOY
# Para uso rápido sem verificações detalhadas

echo "🚀 Iniciando o sistema..."


# Deploy seguro
docker compose -f docker-compose.yml -f docker-compose.security.yml -f docker-compose.firewall.yml up -d

# Status
echo "📊 Status:"
docker compose ps