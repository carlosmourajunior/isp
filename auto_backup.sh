#!/bin/bash
# Script de backup automático e proteção do banco
# Execute este script a cada hora via cron

BACKUP_DIR="/root/isp/backups"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/auto_backup_$DATE.sql"

# Criar diretório se não existir
mkdir -p "$BACKUP_DIR"

echo "🔄 Iniciando backup automático - $(date)"

# Fazer backup
cd /root/isp
docker-compose exec -T db pg_dump -U postgres postgres > "$BACKUP_FILE"

if [ -s "$BACKUP_FILE" ]; then
    echo "✅ Backup criado: $BACKUP_FILE ($(du -h "$BACKUP_FILE" | cut -f1))"
    
    # Manter apenas os últimos 24 backups (1 por hora)
    ls -t "$BACKUP_DIR"/auto_backup_*.sql | tail -n +25 | xargs -r rm
    
    # Verificar se banco principal tem dados
    TABLE_COUNT=$(docker-compose exec -T db psql -U postgres -d postgres -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';" | grep -E "^\s*[0-9]+\s*$" | tr -d ' ')
    
    if [ "$TABLE_COUNT" -lt 5 ]; then
        echo "🚨 ALERTA: Banco principal tem apenas $TABLE_COUNT tabelas!"
        echo "🚨 Possível perda de dados detectada em $(date)" >> "$BACKUP_DIR/alerts.log"
        
        # Tentar restaurar último backup válido se banco estiver muito vazio
        if [ "$TABLE_COUNT" -eq 0 ]; then
            echo "🆘 Banco completamente vazio - tentando restaurar último backup válido"
            LAST_GOOD_BACKUP=$(find "$BACKUP_DIR" -name "auto_backup_*.sql" -size +10k | sort | tail -1)
            if [ -n "$LAST_GOOD_BACKUP" ]; then
                echo "🔄 Restaurando: $LAST_GOOD_BACKUP"
                docker-compose exec -T db psql -U postgres postgres < "$LAST_GOOD_BACKUP"
                echo "✅ Backup restaurado automaticamente"
            fi
        fi
    fi
    
else
    echo "❌ Falha no backup - arquivo vazio ou não criado"
    echo "❌ Falha no backup em $(date)" >> "$BACKUP_DIR/backup_errors.log"
fi

echo "🏁 Backup concluído - $(date)"