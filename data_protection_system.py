#!/usr/bin/env python
"""
Sistema de monitoramento contínuo para detectar e prevenir perda de dados.
Executa verificações a cada 5 minutos e toma ações preventivas.
"""
import os
import django
import time
import logging
import subprocess
from datetime import datetime, timedelta

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'isp.settings')
django.setup()

from django.db import connection, transaction
from django.contrib.auth.models import User

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    handlers=[
        logging.FileHandler('/code/logs/data_protection.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class DataProtectionSystem:
    def __init__(self):
        self.last_table_counts = {}
        self.backup_threshold = 10  # Fazer backup se perda > 10%
        self.critical_tables = [
            'auth_user',
            'django_session', 
            'olt_clientefibraixc',
            'olt_onu',
            'olt_oltusers',
            'olt_oltslot',
            'olt_olttemperature'
        ]
    
    def check_database_health(self):
        """Verifica saúde geral do banco"""
        try:
            cursor = connection.cursor()
            
            # Verificar se consegue conectar
            cursor.execute("SELECT 1")
            
            # Verificar número de tabelas
            cursor.execute("""
                SELECT COUNT(*) FROM information_schema.tables 
                WHERE table_schema = 'public'
            """)
            table_count = cursor.fetchone()[0]
            
            if table_count < 5:
                logger.error(f"🚨 CRÍTICO: Apenas {table_count} tabelas no banco!")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro ao verificar saúde do banco: {e}")
            return False
    
    def count_table_records(self):
        """Conta registros nas tabelas críticas"""
        counts = {}
        
        try:
            cursor = connection.cursor()
            
            for table in self.critical_tables:
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    counts[table] = cursor.fetchone()[0]
                except Exception as e:
                    logger.warning(f"⚠️ Erro ao contar {table}: {e}")
                    counts[table] = -1  # Indica erro
            
            return counts
            
        except Exception as e:
            logger.error(f"❌ Erro ao conectar ao banco: {e}")
            return {}
    
    def detect_data_loss(self, current_counts):
        """Detecta perda de dados comparando com contagem anterior"""
        alerts = []
        
        for table, current_count in current_counts.items():
            if table in self.last_table_counts:
                last_count = self.last_table_counts[table]
                
                # Pular se houve erro
                if current_count == -1 or last_count == -1:
                    continue
                
                # Detectar perda crítica
                if current_count == 0 and last_count > 0:
                    alerts.append({
                        'level': 'CRITICAL',
                        'table': table,
                        'message': f"Tabela {table} completamente esvaziada! Era {last_count}, agora 0"
                    })
                
                # Detectar perda significativa
                elif last_count > 0 and current_count < (last_count * 0.9):
                    loss_pct = ((last_count - current_count) / last_count) * 100
                    alerts.append({
                        'level': 'WARNING',
                        'table': table, 
                        'message': f"Perda de {loss_pct:.1f}% em {table}: {last_count} → {current_count}"
                    })
        
        return alerts
    
    def emergency_backup(self):
        """Cria backup de emergência"""
        try:
            backup_dir = "/code/backups"
            os.makedirs(backup_dir, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = f"{backup_dir}/emergency_backup_{timestamp}.sql"
            
            # Executar backup
            result = subprocess.run([
                'docker-compose', 'exec', '-T', 'db', 
                'pg_dump', '-U', 'postgres', 'postgres'
            ], capture_output=True, text=True, cwd='/code')
            
            if result.returncode == 0 and result.stdout:
                with open(backup_file, 'w') as f:
                    f.write(result.stdout)
                
                logger.info(f"✅ Backup de emergência criado: {backup_file}")
                return backup_file
            else:
                logger.error(f"❌ Falha no backup: {result.stderr}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Erro ao criar backup: {e}")
            return None
    
    def stop_dangerous_processes(self):
        """Para processos que podem causar perda de dados"""
        try:
            logger.warning("🛑 Parando scheduler e workers por segurança...")
            subprocess.run(['docker-compose', 'stop', 'scheduler', 'rq_worker'], 
                         cwd='/code', capture_output=True)
            logger.info("✅ Processos perigosos parados")
        except Exception as e:
            logger.error(f"❌ Erro ao parar processos: {e}")
    
    def run_protection_cycle(self):
        """Executa um ciclo completo de proteção"""
        logger.info("🔍 Iniciando ciclo de proteção de dados...")
        
        # Verificar saúde do banco
        if not self.check_database_health():
            logger.error("🚨 Banco em estado crítico!")
            self.emergency_backup()
            self.stop_dangerous_processes()
            return
        
        # Contar registros atuais
        current_counts = self.count_table_records()
        
        if not current_counts:
            logger.error("❌ Não foi possível contar registros")
            return
        
        # Detectar perda de dados
        alerts = self.detect_data_loss(current_counts)
        
        # Processar alertas
        for alert in alerts:
            if alert['level'] == 'CRITICAL':
                logger.error(f"🚨 {alert['message']}")
                
                # Ações de emergência
                self.emergency_backup()
                self.stop_dangerous_processes()
                
            elif alert['level'] == 'WARNING':
                logger.warning(f"⚠️ {alert['message']}")
                
                # Backup preventivo
                if len([a for a in alerts if a['level'] == 'WARNING']) >= 2:
                    logger.info("📦 Múltiplos alertas - criando backup preventivo")
                    self.emergency_backup()
        
        # Atualizar contagem para próximo ciclo
        self.last_table_counts = current_counts.copy()
        
        # Log status
        total_records = sum(count for count in current_counts.values() if count > 0)
        logger.info(f"📊 Status: {total_records} registros totais em {len(current_counts)} tabelas")
    
    def run_continuous_monitoring(self):
        """Executa monitoramento contínuo"""
        logger.info("🛡️ SISTEMA DE PROTEÇÃO DE DADOS INICIADO")
        logger.info("=" * 50)
        
        # Estado inicial
        self.last_table_counts = self.count_table_records()
        logger.info("📊 Estado inicial capturado")
        
        cycle = 0
        while True:
            try:
                cycle += 1
                
                # Log a cada 12 ciclos (1 hora se ciclo = 5min)
                if cycle % 12 == 0:
                    logger.info(f"⏰ Sistema ativo - Ciclo {cycle}")
                
                self.run_protection_cycle()
                
                # Aguardar 5 minutos
                time.sleep(300)
                
            except KeyboardInterrupt:
                logger.info("🛑 Sistema de proteção interrompido")
                break
            except Exception as e:
                logger.error(f"❌ Erro no ciclo de proteção: {e}")
                time.sleep(60)  # Aguardar 1 minuto em caso de erro

if __name__ == "__main__":
    protection_system = DataProtectionSystem()
    protection_system.run_continuous_monitoring()