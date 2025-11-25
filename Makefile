# Makefile para Sistema ISP - Versão Completa com Monitoramento
SHELL:=/bin/bash
ARGS = $(filter-out $@,$(MAKECMDGOALS))
MAKEFLAGS += --silent
BASE_PATH=${PWD}
PYTHON_EXEC=python
DOCKER_COMPOSE_FILE=$(shell echo -f docker compose.yml)

# Cores para output
RED := \033[31m
GREEN := \033[32m
YELLOW := \033[33m
BLUE := \033[34m
MAGENTA := \033[35m
CYAN := \033[36m
WHITE := \033[37m
RESET := \033[0m

show_env:
	# Show wich DOCKER_COMPOSE_FILE and ENV the recipes will user
	# It should be referenced by all other recipes you want it to show.
	# It's only printed once even when more than a recipe executed uses it
	sh -c "if [ \"${ENV_PRINTED:-0}\" != \"1\" ]; \
	then \
		echo DOCKER_COMPOSE_FILE = \"${DOCKER_COMPOSE_FILE}\"; \
		echo OSFLAG = \"${OSFLAG}\"; \
	fi; \
	ENV_PRINTED=1;"

help: ## Mostrar esta ajuda
	@echo "$(CYAN)Sistema ISP - Comandos Disponíveis$(RESET)"
	@echo "============================================"
	@echo ""
	@echo "$(YELLOW)🚀 COMANDOS PRINCIPAIS:$(RESET)"
	@echo "$(GREEN)  make start$(RESET)          - Iniciar sistema completo (modo produção)"
	@echo "$(GREEN)  make quick-start$(RESET)    - Iniciar sistema rápido (desenvolvimento)"
	@echo "$(GREEN)  make stop$(RESET)           - Parar sistema completo"
	@echo "$(GREEN)  make restart$(RESET)        - Reiniciar sistema completo"
	@echo ""
	@echo "$(YELLOW)📊 MONITORAMENTO:$(RESET)"
	@echo "$(GREEN)  make status$(RESET)         - Status dos serviços"
	@echo "$(GREEN)  make health$(RESET)         - Verificar saúde dos serviços"
	@echo "$(GREEN)  make logs$(RESET)           - Ver logs do sistema"
	@echo "$(GREEN)  make logs-app$(RESET)       - Ver logs apenas da aplicação"
	@echo ""
	@echo "$(YELLOW)⏰ SCHEDULER:$(RESET)"
	@echo "$(GREEN)  make logs-scheduler$(RESET) - Ver logs do scheduler"
	@echo "$(GREEN)  make stop-scheduler$(RESET) - Parar scheduler"
	@echo "$(GREEN)  make start-scheduler$(RESET)- Iniciar scheduler"
	@echo "$(GREEN)  make manual-update$(RESET)  - Atualização manual completa"
	@echo ""
	@echo "$(YELLOW)🔧 DESENVOLVIMENTO:$(RESET)"
	@echo "$(GREEN)  make build$(RESET)          - Construir imagens Docker"
	@echo "$(GREEN)  make dev-restart$(RESET)    - Restart rápido (desenvolvimento)"
	@echo ""
	@echo "$(BLUE)💡 DICA: Use 'make start' para produção e 'make quick-start' para desenvolvimento$(RESET)"

# ==================== SISTEMA COMPLETO ====================

install: ## Instalar e configurar sistema completo
	@echo "$(BLUE)🚀 Instalando Sistema ISP...$(RESET)"
	@python start_system.py

start: show_env ## Iniciar sistema completo com monitoramento
	@echo "$(GREEN)🚀 Iniciando sistema completo...$(RESET)"
	@echo "$(BLUE)📋 Subindo serviços principais...$(RESET)"
	@docker compose -f docker compose.yml -f docker compose.security.yml -f docker compose.firewall.yml up -d
	@echo "$(YELLOW)⏳ Aguardando serviços inicializarem...$(RESET)"
	@sleep 15
	@echo "$(BLUE)📊 Verificando dados do sistema...$(RESET)"
	@make _check_initial_data
	@echo "$(CYAN)⏰ Iniciando scheduler automático...$(RESET)"
	@docker compose -f docker compose.scheduler.yml up -d
	@echo "$(GREEN)🎉 Sistema iniciado com sucesso!$(RESET)"
	@make _show_system_info

up: start ## Alias para start

quick-start: show_env ## Iniciar sistema rápido (sem scheduler, para desenvolvimento)
	@echo "$(GREEN)⚡ Iniciando sistema modo rápido...$(RESET)"
	@echo "$(BLUE)📋 Subindo apenas serviços principais...$(RESET)"
	@docker compose -f docker compose.yml -f docker compose.security.yml up -d
	@echo "$(YELLOW)⏳ Aguardando serviços básicos...$(RESET)"
	@sleep 10
	@echo "$(GREEN)✅ Sistema básico iniciado!$(RESET)"
	@make health

stop: show_env ## Parar sistema completo
	@echo "$(YELLOW)⏹️  Parando sistema completo...$(RESET)"
	@echo "$(YELLOW)📋 Parando serviços principais...$(RESET)"
	@docker compose -f docker compose.yml -f docker compose.security.yml -f docker compose.firewall.yml down
	@echo "$(YELLOW)⏰ Parando scheduler...$(RESET)"
	@docker compose -f docker compose.scheduler.yml down
	@echo "$(YELLOW)✅ Sistema completamente parado!$(RESET)"

restart: show_env ## Reiniciar sistema completo
	@echo "$(CYAN)🔄 Reiniciando sistema...$(RESET)"
	@make stop
	@sleep 3
	@make start

_rebuild: show_env ## Rebuild completo dos containers
	@echo "$(BLUE)🔨 Rebuild completo...$(RESET)"
	@docker compose ${DOCKER_COMPOSE_FILE} down
	@docker compose ${DOCKER_COMPOSE_FILE} build --no-cache --force-rm
	@make start

build: show_env ## Construir imagens Docker
	@echo "$(BLUE)🔨 Construindo imagens...$(RESET)"
	@docker compose ${DOCKER_COMPOSE_FILE} build --no-cache

# ==================== STATUS E LOGS ====================

status: show_env ## Mostrar status dos serviços
	@echo "$(CYAN)📊 Status dos serviços:$(RESET)"
	@docker compose ${DOCKER_COMPOSE_FILE} ps

logs: show_env ## Mostrar logs em tempo real
	@echo "$(CYAN)📋 Logs do sistema:$(RESET)"
	@docker compose ${DOCKER_COMPOSE_FILE} logs -f --tail 200

log: show_env ## Logs apenas da aplicação web
	@docker compose ${DOCKER_COMPOSE_FILE} logs -f --tail 200 web

logs-app: show_env ## Mostrar logs apenas da aplicação
	@echo "$(CYAN)📋 Logs da aplicação:$(RESET)"
	@docker compose ${DOCKER_COMPOSE_FILE} logs -f web rq_worker scheduler

logs-monitoring: show_env ## Mostrar logs do monitoramento
	@echo "$(CYAN)📋 Logs do monitoramento:$(RESET)"
	@docker compose ${DOCKER_COMPOSE_FILE} logs -f prometheus grafana alertmanager

logs-db: show_env ## Logs do banco de dados
	@docker compose ${DOCKER_COMPOSE_FILE} logs -f db

logs-redis: show_env ## Logs do Redis
	@docker compose ${DOCKER_COMPOSE_FILE} logs -f redis

# ==================== HEALTH CHECKS ====================

health: ## Verificar saúde dos serviços
	@echo "$(CYAN)🔍 Verificando saúde dos serviços...$(RESET)"
	@echo "$(WHITE)Aguardando serviços ficarem prontos...$(RESET)"
	@sleep 10
	@echo "$(GREEN)📱 Django App:$(RESET)"
	@curl -s http://localhost:8000/api/health/ | python -m json.tool 2>/dev/null || echo "❌ Não disponível"
	@echo "\n$(GREEN)📊 Prometheus:$(RESET)"
	@curl -s http://localhost:9090/-/healthy 2>/dev/null && echo "✅ Healthy" || echo "❌ Não disponível"
	@echo "$(GREEN)📈 Grafana:$(RESET)"
	@curl -s http://localhost:3000/api/health 2>/dev/null | python -m json.tool 2>/dev/null || echo "❌ Não disponível"

test-health: ## Testar todos os endpoints de health
	@echo "$(CYAN)🔍 Testando endpoints de saúde...$(RESET)"
	@echo "$(WHITE)Basic Health:$(RESET)"
	@curl -s http://localhost:8000/api/health/ | python -m json.tool
	@echo "\n$(WHITE)Detailed Health:$(RESET)"
	@curl -s http://localhost:8000/api/health/detailed/ | python -m json.tool
	@echo "\n$(WHITE)Readiness:$(RESET)"
	@curl -s http://localhost:8000/api/health/readiness/ | python -m json.tool
	@echo "\n$(WHITE)Liveness:$(RESET)"
	@curl -s http://localhost:8000/api/health/liveness/ | python -m json.tool

# ==================== DJANGO MANAGEMENT ====================

sh: show_env ## Shell do container web
	@docker compose ${DOCKER_COMPOSE_FILE} exec web bash

shell_plus: show_env ## Django shell_plus
	@docker compose ${DOCKER_COMPOSE_FILE} exec web ${PYTHON_EXEC} ./manage.py shell_plus

manage: show_env ## Executar comando Django manage.py
	@docker compose ${DOCKER_COMPOSE_FILE} exec web ${PYTHON_EXEC} manage.py ${ARGS}

migrate: show_env ## Executar migrações do banco
	@echo "$(BLUE)💾 Executando migrações...$(RESET)"
	@docker compose ${DOCKER_COMPOSE_FILE} exec web ${PYTHON_EXEC} manage.py migrate

makemigrations: show_env ## Criar migrações
	@docker compose ${DOCKER_COMPOSE_FILE} exec web ${PYTHON_EXEC} manage.py makemigrations ${ARGS}
	@docker compose ${DOCKER_COMPOSE_FILE} exec web ${PYTHON_EXEC} manage.py migrate

createsuperuser: show_env ## Criar superusuário
	@echo "$(BLUE)👤 Criando superusuário...$(RESET)"
	@docker compose ${DOCKER_COMPOSE_FILE} exec web ${PYTHON_EXEC} ./manage.py shell -c "from django.contrib.auth.models import User; User.objects.filter(username='admin').exists() or User.objects.create_superuser('admin', 'admin@localhost', 'admin123'); print('Superuser: admin/admin123')"

collectstatic: show_env ## Coletar arquivos estáticos
	@docker compose ${DOCKER_COMPOSE_FILE} exec web ${PYTHON_EXEC} manage.py collectstatic --no-input

# ==================== MONITORAMENTO ====================

urls: ## Mostrar URLs de acesso
	@echo "$(MAGENTA)🌐 URLs de Acesso:$(RESET)"
	@echo "$(WHITE)================================$(RESET)"
	@echo "$(GREEN)📱 Aplicação Principal:$(RESET)"
	@echo "  • Django:          http://localhost:8000"
	@echo "  • Admin:           http://localhost:8000/admin/ (admin/admin123)"
	@echo "  • API:             http://localhost:8000/api/"
	@echo "  • Health Check:    http://localhost:8000/api/health/"
	@echo ""
	@echo "$(GREEN)📊 Monitoramento:$(RESET)"
	@echo "  • Grafana:         http://localhost:3000/ (admin/admin123)"
	@echo "  • Prometheus:      http://localhost:9090/"
	@echo "  • Alertmanager:    http://localhost:9093/"
	@echo ""
	@echo "$(GREEN)📋 Métricas:$(RESET)"
	@echo "  • Métricas App:    http://localhost:8000/api/metrics/"
	@echo "  • Node Exporter:   http://localhost:9100/metrics"
	@echo "  • Redis Exporter:  http://localhost:9121/metrics"
	@echo "  • PG Exporter:     http://localhost:9187/metrics"

test-alerts: ## Testar sistema de alertas
	@echo "$(CYAN)🚨 Testando alertas...$(RESET)"
	@curl -X POST http://localhost:8000/api/alerts/test/ \
		-H "Content-Type: application/json" \
		-d '{"type": "test", "severity": "warning"}' | python -m json.tool

monitor: ## Abrir interface de monitoramento
	@echo "$(MAGENTA)📊 Abrindo interfaces de monitoramento...$(RESET)"
	@echo "Abrindo Grafana em: http://localhost:3000"
	@python -c "import webbrowser; webbrowser.open('http://localhost:3000')" 2>/dev/null || true

metrics: ## Mostrar métricas atuais
	@echo "$(CYAN)📊 Métricas atuais:$(RESET)"
	@curl -s http://localhost:8000/api/metrics/ | head -50

# ==================== BACKUP E RESTORE ====================

backup: show_env ## Fazer backup do banco de dados
	@echo "$(YELLOW)💾 Fazendo backup do banco...$(RESET)"
	@mkdir -p backups
	@docker compose ${DOCKER_COMPOSE_FILE} exec db pg_dump -U postgres postgres > backups/backup_$(shell date +%Y%m%d_%H%M%S).sql
	@echo "$(GREEN)✅ Backup salvo em backups/$(RESET)"

restore: show_env ## Restaurar backup do banco (use: make restore FILE=backup.sql)
	@echo "$(YELLOW)📥 Restaurando backup...$(RESET)"
	@docker compose ${DOCKER_COMPOSE_FILE} exec -T db psql -U postgres -d postgres < $(FILE)
	@echo "$(GREEN)✅ Backup restaurado!$(RESET)"

# ==================== LIMPEZA ====================

clean: show_env ## Limpar containers e imagens (PRESERVA VOLUMES DE DADOS)
	@echo "$(RED)🧹 Limpando sistema (PRESERVANDO DADOS)...$(RESET)"
	@echo "$(YELLOW)⚠️  Parando containers mas MANTENDO volumes de dados...$(RESET)"
	@docker compose ${DOCKER_COMPOSE_FILE} down
	@docker system prune -f
	@echo "$(GREEN)✅ Limpeza concluída! (Dados preservados)$(RESET)"

clean-all: show_env ## ⚠️ PERIGOSO: Limpar TUDO incluindo volumes de dados
	@echo "$(RED)⚠️ ⚠️ ⚠️  ATENÇÃO: ESTA OPERAÇÃO VAI APAGAR TODOS OS DADOS! ⚠️ ⚠️ ⚠️$(RESET)"
	@echo "$(RED)Pressione Ctrl+C nos próximos 10 segundos para cancelar...$(RESET)"
	@sleep 10
	@echo "$(RED)🧹 Limpando sistema INCLUINDO VOLUMES DE DADOS...$(RESET)"
	@docker compose ${DOCKER_COMPOSE_FILE} down -v
	@docker system prune -f
	@echo "$(GREEN)✅ Limpeza COMPLETA concluída! (TODOS OS DADOS FORAM PERDIDOS)$(RESET)"

clean-logs: ## Limpar logs antigos
	@echo "$(YELLOW)🧹 Limpando logs antigos...$(RESET)"
	@find logs/ -name "*.log.*" -mtime +7 -delete 2>/dev/null || true
	@echo "$(GREEN)✅ Logs limpos!$(RESET)"

chown_project: ## Corrigir permissões dos arquivos
	@sudo chown -R "${USER}:${USER}" ./

# ==================== DESENVOLVIMENTO ====================

dev-setup: ## Setup completo para desenvolvimento
	@echo "$(BLUE)🛠️  Configurando ambiente de desenvolvimento...$(RESET)"
	@make build
	@make start
	@sleep 20
	@make migrate
	@make createsuperuser
	@make health
	@make urls

dev-restart: show_env ## Restart rápido para desenvolvimento
	@docker compose ${DOCKER_COMPOSE_FILE} restart web rq_worker

test: show_env ## Executar testes
	@echo "$(BLUE)🧪 Executando testes...$(RESET)"
	@docker compose ${DOCKER_COMPOSE_FILE} exec web ${PYTHON_EXEC} manage.py test

# ==================== PRODUÇÃO ====================

production-check: ## Verificar configurações para produção
	@echo "$(RED)🔒 Verificando configurações de produção...$(RESET)"
	@echo "$(WHITE)Verificando .env...$(RESET)"
	@grep -q "DEBUG=False" .env && echo "✅ DEBUG=False" || echo "❌ DEBUG deve ser False"
	@grep -q "SECRET_KEY=" .env && echo "✅ SECRET_KEY configurado" || echo "❌ SECRET_KEY não configurado"
	@echo "$(WHITE)Verificando HTTPS...$(RESET)"
	@grep -q "SECURE_SSL_REDIRECT" .env && echo "✅ SSL configurado" || echo "⚠️  Configure SSL para produção"

# ==================== FUNÇÕES AUXILIARES ====================

_check_initial_data: ## Verificar e fazer atualização inicial se necessário
	@RECORD_COUNT=$$(docker compose exec -T web python manage.py shell -c "from olt.models import OltSystemStats; print(OltSystemStats.objects.count())" 2>/dev/null | tail -1 | tr -d '\r\n'); \
	if [ -z "$$RECORD_COUNT" ] || [ "$$RECORD_COUNT" -lt "1" ]; then \
		echo "$(YELLOW)🔄 Nenhum dado encontrado, fazendo atualização inicial COMPLETA...$(RESET)"; \
		echo "$(YELLOW)   (Isso pode levar alguns minutos - ONUs, Clientes, Portas, OLT...)$(RESET)"; \
		docker compose exec web python manage.py collect_olt_periodic --once; \
	else \
		echo "$(GREEN)✅ Dados do sistema encontrados: $$RECORD_COUNT registros da OLT$(RESET)"; \
	fi

_show_system_info: ## Mostrar informações do sistema após inicialização
	@echo ""
	@echo "$(CYAN)📊 Status dos serviços principais:$(RESET)"
	@docker compose ps
	@echo ""
	@echo "$(CYAN)⚡ Status do scheduler:$(RESET)"
	@docker compose -f docker compose.scheduler.yml ps
	@echo ""
	@echo "$(GREEN)🔗 Acessos disponíveis:$(RESET)"
	@echo "$(WHITE)   🖥️  Dashboard OLT: http://localhost:8000$(RESET)"
	@echo "$(WHITE)   📊 Grafana: http://localhost:3000 (admin/admin)$(RESET)"
	@echo "$(WHITE)   🔍 Prometheus: http://localhost:9090$(RESET)"
	@echo ""
	@echo "$(GREEN)📋 Funcionalidades ativas:$(RESET)"
	@echo "$(WHITE)   ✅ Atualização automática COMPLETA: A cada 1 hora$(RESET)"
	@echo "$(WHITE)   ✅ Inclui: ONUs, Clientes, Portas, Dados OLT, MACs$(RESET)"
	@echo "$(WHITE)   ✅ Gráficos de performance: CPU e memória$(RESET)"
	@echo "$(WHITE)   ✅ Histórico: 7 dias de dados$(RESET)"
	@echo "$(WHITE)   ✅ Dashboard otimizado: Sem coleta automática$(RESET)"
	@echo ""
	@echo "$(BLUE)🛠  Comandos úteis:$(RESET)"
	@echo "$(WHITE)   Ver logs scheduler: make logs-scheduler$(RESET)"
	@echo "$(WHITE)   Atualização manual completa: make manual-update$(RESET)"
	@echo "$(WHITE)   Parar scheduler: make stop-scheduler$(RESET)"

# ==================== COMANDOS AUXILIARES ====================

logs-scheduler: ## Ver logs do scheduler
	@docker compose -f docker compose.scheduler.yml logs -f

manual-update: ## Executar atualização manual completa
	@echo "$(BLUE)🔄 Executando atualização manual completa...$(RESET)"
	@docker compose exec web python manage.py collect_olt_periodic --once

stop-scheduler: ## Parar apenas o scheduler
	@echo "$(YELLOW)⏸️  Parando scheduler...$(RESET)"
	@docker compose -f docker compose.scheduler.yml down

start-scheduler: ## Iniciar apenas o scheduler
	@echo "$(GREEN)▶️  Iniciando scheduler...$(RESET)"
	@docker compose -f docker compose.scheduler.yml up -d

restart-scheduler: ## Reiniciar apenas o scheduler
	@make stop-scheduler
	@sleep 2
	@make start-scheduler

# ==================== ALIASES ====================

down: stop ## Alias para stop
ps: status ## Alias para status
rebuild: _rebuild ## Alias para _rebuild

# Default target
.DEFAULT_GOAL := help