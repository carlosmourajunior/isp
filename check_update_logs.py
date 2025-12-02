#!/usr/bin/env python
"""
Check SystemUpdateLog entries
"""

import os
import sys
import django

# Setup Django environment
if __name__ == "__main__":
    # Add the project directory to the path
    project_dir = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, project_dir)
    
    # Setup Django settings
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'isp.settings')
    django.setup()

from olt.models import SystemUpdateLog

def check_logs():
    """Check all SystemUpdateLog entries"""
    print("=" * 60)
    print("📋 SYSTEMUPDATELOG ENTRIES")
    print("=" * 60)
    
    logs = SystemUpdateLog.objects.all().order_by('iniciado_em')
    if logs:
        for log in logs:
            print(f"{log.iniciado_em} | {log.tipo_atualizacao} | {log.status} | {log.usuario}")
    else:
        print("No logs found")
        
    print(f"\nTotal: {logs.count()} logs")

if __name__ == "__main__":
    check_logs()