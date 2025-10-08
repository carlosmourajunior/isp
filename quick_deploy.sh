#!/bin/bash
# SCRIPT RÁPIDO DE DEPLOY
# Para uso rápido sem verificações detalhadas

echo "🚀 Deploy rápido com segurança..."

# Parar
docker compose down

# Limpar redes
docker network prune -f

# Corrigir permissões básicas
sudo chown -R 999:999 data/ 2>/dev/null || true

# Deploy seguro
docker compose -f docker-compose.yml -f docker-compose.security.yml -f docker-compose.firewall.yml up -d

# Status
echo "📊 Status:"
docker compose ps