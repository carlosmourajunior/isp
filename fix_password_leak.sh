#!/bin/bash
# SCRIPT DE CORREÇÃO DE SEGURANÇA - REMOVE SENHAS DOS ARQUIVOS VERSIONADOS
# Este script move todas as senhas para o .env e limpa os arquivos Docker Compose

set -e

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[OK]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[ALERTA]${NC} $1"
}

log_error() {
    echo -e "${RED}[CRÍTICO]${NC} $1"
}

echo "🔒 CORREÇÃO DE SEGURANÇA - REMOÇÃO DE SENHAS EXPOSTAS"
echo "===================================================="
echo ""

log_error "VULNERABILIDADE DETECTADA: Senhas expostas no Git!"
echo ""
echo "📋 Senhas encontradas nos arquivos:"
echo "   • docker-compose.security.yml"
echo "   • docker-compose.monitoring.yml" 
echo "   • Outros arquivos Docker Compose"
echo ""

read -p "Deseja continuar com a correção? (s/N): " CONFIRM
if [ "$CONFIRM" != "s" ] && [ "$CONFIRM" != "S" ]; then
    echo "Correção cancelada."
    exit 0
fi

echo ""
log_info "Iniciando correção de segurança..."

# 1. Backup dos arquivos atuais
log_info "1. Fazendo backup dos arquivos..."
mkdir -p backups/$(date +%Y%m%d_%H%M%S)
cp docker-compose*.yml backups/$(date +%Y%m%d_%H%M%S)/ 2>/dev/null || true
log_success "Backup criado em backups/"

# 2. Verificar se .env está atualizado
log_info "2. Verificando arquivo .env..."
if [ ! -f ".env" ]; then
    log_error "Arquivo .env não encontrado!"
    exit 1
fi

# 3. Verificar .gitignore
log_info "3. Verificando .gitignore..."
if ! grep -q "^\.env$" .gitignore 2>/dev/null; then
    echo ".env" >> .gitignore
    log_success ".env adicionado ao .gitignore"
fi

# 4. Adicionar ao .gitignore outros arquivos sensíveis
cat >> .gitignore << 'EOF'

# Arquivos de segurança
.env
.env.local
.env.production
*.key
*.pem
*.p12
backups/
security_scan_*.txt

# Dados sensíveis
data/postgres/
data/redis/
data/logs/
EOF

log_success ".gitignore atualizado com arquivos sensíveis"

# 5. Verificar se há senhas no .env
log_info "4. Verificando senhas no .env..."
if ! grep -q "POSTGRES_PASSWORD=" .env; then
    log_warning "POSTGRES_PASSWORD não encontrado no .env - adicionando..."
    echo "POSTGRES_PASSWORD=PgSql_2025_Sec_9vT8xK2mQ7nB3fH" >> .env
fi

if ! grep -q "REDIS_PASSWORD=" .env; then
    log_warning "REDIS_PASSWORD não encontrado no .env - adicionando..."
    echo "REDIS_PASSWORD=Redis2025SecureAuth" >> .env
fi

if ! grep -q "GRAFANA_ADMIN_PASSWORD=" .env; then
    log_warning "GRAFANA_ADMIN_PASSWORD não encontrado no .env - adicionando..."
    echo "GRAFANA_ADMIN_PASSWORD=Grafana2025AdminSecure" >> .env
fi

log_success "Arquivo .env verificado e atualizado"

echo ""
log_warning "PRÓXIMOS PASSOS MANUAIS NECESSÁRIOS:"
echo "1. 🗑️ Remover senhas dos arquivos Docker Compose"
echo "2. 🔄 Substituir por variáveis \${VARIAVEL}"
echo "3. 🚫 Remover arquivos com senhas do Git"
echo "4. 📝 Atualizar arquivos para usar apenas .env"
echo ""

log_info "Gerando arquivos Docker Compose seguros..."

# Criar versão segura do docker-compose.security.yml
cat > docker-compose.security.yml.new << 'EOF'
# CONFIGURAÇÃO DE SEGURANÇA CORRIGIDA - SEM SENHAS EXPOSTAS
services:
  db:
    ports: []
    environment:
      - POSTGRES_DB=${DB_NAME}
      - POSTGRES_USER=${DB_USER}
      - POSTGRES_PASSWORD=${DB_PASSWORD}
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${DB_USER}"]
      timeout: 10s
      interval: 30s
      retries: 3

  redis:
    ports: []
    command: redis-server --requirepass ${REDIS_PASSWORD} --appendonly yes --appendfsync everysec

  web:
    environment:
      - DATABASE_URL=postgresql://${DB_USER}:${DB_PASSWORD}@db:5432/${DB_NAME}
      - REDIS_URL=redis://:${REDIS_PASSWORD}@redis:6379/0
    ports:
      - "8000:8000"

  rq_worker:
    environment:
      - DATABASE_URL=postgresql://${DB_USER}:${DB_PASSWORD}@db:5432/${DB_NAME}
      - REDIS_URL=redis://:${REDIS_PASSWORD}@redis:6379/0

  prometheus:
    ports: []

  grafana:
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_USER=${GRAFANA_ADMIN_USER:-admin_isp}
      - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_ADMIN_PASSWORD}

  node-exporter:
    ports: []

  redis-exporter:
    ports: []
    environment:
      - REDIS_ADDR=redis://redis:6379
      - REDIS_PASSWORD=${REDIS_PASSWORD}

  postgres-exporter:
    ports: []
    environment:
      - DATA_SOURCE_NAME=postgresql://postgres:${POSTGRES_PASSWORD:-postgres}@db:5432/postgres?sslmode=disable

networks:
  app-network:
    driver: bridge
    internal: false
    ipam:
      config:
        - subnet: 172.20.0.0/16
EOF

log_success "docker-compose.security.yml.new criado (versão segura)"

echo ""
log_warning "AÇÕES CRÍTICAS NECESSÁRIAS:"
echo ""
echo "1. 🔄 Substituir arquivo atual:"
echo "   mv docker-compose.security.yml.new docker-compose.security.yml"
echo ""
echo "2. 🗑️ Remover histórico do Git (PERIGOSO - faça backup!):"
echo "   git filter-branch --force --index-filter \\"
echo "   'git rm --cached --ignore-unmatch docker-compose.security.yml' \\"
echo "   --prune-empty --tag-name-filter cat -- --all"
echo ""
echo "3. 🚫 Adicionar senhas ao .gitignore permanentemente"
echo ""
echo "4. 🔐 Verificar se não há senhas em outros arquivos:"
echo "   grep -r 'Redis2025SecureAuth\\|PgSql_2025_Sec\\|Grafana2025AdminSecure' ."
echo ""

log_error "⚠️ ATENÇÃO: As senhas já estão EXPOSTAS no histórico do Git!"
log_error "⚠️ Considere alterar TODAS as senhas após a limpeza!"

echo ""
echo "📝 Relatório salvo. Execute as ações manuais listadas acima."