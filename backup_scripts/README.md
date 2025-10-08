# Scripts de Backup e Restauração - ISP Database

Este diretório contém scripts para fazer backup e restauração do banco de dados PostgreSQL do sistema ISP rodando em Docker.

## Arquivos

- `backup_database.sh` - Script para fazer backup automático
- `restore_database.sh` - Script para restaurar backup
- `README.md` - Este arquivo

## Pré-requisitos

1. Docker e Docker Compose funcionando
2. Containers do ISP rodando (especialmente o container do PostgreSQL)
3. Permissões de execução nos scripts

## Uso

### Fazer Backup

```bash
# Backup padrão (salva em ./backups/)
./backup_database.sh

# Backup em diretório específico
./backup_database.sh /path/para/backups
```

O script irá:
- Criar o diretório de backup se não existir
- Verificar se o container está rodando
- Fazer backup no formato custom (.bak)
- Comprimir o arquivo automaticamente (.bak.gz)
- Mostrar informações sobre tamanho e localização

### Restaurar Backup

```bash
# Restaurar de um arquivo específico
./restore_database.sh ./backups/isp_backup_20251006_143000.bak.gz

# Também funciona com arquivos não comprimidos
./restore_database.sh ./backups/isp_backup_20251006_143000.bak
./restore_database.sh ./backups/isp_backup_20251006_143000.sql
```

O script irá:
- Verificar se o arquivo existe
- Detectar o tipo de arquivo automaticamente
- Pedir confirmação antes de sobrescrever o banco
- Restaurar os dados
- Sugerir reiniciar os containers da aplicação

## Dar Permissão de Execução

```bash
chmod +x backup_database.sh
chmod +x restore_database.sh
```

## Comandos Manuais

Se preferir executar manualmente:

### Backup Manual
```bash
# Backup simples
docker exec -t isp-db-1 pg_dump -U postgres -d postgres -F c -b -v > backup_$(date +%Y%m%d_%H%M%S).bak

# Backup comprimido
docker exec -t isp-db-1 pg_dump -U postgres -d postgres -F c -b -v | gzip > backup_$(date +%Y%m%d_%H%M%S).bak.gz
```

### Restauração Manual
```bash
# Restaurar arquivo .bak
docker exec -i isp-db-1 pg_restore -U postgres -d postgres -v --clean --if-exists < backup.bak

# Restaurar arquivo comprimido
zcat backup.bak.gz | docker exec -i isp-db-1 pg_restore -U postgres -d postgres -v --clean --if-exists
```

## Automatização

Para automatizar backups, adicione ao crontab:

```bash
# Backup diário às 2:00
0 2 * * * /path/para/isp/backup_scripts/backup_database.sh /path/para/backups

# Backup a cada 6 horas
0 */6 * * * /path/para/isp/backup_scripts/backup_database.sh /path/para/backups
```

## Notas Importantes

1. **Nome do Container**: Os scripts assumem que o container do PostgreSQL se chama `isp-db-1`. Se for diferente, edite a variável `CONTAINER_NAME` nos scripts.

2. **Espaço em Disco**: Monitore o espaço disponível, especialmente se automatizar backups frequentes.

3. **Segurança**: Os backups contêm dados sensíveis. Mantenha-os em local seguro.

4. **Teste**: Sempre teste a restauração em ambiente de desenvolvimento antes de usar em produção.

5. **Reiniciar Aplicação**: Após restaurar, recomenda-se reiniciar os containers da aplicação:
   ```bash
   docker-compose restart web rq_worker
   ```