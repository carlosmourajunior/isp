# ISP OLT Management System - AI Coding Instructions

## System Architecture Overview

This is a Django-based ISP management system for Optical Line Terminal (OLT) equipment, handling fiber optic network monitoring. The system manages ONUs (Optical Network Units), OLT system data, alarms, and provides REST APIs with real-time monitoring capabilities.

### Core Components
- **Django Web Application** (`olt/` app) - Main business logic
- **OLT Connector** (`olt/utils.py`) - Telnet/SSH communication with physical OLT hardware via netmiko
- **Background Tasks** - Redis/RQ for async OLT data collection
- **Monitoring Stack** - Prometheus, Grafana, AlertManager (via docker-compose files)
- **Security Layer** - IP whitelisting, JWT auth, frontend-only decorators

## Critical Architecture Patterns

### OLT Hardware Integration
- **Connection**: Uses `olt_connector()` class in `olt/utils.py` for telnet/SSH to physical OLT equipment
- **Data Models**: `ONU`, `OltSystemInfo`, `OltSlot`, `OltTemperature`, `OltAlarm` represent physical hardware state
- **Commands**: OLT commands are sent via netmiko, parsed with regex, stored in PostgreSQL
- **Security**: Direct OLT access restricted by `@frontend_only` and `@olt_admin_required` decorators

### Background Task System
```python
# Queue tasks using django-rq
from django_rq import get_queue
queue = get_queue('default')
job = queue.enqueue(comprehensive_update_task, user="admin", timeout=3600)
```
- Tasks in `olt/tasks.py` handle long-running OLT operations
- APScheduler (`olt/scheduler.py`) manages periodic updates (currently disabled for security)
- Job metadata tracks user, timing, progress via `job.meta`

### API Security Model
```python
# Security decorators for OLT endpoints
@frontend_only  # Only allows internal/Docker network access
@olt_admin_required  # Requires staff/superuser permissions
def update_olt_system_data(request):
```
- IP whitelisting in middleware (`isp/middleware.py`) and decorators
- JWT authentication for API access
- Frontend-only restrictions for direct OLT operations

## Development Workflows

### Container Management
```bash
# Use Makefile for all operations
make start     # Start full system with monitoring
make logs      # Follow all container logs  
make health    # Check service health
make rebuild   # Full rebuild with --no-cache
```

### OLT Data Collection Patterns
```python
# Manual collection via API (admin only)
POST /api/olt/update-system-data/

# Background task pattern
from olt.tasks import comprehensive_update_task
queue.enqueue(comprehensive_update_task, user="System")

# Direct connector usage (for debugging)
connector = olt_connector()
connector.update_all_ports()  # Collect ONU data
connector.collect_all_alarms()  # Parse alarm outputs
```

### Testing Approach
- Use `test_*.py` scripts that setup Django environment first
- Manual API testing via `test_api.py`, `test_parsing.py`
- No formal test framework - relies on integration testing against real OLT hardware

## Project-Specific Conventions

### File Organization
- `olt/api_views.py` - REST API endpoints with heavy filtering/pagination
- `olt/utils.py` - Core OLT connector class (400+ lines)
- `docker-compose*.yml` - Multiple compose files for different deployment scenarios
- `manage_ips*.ps1` - PowerShell scripts for IP management
- `*_secure.sh` - Security-focused deployment scripts

### Environment Configuration
- `.env` file drives all configuration
- Multiple docker-compose files for different security/monitoring profiles
- Settings in `isp/settings.py` use IP whitelists and security middleware stack

### Data Flow Patterns
1. **OLT → Connector → Models → API** - Physical hardware data flows through telnet parsing
2. **Frontend → API → Task Queue → OLT** - User actions trigger background OLT operations
3. **Scheduler → Tasks → Database** - Periodic collection (disabled by default)

### Error Handling
- Extensive logging in `olt/utils.py` for OLT connection failures
- Prometheus metrics collection for monitoring
- Health check endpoints in `olt/health_views.py`

## Integration Points

### External Dependencies
- **Physical OLT Hardware** - Accessed via telnet/SSH using netmiko library
- **PostgreSQL** - Primary data store, connection monitoring in multiple scripts
- **Redis** - Task queue and caching, health monitored
- **Prometheus/Grafana** - Metrics collection via custom middleware

### Cross-Service Communication
- Docker network isolation with selective port exposure
- Internal APIs use JWT tokens with IP restrictions
- Background tasks communicate via Redis queues
- Monitoring stack scrapes metrics from Django app

### Key Commands for Development

```bash
# Setup and run
make install  # Initial setup
make start    # Start all services

# Debugging
make logs-app     # Application logs only
python test_api.py    # Manual API testing
python debug_parsing.py  # Test OLT parsing

# Database operations  
./backup_scripts/backup_database.sh    # Backup DB
./backup_scripts/restore_database.sh   # Restore DB
```

This system requires understanding physical fiber optic networking concepts (ONUs, PONs, optical power levels) and real-time hardware monitoring patterns.