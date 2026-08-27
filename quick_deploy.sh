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

# Deploy (hardening já incorporado ao docker-compose.yml)
docker compose -f docker-compose.yml up -d

# Status
echo "📊 Status:"
docker compose ps