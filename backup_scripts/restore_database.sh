#!/bin/bash

# Script de Restauração do Banco PostgreSQL - ISP System
# Uso: ./restore_database.sh <arquivo_backup>

# Verificar se o arquivo foi fornecido
if [ $# -eq 0 ]; then
    echo "Uso: $0 <arquivo_backup>"
    echo "Exemplo: $0 ./backups/isp_backup_20251006_143000.bak.gz"
    exit 1
fi

BACKUP_FILE="$1"
CONTAINER_NAME="isp-db-1"
DB_USER="postgres"
DB_NAME="postgres"

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}=== RESTAURAÇÃO ISP DATABASE ===${NC}"
echo "Data/Hora: $(date)"
echo "Container: ${CONTAINER_NAME}"
echo "Banco: ${DB_NAME}"
echo "Arquivo: ${BACKUP_FILE}"
echo

# Verificar se o arquivo existe
if [ ! -f "$BACKUP_FILE" ]; then
    echo -e "${RED}ERRO: Arquivo $BACKUP_FILE não encontrado!${NC}"
    exit 1
fi

# Verificar se o container está rodando
if ! docker ps | grep -q "$CONTAINER_NAME"; then
    echo -e "${RED}ERRO: Container $CONTAINER_NAME não está rodando!${NC}"
    exit 1
fi

# Confirmação
echo -e "${YELLOW}⚠️  ATENÇÃO: Esta operação irá SOBRESCREVER o banco atual!${NC}"
read -p "Tem certeza que deseja continuar? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}Operação cancelada.${NC}"
    exit 0
fi

# Determinar tipo de arquivo e comando de restauração
if [[ "$BACKUP_FILE" == *.gz ]]; then
    echo -e "${YELLOW}Detectado arquivo comprimido (.gz)${NC}"
    echo -e "${YELLOW}Iniciando restauração...${NC}"
    if zcat "$BACKUP_FILE" | docker exec -i "$CONTAINER_NAME" pg_restore -U "$DB_USER" -d "$DB_NAME" -v --clean --if-exists; then
        echo -e "${GREEN}✓ Restauração concluída com sucesso!${NC}"
    else
        echo -e "${RED}✗ Erro durante a restauração!${NC}"
        exit 1
    fi
elif [[ "$BACKUP_FILE" == *.bak ]]; then
    echo -e "${YELLOW}Detectado arquivo formato custom (.bak)${NC}"
    echo -e "${YELLOW}Iniciando restauração...${NC}"
    if docker exec -i "$CONTAINER_NAME" pg_restore -U "$DB_USER" -d "$DB_NAME" -v --clean --if-exists < "$BACKUP_FILE"; then
        echo -e "${GREEN}✓ Restauração concluída com sucesso!${NC}"
    else
        echo -e "${RED}✗ Erro durante a restauração!${NC}"
        exit 1
    fi
elif [[ "$BACKUP_FILE" == *.sql ]]; then
    echo -e "${YELLOW}Detectado arquivo SQL (.sql)${NC}"
    echo -e "${YELLOW}Iniciando restauração...${NC}"
    if docker exec -i "$CONTAINER_NAME" psql -U "$DB_USER" -d "$DB_NAME" < "$BACKUP_FILE"; then
        echo -e "${GREEN}✓ Restauração concluída com sucesso!${NC}"
    else
        echo -e "${RED}✗ Erro durante a restauração!${NC}"
        exit 1
    fi
else
    echo -e "${RED}ERRO: Tipo de arquivo não suportado!${NC}"
    echo "Tipos suportados: .bak, .sql, .gz"
    exit 1
fi

echo
echo -e "${GREEN}=== RESTAURAÇÃO CONCLUÍDA ===${NC}"
echo -e "${YELLOW}Recomenda-se reiniciar os containers da aplicação:${NC}"
echo "docker-compose restart web rq_worker"