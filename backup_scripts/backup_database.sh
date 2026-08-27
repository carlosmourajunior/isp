#!/bin/bash

# Script de Backup do Banco PostgreSQL - ISP System
# Uso: ./backup_database.sh [diretorio_backup]

# Configurações
CONTAINER_NAME="isp-db-1"
DB_USER="postgres"
DB_NAME="postgres"
BACKUP_DIR="${1:-./backups}"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="isp_backup_${DATE}.bak"
BACKUP_PATH="${BACKUP_DIR}/${BACKUP_FILE}"

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}=== BACKUP ISP DATABASE ===${NC}"
echo "Data/Hora: $(date)"
echo "Container: ${CONTAINER_NAME}"
echo "Banco: ${DB_NAME}"
echo "Arquivo: ${BACKUP_PATH}"
echo

# Criar diretório de backup se não existir
if [ ! -d "$BACKUP_DIR" ]; then
    echo -e "${YELLOW}Criando diretório de backup: $BACKUP_DIR${NC}"
    mkdir -p "$BACKUP_DIR"
fi

# Verificar se o container está rodando
if ! docker ps | grep -q "$CONTAINER_NAME"; then
    echo -e "${RED}ERRO: Container $CONTAINER_NAME não está rodando!${NC}"
    exit 1
fi

# Fazer backup
echo -e "${YELLOW}Iniciando backup...${NC}"
if docker exec -t "$CONTAINER_NAME" pg_dump -U "$DB_USER" -d "$DB_NAME" -F c -b -v > "$BACKUP_PATH"; then
    # Verificar tamanho do arquivo
    BACKUP_SIZE=$(du -h "$BACKUP_PATH" | cut -f1)
    echo -e "${GREEN}✓ Backup concluído com sucesso!${NC}"
    echo -e "${GREEN}  Arquivo: $BACKUP_PATH${NC}"
    echo -e "${GREEN}  Tamanho: $BACKUP_SIZE${NC}"
    
    # Comprimir backup (opcional)
    echo -e "${YELLOW}Comprimindo backup...${NC}"
    if gzip "$BACKUP_PATH"; then
        COMPRESSED_SIZE=$(du -h "${BACKUP_PATH}.gz" | cut -f1)
        echo -e "${GREEN}✓ Backup comprimido: ${BACKUP_PATH}.gz${NC}"
        echo -e "${GREEN}  Tamanho comprimido: $COMPRESSED_SIZE${NC}"
    fi
else
    echo -e "${RED}✗ Erro durante o backup!${NC}"
    exit 1
fi

# Listar backups existentes
echo
echo -e "${YELLOW}Backups existentes em $BACKUP_DIR:${NC}"
ls -lah "$BACKUP_DIR"/isp_backup_* 2>/dev/null || echo "Nenhum backup encontrado."

echo
echo -e "${GREEN}=== BACKUP CONCLUÍDO ===${NC}"