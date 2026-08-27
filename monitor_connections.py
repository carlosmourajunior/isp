#!/usr/bin/env python3
"""
Script para monitorar conexões do PostgreSQL
Executa: python monitor_connections.py
"""

import psycopg2
import os
from datetime import datetime

def monitor_postgres_connections():
    """Monitora as conexões ativas do PostgreSQL"""
    try:
        # Configurações do banco
        conn = psycopg2.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            port=os.getenv('DB_PORT', '5432'),
            database=os.getenv('DB_NAME', 'postgres'),
            user=os.getenv('DB_USER', 'postgres'),
            password=os.getenv('DB_PASSWORD', 'postgres')
        )
        
        cursor = conn.cursor()
        
        print(f"\n🔍 MONITORAMENTO DE CONEXÕES - {datetime.now()}")
        print("=" * 60)
        
        # Query para ver conexões ativas
        cursor.execute("""
            SELECT 
                count(*) as total_connections,
                count(*) FILTER (WHERE state = 'active') as active_connections,
                count(*) FILTER (WHERE state = 'idle') as idle_connections,
                count(*) FILTER (WHERE state = 'idle in transaction') as idle_in_transaction
            FROM pg_stat_activity 
            WHERE datname = %s
        """, (os.getenv('DB_NAME', 'postgres'),))
        
        result = cursor.fetchone()
        total, active, idle, idle_in_tx = result
        
        print(f"📊 TOTAL DE CONEXÕES: {total}")
        print(f"🟢 ATIVAS: {active}")
        print(f"🟡 IDLE: {idle}")
        print(f"🔴 IDLE EM TRANSAÇÃO: {idle_in_tx}")
        
        # Ver limite máximo
        cursor.execute("SHOW max_connections")
        max_conn = cursor.fetchone()[0]
        print(f"⚠️  LIMITE MÁXIMO: {max_conn}")
        
        # Calcular percentual de uso
        usage_percent = (total / int(max_conn)) * 100
        print(f"📈 USO ATUAL: {usage_percent:.1f}%")
        
        if usage_percent > 80:
            print("🚨 ATENÇÃO: Uso de conexões acima de 80%!")
        
        print("\n🔍 DETALHES DAS CONEXÕES:")
        print("-" * 60)
        
        # Detalhes das conexões por aplicação
        cursor.execute("""
            SELECT 
                application_name,
                count(*) as connections,
                state
            FROM pg_stat_activity 
            WHERE datname = %s
            GROUP BY application_name, state
            ORDER BY connections DESC
        """, (os.getenv('DB_NAME', 'postgres'),))
        
        for row in cursor.fetchall():
            app_name, conn_count, state = row
            print(f"📱 {app_name or 'Unknown'}: {conn_count} conexões ({state})")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Erro ao conectar no banco: {e}")

if __name__ == "__main__":
    monitor_postgres_connections()