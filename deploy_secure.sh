#!/bin/bash
# SCRIPT DE DEPLOY SEGURO DO SISTEMA ISP
# Criado em: $(date)

set -e  # Para na primeira falha

echo "🚀 DEPLOY SEGURO DO SISTEMA ISP"
echo "================================"

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Função para log colorido
log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

# 1. Parar containers existentes
log_info "Parando containers existentes..."
docker compose down || true

# 2. Limpar redes não utilizadas
log_info "Limpando redes Docker..."
docker network prune -f

# 3. Verificar e corrigir permissões
log_info "Verificando permissões dos dados..."
if [ -d "data/redis" ]; then
    log_info "Corrigindo permissões do Redis..."
    sudo chown -R 999:999 data/redis/ || true
    sudo chmod -R 755 data/redis/ || true
fi

if [ -d "data/postgres" ]; then
    log_info "Corrigindo permissões do PostgreSQL..."
    sudo chown -R 999:999 data/postgres/ || true
    sudo chmod -R 755 data/postgres/ || true
fi

# 4. Criar diretórios necessários
log_info "Criando diretórios necessários..."
mkdir -p data/{redis,postgres,media,logs,staticfiles}
mkdir -p logs media staticfiles

# 5. Verificar arquivos de configuração
log_info "Verificando arquivos de configuração..."
if [ ! -f "docker-compose.yml" ]; then
    log_error "Arquivo docker-compose.yml não encontrado!"
    exit 1
fi

if [ ! -f "docker-compose.security.yml" ]; then
    log_error "Arquivo docker-compose.security.yml não encontrado!"
    exit 1
fi

if [ ! -f "docker-compose.firewall.yml" ]; then
    log_error "Arquivo docker-compose.firewall.yml não encontrado!"
    exit 1
fi

log_success "Todos os arquivos de configuração encontrados"

# 6. Deploy com todas as configurações de segurança
log_info "Iniciando deploy com configurações de segurança..."
echo "Usando arquivos:"
echo "  - docker-compose.yml (base)"
echo "  - docker-compose.security.yml (segurança)"
echo "  - docker-compose.firewall.yml (firewall)"

docker compose -f docker-compose.yml -f docker-compose.security.yml -f docker-compose.firewall.yml up -d

# 7. Aguardar containers ficarem saudáveis
log_info "Aguardando containers iniciarem..."
sleep 10

# 8. Verificar status
echo ""
log_info "Status dos containers:"
docker compose ps

echo ""
log_info "Verificando logs de erro..."
docker compose logs --tail=20 | grep -i "error\|fail\|exception" || log_success "Nenhum erro encontrado nos logs"

# 9. Verificar portas expostas
echo ""
log_info "Portas expostas após configuração de firewall:"
netstat -tulpn | grep LISTEN | grep -E ":8000|:3000|:22" || log_warning "Algumas portas podem não estar visíveis"

# 10. Teste de conectividade
echo ""
log_info "Testando conectividade dos serviços..."

# Teste da aplicação
if curl -s -f http://localhost:8000/api/health/ > /dev/null 2>&1; then
    log_success "Aplicação ISP (porta 8000) - OK"
else
    log_warning "Aplicação ISP (porta 8000) - Verificar logs"
fi

# Teste do Grafana
if curl -s -f http://localhost:3000 > /dev/null 2>&1; then
    log_success "Grafana (porta 3000) - OK"
else
    log_warning "Grafana (porta 3000) - Verificar logs"
fi

# 11. Resumo final
echo ""
echo "=========================================="
log_success "DEPLOY CONCLUÍDO!"
echo "=========================================="
echo ""
echo "🌐 SERVIÇOS DISPONÍVEIS:"
echo "   • Aplicação ISP: http://$(curl -s ifconfig.me):8000"
echo "   • Grafana:       http://$(curl -s ifconfig.me):3000"
echo ""
echo "🔒 PORTAS BLOQUEADAS (segurança):"
echo "   • 9100 (Node Exporter)"
echo "   • 9090 (Prometheus)" 
echo "   • 9121 (Redis Exporter)"
echo "   • 9187 (Postgres Exporter)"
echo "   • 5432 (PostgreSQL)"
echo "   • 6379 (Redis)"
echo ""
echo "📋 COMANDOS ÚTEIS:"
echo "   • Ver logs:      docker compose logs -f"
echo "   • Parar:         docker compose down"
echo "   • Reiniciar:     ./deploy_secure.sh"
echo "   • Status:        docker compose ps"
echo ""
log_info "Sistema deployado com configurações de segurança ativadas!"