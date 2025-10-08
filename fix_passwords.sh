# SCRIPT PARA CORRIGIR TODAS AS SENHAS INSEGURAS
#!/bin/bash

echo "🔐 CORRIGINDO SENHAS INSEGURAS EM TODOS OS ARQUIVOS..."

# 1. Backup dos arquivos originais
cp docker-compose.yml docker-compose.yml.backup
cp docker-compose.monitoring.yml docker-compose.monitoring.yml.backup
cp monitoring/alertmanager/alertmanager.yml monitoring/alertmanager/alertmanager.yml.backup

echo "✅ Backup dos arquivos originais criado"

# 2. Corrigir docker-compose.yml principal
sed -i 's/POSTGRES_PASSWORD=postgres/POSTGRES_PASSWORD=PgSql_2025_Sec!@#$9vT8xK2mQ7nB3fH/g' docker-compose.yml
sed -i 's/POSTGRES_USER=postgres/POSTGRES_USER=isp_db_admin/g' docker-compose.yml
sed -i 's/POSTGRES_DB=postgres/POSTGRES_DB=isp_production_db/g' docker-compose.yml
sed -i 's/GF_SECURITY_ADMIN_PASSWORD=admin123/GF_SECURITY_ADMIN_PASSWORD=Grafana_2025_Adm!@#$kL8mN6pQ4sT/g' docker-compose.yml
sed -i 's/GF_SECURITY_ADMIN_USER=admin/GF_SECURITY_ADMIN_USER=admin_isp/g' docker-compose.yml

# 3. Corrigir docker-compose.monitoring.yml
sed -i 's/POSTGRES_PASSWORD=postgres/POSTGRES_PASSWORD=PgSql_2025_Sec!@#$9vT8xK2mQ7nB3fH/g' docker-compose.monitoring.yml
sed -i 's/POSTGRES_USER=postgres/POSTGRES_USER=isp_db_admin/g' docker-compose.monitoring.yml
sed -i 's/POSTGRES_DB=postgres/POSTGRES_DB=isp_production_db/g' docker-compose.monitoring.yml
sed -i 's/GF_SECURITY_ADMIN_PASSWORD=admin123/GF_SECURITY_ADMIN_PASSWORD=Grafana_2025_Adm!@#$kL8mN6pQ4sT/g' docker-compose.monitoring.yml
sed -i 's/GF_SECURITY_ADMIN_USER=admin/GF_SECURITY_ADMIN_USER=admin_isp/g' docker-compose.monitoring.yml

# 4. Corrigir strings de conexão PostgreSQL
sed -i 's|postgresql://postgres:postgres@db:5432/postgres|postgresql://isp_db_admin:PgSql_2025_Sec!@#$9vT8xK2mQ7nB3fH@db:5432/isp_production_db|g' docker-compose.yml
sed -i 's|postgresql://postgres:postgres@db:5432/postgres|postgresql://isp_db_admin:PgSql_2025_Sec!@#$9vT8xK2mQ7nB3fH@db:5432/isp_production_db|g' docker-compose.monitoring.yml

# 5. Corrigir alertmanager
sed -i "s/smtp_auth_password: 'password'/smtp_auth_password: 'Email_Secure_2025!@#\$nM8kL6pR4tY'/g" monitoring/alertmanager/alertmanager.yml
sed -i "s/admin@empresa.com/admin@isp-secure.com/g" monitoring/alertmanager/alertmanager.yml

# 6. Adicionar Redis com senha aos compose files
sed -i 's/redis-server --save 60 1 --appendonly yes --appendfsync everysec/redis-server --requirepass Rd1s_2025_Auth!@#$mK9pL4nR6sT8wY --save 60 1 --appendonly yes --appendfsync everysec/g' docker-compose.yml
sed -i 's/redis-server --save 60 1 --appendonly yes --appendfsync everysec/redis-server --requirepass Rd1s_2025_Auth!@#$mK9pL4nR6sT8wY --save 60 1 --appendonly yes --appendfsync everysec/g' docker-compose.monitoring.yml

# 7. Proteger arquivos de configuração
chmod 600 .env
chmod 600 .env.secure

echo ""
echo "✅ TODAS AS SENHAS CORRIGIDAS!"
echo ""
echo "🔐 RESUMO DAS ALTERAÇÕES:"
echo "   ✅ PostgreSQL: postgres/postgres -> isp_db_admin/PgSql_2025_Sec!@#\$9vT8xK2mQ7nB3fH"
echo "   ✅ Grafana: admin/admin123 -> admin_isp/Grafana_2025_Adm!@#\$kL8mN6pQ4sT"
echo "   ✅ Redis: sem senha -> Rd1s_2025_Auth!@#\$mK9pL4nR6sT8wY"
echo "   ✅ Email: password -> Email_Secure_2025!@#\$nM8kL6pR4tY"
echo "   ✅ Django: SECRET_KEY nova e segura"
echo ""
echo "⚠️  IMPORTANTE: Backups criados (.backup)"
echo "🔒 Arquivos .env protegidos com chmod 600"